from typing import Dict, Type

from policies import workload as workload_lib
from utils import config
import enum


class AutoscalerType(enum.Enum):
    BaseAutoscaler = "BaseAutoscaler"
    QpsAutoscaler = "QpsAutoscaler"


class Autoscaler:
    NAME = "Autoscaler"
    REGISTRY: Dict[str, Type["Autoscaler"]] = dict()

    def __init__(self, workload: workload_lib.Workload) -> None:
        self.window_size = 60  # tick = 30s. 60 ticks = 30 mins
        self.workload = workload

    def __init_subclass__(cls) -> None:
        if cls.NAME is None:
            return
        assert cls.NAME not in cls.REGISTRY, f"Name {cls.NAME} already exists"
        cls.REGISTRY[cls.NAME] = cls

    @classmethod
    def from_name(cls, name: str):
        assert name in cls.REGISTRY, (name, cls.REGISTRY)
        return cls.REGISTRY[name]

    def get_target_num_replicas(self, t):
        raise NotImplementedError

    def get_current_request_rate(self, t):
        if t == 0:
            return 0
        num_requests = self.workload.get_window_num_requests(
            max(0, t - self.window_size) * config.time_tick_in_seconds,
            t * config.time_tick_in_seconds,
        )
        window_size = t - max(0, t - self.window_size)
        return num_requests / window_size / config.time_tick_in_seconds

    def get_current_request_rate_autoscaler(self, t):
        return self.get_current_request_rate(t)

    @property
    def name(self):
        return f"{self.NAME}"
