"""Strict pre-registration parsing and resolution (registry spec sections 1–2)."""

import re
from pathlib import Path

from .canonical import strict_json
from .descriptor import RunDescriptor
from .errors import RegistryError
from .validation import (
    BENCHMARK_KEYS,
    PARAM_KEYS,
    exact,
    invalid,
    names,
    number,
    text,
    validate_backtest,
    validate_params,
    validate_period,
)

KEYS = {
    "id",
    "status",
    "frozen_by",
    "universe",
    "asset_class",
    "benchmarks",
    "params",
    "backtest_params",
    "variants",
    "cost_multipliers",
    "dataset",
    "period",
    "exceptions",
}


def _null(value):
    return (
        value is None
        or isinstance(value, dict)
        and any(_null(x) for x in value.values())
        or isinstance(value, list)
        and any(_null(x) for x in value)
    )


def parse_preregistration(path, *, repo_root=None):
    path = Path(path)
    try:
        blocks = re.findall(
            r"^```json preregistration\s*\n(.*?)^```\s*$",
            path.read_text(encoding="utf-8"),
            re.M | re.S,
        )
        if len(blocks) != 1:
            raise ValueError("expected one json preregistration block")
        h = strict_json(blocks[0])
    except (OSError, UnicodeError, ValueError) as exc:
        raise RegistryError("REGISTRY_PREREG_FORMAT", str(exc)) from exc
    exact(h, KEYS, "hypothesis")
    if h["status"] not in ("draft", "frozen"):
        invalid("status")
    frozen = h["status"] == "frozen"
    if frozen and _null(h):
        raise RegistryError("REGISTRY_HYPOTHESIS_INCOMPLETE")
    if (
        not isinstance(h["id"], str)
        or not re.fullmatch(r"H-\d{3}", h["id"])
        or h["id"] != path.stem
    ):
        invalid("id")
    if frozen:
        root = Path(repo_root).resolve() if repo_root else path.resolve().parents[2]
        target = h["frozen_by"]
        if (
            not isinstance(target, str)
            or not re.fullmatch(r"docs/decisions/[^/]+\.md", target)
            or not (root / target).is_file()
            or not (root / target).resolve().is_relative_to(root / "docs/decisions")
        ):
            invalid("frozen_by")
    elif h["frozen_by"] is not None:
        invalid("frozen_by")
    ids = names(h["universe"], "universe", sorted_required=True)
    exact(h["asset_class"], ids, "asset_class")
    validate_params(h["params"], h["asset_class"].values())
    if (
        not isinstance(h["benchmarks"], dict)
        or not set(h["benchmarks"]) <= BENCHMARK_KEYS.keys()
    ):
        raise RegistryError("REGISTRY_PREREG_FORMAT", "benchmarks")
    for name, args in h["benchmarks"].items():
        exact(args, BENCHMARK_KEYS[name], f"benchmarks.{name}")
        if name == "moving_average_10m":
            if args["universe"] != "strategy":
                ids |= names(
                    args["universe"], "benchmarks.universe", sorted_required=True
                )
        else:
            for value in args.values():
                text(value, f"benchmarks.{name}")
                ids.add(value)
    variants = h["variants"]
    if not isinstance(variants, list) or not variants:
        invalid("variants")
    seen, primaries = set(), 0
    for v in variants:
        exact(v, {"id", "role", "schedule", "overrides"}, "variants")
        text(v["id"], "variant.id")
        if v["id"] in seen or v["id"].startswith("B:"):
            invalid("variant.id")
        seen.add(v["id"])
        if v["role"] not in ("primary", "robustness"):
            invalid("variant.role")
        primaries += v["role"] == "primary"
        if v["schedule"] not in ("weekly", "monthly"):
            invalid("variant.schedule")
        if (
            not isinstance(v["overrides"], dict)
            or not set(v["overrides"]) <= PARAM_KEYS
        ):
            raise RegistryError("REGISTRY_PREREG_FORMAT", "overrides")
        validate_params({**h["params"], **v["overrides"]}, h["asset_class"].values())
    if primaries != 1:
        invalid("variants.role")
    ms = h["cost_multipliers"]
    if (
        not isinstance(ms, list)
        or any(not number(m) or m <= 0 for m in ms)
        or 1 not in ms
        or len(set(ms)) != len(ms)
    ):
        invalid("cost_multipliers")
    bp = h["backtest_params"]
    if bp is not None:
        validate_backtest(bp, ids, ms, draft=not frozen)
        exact(bp["HALF_SPREAD"], ids, "HALF_SPREAD")
    for key, fields in {
        "dataset": {"dataset_id", "manifest_digest"},
        "exceptions": {"version", "digest"},
    }.items():
        if h[key] is not None:
            exact(h[key], fields, key)
            for field, value in h[key].items():
                if value is not None:
                    text(value, f"{key}.{field}")
                    if field != "version" and not re.fullmatch(r"[0-9a-f]{64}", value):
                        invalid(f"{key}.{field}")
    if h["period"] is not None:
        exact(h["period"], {"start", "end"}, "period")
        if not _null(h["period"]):
            validate_period(h["period"])
        else:
            from .validation import iso_date

            for value in h["period"].values():
                if value is not None:
                    try:
                        iso_date(value)
                    except ValueError:
                        invalid("period")
    return h


def resolve_descriptors(hypothesis):
    h = hypothesis
    result = {}
    for v in h["variants"]:
        result[v["id"]] = RunDescriptor(
            {
                "kind": "strategy",
                "generator": "strategy",
                "schedule": v["schedule"],
                "universe": h["universe"],
                "asset_class": h["asset_class"],
                "params": {**h["params"], **v["overrides"]},
                "backtest_params": h["backtest_params"],
            }
        )
    for name, args in h["benchmarks"].items():
        config = {
            "kind": "baseline",
            "generator": name,
            "schedule": "monthly",
            "instruments": args,
            "params": h["params"],
            "backtest_params": h["backtest_params"],
        }
        if name == "moving_average_10m":
            config["universe"] = (
                h["universe"] if args["universe"] == "strategy" else args["universe"]
            )
        result[f"B:{name}"] = RunDescriptor(config)
    return result
