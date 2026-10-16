"""Shared strategy pipeline and explicit baseline policies."""

import math
from dataclasses import dataclass, field

from trader.data import JumpException
from trader.errors import InvalidInputError
from trader.params import Params
from trader.planner import AccountState, Order, plan_orders
from trader.portfolio import compute_targets
from trader.signals import compute_signals


@dataclass(frozen=True)
class State:
    holdings: dict[str, int]
    settled: float
    unsettled: float
    nav: float


@dataclass(frozen=True)
class Decision:
    status: str = "OK"
    orders: list = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Generator:
    name: str
    instruments: tuple[str, ...]
    function: object
    schedule: str | None = None
    exceptions: tuple[JumpException, ...] | None = None
    exceptions_version: str | None = None

    def __call__(self, d, state, market):
        return self.function(d, state, market)


def scripted(orders_by_date, *, instruments):
    # An explicit universe ensures a malformed unknown-id order cannot enlarge it.
    copied = {d: tuple(orders) for d, orders in orders_by_date.items()}
    return Generator(
        "scripted",
        tuple(instruments),
        lambda d, state, market: Decision(orders=list(copied.get(d, ()))),
    )


def strategy_generator(
    universe,
    asset_class,
    params=Params(),
    exceptions=(),
    exceptions_version="synthetic-v1",
):
    names, classes = tuple(sorted(universe)), dict(asset_class)

    def generate(d, state, market):
        diagnostics = {}
        try:
            built = market.build(d, names)
            signals = compute_signals(built.dates, built.tr_close, params)
            targets = compute_targets(signals, classes, params)
            diagnostics["targets"] = targets
            account = AccountState(
                state.holdings,
                state.settled,
                state.unsettled,
                False,
                True,
                built.data_ok,
            )
            plan = plan_orders(
                targets,
                account,
                built.trade_close,
                signals.cov,
                classes,
                signals.eligible,
                params,
            )
            diagnostics["plan"] = plan
            return Decision(
                plan.status, plan.orders if plan.status == "OK" else [], diagnostics
            )
        except InvalidInputError as exc:
            diagnostics["code"] = exc.code
            return Decision("BLOCKED_INVALID_INPUT", diagnostics=diagnostics)

    return Generator(
        "strategy",
        names,
        generate,
        exceptions=tuple(exceptions),
        exceptions_version=exceptions_version,
    )


def rebalance(targets, state, prices, params=Params()):
    if state.nav <= 0:
        return []
    delta = {}
    for name, weight in sorted(targets.items()):
        price = prices.get(name)
        if price is None:
            continue
        held = state.holdings.get(name, 0)
        actual = held * price / state.nav
        if abs(actual - weight) > params.BAND + params.TOL or (
            weight == 0 and held > 0
        ):
            delta[name] = (
                math.floor(weight * state.nav / price + params.FLOOR_EPS) - held
            )
    buys = [i for i in delta if delta[i] > 0]
    gross = sum(delta[i] * prices[i] * (1 + params.BUY_BUFFER) for i in buys)
    need = gross + params.COMMISSION_RESERVE * len(buys)
    if buys and need > state.settled:
        k = max(0, state.settled - params.COMMISSION_RESERVE * len(buys)) / gross
        for i in buys:
            delta[i] = math.floor(k * delta[i] + params.FLOOR_EPS)
    return [
        Order(i, side, abs(delta[i]), prices[i], ("baseline",))
        for side in ("SELL", "BUY")
        for i in sorted(delta)
        if (delta[i] < 0 if side == "SELL" else delta[i] > 0)
    ]


def _baseline(name, instruments, policy, params):
    names = tuple(instruments)

    def generate(d, state, market):
        built = market.build(d, names)
        if not built.data_ok:
            return Decision("BLOCKED_DATA")
        targets = policy(d, market, built)
        return Decision(orders=rebalance(targets, state, built.trade_close, params))

    return Generator(name, names, generate, schedule="monthly")


def sixty_forty(equity="VWRL", bond="VGOV", params=Params()):
    return _baseline(
        "sixty_forty", (equity, bond), lambda d, m, b: {equity: 0.6, bond: 0.4}, params
    )


def global_equity(instrument="VWRL", params=Params()):
    return _baseline(
        "global_equity", (instrument,), lambda d, m, b: {instrument: 1.0}, params
    )


def moving_average_10m(universe, params=Params()):
    names = tuple(universe)

    def policy(d, market, built):
        months = [s for s in market.monthly_sessions if s <= d][-10:]
        if len(months) < 10:
            return {}
        indices = [built.dates.index(s) for s in months]
        targets = {}
        for name in names:
            series = built.tr_close[name]
            values = [series[j] for j in indices]
            if series[-1] is not None and all(v is not None for v in values):
                targets[name] = 1 / len(names) if series[-1] > sum(values) / 10 else 0.0
        return targets

    return _baseline("moving_average_10m", names, policy, params)


def cash():
    return Generator("cash", (), lambda d, s, m: Decision(), schedule="monthly")
