import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("name", [
    "data", "signals", "portfolio", "planner", "risk", "backtest",
    "execution", "monitor", "registry",
])
def test_subpackage_imports(name):
    importlib.import_module(f"trader.{name}")


def test_reference_fixture_names():
    fixture = json.loads((ROOT / "tests/fixtures/portfolio_cases.json").read_text())
    expected = {
        "weights": ["W1_asset_cap", "W2_class_cap", "W3_all_cash",
                    "W4_vol_ceiling", "W5_tie_negative_ineligible",
                    "W6_hedged_pair", "W7_empty_universe"],
        "orders": ["O1_band_exit_cap_cashlimit", "O2_post_trade_class_repair",
                   "O3_blocked_open_orders", "O4_blocked_held_ineligible",
                   "O5_zero_signal_exit", "O6_empty_universe_nothing_held",
                   "O7_empty_universe_held", "O8_blocked_nav",
                   "O9_unresolved_vol", "O10_unknown_holding"],
        "signals": ["S1_signals_from_prices"],
        "invalid": ["V1_nan_sigma", "V2_asymmetric_covariance",
                    "V3_unknown_asset_class", "V4_zero_price",
                    "V5_fractional_holding", "V6_negative_cash",
                    "V7_duplicate_date", "V8_negative_price"],
    }
    for group, names in expected.items():
        assert [case["name"] for case in fixture[group]] == names
