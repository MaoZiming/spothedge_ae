from plot import *

sns.set_style('whitegrid')
InitMatplotlib(7, 7)
df = get_df_from_files()

data = {}
traces = ['2-month']

for trace_addr in traces:
    plot_condition = ((df['overprovision_num'] == 1) & 
                    (df['target_num_instances'] == 3) &
                    (df['spot_policy'] == 'SpotHedge') & 
                    (df['fallback_policy'] == 'SpotFailoverNoSafety') &
                    (df['workload'] == 'Poisson') &
                    (df['num_repeats'] == 5) &
                    (df['trace_addr'] == trace_addr))
    
    data[trace_addr] = []
    df_copy = df[plot_condition]
    names = set()
    for index, row in df_copy.iterrows():
        latency_list = row['latency_list']
        
        cold_start_delay = row['cold_start_delay']
        name = f'$d$={cold_start_delay/2}mins'
        if name in names:
            continue
        print(name, trace_addr, row['p99'])
        names.add(name)
        data[trace_addr].append((name, latency_list))
               
fig = plt.figure(figsize=(fig_width - 1.5, fig_height - 1), dpi=300)
axes = fig.subplots(1, len(traces), sharex=True, sharey=True)
for i, trace in enumerate(data.keys()):
    ax = axes
    data[trace] = sorted(data[trace], key=lambda x: x[0])
    names = [t[0] for t in data[trace]]
    if not names:
        continue
    
    value_list_list = [pair[1] for pair in data[trace]]
    positions = list(range(1, len(names) + 1))

    bp = ax.boxplot(value_list_list, positions=positions, labels=names, whis=(10, 99), showfliers=False, showmeans=True, meanprops=meanprops, widths=0.6, patch_artist=True, boxprops=dict(facecolor="white"), medianprops=medianprops)

    boxes = bp['boxes']
    idx = 0
    for box, _ in zip(boxes, boxes):
        if idx >= len(palette):
            break
        box.set_edgecolor(palette[idx])
        idx += 1
        
    # ax2 = ax.twinx()
    # sns.scatterplot(x=names, y=p99_means, ax=ax2, palette=palette, color='red')

    # ax2.set_ylim(1, 3)
    # format_axises_for_sensitivity(ax, ax2, i, names, trace, data, 'P90 Latency (s)')

    ax.set_xticklabels([""] * len(names))
    set_axis_trace_label(ax, trace)
    ax.set_ylabel("")
    # ax.set_ylim(0, 16)

    # ax.set_ylim(10, 50)

    if i != 0:
        ax.set_yticklabels([""] * len(ax.get_yticklabels()))
        ax.tick_params(axis="y", which="both", length=0)

    ax.set_xticklabels([1, 2, 3, 4])
    ax.set_xlabel("$d$ (mins)")

    # for spine in ax.spines.values():
    #     spine.set_visible(False)

    if i == 0:
        ax.set_ylabel("Latency (s)")
        ax.tick_params(axis="y", which="both", length=0)

fig.tight_layout(pad=0.1) 
plt.savefig(f'figures/sensitivity-delay.pdf', bbox_inches='tight')

data = {}
traces = ['2-month']
cost_demand = 3

for trace_addr in traces:
    plot_condition = ((df['cold_start_delay'] == 4) & 
                    (df['target_num_instances'] == 3) &
                    (df['spot_policy'] == 'SpotHedge') & 
                    (df['fallback_policy'] == 'SpotFailoverNoSafety') &
                    (df['workload'] == 'Arena') &
                    (df['trace_addr'] == trace_addr) & 
                    (df['num_repeats'] == 5) &
                    (df['overprovision_num'] <= 3))
    data[trace_addr] = []
    df_copy = df[plot_condition]
    names = set()
    for index, row in df_copy.iterrows():
        availability = row['availability']
        # p90 = row['p90']
        num_extra = row['overprovision_num']
        name = f'$N_{{Extra}}$={num_extra}'
        if name in names:
            continue
        names.add(name)
        print(name, trace_addr, row['availability'])
        data[trace_addr].append((name, row['latency_list']))
                    
    fig = plt.figure(figsize=(fig_width - 1.5, fig_height - 1), dpi=300)
    ax = fig.subplots(1, 1, sharex=True, sharey=True)
    for i, trace in enumerate(data.keys()):
        data[trace] = sorted(data[trace], key=lambda x: x[0])
        names = [t[0] for t in data[trace]]
        if not names:
            continue

        value_list_list = [pair[1] for pair in data[trace]]
        positions = list(range(1, len(names) + 1))
    
        availability_mean = [100 * np.mean([t[1] for t in data[trace] if t[0] == name]) for name in names]
        availability_std = [100 * np.std([t[1] for t in data[trace] if t[0] == name]) for name in names]
        print(positions)
        print(names)
        bp = ax.boxplot(value_list_list, positions=positions, labels=names, whis=(10, 90), showfliers=False, showmeans=True, meanprops=meanprops, widths=0.6, patch_artist=True, boxprops=dict(facecolor="white"), medianprops=medianprops)
        boxes = bp['boxes']
        idx = 0
        for box, _ in zip(boxes, boxes):
            if idx >= len(palette):
                break
            box.set_edgecolor(palette[idx])
            idx += 1
            
    print("X-tick positions:", ax.get_xticks())
    ax.set_xticks([1, 2, 3, 4])
    ax.set_xticklabels(["0", "1", "2", "3"])
    ax.set_xticklabels([str(p) for p in positions])
    ax.set_xlabel("$N_{{Extra}}$")
    ax.set_ylabel("")
    if i != 0:
        ax.set_yticklabels([""] * len(ax.get_yticklabels()))
        ax.tick_params(axis="y", which="both", length=0)
    if i == 0:
        ax.set_ylabel("Latency (s)")
        ax.tick_params(axis="y", which="both", length=0)

    fig.tight_layout(pad=0.1)
    plt.savefig(f'figures/sensitivity-extra.pdf', bbox_inches='tight')
