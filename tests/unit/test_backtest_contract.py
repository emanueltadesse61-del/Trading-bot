"""Admission, causality, execution boundaries and synthetic strategy integration."""

import math
from dataclasses import replace
from datetime import date, timedelta

import pytest

from trader.backtest import (
    BacktestInputError,
    BacktestParams,
    Decision,
    Generator,
    Market,
    State,
    cash,
    global_equity,
    moving_average_10m,
    run_backtest,
    scripted,
    sixty_forty,
    strategy_generator,
)
from trader.backtest.adapter import DecisionMarket
from trader.backtest.metrics import compute_metrics
from trader.backtest.schedule import decision_sessions
from trader.backtest.simulator import fill_cost
from trader.data import (
    DataParams,
    DistributionRecord,
    JumpException,
    PriceRecord,
    build_dataset,
)

D = date.fromisoformat
A, B = "SYN_A", "SYN_B"
CAL = tuple(D("2024-01-08") + timedelta(days=i) for i in range(5))


def simple():
    return Market(CAL, tuple(PriceRecord(A, d, 100.0, "GBP", 100.0) for d in CAL))


def run(market=None, generator=None, params=None, **kwargs):
    return run_backtest(
        market or simple(),
        generator or scripted({}, instruments=(A,)),
        params or BacktestParams(HALF_SPREAD={A: 0.001}),
        start=kwargs.pop("start", CAL[0]),
        end=kwargs.pop("end", CAL[-1]),
        **kwargs,
    )


def code(expected, fn):
    with pytest.raises(BacktestInputError) as exc:
        fn()
    assert exc.value.code == expected


@pytest.mark.parametrize("bad", [None, 0, -1, float("nan"), float("inf")])
def test_bv1_invalid_close(bad):
    m = simple()
    code(
        "BACKTEST_DATA_EXCLUDED",
        lambda: run(
            replace(m, prices=(replace(m.prices[0], close=bad), *m.prices[1:]))
        ),
    )


@pytest.mark.parametrize("value", [1, -1, float("nan"), float("inf"), True])
def test_bv2_costs(value):
    code("BACKTEST_COSTS", lambda: run(params=BacktestParams(HALF_SPREAD={A: value})))


@pytest.mark.parametrize("qty", [-1, 0, 1.5, True])
def test_bv3_order_quantity(qty):
    code(
        "BACKTEST_ORDER",
        lambda: run(
            generator=scripted({CAL[0]: [(A, "BUY", qty)]}, instruments=(A,)),
            decision_dates=[CAL[0]],
        ),
    )


@pytest.mark.parametrize(
    "orders",
    [
        [(A, "BUY", 1), (A, "SELL", 1)],
        [(A, "BUY", 1), (A, "BUY", 1)],
        [(B, "BUY", 1)],
        [(A, "HOLD", 1)],
        ["malformed"],
    ],
)
def test_bv4_bv5_orders(orders):
    code(
        "BACKTEST_ORDER",
        lambda: run(
            generator=scripted({CAL[0]: orders}, instruments=(A,)),
            decision_dates=[CAL[0]],
        ),
    )


@pytest.mark.parametrize(
    "dates",
    [[CAL[1], CAL[0]], [CAL[0], CAL[0]], [CAL[-1]], [D("2024-01-07")], ["2024-01-08"]],
)
def test_bv6_schedule(dates):
    code("BACKTEST_SCHEDULE", lambda: run(decision_dates=dates))


@pytest.mark.parametrize("key", ["SETTLEMENT_LAG", "DISTRIBUTION_LAG", "ANNUALISATION"])
@pytest.mark.parametrize("value", [0, -1, 1.5, True])
def test_bv7_params(key, value):
    code("BACKTEST_PARAMS", lambda: BacktestParams(**{key: value}))


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True])
def test_bv8_open(value):
    m = simple()
    code(
        "BACKTEST_OPEN",
        lambda: run(
            replace(m, prices=(replace(m.prices[0], open=value), *m.prices[1:]))
        ),
    )


@pytest.mark.parametrize("calendar", [(), CAL[::-1], (CAL[0], CAL[0]), ("wrong",)])
def test_calendar_invalid(calendar):
    code("BACKTEST_CALENDAR", lambda: run(replace(simple(), calendar=calendar)))


def test_bounds_spread_initial_cash_and_cost_params():
    code("BACKTEST_CALENDAR", lambda: run(start=CAL[-1]))
    code("BACKTEST_CALENDAR", lambda: run(end=D("2024-01-20")))
    code("BACKTEST_SPREAD", lambda: run(params=BacktestParams()))
    for value in (0, -1, float("nan"), True):
        code("BACKTEST_PARAMS", lambda: BacktestParams(INITIAL_CASH=value))
    for key, value in [
        ("COST_MULTIPLIER", 0),
        ("SLIPPAGE", -1),
        ("COMMISSION_RATE", float("inf")),
        ("COMMISSION_MIN", True),
    ]:
        code("BACKTEST_COSTS", lambda: BacktestParams(**{key: value}))
    code("BACKTEST_SCHEDULE", lambda: run(schedule="daily"))
    code("BACKTEST_SCHEDULE", lambda: run(schedule="weekly", decision_dates=[]))


def test_duplicate_scoping_and_invalid_future_open():
    m = simple()
    code(
        "BACKTEST_DATA_EXCLUDED",
        lambda: run(replace(m, prices=(*m.prices, m.prices[0]))),
    )
    outside = replace(m.prices[0], instrument=B, close=None)
    future = replace(
        m.prices[-1], date=CAL[-1] + timedelta(days=1), close=None, open=-1
    )
    assert run(replace(m, prices=(*m.prices, outside, outside, future, future))) == run(
        m
    )


@pytest.mark.parametrize("side", ["BUY", "SELL"])
@pytest.mark.parametrize("spread", [0.001, 0.4])
def test_exact_cost_stress(side, spread):
    for m in (1, 2):
        p = BacktestParams(HALF_SPREAD={A: spread}, SLIPPAGE=0, COST_MULTIPLIER=m)
        p.validate_instruments([A])
        price, fee, cost = fill_cost(100, A, side, 1000, p)
        expected = 100 * (1 + m * spread if side == "BUY" else 1 - m * spread)
        assert price == expected
        assert fee == max(m * 3, m * 0.0005 * 1000 * expected)
        assert cost == pytest.approx(1000 * 100 * m * spread)


def synthetic_history(n=360):
    sessions, day = [], D("2022-01-03")
    while len(sessions) < n:
        if day.weekday() < 5:
            sessions.append(day)
        day += timedelta(days=1)
    records = []
    for name, phase in [(A, 0), (B, 1)]:
        price = 100.0
        for i, d in enumerate(sessions):
            price *= 1 + 0.001 + 0.002 * math.sin(i + phase)
            records.append(PriceRecord(name, d, price, "GBP", price * 1.0001))
    return Market(tuple(sessions), tuple(records))


@pytest.mark.parametrize("schedule", ["weekly", "monthly"])
def test_strategy_shared_pipeline(schedule, monkeypatch):
    import trader.backtest.generators as module

    calls = []
    for name in ("compute_signals", "compute_targets", "plan_orders"):
        original = getattr(module, name)

        def wrap(*args, _name=name, _fn=original, **kw):
            calls.append(_name)
            return _fn(*args, **kw)

        monkeypatch.setattr(module, name, wrap)
    m = synthetic_history()
    g = strategy_generator((A, B), {A: "equity", B: "bond"})
    result = run_backtest(
        m,
        g,
        BacktestParams(HALF_SPREAD={A: 0.001, B: 0.001}),
        start=m.calendar[270],
        end=m.calendar[-1],
        schedule=schedule,
    )
    assert any(d["status"] == "OK" and d["orders"] for d in result.decisions)
    assert calls == ["compute_signals", "compute_targets", "plan_orders"] * len(
        result.decisions
    )
    jump_date = m.calendar[300]
    jumped = replace(
        m,
        prices=tuple(
            replace(r, close=r.close * 2) if r.date == jump_date else r
            for r in m.prices
        ),
    )
    blocked = run_backtest(
        jumped,
        g,
        BacktestParams(HALF_SPREAD={A: 0.001, B: 0.001}),
        start=m.calendar[270],
        end=m.calendar[-1],
        schedule=schedule,
    )
    assert any(
        d["status"] == "BLOCKED_DATA" and not d["orders"] for d in blocked.decisions
    )


def test_causal_adapter_and_full_snapshot_digest(monkeypatch):
    m = synthetic_history()
    d, future = m.calendar[280], m.calendar[310]
    base_exception = JumpException(A, m.calendar[20], "synthetic", "2026-01-01")
    later = JumpException(A, future, "later synthetic", "2026-01-01")
    m = replace(m, exceptions=(base_exception, later))
    modified = replace(
        m,
        prices=tuple(
            replace(r, close=r.close * 1.01, open=r.open * 1.02)
            if r.date == future
            else r
            for r in m.prices
        ),
        distributions=(DistributionRecord(A, future, 0.5, "GBP"),),
        exceptions=(base_exception, replace(later, reason="changed future")),
    )
    import trader.backtest.adapter as adapter

    original = adapter.build_dataset
    seen = []

    def guarded(
        calendar, t, universe, prices, distributions, exceptions, *args, **kwargs
    ):
        assert all(r.date <= t for r in prices)
        assert all(r.ex_date <= t for r in distributions)
        assert all(r.date <= t for r in exceptions)
        assert all(s <= t for s in calendar)
        seen.append(t)
        return original(
            calendar, t, universe, prices, distributions, exceptions, *args, **kwargs
        )

    monkeypatch.setattr(adapter, "build_dataset", guarded)
    p = BacktestParams(HALF_SPREAD={A: 0.001, B: 0.001})

    def execute(data):
        g = strategy_generator(
            (A, B), {A: "equity", B: "bond"}, exceptions=data.exceptions
        )
        return run_backtest(
            data, g, p, start=m.calendar[270], end=m.calendar[-1], decision_dates=[d]
        )

    a, b = execute(m), execute(modified)
    assert a.decisions == b.decisions
    assert a.decisions[0]["exceptions_count"] == 1
    expected = build_dataset(
        m.calendar,
        m.calendar[-1],
        (A, B),
        m.prices,
        (),
        m.exceptions,
        DataParams(),
        "research",
        "synthetic-v1",
    )
    assert a.inputs["exceptions_digest"] == expected.exceptions_digest
    assert a.inputs["exceptions_digest"] != b.inputs["exceptions_digest"]
    assert d in seen


def test_strategy_invalid_cash_and_held_stale():
    m = synthetic_history()
    d = m.calendar[-1]
    g = strategy_generator((A, B), {A: "equity", B: "bond"})
    view = DecisionMarket(m, tuple(decision_sessions(m.calendar, "monthly")))
    result = g(d, State({}, -1.991, 0, -1.991), view)
    assert result.status == "BLOCKED_INVALID_INPUT"
    assert result.diagnostics["code"] == "INVALID_CASH"
    missing = replace(
        m, prices=tuple(r for r in m.prices if not (r.instrument == A and r.date == d))
    )
    result = g(d, State({A: 1}, 9000, 0, 9100), replace(view, data=missing))
    assert result.status == "BLOCKED_HELD_INELIGIBLE"


@pytest.mark.parametrize(
    "factory", [lambda: sixty_forty(A, B), lambda: global_equity(A)]
)
def test_monthly_baselines_band_and_first_trade(factory):
    m = synthetic_history()
    # Flat prices isolate band behavior from trend/volatility.
    m = replace(m, prices=tuple(replace(r, close=100.0, open=100.0) for r in m.prices))
    result = run_backtest(
        m,
        factory(),
        BacktestParams(HALF_SPREAD={A: 0.001, B: 0.001}),
        start=m.calendar[0],
        end=m.calendar[-1],
    )
    assert result.decisions[0]["orders"]
    assert all(not d["orders"] for d in result.decisions[1:])
    assert all(d["status"] == "OK" for d in result.decisions)


def test_ma_entry_exit_and_missing_history_retains_holding():
    m = synthetic_history(500)
    month_ends = tuple(decision_sessions(m.calendar, "monthly"))
    d = month_ends[12]
    g = moving_average_10m((A, B))
    view = DecisionMarket(m.at(d, (A, B)), month_ends)
    result = g(d, State({}, 10000, 0, 10000), view)
    assert any(o.side == "BUY" for o in result.orders)
    # Smooth descending prices pass the jump gate and fall below the MA.
    falling = replace(
        m,
        prices=tuple(
            replace(r, close=300 - m.calendar.index(r.date) * 0.1) for r in m.prices
        ),
    )
    result = g(
        d,
        State({A: 10}, 9000, 0, 10000),
        DecisionMarket(falling.at(d, (A, B)), month_ends),
    )
    assert any(o.id == A and o.side == "SELL" and o.qty == 10 for o in result.orders)
    missing = replace(
        m,
        prices=tuple(
            r for r in m.prices if not (r.instrument == A and r.date == month_ends[8])
        ),
    )
    result = g(
        d,
        State({A: 10}, 9000, 0, 10000),
        DecisionMarket(missing.at(d, (A, B)), month_ends),
    )
    assert all(o.id != A for o in result.orders)
    early = month_ends[3]
    assert not g(
        early,
        State({A: 10}, 9000, 0, 10000),
        DecisionMarket(m.at(early, (A, B)), month_ends),
    ).orders


def test_cash_baseline_and_anomaly_totals():
    result = run(generator=cash())
    assert all(row["nav"] == 10000 for row in result.ledger)
    assert result.metrics["sharpe"] is None
    assert result.metrics["undefined"]["sharpe"] == "ZERO_STDEV"
    metrics = compute_metrics(CAL[:3], [10, 0, 5], fills=[])
    assert metrics["turnover"] is None and metrics["cost_drag"] is None
    assert metrics["undefined"]["turnover"] == "NON_POSITIVE_NAV"


def test_shortfall_blocks_next_strategy_decision():
    # Script only the setup; the post-shortfall decision uses the real strategy.
    prices = tuple(PriceRecord(A, d, 1.0, "GBP", 1.0) for d in CAL)
    market = Market(CAL, prices)
    strategy = strategy_generator((A,), {A: "equity"})

    def policy(d, state, view):
        if d == CAL[0]:
            return Decision(orders=[(A, "BUY", 1)])
        if d == CAL[1]:
            return Decision(orders=[(A, "SELL", 1)])
        return strategy(d, state, view)

    generator = Generator("shortfall_then_strategy", (A,), policy)
    result = run(
        market,
        generator,
        BacktestParams(HALF_SPREAD={A: 0.0}, INITIAL_CASH=4.01),
        decision_dates=list(CAL[:-1]),
    )
    assert result.decisions[2]["status"] == "BLOCKED_INVALID_INPUT"
    assert result.decisions[2]["diagnostics"]["code"] == "INVALID_CASH"
    assert result.decisions[2]["orders"] == []
    assert result.totals["settled_negative_sessions"] == 3
    assert result.totals["fill_statuses"]["SHORTFALL"] == 1
    assert result.totals["insolvent_on"] == CAL[2].isoformat()


def test_missing_open_expires_and_sell_without_holding():
    market = simple()
    market = replace(
        market,
        prices=tuple(
            replace(r, open=None) if r.date == CAL[1] else r for r in market.prices
        ),
    )
    result = run(
        market,
        scripted({CAL[0]: [(A, "BUY", 1)], CAL[2]: [(A, "SELL", 1)]}, instruments=(A,)),
        decision_dates=[CAL[0], CAL[2]],
    )
    assert result.ledger[1]["cancelled"][0]["reason"] == "NO_PRICE"
    assert result.ledger[3]["cancelled"][0]["reason"] == "NO_HOLDING"
    assert not any(row["fills"] for row in result.ledger)


def test_baseline_blocks_bad_data_and_negative_cash_buys():
    m = simple()
    g = global_equity(A)
    view = DecisionMarket(m, ())
    assert not g(CAL[-1], State({}, -1, 10000, 9999), view).orders
    jumped = replace(
        m,
        prices=tuple(
            replace(r, close=200.0) if r.date == CAL[-1] else r for r in m.prices
        ),
    )
    result = g(CAL[-1], State({}, 10000, 0, 10000), DecisionMarket(jumped, ()))
    assert result.status == "BLOCKED_DATA" and not result.orders


def test_later_invalid_exception_is_not_seen_early():
    m = replace(simple(), exceptions=(JumpException(A, CAL[3], "", "invalid"),))
    early = m.at(CAL[1], (A,)).build(CAL[1], (A,))
    assert early.data_ok
    assert early.report == []
    assert not m.build(CAL[-1], (A,)).data_ok


def test_params_mapping_is_copied_and_frozen():
    spreads = {A: 0.001}
    params = BacktestParams(HALF_SPREAD=spreads)
    spreads[A] = 1
    assert params.HALF_SPREAD[A] == 0.001
    with pytest.raises(TypeError):
        params.HALF_SPREAD[A] = 1


def test_positive_metrics_include_costs_and_turnover():
    fills = [dict(qty=5, fill_price=10.0, commission=3.0, spread_slippage_cost=0.5)]
    result = compute_metrics(CAL[:3], [100, 101, 102], fills=fills)
    assert result["turnover"] == pytest.approx(50 / (2 * 101) * 252 / 2)
    assert result["cost_drag"] == pytest.approx(3.5 / 101 * 252 / 2)


def test_market_approval_used_and_recorded():
    m = synthetic_history()
    jump = m.calendar[280]
    m = replace(m, prices=tuple(replace(r, close=r.close * 1.5, open=r.open * 1.5)
                                if r.instrument == A and r.date >= jump else r for r in m.prices),
                exceptions=(JumpException(A, jump, 'synthetic approved jump', '2026-01-01'),),
                exceptions_version='owner-snapshot-v7')
    generator = strategy_generator((A, B), {A: 'equity', B: 'bond'})
    p = BacktestParams(HALF_SPREAD={A: .001, B: .001})
    def execute(g, market=m):
        return run_backtest(market, g, p, start=m.calendar[270], end=m.calendar[-1], decision_dates=[jump])
    result = execute(generator)
    assert result.decisions[0]['status'] != 'BLOCKED_DATA'
    assert result.decisions[0]['exceptions_count'] == 1
    assert result.inputs['exceptions_version'] == 'owner-snapshot-v7'
    assert result.inputs['exceptions_digest'] == m.exceptions_digest
    confirmed = replace(generator, exceptions=m.exceptions, exceptions_version=m.exceptions_version)
    assert execute(confirmed) == result
    assert execute(generator, replace(m, exceptions=())).decisions[0]['status'] == 'BLOCKED_DATA'
    for conflicting in (replace(generator, exceptions=()),
                        replace(generator, exceptions_version='different'),
                        replace(generator, exceptions=(replace(m.exceptions[0], reason='different'),))):
        code('BACKTEST_PARAMS', lambda: execute(conflicting))


def test_rebalance_omitted_holding_is_not_a_zero_target_exit():
    from trader.backtest import rebalance
    state = State({A: 10, B: 10}, 1000, 0, 3000)
    orders = rebalance({A: 0.}, state, {A: 100., B: 100.})
    assert [(o.id, o.side, o.qty) for o in orders] == [(A, 'SELL', 10)]


def test_baseline_nonpositive_nav_is_reported():
    for nav in (0., -1.):
        response = global_equity(A)(CAL[-1], State({}, nav, 0, nav), DecisionMarket(simple(), ()))
        assert response.status == 'BLOCKED_NAV' and not response.orders
