from plot import *

sns.set_style('whitegrid')
InitMatplotlib(7, 7)
df = get_df_from_files()
cost_diff_list = []
p50_diff_list = []
p90_diff_list = []
p99_diff_list = []
traces = ['4-node', '16-node', '2-month', 'a100']

for workload in ['Poisson', 'Arena', 'MAF']:
    data = {}
    for trace_addr in traces:
        plot_condition = ((df['overprovision_num'] == 1) & 
                        (df['target_num_instances'] == 3) &
                        (df['total_time_period'] == 2880) &
                        (df['workload'] == workload) &
                        (df['num_repeats'] == 10) &
                        (df['cold_start_delay'] == 4) & 
                        (df['trace_addr'] == trace_addr) &
                        (df['fallback_policy'] != 'SpotFailover'))
        df_copy = df[plot_condition]
        data[trace_addr] = []
        for index, row in df_copy.iterrows():
            spot_policy = row['spot_policy']
            fallback_policy = row['fallback_policy']
            overprovision_num = row['overprovision_num']
            policy = update_policy_name(spot_policy, fallback_policy, overprovision_num)
            if policy == 'SpotHedge' and overprovision_num != 1:
                continue
            if policy == 'On-demand':
                continue
            normalized_cost = row['cost'] / row['total_time_period'] / row['target_num_instances'] / cost_demand
            latency_list = row['latency_list']
            
            # if policy == 'SpotHedge' or policy == 'On-demand':
            #     print(policy, workload, workload, row["p99"])
            data[trace_addr].append((policy, latency_list, normalized_cost))

    fig = plt.figure(figsize=(fig_width - 0.3 , fig_height - 1), dpi=300)
    axes = fig.subplots(1, len(traces), squeeze=True)

    bps = []
    
    def flatten_2D_list(list_2d):
        return [item for sublist in list_2d for item in sublist]
    
    for i, trace in enumerate(data.keys()):
        ax = axes[i]
        names = sorted(list(set([t[0] for t in data[trace]])), key=lambda x: order.index(x))
        if not names:
            continue
        costs_mean = [100 * np.mean([t[2] for t in data[trace] if t[0] == name]) for name in names]
        costs_std = [100 * np.std([t[2] for t in data[trace] if t[0] == name]) for name in names]
        value_list_list = [flatten_2D_list([t[1] for t in data[trace] if t[0] == name]) for name in names]
        positions = list(range(1, len(names) + 1))
        palette = [get_color(name) for name in names]
        
        average_list = [sum(value_list) / len(value_list) for value_list in value_list_list]
        print([v / average_list[3] for v in average_list])
        print(names)

        bp = ax.boxplot(value_list_list, positions=positions, labels=names, whis=(10, 90), showfliers=False, showmeans=True, meanprops=meanprops, widths=0.7, patch_artist=True, boxprops=dict(facecolor="white"), medianprops=medianprops)
        bps.append(bp)
        ax.set_xticklabels([""] * len(ax.get_xticklabels()))
        if i != 0:
            ax.set_yticklabels([""] * len(ax.get_yticklabels()))
            ax.tick_params(axis="y", which="both", length=0)
        
        if trace == "4-node":
            ax.set_xlabel("AWS 1")
        elif trace == "16-node":
            ax.set_xlabel("AWS 2")
        elif trace == "2-month":
            ax.set_xlabel("AWS 3")
        elif trace == "a100":
            ax.set_xlabel("GCP 1")
            
        ax.set_ylim(10, 110)

    axes[0].set_ylabel('Latency (s)')
    axes[0].tick_params(axis='y', which='both', length=0)
    for bp in bps:
        boxes = bp['boxes']
        idx = 0
        for box, _ in zip(boxes, boxes):
            if idx >= len(palette):
                break
            box.set_edgecolor(palette[idx])
            idx += 1
    
    legend_elements = [
        Patch(facecolor="White", edgecolor=get_color(names[i], i), label=names[i])
        for i in range(len(names))
    ]
    fig.legend(
        handles=legend_elements,
        title="",
        loc="upper center",
        ncol=2,
        columnspacing=0.3,
        bbox_to_anchor=(0.5, 1.2),
    )
    plt.savefig(f'figures/latency-box-{workload}.pdf', bbox_inches='tight')
    plt.show()
