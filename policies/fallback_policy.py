from typing import Dict, List, Tuple, Type
import enum


class FallbackType(enum.Enum):
    OnDemand = "OnDemand"
    StaticSpotProvision = "StaticSpotProvision"
    SpotFailover = "SpotFailover"
    SpotFailoverNoSafety = "SpotFailoverNoSafety"


class FallbackPolicy:
    NAME = "FallbackPolicy"
    REGISTRY: Dict[str, Type["FallbackPolicy"]] = dict()

    def __init_subclass__(cls) -> None:
        if cls.NAME is None:
            return
        assert cls.NAME not in cls.REGISTRY, f"Name {cls.NAME} already exists"
        cls.REGISTRY[cls.NAME] = cls

    @classmethod
    def from_name(cls, name: str):
        assert name in cls.REGISTRY, (name, cls.REGISTRY)
        return cls.REGISTRY[name]

    def generate_mix_plan(
        self,
        t: int,
        i: int,
        spot_plan: List[List[int]],
        demand_plan: List[int],
        num_target,
        num_provision,
    ) -> Tuple[int, int]:
        raise NotImplementedError

    def reset(self) -> None:
        pass

    @property
    def name(self):
        return f"{self.NAME}"
