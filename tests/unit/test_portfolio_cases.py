"""Every case in tests/fixtures/portfolio_cases.json (docs/portfolio-spec.md v1.2)."""

import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from trader.errors import InvalidInputError
from trader.params import Params
from trader.planner import AccountState, plan_orders
from trader.portfolio import compute_targets
from trader.signals import Signals, compute_signals

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((ROOT / "tests/fixtures/portfolio_cases.json").read_text())
TOL = FIXTURE["meta"]["tolerance_abs"]
PARAMS = Params()
WEIGHT_CASES = {c["name"]: c for c in FIXTURE["weights"]}
SIGNAL_CASES = {c["name"]: c for c in FIXTURE["signals"]}


def nan_if_none(value):
    return float("nan") if value is None else value


def covariance_from(inputs):
    ids = inputs["ids"]
    if "covariance" in inputs:
        return pd.DataFrame(np.array(inputs["covariance"], dtype=float), index=ids, columns=ids)
    corr = np.eye(len(ids))
    for a, b, rho in inputs["correlation"]:
        i, j = ids.index(a), ids.index(b)
        corr[i, j] = corr[j, i] = rho
    vols = np.array([inputs["vol_252d"][k] for k in ids], dtype=float)
    return pd.DataFrame(np.outer(vols, vols) * corr, index=ids, columns=ids)


def signals_from(inputs):
    ids = inputs["ids"]
    return Signals(
        eligible=frozenset(ids),
        ineligible_reason={},
        trend_score={k: nan_if_none(inputs["trend_score"][k]) for k in ids},
        momentum_return={k: nan_if_none(inputs["momentum_return"][k]) for k in ids},
        sigma={k: nan_if_none(inputs["sigma_60d"][k]) for k in ids},
        cov=covariance_from(inputs),
        trend_returns={},
    )


def assert_close(actual, expected, label):
    if isinstance(expected, dict):
        assert set(actual) == set(expected), f"{label}: keys {sorted(actual)} != {sorted(expected)}"
        for key, value in expected.items():
            assert_close(actual[key], value, f"{label}.{key}")
    elif isinstance(expected, list) and expected and isinstance(expected[0], list):
        assert len(actual) == len(expected), label
        for i, row in enumerate(expected):
            assert_close(list(actual[i]), row, f"{label}[{i}]")
    elif isinstance(expected, list) and all(isinstance(v, (int, float)) for v in expected):
        assert len(actual) == len(expected), label
        for i, value in enumerate(expected):
            assert_close(actual[i], value, f"{label}[{i}]")
    elif isinstance(expected, list):
        assert list(actual) == expected, f"{label}: {list(actual)} != {expected}"
    elif expected is None:
        assert actual is None, f"{label}: {actual} is not None"
    else:
        assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=TOL), f"{label}: {actual} != {expected}"


def target_case(name):
    case = WEIGHT_CASES[name]
    inputs = case["inputs"]
    signals = signals_from(inputs)
    return compute_targets(signals, inputs["asset_class"], PARAMS), signals, inputs


@pytest.mark.parametrize("case", FIXTURE["weights"], ids=lambda c: c["name"])
def test_weight_case(case):
    result, _, _ = target_case(case["name"])
    expected = case["expected"]
    assert_close(result.weights, expected["weights"], "weights")
    assert_close(result.cash, expected["cash"], "cash")
    assert result.eligible == expected["eligible"]
    assert result.ranking == expected["ranking"]
    assert result.top_n == expected["top_n"]
    for name in ("w_trend", "w_mom", "combined", "after_asset_cap", "after_class_cap"):
        assert_close(getattr(result, name), expected[name], name)
    assert_close(result.sigma_p_before_scale, expected["sigma_p_before_scale"], "sigma_p_before_scale")
    assert_close(result.scale, expected["scale"], "scale")


def run_plan(inputs):
    targets, signals, weight_inputs = target_case(inputs["targets_from"])
    state = AccountState(
        holdings=inputs["holdings"],
        cash_settled=inputs["cash_settled"],
        cash_unsettled=inputs["cash_unsettled"],
        open_orders=inputs["open_orders"],
        reconciliation_clean=inputs["reconciliation_clean"],
        data_ok=inputs["data_ok"],
    )
    return plan_orders(targets, state, inputs["prices"], signals.cov, weight_inputs["asset_class"],
                       frozenset(targets.eligible), PARAMS)


@pytest.mark.parametrize("case", FIXTURE["orders"], ids=lambda c: c["name"])
def test_order_case(case):
    result = run_plan(case["inputs"])
    expected = case["expected"]
    assert result.status == expected["status"]
    got_orders = [(o.side, o.id, o.qty, set(o.reasons)) for o in result.orders]
    want_orders = [(o["side"], o["id"], o["qty"], set(o["reasons"])) for o in expected["orders"]]
    assert got_orders == want_orders
    for o, e in zip(result.orders, expected["orders"]):
        assert_close(o.ref_price, e["ref_price"], f"{o.id}.ref_price")
    if "nav" in expected:
        assert_close(result.nav, expected["nav"], "nav")
        assert_close(result.actual, expected["actual"], "actual")
    if "passes" in expected:
        assert len(result.passes) == len(expected["passes"])
        for got, want in zip(result.passes, expected["passes"]):
            assert got.delta == want["delta"]
            assert_close(got.buy_need, want["buy_need"], "buy_need")
            assert_close(got.k, want["k"], "k")
            assert_close(got.post_weights, want["post_weights"], "post_weights")
            assert_close(got.post_vol, want["post_vol"], "post_vol")
            assert got.violations == want["violations"]
            assert got.added == want["added"]


def s1_inputs():
    case = SIGNAL_CASES["S1_signals_from_prices"]
    dates = [dt.date.fromisoformat(d) for d in case["inputs"]["dates"]]
    return dates, {k: list(v) for k, v in case["inputs"]["tr_close"].items()}


def test_signal_case():
    case = SIGNAL_CASES["S1_signals_from_prices"]
    dates, series = s1_inputs()
    result = compute_signals(dates, series, PARAMS)
    expected = case["expected"]
    for instrument, want in expected["per_instrument"].items():
        if want["eligible"]:
            assert instrument in result.eligible, instrument
            assert_close(result.trend_returns[instrument][63], want["R63"], f"{instrument}.R63")
            assert_close(result.trend_returns[instrument][126], want["R126"], f"{instrument}.R126")
            assert_close(result.trend_returns[instrument][252], want["R252"], f"{instrument}.R252")
            assert_close(result.trend_score[instrument], want["trend_score"], f"{instrument}.trend_score")
            assert_close(result.momentum_return[instrument], want["momentum_return"], f"{instrument}.momentum")
            assert_close(result.sigma[instrument], want["sigma"], f"{instrument}.sigma")
        else:
            assert instrument not in result.eligible, instrument
            assert result.ineligible_reason[instrument] == want["reason"], instrument
    assert list(result.cov.index) == expected["covariance_ids"]
    assert_close(result.cov.to_numpy().tolist(), expected["covariance_annualised"], "cov")


SIGNAL_OVERRIDES = {
    "dates[-1] = dates[-2]": lambda d, s: (d[:-1] + [d[-2]], s),
    "tr_close.UPTREND[-1] = -1.0": lambda d, s: (d, {**s, "UPTREND": s["UPTREND"][:-1] + [-1.0]}),
}


def invalid_call(case):
    inputs, stage = case["inputs"], case["stage"]
    if stage == "signals":
        dates, series = SIGNAL_OVERRIDES[inputs["override"]](*s1_inputs())
        return lambda: compute_signals(dates, series, PARAMS)
    if stage == "targets":
        base = dict(WEIGHT_CASES[inputs["base"]]["inputs"])
        for key, value in inputs["override"].items():
            base[key] = {**base[key], **value} if isinstance(value, dict) else value
        return lambda: compute_targets(signals_from(base), base["asset_class"], PARAMS)
    if stage == "plan":
        return lambda: run_plan(inputs)
    raise AssertionError(f"unknown stage {stage}")


@pytest.mark.parametrize("case", FIXTURE["invalid"], ids=lambda c: c["name"])
def test_invalid_case(case):
    call = invalid_call(case)
    with pytest.raises(InvalidInputError) as raised:
        call()
    assert raised.value.code == case["expected"]["error"]
