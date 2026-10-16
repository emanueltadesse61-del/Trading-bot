"""Order planner per docs/portfolio-spec.md section 6. Pure function.

The plan is a reference-price approximation, not approval to execute (spec 6.4).
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from trader.errors import InvalidInputError
from trader.numerics import is_finite_number, portfolio_vol, validate_covariance
from trader.params import Params
from trader.portfolio.targets import TargetResult

OK = "OK"


@dataclass(frozen=True)
class AccountState:
    holdings: Mapping[str, int]
    cash_settled: float
    cash_unsettled: float
    open_orders: bool
    reconciliation_clean: bool
    data_ok: bool


@dataclass(frozen=True)
class Order:
    id: str
    side: str
    qty: int
    ref_price: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PlanPass:
    delta: dict[str, int]
    buy_need: float
    k: float | None
    post_weights: dict[str, float]
    post_vol: float
    violations: list[str]
    added: list[str]


@dataclass(frozen=True)
class PlanResult:
    status: str
    orders: list[Order] = field(default_factory=list)
    nav: float | None = None
    actual: dict[str, float] = field(default_factory=dict)
    passes: list[PlanPass] = field(default_factory=list)


def _is_whole_number(value: object) -> bool:
    return isinstance(value, (int, np.integer)) and not isinstance(value, bool)


def _floor(x: float, params: Params) -> int:
    return math.floor(x + params.FLOOR_EPS)


def plan_orders(
    targets: TargetResult,
    state: AccountState,
    prices: Mapping[str, float],
    cov: pd.DataFrame,
    asset_class: Mapping[str, str],
    eligible: frozenset[str],
    params: Params,
) -> PlanResult:
    tol = params.TOL
    holdings = dict(state.holdings)
    w = targets.weights

    # 6.1 checks, in order; the first failure decides.
    for instrument, qty in holdings.items():
        if not _is_whole_number(qty) or qty < 0:
            raise InvalidInputError("INVALID_HOLDING", f"{instrument}: {qty!r}")
    for name in ("cash_settled", "cash_unsettled"):
        value = getattr(state, name)
        if not is_finite_number(value) or float(value) < 0.0:
            raise InvalidInputError("INVALID_CASH", f"{name}: {value!r}")
    if state.open_orders:
        return PlanResult(status="BLOCKED_OPEN_ORDERS")
    if not state.reconciliation_clean:
        return PlanResult(status="BLOCKED_RECONCILIATION")
    if not state.data_ok:
        return PlanResult(status="BLOCKED_DATA")
    held = sorted(i for i, qty in holdings.items() if qty > 0)
    if any(i not in asset_class for i in held):
        return PlanResult(status="BLOCKED_UNKNOWN_HOLDING")
    if any(i not in eligible for i in held):
        return PlanResult(status="BLOCKED_HELD_INELIGIBLE")
    names = sorted(set(held) | {i for i, weight in w.items() if weight > 0.0})
    for instrument in names:
        price = prices.get(instrument)
        if not is_finite_number(price) or float(price) <= 0.0:
            raise InvalidInputError("INVALID_PRICE", f"{instrument}: {price!r}")
    nav = state.cash_settled + state.cash_unsettled + sum(holdings.get(i, 0) * prices[i] for i in names)
    if not nav > 0.0:
        return PlanResult(status="BLOCKED_NAV")
    validate_covariance(cov, params)
    uncovered = [i for i in names if i not in cov.index]
    if uncovered:
        raise InvalidInputError("INVALID_COVARIANCE", f"no covariance for {uncovered}")

    # 6.3 steps 2-3: actual weights and the trade set with every reason that applies.
    actual = {i: holdings.get(i, 0) * prices[i] / nav for i in names}

    def class_weight(weights: Mapping[str, float], cls: str) -> float:
        return sum(weights[i] for i in names if asset_class[i] == cls)

    reasons: dict[str, list[str]] = {i: [] for i in names}
    actual_vol = portfolio_vol(actual, cov, params)
    for i in names:
        target = w.get(i, 0.0)
        if abs(actual[i] - target) > params.BAND + tol:
            reasons[i].append("band")
        if target == 0.0 and holdings.get(i, 0) > 0:
            reasons[i].append("exit")
        if actual[i] > params.ASSET_CAP + tol:
            reasons[i].append("asset_cap")
        if actual[i] > target + tol and class_weight(actual, asset_class[i]) > params.CLASS_CAP + tol:
            reasons[i].append("class_cap")
        if actual[i] > target + tol and actual_vol > params.VOL_CEILING + tol:
            reasons[i].append("vol")
    trade_set = {i for i in names if reasons[i]}

    passes: list[PlanPass] = []
    delta: dict[str, int] = {}
    for iteration in range(2):
        # Step 4: target shares for the trade set.
        delta = {i: 0 for i in names}
        for i in trade_set:
            delta[i] = _floor(w.get(i, 0.0) * nav / prices[i], params) - holdings.get(i, 0)

        # Step 5: settled-cash limit with the commission reserve.
        buys = [i for i in names if delta[i] > 0]
        gross = sum(delta[i] * prices[i] * (1.0 + params.BUY_BUFFER) for i in buys)
        need = gross + params.COMMISSION_RESERVE * len(buys)
        k = None
        if need > state.cash_settled:
            k = max(0.0, state.cash_settled - params.COMMISSION_RESERVE * len(buys)) / gross
            for i in buys:
                delta[i] = _floor(k * delta[i], params)

        # Step 6: post-trade check.
        post = {i: (holdings.get(i, 0) + delta[i]) * prices[i] / nav for i in names}
        post_vol = portfolio_vol(post, cov, params)
        violations: list[str] = []
        to_add: set[str] = set()
        for i in names:
            if post[i] > params.ASSET_CAP + tol:
                violations.append(f"asset_cap:{i}")
                to_add.add(i)
                reasons[i].append("repair_asset")
        for cls in sorted({asset_class[i] for i in names}):
            if class_weight(post, cls) > params.CLASS_CAP + tol:
                violations.append(f"class_cap:{cls}")
                for i in names:
                    if asset_class[i] == cls and post[i] > w.get(i, 0.0) + tol:
                        to_add.add(i)
                        reasons[i].append("repair_class")
        if post_vol > params.VOL_CEILING + tol:
            violations.append("vol")
            for i in names:
                if abs(post[i] - w.get(i, 0.0)) > tol:
                    to_add.add(i)
                    reasons[i].append("repair_vol")
        new = sorted(to_add - trade_set)
        passes.append(PlanPass(delta=dict(delta), buy_need=need, k=k, post_weights=post,
                               post_vol=post_vol, violations=violations, added=new))

        # Step 7: resolution.
        if not violations:
            break
        if iteration == 1 or not new:
            return PlanResult(status="BLOCKED_CONSTRAINTS", nav=nav, actual=actual, passes=passes)
        trade_set |= set(new)

    # Step 8: orders, sells first then buys, each in ascending id.
    orders = [
        Order(i, "SELL", -delta[i], float(prices[i]), tuple(sorted(set(reasons[i]))))
        for i in names if delta[i] < 0
    ]
    orders += [
        Order(i, "BUY", delta[i], float(prices[i]), tuple(sorted(set(reasons[i]))))
        for i in names if delta[i] > 0
    ]
    return PlanResult(status=OK, orders=orders, nav=nav, actual=actual, passes=passes)
