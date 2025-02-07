import math

from policies import autoscaler
from policies import workload as workload_lib
from utils import config
from policies.autoscaler import AutoscalerType


class QpsAutoscaler(autoscaler.Autoscaler):
    NAME = AutoscalerType.QpsAutoscaler

    def __init__(self, workload: workload_lib.Workload) -> None:
        self.target_qps_per_replica = workload.service_rate
        self.num_max = config.target_num_instances * 2
        self.num_min = config.num_min
        self.num_tar = self.num_min
        self.downscale_counter = 0
        self.upscale_counter = 0
        self.upscale_interval_seconds = 300
        self.downscale_interval_seconds = 1200
        super().__init__(workload)

    def reset(self) -> None:
        self.downscale_counter = 0
        self.upscale_counter = 0

    def get_target_num_replicas(self, t):
        request_rates = self.get_current_request_rate(t)
        num_replicas = math.ceil(request_rates / self.target_qps_per_replica)

        # print('QPS AUTOSCALER', t, 'request_rates: ', request_rates,
        #   'num_replicas', num_replicas)
        if num_replicas > self.num_tar:
            self.upscale_counter += 1
            self.downscale_counter = 0
        elif num_replicas < self.num_tar:
            self.downscale_counter += 1
            self.upscale_counter = 0
        else:
            self.downscale_counter = 0
            self.upscale_counter = 0

        # ARENA: 5 mins
        if (
            self.upscale_counter
            >= self.upscale_interval_seconds / config.time_tick_in_seconds
            and self.num_tar < self.num_max
        ):
            self.num_tar = num_replicas
            print(
                "UPSCALE",
                t,
                "request_rates: ",
                request_rates,
                "num_replicas: ",
                num_replicas,
                "target_num_replicas: ",
                self.num_tar,
                "upscale_counter: ",
                self.upscale_counter,
                "downscale_counter: ",
                self.downscale_counter,
            )
            self.upscale_counter = 0
            self.downscale_counter = 0

        # ARENA: 20 mins
        if (
            self.downscale_counter
            >= self.downscale_interval_seconds / config.time_tick_in_seconds
            and self.num_tar > self.num_min
        ):
            self.num_tar = num_replicas
            print(
                "DOWNSCALE",
                t,
                "request_rates: ",
                request_rates,
                "num_replicas: ",
                num_replicas,
                "target_num_replicas: ",
                self.num_tar,
                "upscale_counter: ",
                self.upscale_counter,
                "downscale_counter: ",
                self.downscale_counter,
            )
            self.upscale_counter = 0
            self.downscale_counter = 0

        return self.num_tar
