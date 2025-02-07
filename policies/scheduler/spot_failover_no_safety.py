from typing import List, Tuple

from policies import fallback_policy, spot_policy
from policies.fallback_policy import FallbackType


class SpotFailoverNoSafety(fallback_policy.FallbackPolicy):
    NAME = FallbackType.SpotFailoverNoSafety

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
        if num_provision - num_active_spot > 0:
            num_demand = min(num_target, num_provision - num_active_spot)

        return num_demand, num_spot
