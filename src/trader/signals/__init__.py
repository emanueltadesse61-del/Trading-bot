"""Signal computation: price history up to t -> eligibility, scores, volatility, covariance."""

from trader.signals.core import Signals, compute_signals

__all__ = ["Signals", "compute_signals"]
