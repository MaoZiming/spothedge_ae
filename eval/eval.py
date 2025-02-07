import argparse

import ray
import tqdm
from utils import config, job_runner
from policies.fallback_policy import FallbackType
from policies.autoscaler import AutoscalerType
from policies.spot_policy import SpotPolicyType
from policies.workload import WorkloadType
import copy

args_set = set()
exps = []


def _add_experiment(
    args,
    spot_policy,
    fallback_policy,
    autoscaler,
    overprovision_num,
    cold_start_in_s,
    trace_address,
    workload,
):
    copy_args = copy.deepcopy(args)
    copy_args.spot_policy = spot_policy
    copy_args.fallback_policy = fallback_policy
    copy_args.autoscaler = autoscaler
    copy_args.overprovision_num = overprovision_num
    copy_args.cold_start_delay = int(cold_start_in_s / config.time_tick_in_seconds)
    copy_args.trace_addr = trace_address
    copy_args.workload = workload

    if (
        spot_policy,
        fallback_policy,
        autoscaler,
        overprovision_num,
        cold_start_in_s,
        trace_address,
        workload,
    ) in args_set:
        return

    exps.append(job_runner.run_one_exp.options(num_cpus=1).remote(args=copy_args))

    args_set.add(
        (
            spot_policy,
            fallback_policy,
            autoscaler,
            overprovision_num,
            cold_start_in_s,
            trace_address,
            workload,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-num-instances", type=int, default=3)
    parser.add_argument("--trace-addr", type=str, default="4-node")
    parser.add_argument("--total-time-period", type=int, default=2880)
    parser.add_argument("--num-repeats", type=int, default=1)
    parser.add_argument("--cold-start-time", type=int, default=0)
    parser.add_argument("--cost-demand", type=int, default=3)
    parser.add_argument("--spot-policy", type=str, default=SpotPolicyType.OnDemand)
    parser.add_argument(
        "--fallback-policy", type=str, default=FallbackType.StaticSpotProvision
    )
    parser.add_argument("--autoscaler", type=str, default=AutoscalerType.BaseAutoscaler)
    parser.add_argument("--workload", type=str, default=WorkloadType.Poisson)
    parser.add_argument("--results-dir", type=str, default="results")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--overprovision-number", type=int, default=0)
    parser.add_argument("--cost-cap", type=int, default=-1)
    args = parser.parse_args()

    run_experiments = ["Optimal", "Main", "Sensitivity"]
                        
    if "Optimal" in run_experiments:
        for workload in [WorkloadType.Arena, WorkloadType.MAF, WorkloadType.Poisson]:
            for trace_addr in ["a100", "4-node", "16-node", "2-month"]:
                for cold_start_delay_in_s in [120]:
                    
                    args.cost_cap = int(args.target_num_instances * args.total_time_period * args.cost_demand)
                    
                    _add_experiment(
                        args=args,
                        spot_policy=SpotPolicyType.Optimal,
                        fallback_policy=FallbackType.StaticSpotProvision,
                        autoscaler=AutoscalerType.BaseAutoscaler,
                        overprovision_num=1, # Same as SpotHedge. 
                        cold_start_in_s=cold_start_delay_in_s,
                        trace_address=trace_addr,
                        workload=workload,
                    )


    # Main Experiment
    if "Main" in run_experiments:
        for workload in [WorkloadType.Arena, WorkloadType.MAF, WorkloadType.Poisson]:
            for trace_addr in ["a100", "4-node", "16-node", "2-month"]:
                for cold_start_delay_in_s in [120]:
                    for overprovision_num in [0]:
                        _add_experiment(
                            args=args,
                            spot_policy=SpotPolicyType.OnDemand,
                            fallback_policy=FallbackType.OnDemand,
                            autoscaler=AutoscalerType.BaseAutoscaler,
                            overprovision_num=overprovision_num,
                            cold_start_in_s=cold_start_delay_in_s,
                            trace_address=trace_addr,
                            workload=workload,
                        )

                    for overprovision_num in [0]:
                        _add_experiment(
                            args=args,
                            spot_policy=SpotPolicyType.NaiveSpread,
                            fallback_policy=FallbackType.StaticSpotProvision,
                            autoscaler=AutoscalerType.BaseAutoscaler,
                            overprovision_num=overprovision_num,
                            cold_start_in_s=cold_start_delay_in_s,
                            trace_address=trace_addr,
                            workload=workload,
                        )
                        _add_experiment(
                            args=args,
                            spot_policy=SpotPolicyType.RoundRobin,
                            fallback_policy=FallbackType.StaticSpotProvision,
                            autoscaler=AutoscalerType.BaseAutoscaler,
                            overprovision_num=overprovision_num,
                            cold_start_in_s=cold_start_delay_in_s,
                            trace_address=trace_addr,
                            workload=workload,
                        )
                    for overprovision_num in [1]:
                        _add_experiment(
                            args=args,
                            spot_policy=SpotPolicyType.SpotHedge,
                            fallback_policy=FallbackType.SpotFailoverNoSafety,
                            autoscaler=AutoscalerType.BaseAutoscaler,
                            overprovision_num=overprovision_num,
                            cold_start_in_s=cold_start_delay_in_s,
                            trace_address=trace_addr,
                            workload=workload,
                        )

    # Sensitivity Experiment
    if "Sensitivity" in run_experiments:
        for workload in [WorkloadType.Poisson]:
            for trace_addr in ["4-node"]:
                for cold_start_delay_in_s in [60, 120, 240, 480]:
                    for overprovision_num in [1]:
                        _add_experiment(
                            args=args,
                            spot_policy=SpotPolicyType.SpotHedge,
                            fallback_policy=FallbackType.SpotFailoverNoSafety,
                            autoscaler=AutoscalerType.BaseAutoscaler,
                            overprovision_num=overprovision_num,
                            cold_start_in_s=cold_start_delay_in_s,
                            trace_address=trace_addr,
                            workload=workload,
                        )
                for cold_start_delay_in_s in [120]:
                    for overprovision_num in [0, 1, 2, 3]:
                        _add_experiment(
                            args=args,
                            spot_policy=SpotPolicyType.SpotHedge,
                            fallback_policy=FallbackType.SpotFailoverNoSafety,
                            autoscaler=AutoscalerType.BaseAutoscaler,
                            overprovision_num=overprovision_num,
                            cold_start_in_s=cold_start_delay_in_s,
                            trace_address=trace_addr,
                            workload=workload,
                        )
                        
    pbar = tqdm.tqdm(total=len(exps), desc="Job completion")
    while len(exps) > 0:
        done, exps = ray.wait(exps, num_returns=1)
        pbar.update(1)
        result = ray.get(done[0])
