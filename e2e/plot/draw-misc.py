import logging
import os

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from plot import *

logging.getLogger("fontTools").setLevel(logging.CRITICAL)


def draw_latency_breakdown():
    sns.set_palette("colorblind")
    InitMatplotlib(9)
    times = [0.04 + 0.17, 2.01, 0.05]
    categories = ["Send Traffic\nto Worker", "Worker\nCompute", "Receive\nResponse"]

    plt.figure(figsize=[fig_width, fig_height], dpi=400)
    ax = sns.barplot(
        x=categories, y=times, palette="viridis", hue=categories, legend=False
    )
    for p in ax.patches:
        ax.annotate(
            f"{p.get_height():.2f}s",
            (p.get_x() + p.get_width() / 2.0, p.get_height()),
            ha="center",
            va="top",
            xytext=(0, 9),
            textcoords="offset points",
        )
    plt.ylabel("Time (sec)")

    fn = "pic/fig-6-a.pdf"
    plt.savefig(fn, format="pdf", bbox_inches="tight")
    print(f"Figure 6(a) saved to {fn}")


def draw_cross_region_latency():
    data = [
        ["0.341", "101.681", "124.096", "137.122"],
        ["101.614", "0.250", "221.576", "200.108"],
        ["124.156", "221.539", "0.269", "256.260"],
        ["137.121", "200.145", "256.468", "0.304"],
    ]
    data = np.array(data, dtype=float)
    regions = ["us", "eu", "asia", "sa"]
    FONT_SIZE = 14

    sns.set()
    plt.figure(figsize=(5, 4))
    import matplotlib.figure

    matplotlib.figure.Figure.colorbar
    sns.heatmap(
        data,
        annot=True,
        annot_kws={"size": FONT_SIZE},
        fmt=".2f",
        linewidths=0.5,
        square=True,
        cbar_kws={"format": "%.0fms"},
        xticklabels=regions,
        yticklabels=regions,
        cmap="rocket_r",
    )

    plt.tight_layout(pad=2.0)
    plt.xticks(rotation=45, ha="right", fontsize=FONT_SIZE)
    plt.yticks(rotation=0, fontsize=FONT_SIZE)
    fn = "pic/fig-6-b.pdf"
    plt.savefig(fn)
    print(f"Figure 6(b) saved to {fn}")


if __name__ == "__main__":
    os.makedirs("pic", exist_ok=True)
    draw_latency_breakdown()
    draw_cross_region_latency()
