import os
import time
from typing import Dict

import pulp

from policies import latency_simulator, spot_policy
from utils import config, utils
from policies.spot_policy import SpotPolicyType


class Optimal(spot_policy.Policy):
    NAME = SpotPolicyType.Optimal

    def __init__(self, args, verbose=False) -> None:
        super().__init__(args)
        self.soft_target = config.target_num_instances + args.overprovision_num
        self._verbose = verbose
        self._results_dir = args.results_dir
        self._workload_str = args.workload
        self._cost_cap = args.cost_cap

    def _run_exp_one(self, i: int):
        spot_variables = []
        active_spot_instance_variables = []
        num_regions = len(config.regions)
        tic = time.time()

        print(
            f"_run_exp_one_slo max_cost: {self._cost_cap}, slo: {config.slo}, step: {int(config.target_num_instances * config.total_time_period / 2)}, config.total_time_period: {config.total_time_period}"
        )

        # prob = pulp.LpProblem("Service-Maximization", pulp.LpMaximize)
        prob = pulp.LpProblem("Cost-Minimization", pulp.LpMinimize)
        for region_idx in range(num_regions):
            spot_variables.append(
                pulp.LpVariable.dicts(
                    f"r{region_idx}",
                    range(config.total_time_period),
                    lowBound=0,
                    upBound=self.soft_target,
                    cat=pulp.LpInteger,
                )
            )
            active_spot_instance_variables.append(
                pulp.LpVariable.dicts(
                    f"a{region_idx}",
                    range(config.total_time_period),
                    lowBound=0,
                    upBound=self.soft_target,
                    cat=pulp.LpInteger,
                )
            )

        on_demand_variables = pulp.LpVariable.dicts(
            "on_demand",
            range(config.total_time_period),
            lowBound=0,
            upBound=self.soft_target,
            cat=pulp.LpInteger,
        )

        active_on_demand_variables = pulp.LpVariable.dicts(
            "active_on_demand",
            range(config.total_time_period),
            lowBound=0,
            upBound=self.soft_target,
            cat=pulp.LpInteger,
        )
        
        num_active_at_t = pulp.LpVariable.dicts(
            "num_active_at_t",
            range(config.total_time_period),
            lowBound=0,
            upBound=self.soft_target,
            cat=pulp.LpInteger,
        )

        for t in range(config.total_time_period):
            for r, _ in enumerate(config.regions):
                prob += spot_variables[r][t] <= utils.num_available_spot(r, t, i)

                # Check for active number of spot instances
                if t >= config.cold_start_delay:
                    for t_past in range(t - config.cold_start_delay, t + 1):
                        prob += (
                            active_spot_instance_variables[r][t]
                            <= spot_variables[r][t_past]
                        )
                else:
                    prob += active_spot_instance_variables[r][t] <= 0

            if t >= config.cold_start_delay:
                for t_past in range(t - config.cold_start_delay, t + 1):
                    prob += active_on_demand_variables[t] <= on_demand_variables[t_past]
            else:
                prob += active_on_demand_variables[t] <= 0

            num_active_at_t[t] = (
                pulp.lpSum(
                    active_spot_instance_variables[region_idx][t]
                    for region_idx in range(num_regions)
                )
                + active_on_demand_variables[t]
            )

            if t >= config.cold_start_delay:
                prob += num_active_at_t[t] <= self.soft_target
                prob += num_active_at_t[t] >= config.target_num_instances

        cost = (
            pulp.lpSum(
                pulp.lpSum(spot_variables[r][t] for r in range(num_regions))
                for t in range(config.total_time_period)
            )
            + pulp.lpSum(
                on_demand_variables[t] for t in range(config.total_time_period)
            )
            * config.cost_demand
        )
        # prob += cost <= self._cost_cap
        prob += cost, "Total Cost"

        solver = pulp.PULP_CBC_CMD(
            mip=True, msg=0
        )
        tmpdir = os.path.expanduser("~/solver_tmp")
        os.makedirs(tmpdir, exist_ok=True)
        solver.tmpDir = tmpdir
        prob.solve(solver)
        
        print("Status", pulp.LpStatus[prob.status])

        if self._verbose:
            status = prob.status
            objective = pulp.value(prob.objective)
            objective = float(objective) if objective is not None else -1.0
            print(
                f"ILP Status: {pulp.LpStatus[status]}\tObjective: {objective}\t"
                f"Time: {time.time() - tic}"
            )

        if pulp.LpStatus[prob.status] != "Optimal":
            return

        max_service = pulp.value(prob.objective)
        # avail = pulp.value(availability)
        avail = 1
        cost = pulp.value(cost)

        active_on_demand_list = [
            active_on_demand_variables[t].value()
            for t in range(config.total_time_period)
        ]
        active_spot_list = [
            [active_spot_instance_variables[r][t].value() for r in range(num_regions)]
            for t in range(config.total_time_period)
        ]

        total_active_list = [
            int(sum(active_spot_list[i]) + active_on_demand_list[i])
            for i in range(config.total_time_period)
        ]

        nodes_to_count: Dict[int, int] = {}
        for t in range(config.total_time_period):
            nodes_to_count[total_active_list[t]] = (
                nodes_to_count.get(total_active_list[t], 0) + 1
            )

        cost = round(cost, 4)
        avail = round(avail, 4)

        print(
            f"max_cost: {self._cost_cap}, cost: {cost}, avail: {avail}, max_service: {max_service}"
            f", nodes_to_count: {nodes_to_count}"
        )

        p50, p90, p99, p999, latency_list = latency_simulator.simulate_latency(
            total_active_list, self.workload, i
        )

        new_result = {
            "repeat_idx": i,
            "availability": avail,
            "cost": cost,
            "cost_cap": self._cost_cap,
            "node_hist": nodes_to_count,
            "p50": p50,
            "p90": p90,
            "p99": p99,
            "p999": p999,
            "latency_list": latency_list,
        }
        self._results.append(new_result)
