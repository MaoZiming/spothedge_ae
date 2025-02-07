import random
from typing import Dict, List, Tuple, Type

from policies import autoscaler, fallback_policy, latency_simulator, workload
from utils import config, utils
import enum


class SpotPolicyType(enum.Enum):
    OnDemand = "OnDemand"
    NaiveSpread = "NaiveSpread"
    RoundRobin = "RoundRobin"
    SpotHedge = "SpotHedge"
    Optimal = "Optimal"


class Policy:
    REGISTRY: Dict[str, Type["Policy"]] = dict()

    def __init__(self, args) -> None:
        self._num_repeat = config.num_repeats
        self._results: List[
            Dict[
                str,
                List[
                    Tuple[
                        float, float, Dict[int, int], Tuple[float, float, float, float]
                    ]
                ],
            ]
        ] = []

        self.spot_plan = [
            [0] * len(config.regions) for _ in range(config.total_time_period)
        ]
        self.demand_plan = [0 for _ in range(config.total_time_period)]
        self.overprovision_num = args.overprovision_num

        self.fallback_policy = fallback_policy.FallbackPolicy.from_name(
            args.fallback_policy
        )()
        self.workload = workload.Workload.from_name(args.workload)(use_simulator=True)
        self.autoscaler = autoscaler.Autoscaler.from_name(args.autoscaler)(
            self.workload
        )

    def __init_subclass__(cls) -> None:
        if cls.NAME is None:
            return
        assert cls.NAME not in cls.REGISTRY, f"Name {cls.NAME} already exists"
        cls.REGISTRY[cls.NAME] = cls

    @classmethod
    def from_name(cls, name: str):
        assert name in cls.REGISTRY, (name, cls.REGISTRY)
        return cls.REGISTRY[name]

    def _reset(self) -> None:
        self.spot_plan = [
            [0] * len(config.regions) for _ in range(config.total_time_period)
        ]
        self.demand_plan = [0 for _ in range(config.total_time_period)]
        self.fallback_policy.reset()

    def run_exp(self):
        for i in range(config.num_repeats):
            random.shuffle(config.regions)
            self._run_exp_one(i)
            self._reset()
        return self._results

    def _current_satisfied_time(self, t: int):
        avail_meet_time = 0
        for i in range(t):
            active_num_spots = Policy.num_active_spot(i, self.spot_plan)
            active_num_demand = Policy.num_active_demand(i, self.demand_plan)
            total_active_nodes = active_num_demand + active_num_spots

            if total_active_nodes >= config.num_min:
                avail_meet_time += 1
        return avail_meet_time

    def _run_exp_one(self, i: int):
        for t in range(config.total_time_period):
            num_target = self.autoscaler.get_target_num_replicas(t + i)
            num_provision = num_target + self.overprovision_num

            # spot_policy
            num_demand, num_spot = self.fallback_policy.generate_mix_plan(
                t, i, self.spot_plan, self.demand_plan, num_target, num_provision
            )
            assert (
                self.NAME == SpotPolicyType.OnDemand
                or num_spot + num_demand >= num_target
            ), (
                self.NAME,
                num_demand,
                num_spot,
                self.overprovision_num,
                num_target,
                num_provision,
            )
            assert self.NAME == SpotPolicyType.OnDemand or num_demand <= num_target, (
                self.NAME,
                num_demand,
                num_target,
            )

            # SPOT_ALLOCATOR
            self._get_next_allocation(t, i, num_spot)
            self._step_spot(t, i)
            self._step_demand(t, num_demand)

        self._record_exp_result(i)

    def _get_next_allocation(self, t, i, num_spots):
        raise NotImplementedError

    def _step_spot(self, t, i):
        for region_idx, _ in enumerate(config.regions):
            max_num_spot_available = utils.num_available_spot(region_idx, t, i)
            if self.spot_plan[t][region_idx] > max_num_spot_available:
                self.spot_plan[t][region_idx] = max_num_spot_available

    @classmethod
    def num_active_spot(cls, t, spot_plan):
        active_num_spots = 0
        if t < config.cold_start_delay:
            pass
        else:
            for region_idx, _ in enumerate(config.regions):
                num_spot_history = []
                for t_past in range(t - config.cold_start_delay, t + 1):
                    num_spot_history.append(spot_plan[t_past][region_idx])
                active_num_spots += min(num_spot_history) if num_spot_history else 0
        return active_num_spots

    @classmethod
    def num_active_demand(cls, t, demand_plan):
        if t < config.cold_start_delay:
            active_num_demand = 0
        else:
            num_demand_history = []
            for t_past in range(t - config.cold_start_delay, t + 1):
                num_demand_history.append(demand_plan[t_past])
            active_num_demand = min(num_demand_history) if num_demand_history else 0
        return active_num_demand

    def _step_demand(self, t, num_demand):
        self.demand_plan[t] = num_demand

    def _record_exp_result(self, i):
        availability, cumulative_cost, node_hist, node_over_time = self.score_plan()
        p50, p90, p99, p999, latency_list = latency_simulator.simulate_latency(
            node_over_time, self.workload, i
        )
        new_result = {
            "repeat_idx": i,
            "availability": availability,
            "cost": cumulative_cost,
            "node_hist": node_hist,
            "p50": p50,
            "p90": p90,
            "p99": p99,
            "p999": p999,
            "latency_list": latency_list,
        }
        self._results.append(new_result)
        print(round(availability, 3), round(cumulative_cost, 3), node_hist)

    def score_plan(self):
        cumulative_cost = 0
        avail_meet_time = 0
        total_num_spots = 0
        total_num_demand = 0
        nodes_to_count = {}
        node_over_time = []

        for t in range(config.cold_start_delay, config.total_time_period):
            total_num_spots += sum(
                [
                    self.spot_plan[t][region_idx]
                    for region_idx in range(len(config.regions))
                ]
            )
            total_num_demand += self.demand_plan[t]

            active_num_spots = Policy.num_active_spot(t, self.spot_plan)
            active_num_demand = Policy.num_active_demand(t, self.demand_plan)
            if active_num_demand + active_num_spots >= config.num_min:
                avail_meet_time += 1
                if t < config.cold_start_delay:
                    assert False, (active_num_demand, active_num_spots)

            total_active_nodes = active_num_demand + active_num_spots
            nodes_to_count[total_active_nodes] = (
                nodes_to_count.get(total_active_nodes, 0) + 1
            )
            node_over_time.append(total_active_nodes)

        avail = avail_meet_time / (config.total_time_period - config.cold_start_delay)
        cumulative_cost = total_num_spots + total_num_demand * config.cost_demand
        print(
            f"Name: {self.name}, total_num_spots: {total_num_spots}, total_num_demand: {total_num_demand}, avail_meet_time: {avail_meet_time}"
        )
        return avail, cumulative_cost, nodes_to_count, node_over_time

    @property
    def name(self):
        return self.NAME.value
