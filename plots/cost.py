from plot import *

sns.set_style('whitegrid')
InitMatplotlib(7, 7)
df = get_df_from_files()
traces = ['4-node', '16-node', '2-month', 'a100']
data = {}

for trace_addr in traces:
    
    plot_condition = ((df['overprovision_num'] <= 1) & 
                    (df['target_num_instances'] == 3) &
                    (df['workload'] == 'Poisson') &
                    (df['total_time_period'] == 2880) &
                    (df['num_repeats'] == 10) &
                    (df['cold_start_delay'] == 4) & 
                    (df['trace_addr'] == trace_addr) &
                    (df['fallback_policy'] != 'SpotFailover'))
    
    df_copy = df[plot_condition]
    data[trace_addr] = []
    
    max_cost = 0
    for index, row in df_copy.iterrows():
        spot_policy = row['spot_policy']
        fallback_policy = row['fallback_policy']
        overprovision_num = row['overprovision_num']
        policy = update_policy_name(spot_policy, fallback_policy, overprovision_num)
        if policy == 'SpotHedge' and overprovision_num != 1:
            continue
        if policy == 'SkyServe' and overprovision_num != 1:
            continue
        if policy == 'On-demand' and overprovision_num != 0:
            continue
        if policy == 'Optimal' and overprovision_num != 0:
            continue
        
        cost = row['cost']
        max_cost = max(cost, max_cost)
        data[trace_addr].append((policy, cost))
        
    for i, (policy, cost) in enumerate(data[trace_addr]):
        data[trace_addr][i] = (policy, cost / max_cost)
            
num_trace_groups = len(data)
fig = plt.figure(figsize=(fig_width + 0.3 , fig_height - 0.7), dpi=300)
axes = fig.subplots(1, num_trace_groups,
                    sharex=True,
                    sharey=True,
                    )

for i, trace in enumerate(data.keys()):
    
    ax = axes[i]
    names = sorted(list(set([t[0] for t in data[trace]])), key=lambda x: order.index(x))
    # names = [name for name in names if name != "On-demand"]

    if not names:
        continue

    availability_mean = [100 * np.mean([t[1] for t in data[trace] if t[0] == name]) for name in names]
    availability_std = [100 * np.std([t[1] for t in data[trace] if t[0] == name]) for name in names]
    

    palette = [get_color(name) for name in names]
    
    sns.barplot(x=names, y=availability_mean, ax=ax, palette=palette, width=1)
    ax.errorbar(x=names, y=availability_mean, yerr=availability_std, fmt='none', ecolor='black', capsize=2, alpha=0.3)
    add_bar_annotations(ax, availability_std, value_precision=0, error_precision=None)

    ax.set_xticklabels([''] * len(names))
    set_axis_trace_label(ax, trace)

    ax.set_ylabel('')
    # ax.set_ylim(0, 70) # Needed

    
    if i == 0:
        ax.set_ylabel('Relative Cost (%)')
        ax.tick_params(axis='y', which='both', length=0)

        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=get_color(names[i], i), edgecolor="white", label=names[i])
            for i in range(len(names))
        ]
        fig.legend(
            handles=legend_elements,
            title="",
            loc="upper center",
            ncol=3,
            columnspacing=0.3,
            bbox_to_anchor=(0.5, 1.25),
        )

        fig.tight_layout(pad=0.3)

plt.savefig(f'figures/cost.pdf', bbox_inches='tight')

