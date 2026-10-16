"""Strategy parameters are frozen (portfolio spec v1.2 section 1; research protocol preamble).

If this test fails, a parameter changed. That is a new registered variant, not a
code fix: it needs a decision record in docs/decisions/ dated before any result it
affects, an experiment-registry entry, and the owner's approval. Update APPROVED
below only in the same PR as that decision record.
"""

from dataclasses import fields

from trader.params import Params

APPROVED = {
    "ANNUALISATION": 252,
    "TREND_LOOKBACKS": (63, 126, 252),
    "MOM_LONG": 252,
    "MOM_SKIP": 21,
    "VOL_WINDOW": 60,
    "COV_WINDOW": 252,
    "TOP_N": 4,
    "SLEEVE_TREND": 0.5,
    "SLEEVE_MOM": 0.5,
    "ASSET_CAP": 0.25,
    "CLASS_CAP": 0.60,
    "VOL_CEILING": 0.10,
    "BAND": 0.02,
    "MIN_VOL": 0.005,
    "BUY_BUFFER": 0.005,
    "COMMISSION_RESERVE": 3.0,
    "TOL": 1e-9,
    "FLOOR_EPS": 1e-9,
    "SYM_TOL": 1e-12,
    "PSD_TOL": 1e-12,
    "ASSET_CLASSES": frozenset({"equity", "bond", "real_asset"}),
}


def test_parameters_match_approved_values():
    params = Params()
    actual = {f.name: getattr(params, f.name) for f in fields(params)}
    changed = {k: (APPROVED.get(k), v) for k, v in actual.items() if APPROVED.get(k) != v}
    assert not changed, f"strategy parameters changed (approved, now): {changed}; see module docstring"
    assert set(actual) == set(APPROVED), "parameter added or removed; see module docstring"
