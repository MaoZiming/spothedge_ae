from typing import List, Tuple

from policies import fallback_policy, spot_policy
from utils import config
from policies.fallback_policy import FallbackType


class SpotFailover(fallback_policy.FallbackPolicy):
    NAME = FallbackType.SpotFailover

    def __init__(self) -> None:
        super().__init__()
        self.last_fallback_t = -1
        self.last_fallback_num_demand = -1

    def is_safety_net(self, current_time, spot_plan, demand_plan):
        start_time = 0
        total_time = current_time - start_time + 1
        avail_meet_time = 0
        for t in range(start_time, current_time + 1):
            active_num_spots = spot_policy.Policy.num_active_spot(t, spot_plan)
            active_num_demand = spot_policy.Policy.num_active_demand(t, demand_plan)
            if active_num_demand + active_num_spots >= config.num_min:
                avail_meet_time += 1

        return (avail_meet_time / total_time) <= config.slo

    def generate_mix_plan(
        self,
        t: int,
        i: int,
        spot_plan: List[List[int]],
        demand_plan: List[int],
        num_target,
        num_provision,
    ) -> Tuple[int, int]:
        num_demand = 0
        num_spot = num_provision
        num_active_spot = spot_policy.Policy.num_active_spot(t - 1, spot_plan)

        if self.is_safety_net(t, spot_plan, demand_plan):
            num_demand = config.num_min

        if num_provision - num_active_spot > 0:
            num_demand = max(
                num_demand, min(num_target, num_provision - num_active_spot)
            )
            self.last_fallback_t = t
            self.last_fallback_num_demand = num_demand

        # Wait for cold start delay when spot instances are replenished.
        elif t - self.last_fallback_t < config.cold_start_delay:
            num_demand = max(num_demand, self.last_fallback_num_demand)

        return num_demand, num_spot
