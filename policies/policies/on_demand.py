from policies import spot_policy
from utils import config
from policies.spot_policy import SpotPolicyType


class OnDemand(spot_policy.Policy):
    NAME = SpotPolicyType.OnDemand

    def _get_next_allocation(self, t, i, num_spots):
        self.spot_plan[t] = [0] * len(config.regions)
