import numpy as np

from policies import workload
from policies.workload import WorkloadType


class PoissonWorkload(workload.Workload):
    NAME = WorkloadType.Poisson

    def __init__(self, use_simulator=False, seed=0):
        self.request_rate = 0.05
        self.num_requests = 8000000
        super().__init__(seed)

    def load_workload(self):
        t_prev = 0
        for _ in range(self.num_requests):
            inter_arrival_time = np.random.exponential(1 / self.request_rate)
            t_prev = inter_arrival_time + t_prev
            self.request_arrival_times.append(t_prev)
            self.request_interarrival_times.append(inter_arrival_time)
