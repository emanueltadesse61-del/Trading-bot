"""Data quality defaults; independent of strategy parameters."""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class DataParams:
    JUMP_LIMIT: float = 0.25
    UNITS: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType({"GBP": 1.0, "GBX": 0.01})
    )
