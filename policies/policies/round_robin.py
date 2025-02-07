from policies import spot_policy
from utils import config
from policies.spot_policy import SpotPolicyType


class RoundRobin(spot_policy.Policy):
    NAME = SpotPolicyType.RoundRobin

    def __init__(self, args) -> None:
        super().__init__(args)
        self.last_zone_idx = 0

    def _reset(self) -> None:
        super()._reset()
        self.last_zone_idx = 0

    def _get_next_allocation(self, t, i, num_spots):
        if num_spots < sum(self.spot_plan[t - 1]):
            available_spot_to_redistribute = num_spots
            self.spot_plan[t] = [0] * len(config.regions)
        else:
            available_spot_to_redistribute = num_spots - sum(self.spot_plan[t - 1])
            self.spot_plan[t] = self.spot_plan[t - 1].copy()

        while available_spot_to_redistribute > 0:
            self.spot_plan[t][self.last_zone_idx] += 1
            self.last_zone_idx = (self.last_zone_idx + 1) % len(config.regions)
            available_spot_to_redistribute -= 1
