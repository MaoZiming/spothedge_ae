import base64
import collections
import json
import logging
import os
import pickle
from typing import Generator, Tuple

from matplotlib.patches import Patch

from plot import *

logging.getLogger("fontTools.subset").setLevel(logging.WARNING)

exps = [
    "spot-hedge",
    "aws-autoscaling-mixed",
    "aws-autoscaling-pure-spot",
    "mark",
]
zones = ["us-central1-a", "asia-northeast1-a", "europe-west4-a"]

USE_T4_COST = False

# NOTE: From catalog on May 7, 2024, at the time when experiment was conducted.
# As the spot price changes across time, we use a fixed price to guarantee reproducibility.
# See https://raw.githubusercontent.com/skypilot-org/skypilot-catalog/f8c68c784da8507bdeeffbea27fd818c495b8f97/catalogs/v5/aws/vms.csv
catalog = {
    "eu-central-1c": {"g5.48xlarge": {True: 4.9409}, "g4dn.12xlarge": {True: 1.1791}},
    "eu-central-1b": {"g5.48xlarge": {True: 4.5375}, "g4dn.12xlarge": {True: 1.5586}},
    "us-east-2a": {
        "g5.48xlarge": {False: 16.288, True: 2.9589},
        "g4dn.12xlarge": {False: 3.912, True: 2.0353},
    },
    "us-east-2b": {
        "g5.48xlarge": {True: 2.7112, False: 16.288},
        "g4dn.12xlarge": {True: 1.977, False: 3.912},
    },
    "us-east-2c": {"g5.48xlarge": {True: 2.9866}, "g4dn.12xlarge": {True: 2.1002}},
    "us-west-2b": {
        "g5.48xlarge": {True: 3.686, False: 16.288},
        "g4dn.12xlarge": {True: 1.54, False: 3.912},
    },
    "us-west-2a": {"g5.48xlarge": {True: 4.2402}, "g4dn.12xlarge": {True: 1.4449}},
    "us-west-2c": {
        "g5.48xlarge": {True: 4.9078, False: 16.288},
        "g4dn.12xlarge": {True: 1.5957, False: 3.912},
    },
    "eu-west-2b": {"g5.48xlarge": {True: 6.4523}, "g4dn.12xlarge": {True: 1.6327}},
    "eu-west-2a": {"g5.48xlarge": {True: 6.8373}, "g4dn.12xlarge": {True: 1.6632}},
    "eu-central-1a": {"g5.48xlarge": {True: 4.6387}, "g4dn.12xlarge": {True: 1.4809}},
}


def get_price_per_hour(zone: str, use_spot: bool, instance_type=None) -> float:
    if instance_type is None:
        if USE_T4_COST:
            instance_type = "g4dn.12xlarge"  # T4:4
        else:
            instance_type = "g5.48xlarge"  # A10G:8
    return catalog[zone][instance_type][use_spot]


def get_data(group: str, exp: str) -> Generator[Tuple[int, int, int], None, None]:
    """
    Yield (time, #spot, #spot_total, #ondemand, spot_price, ondemand_price)
    """
    dpath = f"data/{group}/"
    if exp == "mark":
        calc_spot_active = False
        with open(f"{dpath}{exp}.jsonl", "r") as f:
            for l in f:
                try:
                    data = json.loads(l)
                except json.JSONDecodeError:
                    print(f"json decode error for\n{l}")
                    continue
                try:
                    spot_price_uw2 = get_price_per_hour(
                        zone="us-west-2c", use_spot=True
                    )
                    active_cnt = 0
                    for stat in data["node_status"]:
                        if stat["status"] == "active":
                            active_cnt += 1
                    price = (
                        len(data["node_status"]) * spot_price_uw2
                        if not calc_spot_active
                        else active_cnt * spot_price_uw2
                    )
                    yield data["time"], active_cnt, len(
                        data["node_status"]
                    ), 0, price, 0
                except:
                    # new data format
                    active_cnt = len(data["instance_info"])
                    total_price = 0
                    active_instance_ids = {
                        info["ins_id"] for info in data["instance_info"]
                    }
                    total_cnt = 0
                    all_ins_id_visited = set()
                    for infos in data["sfr_info"].values():
                        ress = infos["ins_infos"]["Reservations"]
                        if not ress:
                            continue
                        for res in ress:
                            inss = res["Instances"]
                            if not inss:
                                continue
                            for ins in inss:
                                if ins["State"]["Name"] not in [
                                    "running",
                                    "shutting-down",
                                ]:
                                    continue
                                if ins["InstanceId"] in all_ins_id_visited:
                                    continue
                                all_ins_id_visited.add(ins["InstanceId"])
                                total_cnt += 1
                                zone = ins["Placement"]["AvailabilityZone"]
                                if (
                                    not calc_spot_active
                                    or ins["InstanceId"] in active_instance_ids
                                ):
                                    total_price += get_price_per_hour(zone, True)
                    yield data["time"], active_cnt, total_cnt, 0, total_price, 0
    elif exp.replace("_", "-").startswith("spot-hedge"):
        use_od_override = exp.endswith("od")
        if use_od_override:
            exp = "spot-hedge"
        active_status = ["READY"]
        all_spot_status = active_status + ["PROVISIONING", "STARTING"]
        with open(f"{dpath}{exp}.jsonl") as f:
            for l in f:
                try:
                    data = json.loads(l)
                except json.JSONDecodeError:
                    print(f"json decode error for\n{l}")
                    continue
                spot_active_cnt = 0
                spot_cnt = 0
                ondemand_active_cnt = 0
                spot_price = 0
                ondemand_price = 0
                spot_zones = []
                for info in data["replica_info"]:
                    if info["status"] in all_spot_status:
                        cr = info.get("cluster_record")
                        if cr is None:
                            raise ValueError(f"Invalid info {info}")
                        cr = pickle.loads(base64.b64decode(cr.encode()))
                        if cr is None:
                            # Not ready cluster. Handle as 0 cost.
                            zone = None
                        else:
                            zone = cr["handle"].launched_resources.zone
                        if info["is_spot"]:
                            spot_zones.append(zone)
                            if info["status"] in active_status:
                                spot_active_cnt += 1
                            else:
                                spot_cnt += 1
                            if zone is not None:
                                spot_price += get_price_per_hour(
                                    zone, True and not use_od_override
                                )
                        else:
                            ondemand_active_cnt += 1
                            if zone is not None:
                                ondemand_price += get_price_per_hour(zone, False)
                yield (
                    data["time"],
                    spot_active_cnt,
                    spot_cnt,
                    ondemand_active_cnt,
                    spot_price,
                    ondemand_price,
                )
    elif exp.replace("_", "-").startswith("aws-autoscaling"):
        use_od_override = exp.endswith("od")
        if use_od_override:
            exp = "aws-autoscaling-mixed"
        ins_id_to_life_cycle = {}
        if group == "f4":
            with open(f"{dpath}{exp}.jsonl") as f:
                for l in f:
                    try:
                        data = json.loads(l)
                    except json.JSONDecodeError:
                        print(f"json decode error for\n{l}")
                        continue
                    for ins_id, cycle in data["total"]:
                        ins_id_to_life_cycle[ins_id] = cycle == "spot"
        with open(f"{dpath}{exp}.jsonl") as f:
            for l in f:
                try:
                    data = json.loads(l)
                except json.JSONDecodeError:
                    print(f"json decode error for\n{l}")
                    continue
                spot_healthy_cnt = 0
                od_cnt = 0
                spot_cnt = 0
                spot_price = 0
                ondemand_price = 0
                for _, cycle in data["healthy"]:
                    if cycle == "spot":
                        spot_healthy_cnt += 1
                    else:
                        assert cycle is None
                if group == "f4":

                    def _find_is_spot_in_total(ins_id: str) -> bool:
                        if ins_id in ins_id_to_life_cycle:
                            return ins_id_to_life_cycle[ins_id]
                        return True

                    total_in_asg = data["asg"]["AutoScalingGroups"][0]["Instances"]
                    for ins in total_in_asg:
                        is_spot = _find_is_spot_in_total(ins["InstanceId"])
                        if is_spot:
                            spot_cnt += 1
                            spot_price += get_price_per_hour(
                                ins["AvailabilityZone"], True and not use_od_override
                            )
                        else:
                            od_cnt += 1
                            ondemand_price += get_price_per_hour(
                                ins["AvailabilityZone"], False
                            )
                else:
                    # new data format
                    ins_detail_ress_asg = (
                        data["asg"].get("instance_details", {}).get("Reservations", [])
                    )
                    total_detail_inss = []
                    for reservation in ins_detail_ress_asg:
                        total_detail_inss.extend(reservation["Instances"])
                    if "total_details" in data:
                        ins_detail_ress_total = data["total_details"]["Reservations"]
                        for reservation in ins_detail_ress_total:
                            total_detail_inss.extend(reservation["Instances"])
                    all_ins_id_visited = set()
                    for ins in total_detail_inss:
                        if ins["InstanceId"] in all_ins_id_visited:
                            continue
                        all_ins_id_visited.add(ins["InstanceId"])
                        if ins["State"]["Name"] not in ["running", "shutting-down"]:
                            # Not gonna cost
                            continue
                        zone = ins["Placement"]["AvailabilityZone"]
                        if "InstanceLifecycle" in ins:
                            assert ins["InstanceLifecycle"] == "spot"
                            spot_cnt += 1
                            spot_price += get_price_per_hour(
                                zone, True and not use_od_override
                            )
                        else:
                            od_cnt += 1
                            ondemand_price += get_price_per_hour(zone, False)
                yield (
                    data["time"],
                    spot_healthy_cnt,
                    spot_cnt,
                    od_cnt,
                    spot_price,
                    ondemand_price,
                )
    else:
        raise ValueError(f"Unknown experiment: {exp}")


InitMatplotlib(11, 7)
sns.set_style("whitegrid")
palette = sns.color_palette("colorblind", n_colors=10)

name2style = {
    "total": "-",
    "spot": "-",
    "spot_total": "-.",
    "on_demand": "-",
}

name2color = {
    "total": "#617580",
    "spot": (0.0, 0.4470588235294118, 0.6980392156862745),
    "spot_total": "#807661",
    "on_demand": (0.0, 0.6196078431372549, 0.45098039215686275),
}

namealias = {
    "total": "Total",
    "spot": "Spot",
    "spot_total": "Spot Total",
    "on_demand": "On-demand",
}


def main(all_group, aggregate_groups=True, use_t4_cost=False):
    with_spot_total = not aggregate_groups
    global USE_T4_COST
    USE_T4_COST = use_t4_cost

    if aggregate_groups:
        timestamp_lims = {group: (float("inf"), 0) for group in all_group}
    else:
        assert len(all_group) == 1
        group_name = all_group[0]
        timestamp_lims = {group_name: (float("inf"), 0)}

    num_node_lims = {group: 0 for group in all_group}

    def prepare_lims(group: str, exp: str):
        times = []
        num_nodes = []
        num_tot_nodes = []
        for ti, nspot, nspottot, nod, _, _ in get_data(group, exp):
            times.append(ti)
            num_nodes.append(nspot + nod)
            num_tot_nodes.append(nspottot + nod)
        nonlocal timestamp_lims, num_node_lims
        timestamp_lims[group] = (
            min(timestamp_lims[group][0], times[0]),
            max(timestamp_lims[group][1], times[-1]),
        )
        if with_spot_total:
            num_node_lims[group] = max(num_node_lims[group], max(num_tot_nodes))
        else:
            num_node_lims[group] = max(num_node_lims[group], max(num_nodes))

    exp2price = {}

    def _get_tag(exp: str):
        alias = {
            "spot-hedge": "Spot\nHedge",
            "mark": "MArk",
            "aws-autoscaling-mixed": "ASG",
            "aws-autoscaling-pure-spot": "AWS\nSpot",
            "aws-autoscaling-od": "OD",
            "spot-hedge-od": "OD",
        }
        return alias[exp]

    group_and_exp_to_data = collections.defaultdict(dict)
    group_and_exp_to_x_min = collections.defaultdict(dict)
    group_and_exp_to_x_max = collections.defaultdict(dict)
    group_to_elapsed = collections.defaultdict(int)

    def draw_exp(group: str, exp: str, prepare_only: bool = False):
        times = []
        num_spot = []
        num_spot_total = []
        num_ondemand = []
        num_total = []
        total_spot_price = 0
        total_ondemand_price = 0
        for (ti, nspot, nspottot, nod, spot_price, ondemand_price) in get_data(
            group, exp
        ):
            if times:
                total_spot_price += spot_price * (ti - times[-1]) / 3600
                total_ondemand_price += ondemand_price * (ti - times[-1]) / 3600
            times.append(ti)
            num_spot.append(nspot)
            num_spot_total.append(nspottot)
            num_ondemand.append(nod)
            num_total.append(nspot + nod)
        group_to_elapsed[group] = times[-1] - times[0]
        if exp.endswith("od"):
            total_spot_price, total_ondemand_price = (
                0,
                total_spot_price + total_ondemand_price,
            )
        if exp not in exp2price:
            exp2price[exp] = (total_spot_price, total_ondemand_price)
        else:
            exp2price[exp] = (
                exp2price[exp][0] + total_spot_price,
                exp2price[exp][1] + total_ondemand_price,
            )
        min_ti, max_ti = timestamp_lims[group]
        group_and_exp_to_x_min[exp][group] = min_ti
        group_and_exp_to_x_max[exp][group] = max_ti
        times = [t - min_ti for t in times]
        times = [t / 3600 for t in times]
        xlim = (0, (max_ti - min_ti) / 3600)
        xlabel = "Relative Time (hours)"
        data_to_use = {}
        for name, value in zip(
            ["total", "spot", "spot_total", "on_demand"],
            [num_total, num_spot, num_spot_total, num_ondemand],
        ):
            if not with_spot_total:
                if name == "spot_total":
                    continue
            if name == "total":
                continue
            if exp in ["aws-autoscaling-pure-spot", "mark"] and name in [
                "on_demand",
                "total",
            ]:
                # Skip ondemand and total for pure spot deployments
                continue
            data_to_use[name] = times, value
        group_and_exp_to_data[exp][group] = data_to_use
        if prepare_only:
            return
        fig = plt.figure(figsize=((fig_width), fig_height), dpi=300)
        ax_to_use = plt.gca()
        legend_elements = []
        for name, (xaxis, yaxis) in data_to_use.items():
            style = (
                "-"
                if exp in ["aws-autoscaling-pure-spot", "mark"]
                else name2style[name]
            )
            linewidth = 1.5 if not aggregate_groups else 1
            sns.lineplot(
                x=xaxis,
                y=yaxis,
                label=name,
                linestyle=style,
                color=name2color[name],
                linewidth=linewidth,
                ax=ax_to_use,
            )
            label = namealias[name]
            if exp in ["aws-autoscaling-pure-spot", "mark"]:
                convert_if_show_spot_total = {
                    "Spot": "Ready Spot",
                    "Spot Total": "Requested Spot",
                }
                if with_spot_total and label in convert_if_show_spot_total:
                    label = convert_if_show_spot_total[label]
            legend_elements.append(
                Patch(facecolor="White", edgecolor=name2color[name], label=label)
            )

        ax_to_use.set_xlim(*xlim)
        ax_to_use.set_xticks(np.arange(np.floor(xlim[0]), np.ceil(xlim[1]), 2))
        if aggregate_groups:
            ax_to_use.set_xticks([])
        ylim = (-0.1, num_node_lims[group] + 0.1)
        ax_to_use.set_ylim(*ylim)
        step = 1 if aggregate_groups else 2
        ax_to_use.set_yticks(np.arange(0, np.ceil(ylim[1]), step))

        if aggregate_groups:
            ax_to_use.legend().set_visible(False)
            ax_to_use.tick_params(
                axis="x", which="both", bottom=False, top=False, labelbottom=False
            )
            ax_to_use.tick_params(axis="y", which="both", left=False, labelleft=False)
            if all_group.index(group) == 0:
                ax_to_use.set_ylabel(_get_tag(exp), fontsize=font_size)
        if not aggregate_groups:
            ax_to_use.set_xlabel(xlabel, fontsize=font_size)
            ax_to_use.set_ylabel("Number of Replicas", fontsize=font_size)
            fig.legend(
                handles=legend_elements,
                loc="upper center",
                bbox_to_anchor=(0.52, 1.05),
                ncol=4,
            )
            ax_to_use.legend().set_visible(False)
        if not aggregate_groups:
            if with_spot_total and not aggregate_groups:
                is_awsspot = exp == "aws-autoscaling-pure-spot" and group == "f4"
                is_mark = exp == "mark" and group == "f5"
                if is_awsspot or is_mark:
                    subfigure = "a" if is_mark else "b"
                    fn = f"pic/fig-11-{subfigure}.pdf"
                    fig.savefig(fn, bbox_inches="tight")
                    print(f"Figure 11({subfigure}) saved to {fn}")

    def calc_min_x_from_client_data(exp):
        min_x = float("inf")

        def _prepare_zone(group, zone):
            nonlocal min_x
            with open(f"client_data/{group}/{zone}/{exp}/latencies.jsonl", "r") as f:
                for l in f.readlines():
                    data = json.loads(l)
                    min_x = min(min_x, data["start_time"])

        for zone in zones:
            for group in all_group:
                _prepare_zone(group, zone)

        return min_x

    def prepare_od_cost_from_client(od_exp_name):
        # Use spot hedge client data here; all of them should be the same.
        exp = "spot-hedge"
        window = 60
        for group in all_group:
            req_times = list()
            for zone in zones:
                with open(
                    f"client_data/{group}/{zone}/{exp}/latencies.jsonl", "r"
                ) as f:
                    for l in f.readlines():
                        data = json.loads(l)
                        req_times.append(data["start_time"])
            req_times = sorted(req_times)
            min_ti = group_and_exp_to_x_min["spot-hedge"][group]
            max_ti = group_and_exp_to_x_max["spot-hedge"][group]
            while req_times[0] < min_ti:
                req_times.pop(0)
            while req_times[-1] > max_ti:
                req_times.pop(-1)
            window2numreq = collections.defaultdict(int)
            for t in req_times:
                window2numreq[(t - min_ti) // window] += 1
            tot_num_window = int((max_ti - min_ti) // window)
            od_cost = 0
            for window_idx in range(tot_num_window):
                v = window2numreq[window_idx]
                rps = v / window
                desired_num_od = rps / 0.2
                if group == "f4":
                    desired_num_od = min(desired_num_od, 5)
                    desired_num_od = max(desired_num_od, 2)
                else:
                    desired_num_od = min(desired_num_od, 3)
                    desired_num_od = max(desired_num_od, 1)
                od_cost += (
                    get_price_per_hour("us-west-2c", False)
                    / 3600
                    * desired_num_od
                    * window
                )
            if od_exp_name not in exp2price:
                exp2price[od_exp_name] = 0, 0
            exp2price[od_exp_name] = 0, exp2price[od_exp_name][1] + od_cost

    def draw_merge_into_one_plot():
        fig_w = fig_width * 1.3
        fig_h = fig_height
        fig_merged, axes_merged = plt.subplots(
            len([e for e in exps]), 1, figsize=(fig_w, fig_h), dpi=300
        )
        all_names = set()
        for exp in exps:
            ax_to_use = axes_merged[exps.index(exp)]
            name_to_data = {}
            for group in sorted(
                group_and_exp_to_data[exp].keys(), key=lambda x: int(x[1:])
            ):
                data = group_and_exp_to_data[exp][group]
                for name, (xaxis, yaxis) in data.items():
                    all_names.add(name)
                    if name not in name_to_data:
                        name_to_data[name] = ([], [])
                    if name_to_data[name][0]:
                        prev_end = name_to_data[name][0][-1]
                        xaxis = [x + prev_end + 0 for x in xaxis]
                        if name == "spot":
                            ax_to_use.axvline(
                                x=prev_end + 0.02,
                                color="grey",
                                linestyle="--",
                                linewidth=1,
                            )
                    if group == "f4":
                        len_to_keep = len(xaxis) * 0.48
                        len_to_keep = int(len_to_keep)
                        xaxis = xaxis[:len_to_keep]
                        yaxis = yaxis[:len_to_keep]
                    name_to_data[name][0].extend(xaxis)
                    name_to_data[name][1].extend(yaxis)
                    linewidth = 1
                    sns.lineplot(
                        x=xaxis,
                        y=yaxis,
                        label=name,
                        linestyle=name2style[name],
                        color=name2color[name],
                        linewidth=linewidth,
                        ax=ax_to_use,
                    )
            min_x, max_x = 0, float("inf")
            min_y, max_y = 0, 0
            for name, (all_xaxis, all_yaxis) in name_to_data.items():
                min_x = max(min_x, all_xaxis[0])
                max_x = min(max_x, all_xaxis[-1])
                min_y = max(min_y, min(all_yaxis))
                max_y = max(max_y, max(all_yaxis))
            min_x_in_client = calc_min_x_from_client_data(exp)
            min_x_ori = group_and_exp_to_x_min[exp][group]
            min_x = (min_x_in_client - min_x_ori) / 3600
            min_x = max(min_x, 0)
            ax_to_use.set_xlim(min_x, max_x)
            ylim = ax_to_use.get_ylim()
            expand = 0.2
            ylim = (-expand, 8 + expand)
            ax_to_use.set_ylim(*ylim)
            ax_to_use.set_xticks([])
            ax_to_use.set_yticks([])
            ax_to_use.legend().set_visible(False)
            ax_to_use.xaxis.grid(False)
            ax_to_use.yaxis.grid(False)
            ax_to_use.set_ylabel(_get_tag(exp), fontsize=font_size)
        legend_elements = []
        for name in ["on_demand", "spot"]:
            label = namealias[name]
            legend_elements.append(
                Patch(
                    facecolor="White",
                    edgecolor=name2color[name],
                    label=label,
                    linestyle=name2style[name],
                )
            )
        fig_merged.legend(
            handles=legend_elements,
            loc="upper center",
            bbox_to_anchor=(0.5, 1.03),
            ncol=3,
        )
        assert len(all_group) == 1
        subfigure = "a" if all_group[0] == "f4" else "b"
        fn = f"pic/fig-10-{subfigure}.pdf"
        fig_merged.savefig(fn, bbox_inches="tight")
        print(f"Figure 10({subfigure}) saved to {fn}")

    OD_EXP_NAME = "spot-hedge-od"

    def draw_cost(plot_percentage: bool = False):
        fw = fig_width
        fig, ax = plt.subplots(figsize=((fw), fig_height), dpi=300)
        od_costs = [exp2price[exp][1] for exp in exp2price.keys() if exp != OD_EXP_NAME]
        spot_costs = [
            exp2price[exp][0] for exp in exp2price.keys() if exp != OD_EXP_NAME
        ]
        if plot_percentage:
            max_costs = exp2price[OD_EXP_NAME][1]
            od_costs = [cost / max_costs for cost in od_costs]
            spot_costs = [cost / max_costs for cost in spot_costs]
        parsed_exps = [_get_tag(exp) for exp in exp2price.keys() if exp != OD_EXP_NAME]
        ax.bar(
            parsed_exps,
            od_costs,
            label="On-demand",
            bottom=spot_costs,
            color=name2color["on_demand"],
        )

        for i, p in enumerate(ax.patches):
            height = od_costs[i] + spot_costs[i]
            width = p.get_width()
            if plot_percentage:
                label = f"{height:.1%}"
            else:
                label = f"{int(height)}"
            ax.text(p.get_x() + width / 2, height, label, ha="center", va="bottom")

        ax.bar(parsed_exps, spot_costs, label="Spot", color=name2color["spot"])
        if plot_percentage:
            ax.set_ylabel("Cost (%)", fontsize=font_size)
            yticks = [0, 0.2, 0.4, 0.6, 0.8, 1]
            ytick_labs = [f"{int(v * 100)}%" for v in yticks]
            ax.set_yticks(yticks)
            ax.set_yticklabels(ytick_labs)
        else:
            ax.set_ylabel("Cost (\$)", fontsize=font_size)
        if USE_T4_COST:
            # for T4:4
            if not (aggregate_groups and all_group == ["f5", "f6"]):
                ax.legend(frameon=True, fontsize="x-small", bbox_to_anchor=(0.547, 0.5))
            else:
                ax.legend(frameon=True, fontsize="x-small")
        else:
            # for A10G:8
            if not (aggregate_groups and all_group == ["f5", "f6"]):
                ax.legend(frameon=True, fontsize="x-small", bbox_to_anchor=(0.72, 0.65))
            else:
                ax.legend(frameon=True, fontsize="x-small")
        ax.grid(visible=False, axis="x")
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        plt.tight_layout()
        figure_num = 12 if USE_T4_COST else 9
        subfigure = "e" if all_group == ["f4", "f7"] else "f"
        fn = f"pic/fig-{figure_num}-{subfigure}.pdf"
        fig.savefig(fn, bbox_inches="tight")
        print(f"Figure {figure_num}({subfigure}) saved to {fn}")

    def draw():
        for exp in exps:
            if aggregate_groups:
                for group in all_group:
                    prepare_lims(group, exp)
            else:
                prepare_lims(group_name, exp)
        if aggregate_groups:
            for exp in exps:
                for group in all_group:
                    draw_exp(group, exp, prepare_only=True)
            if len(all_group) == 1:
                draw_merge_into_one_plot()
        else:
            for exp in exps:
                draw_exp(group_name, exp)
        if aggregate_groups and len(all_group) > 1:
            prepare_od_cost_from_client(OD_EXP_NAME)
            draw_cost(plot_percentage=True)

    draw()


if __name__ == "__main__":
    os.makedirs("pic", exist_ok=True)

    # cost, vllm
    main(["f4", "f7"], use_t4_cost=False)
    main(["f5", "f6"], use_t4_cost=False)

    # num node to time
    main(["f4"])
    main(["f6"])

    # spot total
    main(["f5"], aggregate_groups=False)
    main(["f4"], aggregate_groups=False)

    # cost, spot serve
    main(["f4", "f7"], use_t4_cost=True)
    main(["f5", "f6"], use_t4_cost=True)
