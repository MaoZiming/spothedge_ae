from policies import workload
from policies.workload import WorkloadType
from workloads.arena import loader
import random


class ArenaWorkload(workload.Workload):
    NAME = WorkloadType.Arena

    def __init__(self, use_simulator=False, seed=0, arena_trace_scale=None):
        self.intervals = None
        self.conversations = None
        self.start_idx = None
        self.current_idx = 0
        print('arg', use_simulator, seed, arena_trace_scale)
        self.arena_trace_scale = (
            arena_trace_scale if arena_trace_scale else loader._ARENA_TRACE_SCALE
        )
        if use_simulator:
            # Account for batching.
            self.arena_trace_scale /= 10

        print(self.arena_trace_scale)
        super().__init__(use_simulator, seed)


    def reset(self):
        self.start_idx = None
        self.current_idx = 0

    def load_workload(self):
        self.intervals, self.conversations = loader.load_arena_dataset(
            self.arena_trace_scale
        )
        print("Arena", "load_workload", self.intervals[:10])
        t_prev = 0
        for interval in self.intervals:
            t_prev = interval + t_prev
            self.request_arrival_times.append(t_prev)
            self.request_interarrival_times.append(interval)

    def get_next_interval_and_conversation(self):
        # Matches the e2e file.
        if self.start_idx is None:
            self.start_idx = random.randint(0, len(self.intervals) - 1)

        idx = (self.start_idx + self.current_idx) % len(self.intervals)
        self.current_idx += 1
        return self.intervals[idx], self.conversations[idx]

    def get_next_interarrival_time(self, i):
        del i
        interval, _ = self.get_next_interval_and_conversation()
        return interval

    def calculate_max_request_num(self, run_time: float) -> int:
        tot = 0.0
        if self.start_idx is None:
            self.start_idx = random.randint(0, len(self.intervals) - 1)
        self.reload_seed()
        i = 0
        while True:
            idx = (self.start_idx + i) % len(self.intervals)
            tot += self.intervals[idx]
            if tot > run_time:
                return i
            i += 1

    @property
    def trace_scale(self):
        return loader._ARENA_TRACE_SCALE
