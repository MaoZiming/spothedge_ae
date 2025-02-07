import random

import numpy as np

from utils import config, data_loader, utils, workload_loader


def init(
    target_num_instances: int,
    num_repeats: int,
    cold_start_delay: int,
    total_time_period: int,
    slo: float,
    cost_demand: int,
    spot_policy: str,
    autoscaler: str,
    trace_addr: str,
    workload_dir: str,
    seed: int,
):
    random.seed(seed)
    np.random.seed(seed)

    config.target_num_instances = target_num_instances
    config.cold_start_delay = cold_start_delay
    config.cost_demand = cost_demand
    config.spot_policy = spot_policy
    config.autoscaler = autoscaler
    config.trace_addr = trace_addr
    data_loader.load_trace_from_dir(trace_addr)
    workload_loader.load_workload_from_dir(workload_dir)

    config.total_time_period = (
        int(min(10000, config.min_trace_len / 5))
        if total_time_period == -1
        else total_time_period
    )
    config.num_repeats = num_repeats
    config.slo = slo
    utils.generate_random_offset()
