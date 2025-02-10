import collections
import json
import os
import re

import seaborn as sns

from plot import *

exps = [
    "spot-hedge",
    "aws-autoscaling-mixed",
    "aws-autoscaling-pure-spot",
    "mark",
]
zones = ["us-central1-a", "asia-northeast1-a", "europe-west4-a"]

avail_groups = {
    "available": ["f4", "f7"],
    "volatile": ["f6", "f5"],
}

SPOT_SERVE_EXP_NAME = "spot-serve"
SPOT_SERVE_GENERATED_TRACE_DIR = "ts_generated_trace"


def _get_figure_name_in_paper(spot_avail: str, replica: str, is_latency: bool):
    if is_latency:
        subfigure = "a" if spot_avail == "available" else "b"
    else:
        subfigure = "c" if spot_avail == "available" else "d"
    figure_num = 9 if replica == "vllm" else 13
    return f"Figure {figure_num}({subfigure})", f"pic/fig-{figure_num}-{subfigure}.pdf"


def main(spot_avail: str, replica: str):
    groups_to_draw = avail_groups[spot_avail]
    use_spot_serve = replica == "spot-serve"
    if use_spot_serve:
        exps.append(SPOT_SERVE_EXP_NAME)
    FAILED_THRESHOLD_SECONDS = 20 if use_spot_serve else 100

    exp2latencies = collections.defaultdict(list)
    exp2failure = collections.defaultdict(int)
    exp2total = collections.defaultdict(int)
    exp2processed = collections.defaultdict(list)
    exp2client_start = {exp: float("inf") for exp in exps}
    exp2client_end = {exp: 0 for exp in exps}

    def _prepare_spot_serve_one_slice(exp, group, slice_idx):
        """Get the latencies of spot serve from a single slice."""
        dirname = f"{exp}_{group}_s{slice_idx}"
        inf_log = f"workdir/spot_serve_result/{dirname}/inference_service.log"
        with open(inf_log, "r") as f:
            for l in f.readlines():
                res = re.search(r"Request (\d+) arrival .* latency: (\d+\.\d+),", l)
                if res is None:
                    continue
                latency = float(res.group(2)) / 1000
                rid = int(res.group(1))
                yield rid, latency

    def _get_spot_serve_data(exp, group, id2lat):
        tot = 0
        exp_name_to_use = exp
        with open(
            f"workdir/{SPOT_SERVE_GENERATED_TRACE_DIR}/{exp}_{group}_requests.txt", "r"
        ) as f:
            for l in f.readlines():
                rid, tstamp = l.split(",")
                rid = int(rid)
                tstamp = float(tstamp)
                exp2total[exp_name_to_use] += 1
                tot += 1
                if rid in id2lat and id2lat[rid] < FAILED_THRESHOLD_SECONDS:
                    exp2latencies[exp_name_to_use].append(id2lat[rid])
                else:
                    exp2failure[exp_name_to_use] += 1
        return tot

    def _spot_serve_prepare_zone(exp, group):
        if group in exp2processed[exp]:
            return
        exp2processed[exp].append(group)
        with open(
            f"workdir/{SPOT_SERVE_GENERATED_TRACE_DIR}/{exp}_{group}_traces.json", "r"
        ) as f:
            traces_data = json.load(f)
            start_hour = float("inf")
            end_hour = 0
            id2lat = {}
            for trace in traces_data:
                start_hour = min(start_hour, trace["start"])
                end_hour = max(end_hour, trace["end"])
                if not trace["is_zero_trace"]:
                    id2lat_slice = _prepare_spot_serve_one_slice(
                        exp, group, trace["index"]
                    )
                    id2lat.update(id2lat_slice)
            assert start_hour < end_hour
            _get_spot_serve_data(exp, group, id2lat)

    def _prepare_zone(group, zone):
        failed = set()
        for exp in exps:
            if exp == SPOT_SERVE_EXP_NAME:
                _spot_serve_prepare_zone("mark", group)
                continue
            if use_spot_serve:
                _spot_serve_prepare_zone(exp, group)
                continue
            with open(f"client_data/{group}/{zone}/{exp}/latencies.jsonl", "r") as f:
                start_ts = float("inf")
                end_ts = 0
                for l in f.readlines():
                    exp2total[exp] += 1
                    data = json.loads(l)
                    start_ts = min(start_ts, data["start_time"])
                    end_ts = max(end_ts, data["start_time"])
                    if data["is_failed"]:
                        if data["is_failed"] not in failed:
                            failed.add(data["is_failed"])
                        exp2failure[exp] += 1
                    else:
                        exp2latencies[exp].append(data["latency"])
                exp2client_start[exp] = min(exp2client_start[exp], start_ts)
                exp2client_end[exp] = max(exp2client_end[exp], end_ts)

    for group in groups_to_draw:
        for zone in zones:
            _prepare_zone(group, zone)

    frs = [exp2failure[exp] / exp2total[exp] for exp in exp2total.keys()]

    def _get_tag(exp: str):
        alias = {
            "spot-hedge": "Sky\nServe",
            "mark": "MArk",
            "aws-autoscaling-mixed": "ASG",
            "aws-autoscaling-pure-spot": "AWS\nSpot",
            SPOT_SERVE_EXP_NAME: "Spot\nServe",
        }
        return alias[exp]

    medianprops = {"solid_capstyle": "butt", "color": "red"}
    meanprops = dict(
        marker="v",
        markerfacecolor="r",
        linestyle="none",
        markeredgecolor="b",
        markersize=3,
    )

    def draw_separate():
        InitMatplotlib(11, 7)
        sns.set_style("whitegrid")
        fw = fig_width
        palette = sns.color_palette("husl")
        palette = [palette[i] for i in [3, 1, 0, 5]]
        fig0, ax0 = plt.subplots(figsize=((fig_width), fig_height), dpi=300)
        for i, (exp, latencies) in enumerate(exp2latencies.items()):
            latencies_new = latencies[:]
            latencies_new += [FAILED_THRESHOLD_SECONDS] * exp2failure[exp]
            tag = _get_tag(exp)

            def _boxplot(ax):
                tags = [tag] * len(latencies_new)
                sns.boxplot(
                    x=tags,
                    y=latencies_new,
                    ax=ax,
                    palette=palette[i : i + 1],
                    whis=(10, 90),
                    showfliers=False,
                    showmeans=True,
                    meanprops=meanprops,
                    widths=0.7,
                    patch_artist=True,
                    # boxprops=dict(facecolor="white", edgecolor=palette[i]),
                    boxprops=dict(facecolor="white", edgecolor="black"),
                    medianprops=medianprops,
                    hue=tags,
                    legend=False,
                )

            if exp != SPOT_SERVE_EXP_NAME:
                _boxplot(ax0)

        def _apply_attrs(ax):
            ax.set_ylim(0, FAILED_THRESHOLD_SECONDS * 1.05)
            ax.set_ylabel("Latency (s)", fontsize=font_size)
            ax.tick_params(axis="y")
            tick_vals = [
                v * FAILED_THRESHOLD_SECONDS for v in [0, 0.2, 0.4, 0.6, 0.8, 1]
            ]
            tick_labs = [f"{int(v)}" for v in tick_vals]
            ax.set_yticks(tick_vals, tick_labs)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(False)

        _apply_attrs(ax0)
        fig0.tight_layout()
        figure_name, fn = _get_figure_name_in_paper(
            spot_avail, replica, is_latency=True
        )
        fig0.savefig(fn, bbox_inches="tight")
        print(f"{figure_name} saved to {fn}")
        fig2, ax2 = plt.subplots(figsize=((fw), fig_height), dpi=300)
        tags = [_get_tag(exp) for exp in exp2latencies.keys()]
        sns.barplot(
            x=tags,
            y=frs,
            label="Failure Rate",
            palette=palette,
            edgecolor="black",
            linewidth=1,
            hue=tags,
            legend=False,
        )
        ax2.tick_params(axis="y")
        tick_vals = [0, 0.2, 0.4, 0.6, 0.8, 1]
        tick_labs = [f"{int(v * 100)}%" for v in tick_vals]
        plt.yticks(tick_vals, tick_labs)
        ax2.set_ylim(0, 1)
        ax2.set_ylabel("Failure Rate", fontsize=font_size)

        for p in ax2.patches:
            height = p.get_height()
            width = p.get_width()
            label = f"{height * 100:.2g}%"
            ax2.text(p.get_x() + width / 2, height, label, ha="center", va="bottom")

        ax2.spines["right"].set_visible(False)
        ax2.spines["left"].set_visible(False)
        plt.tight_layout()
        figure_name, fn = _get_figure_name_in_paper(
            spot_avail, replica, is_latency=False
        )
        fig2.savefig(fn, bbox_inches="tight")
        print(f"{figure_name} saved to {fn}")

    draw_separate()


if __name__ == "__main__":
    spot_avail_choices = ["available", "volatile"]
    replica_choices = ["vllm", "spot-serve"]
    os.makedirs("pic", exist_ok=True)
    for replica in replica_choices:
        for spot_avail in spot_avail_choices:
            main(spot_avail, replica)
