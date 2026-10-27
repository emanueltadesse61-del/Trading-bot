"""Validate registry values independently of the portfolio constructors."""

import math
from dataclasses import fields
from datetime import date

from trader.backtest.params import BacktestParams
from trader.params import Params

from .errors import RegistryError

PARAM_KEYS = {f.name for f in fields(Params)}
BACKTEST_KEYS = {f.name for f in fields(BacktestParams)} - {"COST_MULTIPLIER"}
BENCHMARK_KEYS = {
    "sixty_forty": {"equity", "bond"},
    "global_equity": {"instrument"},
    "moving_average_10m": {"universe"},
    "cash": set(),
}


def invalid(field):
    raise RegistryError("REGISTRY_PREREG_INVALID", field)


def exact(value, keys, field):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise RegistryError("REGISTRY_PREREG_FORMAT", field)


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        invalid(field)


def number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def iso_date(value):
    if not isinstance(value, str):
        raise ValueError("date must be text")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("date must round-trip")
    return parsed


def validate_period(value):
    exact(value, {"start", "end"}, "period")
    try:
        if iso_date(value["start"]) >= iso_date(value["end"]):
            invalid("period")
    except (TypeError, ValueError) as exc:
        raise RegistryError("REGISTRY_PREREG_INVALID", "period") from exc


def names(value, field, *, sorted_required=False):
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(x, str) or not x.strip() for x in value)
        or len(set(value)) != len(value)
        or (sorted_required and value != sorted(value))
    ):
        invalid(field)
    return set(value)


def validate_params(p, asset_class=()):
    exact(p, PARAM_KEYS, "params")
    for key, minimum in {
        "ANNUALISATION": 1,
        "MOM_SKIP": 0,
        "MOM_LONG": 1,
        "VOL_WINDOW": 2,
        "COV_WINDOW": 2,
        "TOP_N": 1,
    }.items():
        if type(p[key]) is not int or p[key] < minimum:
            invalid(key)
    if p["MOM_LONG"] <= p["MOM_SKIP"]:
        invalid("MOM_LONG")
    looks = p["TREND_LOOKBACKS"]
    if (
        not isinstance(looks, list)
        or not looks
        or any(type(x) is not int or x < 1 for x in looks)
        or any(a >= b for a, b in zip(looks, looks[1:]))
    ):
        invalid("TREND_LOOKBACKS")
    for key in (
        "SLEEVE_TREND",
        "SLEEVE_MOM",
        "ASSET_CAP",
        "CLASS_CAP",
        "BAND",
        "VOL_CEILING",
        "MIN_VOL",
        "BUY_BUFFER",
        "COMMISSION_RESERVE",
        "TOL",
        "FLOOR_EPS",
        "SYM_TOL",
        "PSD_TOL",
    ):
        x = p[key]
        if not number(x) or x < 0:
            invalid(key)
        if key in {"ASSET_CAP", "CLASS_CAP", "VOL_CEILING"} and x == 0:
            invalid(key)
        if key in {"SLEEVE_TREND", "SLEEVE_MOM", "ASSET_CAP", "CLASS_CAP"} and x > 1:
            invalid(key)
        if key == "BAND" and x >= 1:
            invalid(key)
        if key in {"TOL", "FLOOR_EPS", "SYM_TOL", "PSD_TOL"} and x > 1e-3:
            invalid(key)
    if abs(p["SLEEVE_TREND"] + p["SLEEVE_MOM"] - 1) > 1e-12:
        invalid("SLEEVE_TREND/SLEEVE_MOM")
    classes = names(p["ASSET_CLASSES"], "ASSET_CLASSES")
    if any(not isinstance(x, str) or x not in classes for x in asset_class):
        invalid("ASSET_CLASSES/asset_class")


def validate_backtest(p, instruments, multipliers, *, draft=False):
    exact(p, BACKTEST_KEYS, "backtest_params")
    if not isinstance(p["HALF_SPREAD"], dict):
        invalid("HALF_SPREAD")
    resolved = dict(p)
    # Draft placeholders skip only their own value check. Zero spread and a
    # valid lag permit checking all other values, including doubled slippage.
    resolved["HALF_SPREAD"] = {
        k: 0 if draft and v is None else v for k, v in p["HALF_SPREAD"].items()
    }
    if draft and p["DISTRIBUTION_LAG"] is None:
        resolved["DISTRIBUTION_LAG"] = 1
    for m in multipliers:
        if not number(m) or m <= 0:
            invalid("cost_multipliers")
        try:
            BacktestParams(**resolved, COST_MULTIPLIER=m).validate_instruments(
                instruments
            )
        except ValueError as exc:
            raise RegistryError(
                "REGISTRY_PREREG_INVALID", f"backtest_params/HALF_SPREAD: {exc}"
            ) from exc


def params_object(value):
    return Params(
        **{
            **value,
            "TREND_LOOKBACKS": tuple(value["TREND_LOOKBACKS"]),
            "ASSET_CLASSES": frozenset(value["ASSET_CLASSES"]),
        }
    )
