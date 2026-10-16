"""Unmodified Claude fixtures: the implementation is not its own oracle."""

import json
from datetime import date
from pathlib import Path

import pytest

from trader.backtest import (
    BacktestParams,
    Market,
    State,
    rebalance,
    run_backtest,
    scripted,
)
from trader.backtest.metrics import compute_metrics
from trader.backtest.schedule import decision_sessions
from trader.data import DistributionRecord, PriceRecord

FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures/backtest_cases.json").read_text()
)
D = date.fromisoformat


def market_for(case):
    inputs = case["inputs"]
    market = Market(
        tuple(map(D, inputs["calendar"])),
        tuple(PriceRecord(**{**r, "date": D(r["date"])}) for r in inputs["prices"]),
        tuple(
            DistributionRecord(**{**r, "ex_date": D(r["ex_date"])})
            for r in inputs["distributions"]
        ),
    )
    params = BacktestParams(HALF_SPREAD=inputs["half_spread"], **inputs["params"])
    orders = {D(d): rows for d, rows in inputs["scripted_orders"].items()}
    generator = scripted(orders, instruments=tuple(inputs["half_spread"]))
    return market, params, generator, sorted(orders)


def compare(actual, expected):
    if isinstance(expected, dict):
        assert set(actual) == set(expected)
        for key in expected:
            compare(actual[key], expected[key])
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for a, b in zip(actual, expected):
            compare(a, b)
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        assert actual == pytest.approx(expected, rel=1e-12, abs=1e-9)
    else:
        assert actual == expected


@pytest.mark.parametrize("case", FIXTURE["simulator_cases"], ids=lambda c: c["name"])
def test_simulator_fixture(case):
    market, params, generator, dates = market_for(case)
    result = run_backtest(
        market,
        generator,
        params,
        start=D(case["inputs"]["start"]),
        end=market.calendar[-1],
        decision_dates=dates,
    )
    compare(result.ledger, case["expected"])
    assert result == run_backtest(
        market,
        generator,
        params,
        start=D(case["inputs"]["start"]),
        end=market.calendar[-1],
        decision_dates=dates,
    )
    # Reconcile cash from actual ledger events, not the simulator's lot state.
    balance = params.INITIAL_CASH
    last = {}
    for row in result.ledger:
        for r in market.prices:
            if r.date == D(row["date"]):
                last[r.instrument] = r.close / (100 if r.unit == "GBX" else 1)
        for f in row["fills"]:
            signed = -1 if f["kind"] == "BUY" else 1
            balance += signed * f["qty"] * f["fill_price"] - f["commission"]
        balance += sum(x["cash"] for x in row["distributions"])
        assert row["settled"] + row["unsettled"] == pytest.approx(balance, abs=1e-9)
        assert row["nav"] == pytest.approx(
            balance + sum(q * last[i] for i, q in row["holdings"].items())
        )
        assert all(type(q) is int and q > 0 for q in row["holdings"].values())


@pytest.mark.parametrize("case", FIXTURE["rebalancer_cases"], ids=lambda c: c["name"])
def test_rebalancer_fixture(case):
    orders = rebalance(case["targets"], State(**case["state"]), case["prices"])
    assert [[o.id, o.side, o.qty] for o in orders] == case["orders"]


@pytest.mark.parametrize("case", FIXTURE["metric_cases"], ids=lambda c: c["name"])
def test_metric_fixture(case):
    compare(compute_metrics(list(map(D, case["dates"])), case["nav"]), case["expected"])


def test_schedule_fixture():
    case = FIXTURE["schedule_case"]
    for kind in ("weekly", "monthly"):
        assert [
            d.isoformat()
            for d in decision_sessions(list(map(D, case["calendar"])), kind)
        ] == case[kind]
