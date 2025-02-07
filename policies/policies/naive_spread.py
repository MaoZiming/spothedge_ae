from policies import spot_policy
from utils import config
from policies.spot_policy import SpotPolicyType


class NaiveSpread(spot_policy.Policy):
    NAME = SpotPolicyType.NaiveSpread

    def _get_next_allocation(self, t, i, num_spots):
        if num_spots < sum(self.spot_plan[t - 1]):
            available_spot_to_redistribute = num_spots
            self.spot_plan[t] = [0] * len(config.regions)
        else:
            available_spot_to_redistribute = num_spots - sum(self.spot_plan[t - 1])
            self.spot_plan[t] = self.spot_plan[t - 1].copy()

        min_spot = 0
        while available_spot_to_redistribute > 0:
            for region_idx, _ in enumerate(config.regions):
                if available_spot_to_redistribute == 0:
                    break
                if self.spot_plan[t][region_idx] == min_spot:
                    self.spot_plan[t][region_idx] += 1
                    available_spot_to_redistribute -= 1
            min_spot += 1
