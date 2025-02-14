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
    
    # Data for stacked bars
    categories = ["Send Traffic\nto Worker", "Worker\nCompute", "Receive\nResponse"]
    # times = [0.21, 2.01, 0.05]
    times = [0.21, 2.0, 0.05]
    
    plt.figure(figsize=[fig_width * 0.8, fig_height], dpi=400)
    ax = plt.gca()
    
    # Create stacked bar
    bottom = 0
    colors = sns.color_palette("deep", n_colors=3)
    bars = []
    for i, (time, color) in enumerate(zip(times, colors)):
        bar = ax.bar(0.5, time, bottom=bottom, width=0.5, color=color) # Increased width from 0.15 to 0.3
        bottom += time
        bars.append(bar)
    
    # Add arrows pointing to different parts of the bar with categories text
    total = sum(times)
    offset = bottom / 10
    hs = [offset, 0, -offset]
    bottom = 0
    for i, (category, time) in enumerate(zip(categories, times)):
        height = time / 2 + bottom
        plt.annotate(f"{category}",
                    xy=(0.5, height),
                    xytext=(1.5, height + hs[i]),
                    ha='center',
                    va='bottom',
                    color='black',
                    arrowprops=dict(arrowstyle='->'))
        plt.annotate(f"({time:.2g}s)",
                    xy=(1.5, height + hs[i]),
                    xytext=(1.5, height + hs[i] - 0.05),
                    ha='center',
                    va='top',
                    color='royalblue')
        bottom += time
    
    # Adjust plot
    plt.xlim(0, 2)  # Make space for annotation
    plt.ylim(0, total * 1.1)
    plt.xticks([])  # Remove x-axis ticks
    plt.ylabel("Time (s)")
    
    fn = "pic/fig-6-a.pdf"
    plt.savefig(fn, format="pdf", bbox_inches="tight")
    print(f"Figure 6(a) saved to {fn}")


def draw_cross_region_latency():
    raw_data = [
        ["0.341", "101.681", "124.096", "137.122"],
        ["101.614", "0.250", "221.576", "200.108"],
        ["124.156", "221.539", "0.269", "256.260"],
        ["137.121", "200.145", "256.468", "0.304"],
    ]
    data = raw_data
    data = np.array(data, dtype=float)
    regions = ["us", "eu", "asia", "sa"]
    FONT_SIZE = 14

    sns.set()
    plt.figure(figsize=(5, 4))

    sns.heatmap(
        data,
        annot=True,
        annot_kws={"size": FONT_SIZE},
        fmt=".1f",
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
