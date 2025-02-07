import math
from policies import workload
from policies.workload import WorkloadType


class MAFWorkload(workload.Workload):
    NAME = WorkloadType.MAF

    def __init__(self, use_simulator=False, seed=0):
        self.workload_addr = "workloads/maf1/cleaned.csv"
        self.scale_factor = 10000
        super().__init__(seed)

    def load_workload(self):
        t_prev = 0
        with open(self.workload_addr, "r") as f:
            skip_first_line = True
            for line in f:
                if skip_first_line:
                    skip_first_line = False
                    continue

                line = line.split(",")[1]
                num_requests = int(int(line)) / self.scale_factor

                # Cap max at 2 requests per seconds.
                num_requests = min(num_requests, 60 * 1.5)
                request_per_sec = num_requests / 60
                inter_arrival_times = [1 / request_per_sec] * math.ceil(request_per_sec)

                for inter_arrival_time in inter_arrival_times:
                    t_prev += inter_arrival_time
                    self.request_arrival_times.append(t_prev)
                    self.request_interarrival_times.append(inter_arrival_time)
