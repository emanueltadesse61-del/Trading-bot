"""Deterministic next-open simulator. Synthetic use only in T-008."""

import math
from collections import Counter
from dataclasses import dataclass
from datetime import date

from trader.data import DataParams
from trader.data.build import exceptions_digest
from trader.numerics import is_finite_number
from trader.planner import Order

from .adapter import DecisionMarket
from .errors import BacktestInputError
from .generators import Decision, State
from .metrics import compute_metrics
from .schedule import decision_sessions, validate_calendar


@dataclass(frozen=True)
class BacktestResult:
    ledger: list[dict]
    decisions: list[dict]
    metrics: dict
    totals: dict
    inputs: dict


def _orders(orders, names):
    valid, seen = [], set()
    for raw in orders:
        if isinstance(raw, Order):
            instrument, side, qty = raw.id, raw.side, raw.qty
        elif isinstance(raw, (tuple, list)) and len(raw) == 3:
            instrument, side, qty = raw
        else:
            raise BacktestInputError("BACKTEST_ORDER", repr(raw))
        if (
            not isinstance(instrument, str)
            or instrument not in names
            or instrument in seen
            or side not in ("BUY", "SELL")
            or type(qty) is not int
            or qty <= 0
        ):
            raise BacktestInputError("BACKTEST_ORDER", repr(raw))
        seen.add(instrument)
        valid.append((instrument, side, qty))
    return sorted(valid, key=lambda o: (o[1] == "BUY", o[0]))


def fill_cost(open_price, instrument, side, quantity, params):
    m = params.COST_MULTIPLIER
    spread = m * (params.HALF_SPREAD[instrument] + params.SLIPPAGE)
    price = open_price * (1 + spread if side == "BUY" else 1 - spread)
    fee = (
        max(m * params.COMMISSION_MIN, m * params.COMMISSION_RATE * quantity * price)
        if quantity
        else 0.0
    )
    return price, fee, quantity * abs(price - open_price)


def run_backtest(
    market, generator, params, *, start, end, schedule=None, decision_dates=None
):
    calendar = market.calendar
    validate_calendar(calendar)
    if (
        type(start) is not date
        or type(end) is not date
        or start not in calendar
        or end not in calendar
        or start >= end
    ):
        raise BacktestInputError("BACKTEST_CALENDAR", "invalid run bounds")
    names = tuple(generator.instruments)
    params.validate_instruments(names)
    # Market is the sole source of run approvals. Legacy generator arguments
    # are optional assertions, never an override of data or provenance.
    if (generator.exceptions is not None
            and exceptions_digest(generator.exceptions) != market.exceptions_digest):
        raise BacktestInputError("BACKTEST_PARAMS", "conflicting exception snapshots")
    if (generator.exceptions_version is not None
            and generator.exceptions_version != market.exceptions_version):
        raise BacktestInputError("BACKTEST_PARAMS", "conflicting exception versions")
    bounded = market.at(end, names)
    built = bounded.build(end, names)
    non_excluding = {
        "DATA_STALE",
        "DATA_JUMP",
        "DATA_JUMP_APPROVED",
        "DATA_INVALID_EXCEPTION",
    }
    excluding = [i for i in built.report if i.code not in non_excluding]
    if excluding:
        raise BacktestInputError("BACKTEST_DATA_EXCLUDED", repr(excluding))
    units = DataParams().UNITS
    for r in bounded.prices:
        if r.open is not None and (
            not is_finite_number(r.open) or r.open * units[r.unit] <= 0
        ):
            raise BacktestInputError("BACKTEST_OPEN", f"{r.instrument} {r.date}")
    if decision_dates is not None:
        if schedule is not None:
            raise BacktestInputError(
                "BACKTEST_SCHEDULE", "choose schedule or decision_dates"
            )
        dates = tuple(decision_dates)
        if any(
            type(d) is not date or d not in calendar or not start <= d < end
            for d in dates
        ) or any(a >= b for a, b in zip(dates, dates[1:])):
            raise BacktestInputError("BACKTEST_SCHEDULE", "invalid decision dates")
        schedule_name = "explicit"
    else:
        schedule_name = schedule or generator.schedule or "weekly"
        if generator.schedule and schedule_name != generator.schedule:
            raise BacktestInputError("BACKTEST_SCHEDULE", "baseline requires monthly")
        dates = tuple(
            d for d in decision_sessions(calendar, schedule_name) if start <= d < end
        )
    monthly = tuple(decision_sessions(calendar, "monthly"))
    prices = {(r.instrument, r.date): r for r in bounded.prices}
    dividends = {}
    for r in bounded.distributions:
        dividends.setdefault(r.ex_date, []).append(r)
    holdings, last_close, lots = {}, {}, []
    settled, pending, ledger, decisions = float(params.INITIAL_CASH), [], [], []
    for index in range(calendar.index(start), calendar.index(end) + 1):
        d = calendar[index]
        settled += sum(amount for due, amount in lots if due <= index)
        lots = [(due, amount) for due, amount in lots if due > index]
        distributions, fills, cancellations = [], [], []
        for r in sorted(dividends.get(d, ()), key=lambda r: r.instrument):
            shares = holdings.get(r.instrument, 0)
            if shares:
                amount = shares * r.amount * units[r.unit]
                lots.append((index + params.DISTRIBUTION_LAG, amount))
                distributions.append(
                    dict(instrument=r.instrument, shares=shares, cash=amount)
                )
        for name, side, ordered in pending:
            record = prices.get((name, d))
            if record is None or record.open is None:
                cancellations.append(
                    dict(instrument=name, side=side, qty=ordered, reason="NO_PRICE")
                )
                continue
            opening = record.open * units[record.unit]
            price, _, _ = fill_cost(opening, name, side, 1, params)
            if side == "SELL":
                qty = min(ordered, holdings.get(name, 0))
                if qty == 0:
                    cancellations.append(
                        dict(
                            instrument=name, side=side, qty=ordered, reason="NO_HOLDING"
                        )
                    )
                    continue
            else:
                qty = min(ordered, max(0, math.floor(settled / price)))
                # Binary search is equivalent to the specified decrement loop:
                # total cost is monotone for non-negative rates/minimum.
                lo, hi = 0, qty
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    _, fee, _ = fill_cost(opening, name, side, mid, params)
                    if mid * price + fee <= settled + 1e-9:
                        lo = mid
                    else:
                        hi = mid - 1
                qty = lo
            price, fee, spread_cost = fill_cost(opening, name, side, qty, params)
            if side == "SELL":
                holdings[name] -= qty
                if not holdings[name]:
                    del holdings[name]
                net = qty * price - fee
                if net >= 0:
                    lots.append((index + params.SETTLEMENT_LAG, net))
                else:
                    settled += net
                status = "SHORTFALL" if settled < 0 else "OK"
            else:
                if qty:
                    settled -= qty * price + fee
                    holdings[name] = holdings.get(name, 0) + qty
                status = (
                    "OK"
                    if qty == ordered
                    else ("CASH_LIMITED" if qty else "SKIPPED_CASH")
                )
            fills.append(
                dict(
                    kind=side,
                    instrument=name,
                    qty=qty,
                    fill_price=price,
                    commission=fee,
                    spread_slippage_cost=spread_cost,
                    status=status,
                )
            )
        pending = []
        stale = []
        for name in holdings:
            record = prices.get((name, d))
            if record is None:
                stale.append(name)
            else:
                last_close[name] = record.close * units[record.unit]
        unsettled = sum(amount for _, amount in lots)
        nav = settled + unsettled + sum(q * last_close[i] for i, q in holdings.items())
        ledger.append(
            dict(
                date=d.isoformat(),
                settled=settled,
                unsettled=unsettled,
                holdings=dict(sorted(holdings.items())),
                nav=nav,
                stale=sorted(stale),
                fills=fills,
                cancelled=cancellations,
                distributions=distributions,
                settled_negative=settled < 0,
            )
        )
        if d in dates:
            view = market.at(d, names)
            response = generator(
                d,
                State(dict(holdings), settled, unsettled, nav),
                DecisionMarket(view, monthly),
            )
            if not isinstance(response, Decision):
                response = Decision(orders=response)
            pending = _orders(response.orders, names)
            if response.status != "OK" and pending:
                raise BacktestInputError(
                    "BACKTEST_ORDER", "blocked decision returned orders"
                )
            decisions.append(
                dict(
                    date=d.isoformat(),
                    status=response.status,
                    orders=[list(o) for o in pending],
                    diagnostics=response.diagnostics,
                    exceptions_count=len(view.exceptions),
                )
            )
    all_fills = [f for row in ledger for f in row["fills"]]
    totals = dict(
        commission=sum(f["commission"] for f in all_fills),
        spread_slippage_cost=sum(f["spread_slippage_cost"] for f in all_fills),
        distributions_received=sum(
            x["cash"] for row in ledger for x in row["distributions"]
        ),
        fill_statuses=dict(Counter(f["status"] for f in all_fills)),
        settled_negative_sessions=sum(r["settled_negative"] for r in ledger),
        stale_sessions=sum(bool(r["stale"]) for r in ledger),
        blocked_decisions=dict(
            Counter(r["status"] for r in decisions if r["status"] != "OK")
        ),
    )
    metrics = compute_metrics(
        [date.fromisoformat(r["date"]) for r in ledger],
        [r["nav"] for r in ledger],
        annualisation=params.ANNUALISATION,
        fills=all_fills,
    )
    totals["insolvent_on"] = metrics["insolvent_on"]
    return BacktestResult(
        ledger,
        decisions,
        metrics,
        totals,
        dict(
            start=start,
            end=end,
            schedule=schedule_name,
            decision_dates=dates,
            params=params,
            generator=generator.name,
            exceptions_version=market.exceptions_version,
            exceptions_digest=market.exceptions_digest,
        ),
    )
