from policies.policies import (
    naive_spread,
    on_demand,
    optimal_ilp,
    round_robin,
    spot_hedge,
)

from policies.scheduler import (
    on_demand_only,
    spot_failover,
    spot_failover_no_safety,
    static_spot_provision,
)

from policies.workloads import arena_workload, maf_workload, poisson_workload

from policies.autoscalers import base_autoscaler, qps_autoscaler

__all__ = [
    "naive_spread",
    "on_demand",
    "optimal_ilp",
    "round_robin",
    "spot_hedge",
    "on_demand_only",
    "spot_failover",
    "spot_failover_no_safety",
    "static_spot_provision",
    "arena_workload",
    "maf_workload",
    "poisson_workload",
    "base_autoscaler",
    "qps_autoscaler",
]
