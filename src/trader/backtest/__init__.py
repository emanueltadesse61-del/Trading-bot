"""Synthetic backtest machinery; no downloads, broker access or edge claims."""

from .adapter import Market, market_from_raw
from .errors import BacktestInputError
from .generators import (
    Decision,
    Generator,
    State,
    cash,
    global_equity,
    moving_average_10m,
    rebalance,
    scripted,
    sixty_forty,
    strategy_generator,
)
from .params import BacktestParams
from .simulator import BacktestResult, run_backtest

__all__ = [
    "Market",
    "market_from_raw",
    "BacktestInputError",
    "Decision",
    "Generator",
    "State",
    "cash",
    "global_equity",
    "moving_average_10m",
    "rebalance",
    "scripted",
    "sixty_forty",
    "strategy_generator",
    "BacktestParams",
    "BacktestResult",
    "run_backtest",
]
