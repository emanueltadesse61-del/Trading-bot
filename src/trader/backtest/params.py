"""Frozen synthetic execution assumptions (backtest spec section 1)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from trader.numerics import is_finite_number

from .errors import BacktestInputError


@dataclass(frozen=True)
class BacktestParams:
    HALF_SPREAD: Mapping[str, float] = field(default_factory=dict)
    INITIAL_CASH: float = 10000.0
    COMMISSION_RATE: float = 0.0005
    COMMISSION_MIN: float = 3.0
    SLIPPAGE: float = 0.0005
    COST_MULTIPLIER: float = 1.0
    SETTLEMENT_LAG: int = 2
    DISTRIBUTION_LAG: int = 20
    ANNUALISATION: int = 252

    def __post_init__(self):
        for key in ("SETTLEMENT_LAG", "DISTRIBUTION_LAG", "ANNUALISATION"):
            if type(getattr(self, key)) is not int or getattr(self, key) < 1:
                raise BacktestInputError("BACKTEST_PARAMS", key)
        if not is_finite_number(self.INITIAL_CASH) or self.INITIAL_CASH <= 0:
            raise BacktestInputError("BACKTEST_PARAMS", "INITIAL_CASH")
        if not isinstance(self.HALF_SPREAD, Mapping):
            raise BacktestInputError("BACKTEST_COSTS", "HALF_SPREAD")
        object.__setattr__(
            self, "HALF_SPREAD", MappingProxyType(dict(self.HALF_SPREAD))
        )
        for key in ("COMMISSION_RATE", "COMMISSION_MIN", "SLIPPAGE", "COST_MULTIPLIER"):
            value = getattr(self, key)
            if (
                not is_finite_number(value)
                or value < 0
                or (key == "COST_MULTIPLIER" and value == 0)
            ):
                raise BacktestInputError("BACKTEST_COSTS", key)

    def validate_instruments(self, instruments):
        for name in instruments:
            if name not in self.HALF_SPREAD:
                raise BacktestInputError("BACKTEST_SPREAD", name)
            value = self.HALF_SPREAD[name]
            if (
                not is_finite_number(value)
                or value < 0
                or self.COST_MULTIPLIER * (value + self.SLIPPAGE) >= 1
            ):
                raise BacktestInputError("BACKTEST_COSTS", name)
