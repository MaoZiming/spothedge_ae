from policies import autoscaler
from policies.autoscaler import AutoscalerType
from utils import config


class BaseAutoscaler(autoscaler.Autoscaler):
    NAME = AutoscalerType.BaseAutoscaler

    def __init__(self, workload) -> None:
        super().__init__(workload)
        self._target_num_replicas = config.target_num_instances

    def get_target_num_replicas(self, t):
        return self._target_num_replicas
