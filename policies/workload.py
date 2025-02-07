from typing import Dict, List, Type
import enum
import random
import numpy as np


class WorkloadType(enum.Enum):
    Poisson = "Poisson"
    Arena = "Arena"
    MAF = "MAF"


class Workload:
    REGISTRY: Dict[str, Type["Workload"]] = dict()

    def __init__(self, use_simulator=False, seed=0) -> None:
        self.request_arrival_times: List[int] = []
        self.request_interarrival_times: List[int] = []
        self.load_workload()
        self.service_time = 10  # To match e2e. 
        self.service_rate = 1 / self.service_time  # To match e2e.
        self.TIMEOUT = 100
        self.seed = seed
        self.reload_seed()

    def reload_seed(self):
        random.seed(self.seed)
        np.random.seed(self.seed)

    def __init_subclass__(cls) -> None:
        if cls.NAME is None:
            return
        assert cls.NAME not in cls.REGISTRY, f"Name {cls.NAME} already exists"
        cls.REGISTRY[cls.NAME] = cls

    @classmethod
    def from_name(cls, name):
        assert name in cls.REGISTRY, (name, cls.REGISTRY)
        return cls.REGISTRY[name]

    def get_window_num_requests(self, start_time, end_time):
        assert start_time <= self.request_arrival_times[-1], (
            "start_time: %s, end_time: %s, last_arrival_time: %s"
            % (start_time, end_time, self.request_arrival_times[-1])
        )

        num_requests = 0
        for i in range(len(self.request_arrival_times)):
            if (
                self.request_arrival_times[i] >= start_time
                and self.request_arrival_times[i] <= end_time
            ):
                num_requests += 1

            if self.request_arrival_times[i] > end_time:
                break
        return num_requests

    def get_next_interarrival_time(self, i):
        i = i % len(self.request_interarrival_times)
        return self.request_interarrival_times[i]

    @property
    def name(self):
        return self.NAME

    @property
    def timeout(self):
        return self.TIMEOUT
