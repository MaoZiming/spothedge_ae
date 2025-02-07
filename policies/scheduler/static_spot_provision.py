from typing import List, Tuple

from policies import fallback_policy
from policies.fallback_policy import FallbackType


class StaticSpotProvision(fallback_policy.FallbackPolicy):
    NAME = FallbackType.StaticSpotProvision

    def generate_mix_plan(
        self,
        t: int,
        i: int,
        spot_plan: List[List[int]],
        demand_plan: List[int],
        num_target,
        num_provision,
    ) -> Tuple[int, int]:
        return 0, num_provision
