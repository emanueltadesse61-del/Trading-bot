"""Signals per docs/portfolio-spec.md sections 2, 3 and 4.

Pure function: no I/O, no clock, no randomness. The caller passes the session
calendar ending at the decision date t and exactly one value per session for
every instrument; nothing is aligned or re-indexed here.
"""

import datetime as dt
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from trader.errors import InvalidInputError
from trader.numerics import is_finite_number
from trader.params import Params


@dataclass(frozen=True)
class Signals:
    eligible: frozenset[str]
    ineligible_reason: dict[str, str]
    trend_score: dict[str, float]
    momentum_return: dict[str, float]
    sigma: dict[str, float]
    cov: pd.DataFrame
    trend_returns: dict[str, dict[int, float]]


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    return isinstance(value, (float, np.floating)) and math.isnan(float(value))


def _validate(dates: Sequence[dt.date], tr_close: Mapping[str, Sequence[object]]) -> None:
    for earlier, later in zip(dates, list(dates)[1:]):
        if not later > earlier:
            raise InvalidInputError("INVALID_CALENDAR", f"dates not strictly increasing at {later}")
    for instrument, series in tr_close.items():
        if len(series) != len(dates):
            raise InvalidInputError(
                "INVALID_CALENDAR",
                f"{instrument}: {len(series)} values for {len(dates)} sessions",
            )
        for value in series:
            if _is_missing(value):
                continue
            if not is_finite_number(value) or float(value) <= 0.0:
                raise InvalidInputError("INVALID_PRICE_SERIES", f"{instrument}: invalid close {value!r}")


def _sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def compute_signals(
    dates: Sequence[dt.date],
    tr_close: Mapping[str, Sequence[float | None]],
    params: Params,
) -> Signals:
    _validate(dates, tr_close)
    window = params.window
    reasons: dict[str, str] = {}
    trend: dict[str, float] = {}
    momentum: dict[str, float] = {}
    sigma: dict[str, float] = {}
    trend_returns: dict[str, dict[int, float]] = {}
    returns: dict[str, np.ndarray] = {}

    for instrument in sorted(tr_close):
        series = list(tr_close[instrument])
        if len(dates) < window:
            reasons[instrument] = "insufficient_history"
            continue
        recent = series[-window:]
        missing = [i for i, v in enumerate(recent) if _is_missing(v)]
        if missing:
            first_valid = next((i for i, v in enumerate(recent) if not _is_missing(v)), None)
            if first_valid is None or max(missing) < first_valid:
                reasons[instrument] = "insufficient_history"
            else:
                reasons[instrument] = "missing_data"
            continue

        prices = np.array(recent, dtype=float)
        daily = prices[1:] / prices[:-1] - 1.0
        vol = float(np.std(daily[-params.VOL_WINDOW:], ddof=1) * math.sqrt(params.ANNUALISATION))
        if vol < params.MIN_VOL:
            reasons[instrument] = "min_vol"
            continue

        last = prices[-1]
        lookback_returns = {L: float(last / prices[-1 - L] - 1.0) for L in params.TREND_LOOKBACKS}
        mean_sign = sum(_sign(r) for r in lookback_returns.values()) / len(lookback_returns)
        trend[instrument] = max(0.0, mean_sign)
        momentum[instrument] = float(prices[-1 - params.MOM_SKIP] / prices[-1 - params.MOM_LONG] - 1.0)
        sigma[instrument] = vol
        trend_returns[instrument] = lookback_returns
        returns[instrument] = daily[-params.COV_WINDOW:]

    eligible = sorted(returns)
    if eligible:
        stacked = np.vstack([returns[i] for i in eligible])
        cov_matrix = np.atleast_2d(np.cov(stacked, ddof=1)) * params.ANNUALISATION
    else:
        cov_matrix = np.zeros((0, 0))
    cov = pd.DataFrame(cov_matrix, index=eligible, columns=eligible)

    return Signals(
        eligible=frozenset(eligible),
        ineligible_reason=reasons,
        trend_score=trend,
        momentum_return=momentum,
        sigma=sigma,
        cov=cov,
        trend_returns=trend_returns,
    )
