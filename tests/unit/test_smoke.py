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
                    "W4_vol_ceiling", "W5_tie_negative_ineligible"],
        "orders": ["O1_band_exit_cap_cashlimit", "O2_post_trade_class_repair",
                   "O3_blocked_open_orders", "O4_blocked_held_ineligible"],
        "signals": ["S1_signals_from_prices"],
    }
    for group, names in expected.items():
        assert [case["name"] for case in fixture[group]] == names
