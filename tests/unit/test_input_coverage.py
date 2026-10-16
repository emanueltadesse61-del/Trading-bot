"""Input-coverage and covariance-label regressions (Codex T-003 review B1, B2; decision 0005).

Independent of the reference fixture: each case is a malformed input that must raise
the named InvalidInputError instead of producing a plausible-looking allocation.
"""

import math

import pandas as pd
import pytest

from trader.errors import InvalidInputError
from trader.numerics import portfolio_vol, validate_covariance
from trader.params import Params
from trader.planner import AccountState, plan_orders
from trader.portfolio import compute_targets
from trader.signals import Signals

PARAMS = Params()


def one_asset(sigma=None, trend=None, momentum=None, cov=None, eligible=("A",)):
    return Signals(
        eligible=frozenset(eligible),
        ineligible_reason={},
        trend_score={"A": 1.0} if trend is None else trend,
        momentum_return={"A": 0.1} if momentum is None else momentum,
        sigma={"A": 0.2} if sigma is None else sigma,
        cov=pd.DataFrame([[0.04]], index=["A"], columns=["A"]) if cov is None else cov,
        trend_returns={},
    )


def expect(code, call):
    with pytest.raises(InvalidInputError) as raised:
        call()
    assert raised.value.code == code


# B1 — every eligible id must carry its inputs.

def test_eligible_id_without_asset_class_is_rejected():
    expect("INVALID_ASSET_CLASS", lambda: compute_targets(one_asset(), {}, PARAMS))


def test_eligible_id_without_sigma_is_rejected():
    expect("INVALID_SIGMA", lambda: compute_targets(one_asset(sigma={}), {"A": "equity"}, PARAMS))


def test_eligible_id_without_trend_score_is_rejected():
    expect("INVALID_SIGNAL", lambda: compute_targets(one_asset(trend={}), {"A": "equity"}, PARAMS))


def test_eligible_id_without_momentum_is_rejected():
    expect("INVALID_SIGNAL", lambda: compute_targets(one_asset(momentum={}), {"A": "equity"}, PARAMS))


def test_covariance_missing_an_eligible_id_is_rejected():
    signals = one_asset(
        sigma={"A": 0.2, "B": 0.2}, trend={"A": 1.0, "B": 1.0}, momentum={"A": 0.1, "B": 0.1},
        eligible=("A", "B"),
    )
    expect("INVALID_COVARIANCE",
           lambda: compute_targets(signals, {"A": "equity", "B": "bond"}, PARAMS))


def test_covariance_with_an_extra_id_is_rejected():
    cov = pd.DataFrame([[0.04, 0.0], [0.0, 0.04]], index=["A", "Z"], columns=["A", "Z"])
    expect("INVALID_COVARIANCE", lambda: compute_targets(one_asset(cov=cov), {"A": "equity"}, PARAMS))


def test_well_formed_single_asset_still_allocates():
    result = compute_targets(one_asset(), {"A": "equity"}, PARAMS)
    assert result.weights["A"] > 0.0
    assert result.eligible == ["A"]


# B2 — covariance labels must be unique and numeric.

DUPLICATE = pd.DataFrame([[0.04, 0.0], [0.0, 0.04]], index=["A", "A"], columns=["A", "A"])


def test_duplicate_labels_rejected_by_validation():
    expect("INVALID_COVARIANCE", lambda: validate_covariance(DUPLICATE, PARAMS))


def test_duplicate_labels_rejected_by_portfolio_vol():
    expect("INVALID_COVARIANCE", lambda: portfolio_vol({"A": 0.25}, DUPLICATE, PARAMS))


def test_duplicate_labels_rejected_by_targets():
    expect("INVALID_COVARIANCE", lambda: compute_targets(one_asset(cov=DUPLICATE), {"A": "equity"}, PARAMS))


def test_non_numeric_covariance_entry_is_rejected():
    cov = pd.DataFrame([["x"]], index=["A"], columns=["A"])
    expect("INVALID_COVARIANCE", lambda: validate_covariance(cov, PARAMS))


def test_single_asset_volatility_is_exact():
    cov = pd.DataFrame([[0.04]], index=["A"], columns=["A"])
    assert math.isclose(portfolio_vol({"A": 0.25}, cov, PARAMS), 0.05, rel_tol=0.0, abs_tol=1e-15)


# Planner path — the covariance it receives is validated too.

def plan_with(cov):
    targets = compute_targets(one_asset(), {"A": "equity"}, PARAMS)
    state = AccountState(holdings={"A": 10}, cash_settled=1000.0, cash_unsettled=0.0,
                         open_orders=False, reconciliation_clean=True, data_ok=True)
    return plan_orders(targets, state, {"A": 10.0}, cov, {"A": "equity"}, frozenset({"A"}), PARAMS)


def test_planner_rejects_duplicate_labels():
    expect("INVALID_COVARIANCE", lambda: plan_with(DUPLICATE))


def test_planner_rejects_covariance_missing_a_held_id():
    cov = pd.DataFrame([[0.04]], index=["B"], columns=["B"])
    expect("INVALID_COVARIANCE", lambda: plan_with(cov))


def test_planner_accepts_well_formed_covariance():
    assert plan_with(pd.DataFrame([[0.04]], index=["A"], columns=["A"])).status == "OK"
