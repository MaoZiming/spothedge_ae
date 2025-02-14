import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Patch
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

# Purples.
colors = list(reversed(sns.color_palette("ch:2.5,+.2,dark=.3")))[:2]
colors = sns.color_palette("ch:2.5,+.2,dark=.3")[:2]
darker_purple = colors[-1]
light_purple = colors[0]
light_blue = "#a2d4ec"
set2 = sns.color_palette("Set2")
paired = sns.color_palette("Paired")
cost_demand = 3

plt.rcParams['font.family'] = 'FreeSans'  # or any other installed font


###############

RESEARCH = 1  # For research presentation.
# RESEARCH = 0  # For paper pdf.

# font_size = {0: 10, 1: 8}[RESEARCH]
# font_size = 6.5  # Manual fix for 1-full-col figures.
font_size = 12  # Manual fix for 0.5-full-col figures.
TEXT_USETEX = bool(1 - RESEARCH)

# Get from LaTeX using "The column width is: \the\columnwidth"
vldb_col_width_pt = 240
icml_col_width_pt = 234.8775
sigmod20_col_width_pt = 241.14749
vldb21_col_width_pt = 241.14749
nsdi23_col_width_pt = 241.02039

fig_width_pt = nsdi23_col_width_pt

inches_per_pt = 1.0 / 72.27  # Convert pt to inch
golden_mean = (np.sqrt(5) - 1.0) / 2.0  # Aesthetic ratio


def FigWidth(pt):
    return pt * inches_per_pt  # width in inches


fig_width = FigWidth(fig_width_pt)  # width in inches
fig_height = fig_width * golden_mean  # height in inches
fig_size = [fig_width, fig_height]


def InitMatplotlib(font_size, title_size=9):
    print("use_tex", TEXT_USETEX, "\nfont_size", font_size, "\ntitle_size", title_size)
    # https://matplotlib.org/3.2.1/tutorials/introductory/customizing.html
    params = {
        "backend": "ps",
        "figure.figsize": fig_size,
        "text.usetex": TEXT_USETEX,
        # 'font.family': 'serif',
        # 'font.serif': ['Times'],
        # 'font.family': 'sans-serif',
        # "font.sans-serif": [
        #     # 'Lato',
        #     # 'DejaVu Sans', 'Bitstream Vera Sans',
        #     # 'Computer Modern Sans Serif', 'Lucida Grande', 'Verdana', 'Geneva',
        #     # 'Lucid',
        #     # 'Arial',
        #     "Helvetica",
        #     "Avant Garde",
        #     "sans-serif",
        # ],
        # Make math fonts (e.g., tick labels) sans-serif.
        # https://stackoverflow.com/a/20709149/1165051
        "text.latex.preamble": "\n".join(
            [
                r"\usepackage{siunitx}",  # i need upright \micro symbols, but you need...
                r"\sisetup{detect-all}",  # ...this to force siunitx to actually use your fonts
                r"\usepackage{helvet}",  # set the normal font here
                r"\usepackage{sansmath}",  # load up the sansmath so that math -> helvet
                r"\sansmath",  # <- tricky! -- gotta actually tell tex to use!
            ]
        ),
        # axes.titlesize      : large   # fontsize of the axes title
        # 'axes.titlesize': font_size,
        "axes.titlesize": title_size,  # For plt.title().
        # 'axes.labelsize': 7,
        # 'legend.fontsize': 7,
        # 'font.size': 7,
        # 'xtick.labelsize': 7,
        # 'ytick.labelsize': 7,
        "xtick.labelsize": font_size,
        "ytick.labelsize": font_size,
        "axes.labelsize": font_size,
        "legend.fontsize": font_size,
        "font.size": font_size,
        "legend.fancybox": False,
        "legend.framealpha": 1.0,
        "legend.edgecolor": "0.1",  # ~black border.
        "legend.shadow": False,
        "legend.frameon": False,
        "xtick.direction": "in",
        "ytick.direction": "in",
        # http://phyletica.org/matplotlib-fonts/
        # Important for cam-ready (otherwise some fonts are not embedded):
        "pdf.fonttype": 42,
        "lines.linewidth": 1,
        # Styling.
        # 'grid.color': '#dedddd',
        # 'grid.linewidth': .5,
        # 'axes.grid.axis': 'y',
        "xtick.bottom": False,
        "xtick.top": False,
        "ytick.left": False,
        "ytick.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": True,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.axisbelow": True,
    }

    # plt.style.use("seaborn-colorblind")
    plt.rcParams.update(params)
    # 


def PlotCdf(data, label=None, bins=2000, **kwargs):
    counts, bin_edges = np.histogram(data, bins=bins)
    cdf = np.cumsum(counts)
    plt.plot(bin_edges[1:], cdf / cdf[-1], label=label, lw=2, **kwargs)


def get_df_from_files():
    folder_path = "../results/"  # Replace with the path to your folder
    target_columns = [
        "target_num_instances",
        "overprovision_num",
        "total_time_period",
        "cold_start_delay",
        "num_repeats",
        "trace_addr",
        "spot_policy",
        "time_tick_in_seconds",
        "workload",
        "autoscaler",
        "fallback_policy",
        "availability",
        "cost",
        "node_hist",
        "p50",
        "p90",
        "p99",
        "p999",
        "latency_list",
        "repeat_idx",
    ]

    # Initialize an empty DataFrame
    df = pd.DataFrame(columns=target_columns)

    # Loop through each file in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith(".jsonl"):
            file_path = os.path.join(folder_path, filename)

            # Read the JSONL file
            with open(file_path, "r") as file:
                for line in file:
                    content_json = json.loads(line)
                    # Add a new row to the DataFrame
                    row_data = {
                        column: content_json.get(column, None)
                        for column in target_columns
                    }
                    df = pd.concat([df, pd.DataFrame([row_data])], ignore_index=True)
                    # df = df.append(row_data, ignore_index=True)
    return df


def add_bar_annotations(ax, errors=None, value_precision=4, error_precision=4):
    for i, p in enumerate(ax.patches):
        height = p.get_height()
        error_value = ""
        if error_precision is not None:
            error_value = (
                f" ± {errors[i]:.{error_precision}f}" if errors is not None else ""
            )
        annotation = f"{height:.{value_precision}f}{error_value}"
        ax.annotate(
            annotation,
            (p.get_x() + p.get_width() / 2, height),
            ha="center",
            va="bottom",
            xytext=(0, 5),
            textcoords="offset points",
        )


def set_axis_trace_label(ax, trace):
    if trace == "4-node":
        ax.set_xlabel("AWS 1")
    elif trace == "16-node":
        ax.set_xlabel("AWS 2")
    elif trace == "2-month":
        ax.set_xlabel("AWS 3")
    elif trace == "a100":
        ax.set_xlabel("GCP 1")


def format_y_ticks(value, _):
    return f"{value:.1f}"  # Two decimal places


def format_figure_and_legend(fig, names, ncol=4):
    # Create custom legend elements
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="White", edgecolor=get_color(names[i], i), label=names[i])
        for i in range(len(names))
    ]
    fig.legend(
        handles=legend_elements,
        title="",
        loc="upper center",
        ncol=ncol,
        columnspacing=0.3,
        bbox_to_anchor=(0.5, 1.2),
    )

    fig.tight_layout(pad=0.3)


def format_axises_for_sensitivity(ax1, ax2, i, names, trace, data, right_axis_label):
    ax1.set_xticklabels([""] * len(names))
    set_axis_trace_label(ax1, trace)
    ax1.set_ylabel("")

    ax2.set_xticklabels([""] * len(names))
    set_axis_trace_label(ax2, trace)
    ax2.set_ylabel("")
    if i != 0:
        ax1.set_yticklabels([""] * len(ax1.get_yticklabels()))
        ax1.tick_params(axis="y", which="both", length=0)

    if i != len(data.keys()) - 1:
        ax2.set_yticklabels([""] * len(ax2.get_yticklabels()))
        ax2.tick_params(axis="y", which="both", length=0)
    for spine in ax1.spines.values():
        spine.set_visible(False)
    for spine in ax2.spines.values():
        spine.set_visible(False)

    ax2.yaxis.grid(False)
    if i == 0:
        ax1.set_ylabel("$C$ relative to OD (\%)")
        ax1.tick_params(axis="y", which="both", length=0)
    if i == len(data.keys()) - 1:
        ax2.set_ylabel(right_axis_label)
        ax2.tick_params(axis="y", which="both", length=0)
        ax2.yaxis.set_major_formatter(FuncFormatter(format_y_ticks))


patterns = ("++", "xx", "//", "..")
colors = ["royalblue", "orange", "green", "Red"]
medianprops = {"solid_capstyle": "butt", "color": "red"}
meanprops = dict(
    marker="v", markerfacecolor="r", linestyle="none", markeredgecolor="b", markersize=3
)

# order = [
#     "ES",
#     "RR",
#     "OD",
#     "OD+",
#     "SpotHedge w/o S",
#     "SpotHedge",
#     "Optimal",
# ]

order = [
    "Even Spread",
    "Round Robin",
    "On-demand",
    "SpotHedge",
    "SkyServe",
    "Optimal",
    "OnDemand",
]

palette = sns.color_palette("colorblind", n_colors=10)
strategy_to_colors = {
    "OD": palette[0],
    "ES": palette[1],
    "RR": palette[2],
    "DP": palette[3],
    "SpotHedge": palette[4],
    "SkyServe": palette[4],
    "ES + F": palette[5],
    "OD+": palette[6],
    "SpotHedge w/o S": palette[9],
    "Optimal": palette[7],
}

strategy_to_colors = {
    "On-demand": palette[0],
    "Even Spread": palette[1],
    "Round Robin": palette[2],
    "DP": palette[3],
    "SpotHedge": palette[4],
    "SkyServe": palette[4],
    "ES + F": palette[5],
    "OD+": palette[6],
    "SpotHedge w/o S": palette[9],
    "Optimal": palette[7],
}


def get_color(strategy, i=-1):
    # print(strategy)
    if strategy in strategy_to_colors:
        return strategy_to_colors[strategy]
    else:
        # print(strategy)
        # return 'black
        return palette[i]


def update_policy_name(policy, spot_policy, num_overprovision):
    if policy == "SpotHedge":
        if spot_policy == "SpotFailover":
            policy = "SpotHedge w/ S"
        elif spot_policy == "SpotFailoverNoSafety":
            policy = "SpotHedge"
            policy = "SkyServe"
        else:
            return None
    elif policy == "NaiveSpread":
        policy = "Even Spread"
    elif policy == "OnDemand":
        policy = "On-demand"
    elif policy == "RoundRobin":
        policy = "Round Robin"
    return policy


def format_axes_for_box_plot(ax, ax2, i):
    ax.set_xticklabels([""] * len(ax.get_xticklabels()))
    ax2.set_xticklabels([""] * len(ax2.get_xticklabels()))
    ax2.set_xlabel(f"Trace {i+1}")
    ax2.set_ylabel("")
    if i != 0:
        ax.set_yticklabels([""] * len(ax.get_yticklabels()))
        ax.tick_params(axis="y", which="both", length=0)
        ax2.set_yticklabels([""] * len(ax2.get_yticklabels()))
        ax2.tick_params(axis="y", which="both", length=0)

    # Hide all spines for ax1
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Hide all spines for ax2
    for spine in ax2.spines.values():
        spine.set_visible(False)


def calculate_service_score(node_hist, base):
    service_score = 0
    num_time = 0
    for num_node in node_hist:
        num_time += int(node_hist[num_node])
        service_score += int(node_hist[num_node]) * int(num_node)

    if num_time == 0:
        return 0

    return service_score / int(base) / num_time


trace_to_name = {
    "4-node": "AWS 1",
    "16-node": "AWS 2",
    "2-month": "AWS 3",
    "a100": "GCP 1",
}
