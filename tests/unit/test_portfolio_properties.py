"""Leakage and property tests for signals, targets and the planner (T-003)."""

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from trader.errors import InvalidInputError
from trader.numerics import portfolio_vol
from trader.params import Params
from trader.planner import AccountState, plan_orders
from trader.portfolio import compute_targets
from trader.signals import Signals, compute_signals

PARAMS = Params()


def weekdays(n, start=dt.date(2024, 1, 1)):
    days, day = [], start
    while len(days) < n:
        if day.weekday() < 5:
            days.append(day)
        day += dt.timedelta(days=1)
    return days


def random_series(rng, n, ids):
    out = {}
    for k in ids:
        steps = rng.normal(0.0003, 0.01, n)
        out[k] = list(100.0 * np.exp(np.cumsum(steps)))
    return out


def signal_snapshot(signals):
    return (
        sorted(signals.eligible), signals.ineligible_reason, signals.trend_score,
        signals.momentum_return, signals.sigma, signals.cov.to_numpy().tolist(),
    )


def test_future_values_cannot_change_signals():
    rng = np.random.default_rng(7)
    total, cut = 320, 290
    dates = weekdays(total)
    series = random_series(rng, total, ["A", "B", "C"])
    truncated = {k: v[:cut] for k, v in series.items()}
    before = signal_snapshot(compute_signals(dates[:cut], truncated, PARAMS))

    altered = {k: v[:cut] + list(rng.uniform(1.0, 1000.0, total - cut)) for k, v in series.items()}
    after = signal_snapshot(compute_signals(dates[:cut], {k: v[:cut] for k, v in altered.items()}, PARAMS))
    assert before == after


def test_series_longer_than_calendar_is_rejected():
    rng = np.random.default_rng(8)
    dates = weekdays(260)
    series = random_series(rng, 261, ["A"])
    with pytest.raises(InvalidInputError) as raised:
        compute_signals(dates, series, PARAMS)
    assert raised.value.code == "INVALID_CALENDAR"


def test_short_calendar_makes_everything_insufficient_history():
    rng = np.random.default_rng(9)
    dates = weekdays(200)
    result = compute_signals(dates, random_series(rng, 200, ["A", "B"]), PARAMS)
    assert result.eligible == frozenset()
    assert result.ineligible_reason == {"A": "insufficient_history", "B": "insufficient_history"}


def random_universe(rng):
    n = int(rng.integers(2, 9))
    ids = [f"I{i}" for i in range(n)]
    classes = {k: str(rng.choice(sorted(PARAMS.ASSET_CLASSES))) for k in ids}
    sigma = {k: float(rng.uniform(0.03, 0.6)) for k in ids}
    factors = rng.normal(size=(n, int(rng.integers(1, n + 1))))
    raw = factors @ factors.T + np.diag(rng.uniform(0.01, 0.5, n))
    d = np.sqrt(np.diag(raw))
    corr = raw / np.outer(d, d)
    vols = np.array([sigma[k] for k in ids])
    cov = pd.DataFrame(np.outer(vols, vols) * corr, index=ids, columns=ids)
    signals = Signals(
        eligible=frozenset(ids),
        ineligible_reason={},
        trend_score={k: float(rng.choice([0.0, 1 / 3, 2 / 3, 1.0])) for k in ids},
        momentum_return={k: float(rng.normal(0.02, 0.15)) for k in ids},
        sigma=sigma,
        cov=cov,
        trend_returns={},
    )
    return ids, classes, signals


@pytest.mark.parametrize("seed", range(300))
def test_targets_respect_every_limit(seed):
    rng = np.random.default_rng(seed)
    ids, classes, signals = random_universe(rng)
    result = compute_targets(signals, classes, PARAMS)
    tol = PARAMS.TOL
    assert all(w >= 0.0 for w in result.weights.values())
    assert all(w <= PARAMS.ASSET_CAP + tol for w in result.weights.values())
    for cls in set(classes.values()):
        assert sum(result.weights[k] for k in ids if classes[k] == cls) <= PARAMS.CLASS_CAP + tol
    assert portfolio_vol(result.weights, signals.cov, PARAMS) <= PARAMS.VOL_CEILING + tol
    assert result.cash >= -tol
    assert result.scale <= 1.0
    for k in result.eligible:
        assert result.weights[k] <= result.after_class_cap[k] + tol


@pytest.mark.parametrize("seed", range(200))
def test_plans_never_breach_limits_or_overdraw_settled_cash(seed):
    rng = np.random.default_rng(1000 + seed)
    ids, classes, signals = random_universe(rng)
    targets = compute_targets(signals, classes, PARAMS)
    prices = {k: float(rng.uniform(5.0, 200.0)) for k in ids}
    holdings = {k: int(rng.integers(0, 60)) for k in ids}
    state = AccountState(holdings=holdings, cash_settled=float(rng.uniform(0.0, 5000.0)),
                         cash_unsettled=float(rng.uniform(0.0, 1000.0)), open_orders=False,
                         reconciliation_clean=True, data_ok=True)
    result = plan_orders(targets, state, prices, signals.cov, classes, frozenset(targets.eligible), PARAMS)
    if result.status != "OK":
        assert result.status == "BLOCKED_CONSTRAINTS"
        assert result.orders == []
        return
    tol = PARAMS.TOL
    spend = sum(o.qty * o.ref_price * (1 + PARAMS.BUY_BUFFER) for o in result.orders if o.side == "BUY")
    buys = sum(1 for o in result.orders if o.side == "BUY")
    assert spend + PARAMS.COMMISSION_RESERVE * buys <= state.cash_settled + 1e-6
    final = dict(holdings)
    for o in result.orders:
        assert o.qty > 0
        final[o.id] = final.get(o.id, 0) + (o.qty if o.side == "BUY" else -o.qty)
    assert all(q >= 0 for q in final.values())
    weights = {k: final.get(k, 0) * prices[k] / result.nav for k in ids}
    assert all(w <= PARAMS.ASSET_CAP + tol for w in weights.values())
    for cls in set(classes.values()):
        assert sum(weights[k] for k in ids if classes[k] == cls) <= PARAMS.CLASS_CAP + tol
    assert portfolio_vol(weights, signals.cov, PARAMS) <= PARAMS.VOL_CEILING + tol
