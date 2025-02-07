import json
import os

import ray

from policies import spot_policy
from utils import config, init


def get_config_dict(args):
    config_dict = {}
    config_dict["target_num_instances"] = config.target_num_instances
    config_dict["total_time_period"] = config.total_time_period
    config_dict["cold_start_delay"] = config.cold_start_delay
    config_dict["num_repeats"] = config.num_repeats
    config_dict["gap_seconds"] = config.gap_seconds
    config_dict["time_tick_in_seconds"] = config.time_tick_in_seconds
    config_dict["autoscaler"] = config.autoscaler.value
    config_dict["trace_addr"] = config.trace_addr
    config_dict["overprovision_num"] = args.overprovision_num
    config_dict["workload"] = args.workload.value
    config_dict["spot_policy"] = args.spot_policy.value
    config_dict["fallback_policy"] = args.fallback_policy.value
    return config_dict


def _get_file_location(args):
    return f"./{args.results_dir}/{args.trace_addr}_{args.workload.value}_{args.spot_policy.value}_{args.fallback_policy.value}_{args.autoscaler.value}.jsonl"


def write_results_to_file(dict_results, args):
    dict_results = {**get_config_dict(args), **dict_results}
    jsonl = json.dumps(dict_results)
    with open(
        _get_file_location(args),
        "a",
    ) as f:
        f.write(jsonl + "\n")


def check_config_exists(args):
    config_dict = get_config_dict(args)

    if os.path.exists(
        _get_file_location(args),
    ):
        with open(
            _get_file_location(args),
        ) as file:
            for line in file:
                json_data = json.loads(line)
                different = False
                for key, value in config_dict.items():
                    if json_data[key] != value:
                        different = True
                if not different:
                    print("Skip", config_dict)
                    return True
                else:
                    break
    return False


@ray.remote(num_cpus=1)
def run_one_exp(args):
    init.init(
        target_num_instances=args.target_num_instances,
        num_repeats=args.num_repeats,
        cold_start_delay=args.cold_start_delay,
        total_time_period=args.total_time_period,
        slo=config.slo,
        cost_demand=args.cost_demand,
        spot_policy=args.spot_policy,
        autoscaler=args.autoscaler,
        trace_addr=args.trace_addr,
        workload_dir=args.workload.value,
        seed=args.seed,
    )

    if check_config_exists(args):
        return {}

    results = spot_policy.Policy.from_name(args.spot_policy)(args=args).run_exp()

    for result in results:
        write_results_to_file(result, args)
    return results
