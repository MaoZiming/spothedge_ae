import numpy as np

from utils import config


def generate_random_offset():
    for _ in range(config.num_repeats):
        config.random_offsets.append(
            np.random.randint(0, config.min_trace_len - config.total_time_period)
        )


def num_available_spot(region_idx, t, i):
    region_trace = config.trace_for_each_region[config.regions[region_idx]]
    trace_len = len(region_trace)
    return region_trace[(t + config.random_offsets[i]) % trace_len]
