import random
from typing import List

from policies import spot_policy
from utils import config
from policies.spot_policy import SpotPolicyType


class SpotHedge(spot_policy.Policy):
    NAME = SpotPolicyType.SpotHedge

    def __init__(self, args) -> None:
        super().__init__(args)
        self.active_region_list: List[int] = list(range(len(config.regions)))
        self.preemptive_region_list: List[int] = []
        self.last_spot_plan: List[int] = []
        self.available_spots_to_distribute = 0

    def _reset(self) -> None:
        super()._reset()
        self.active_region_list = list(range(len(config.regions)))
        self.preemptive_region_list = []
        self.last_spot_plan = []
        self.available_spots_to_distribute = 0

    def _distribute_available_spot(self, t):
        def allocate_zone(current_zones):
            idx = random.choice(current_zones)
            self.spot_plan[t][idx] += 1
            self.available_spots_to_distribute -= 1
            self._distribute_available_spot(t)

        if self.available_spots_to_distribute <= 0:
            return

        current_zones = list(self.active_region_list)
        for region_idx, _ in enumerate(config.regions):
            if self.spot_plan[t][region_idx] > 0 and region_idx in current_zones:
                current_zones.remove(region_idx)

        if len(current_zones) > 0:
            allocate_zone(current_zones)
            return

        current_zones = list(self.active_region_list)
        allocate_zone(current_zones)
        return

    def _move_region_to_active(self, region_idx):
        for r in self.preemptive_region_list:
            if region_idx == r:
                self.preemptive_region_list.remove(r)
                self.active_region_list.append(r)

    def _move_region_to_preempt(self, region_idx):
        for r in self.active_region_list:
            if region_idx == r:
                self.active_region_list.remove(r)
                self.preemptive_region_list.append(r)

    def _maintain_list(self):
        if len(self.active_region_list) <= min(1, len(config.regions) - 3):
            self.active_region_list = list(range(len(config.regions)))
            self.preemptive_region_list = []

    def _get_next_allocation(self, t, i, num_spots):
        if self.last_spot_plan:
            for region_idx, _ in enumerate(config.regions):
                if self.last_spot_plan[region_idx] > self.spot_plan[t - 1][region_idx]:
                    self._move_region_to_preempt(region_idx)

                elif (
                    self.last_spot_plan[region_idx] > 0
                    and self.last_spot_plan[region_idx]
                    == self.spot_plan[t - 1][region_idx]
                ):
                    self._move_region_to_active(region_idx)

        if num_spots >= sum(self.spot_plan[t - 1]):
            self.available_spots_to_distribute = num_spots - sum(self.spot_plan[t - 1])
            self.spot_plan[t] = self.spot_plan[t - 1].copy()
        else:
            self.available_spots_to_distribute = num_spots
            self.spot_plan[t] = [0] * len(config.regions)

        self._maintain_list()
        self._distribute_available_spot(t)
        self.last_spot_plan = self.spot_plan[t].copy()
