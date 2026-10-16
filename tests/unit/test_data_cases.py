"""Accepted data fixtures plus boundary and engine-composition checks."""

import copy
import json
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from trader.data import (
    DataParams,
    DistributionRecord,
    HoldoutPathError,
    JumpException,
    PriceRecord,
    build_dataset,
    check_holdout_path,
)
from trader.errors import InvalidInputError
from trader.params import Params
from trader.planner import AccountState, plan_orders
from trader.portfolio import compute_targets
from trader.signals import compute_signals

FIXTURE = json.loads((Path(__file__).parents[1] / "fixtures/data_cases.json").read_text())
PARAMS = DataParams()


def inputs(raw):
    x = copy.deepcopy(raw)
    x["calendar"] = [date.fromisoformat(d) for d in x["calendar"]]
    x["t"] = date.fromisoformat(x["t"])
    for key, cls, field in [("prices", PriceRecord, "date"),
                            ("distributions", DistributionRecord, "ex_date"),
                            ("exceptions", JumpException, "date")]:
        x[key] = [cls(**{**r, field: date.fromisoformat(r[field])}) for r in x[key]]
    return x


def normalized(value):
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalized(v) for v in value]
    return value


def compare(actual, expected):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            compare(actual[key], expected[key])
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for a, e in zip(actual, expected):
            compare(a, e)
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        assert actual == pytest.approx(expected, abs=1e-10, rel=0)
    else:
        assert actual == expected


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c: c["name"])
def test_data_case(case):
    if case["name"] == "D14_holdout_path":
        x = case["inputs"]
        for p, expected in case["expected"].items():
            if expected == "OK":
                check_holdout_path(Path(p), Path(x["repo_root"]), list(map(Path, x["agent_workspaces"])))
            else:
                with pytest.raises(HoldoutPathError) as exc:
                    check_holdout_path(Path(p), Path(x["repo_root"]), list(map(Path, x["agent_workspaces"])))
                assert exc.value.code == expected
    else:
        compare(normalized(asdict(build_dataset(**inputs(case["inputs"]), params=PARAMS))),
                case["expected"])


@pytest.mark.parametrize("case", FIXTURE["invalid"], ids=lambda c: c["name"])
def test_invalid_data_case(case):
    with pytest.raises(InvalidInputError) as exc:
        build_dataset(**inputs(case["inputs"]), params=PARAMS)
    assert exc.value.code == case["expected"]["error"]


def test_data_defaults_are_frozen():
    assert PARAMS.JUMP_LIMIT == .25
    assert dict(PARAMS.UNITS) == {"GBP": 1.0, "GBX": .01}
    with pytest.raises(FrozenInstanceError):
        PARAMS.JUMP_LIMIT = .3
    with pytest.raises(TypeError):
        PARAMS.UNITS["GBP"] = 2.0


@pytest.mark.parametrize("universe", [[], ["A"]])
def test_empty_or_unobserved_universe(universe):
    t = date(2026, 1, 5)
    result = build_dataset([t], t, universe, [], [], [], PARAMS)
    assert result.data_ok
    assert result.tr_close == ({"A": [None]} if universe else {})
    assert result.trade_close == ({"A": None} if universe else {})
    assert [i.code for i in result.report] == (["DATA_STALE"] if universe else [])


def history():
    days = [date(2024, 1, 1) + timedelta(days=k) for k in range(380)]
    days = [d for d in days if d.weekday() < 5][:260]
    prices = [PriceRecord(name, d, 100 + k * .05 + (k % 3), "GBP")
              for name in ["A", "B"] for k, d in enumerate(days)]
    return days, prices


@pytest.mark.parametrize("problem,expected", [("unheld_error", "BLOCKED_DATA"),
                                              ("held_stale", "BLOCKED_HELD_INELIGIBLE")])
def test_engine_composition(problem, expected):
    days, prices = history()
    if problem == "unheld_error":
        prices.append(PriceRecord("B", days[-1], -1, "GBP"))
    else:
        prices = [r for r in prices if not (r.instrument == "A" and r.date == days[-1])]
    built = build_dataset(days, days[-1], ["A", "B"], prices, [], [], PARAMS)
    signals = compute_signals(built.dates, built.tr_close, Params())
    if problem == "held_stale":
        assert built.data_ok and signals.ineligible_reason["A"] == "missing_data"
    else:
        assert not built.data_ok
    classes = {"A": "equity", "B": "bond"}
    targets = compute_targets(signals, classes, Params())
    state = AccountState({"A": 1}, 1000, 0, False, True, built.data_ok)
    plan = plan_orders(targets, state, built.trade_close, signals.cov, classes,
                       signals.eligible, Params())
    assert plan.status == expected and plan.orders == []


def test_valid_build_feeds_engine_without_mutation():
    days, prices = history()
    before = copy.deepcopy(prices)
    built = build_dataset(days, days[-1], ["A", "B"], prices, [], [], PARAMS)
    signals = compute_signals(built.dates, built.tr_close, Params())
    assert signals.eligible == frozenset({"A", "B"})
    assert prices == before
    assert build_dataset(days, days[-1], ["B", "A"], list(reversed(prices)), [], [], PARAMS) == built


def test_holdout_real_paths(tmp_path):
    workspace = tmp_path / "workspace"
    repo = workspace / "repo"
    repo.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = outside / "link"
    link.symlink_to(workspace, target_is_directory=True)
    for destination in [repo, workspace, workspace / "repo-sibling", link / "new" / "holdout",
                        outside / ".." / "workspace" / "holdout"]:
        with pytest.raises(HoldoutPathError):
            check_holdout_path(destination, repo, [workspace])
    check_holdout_path(tmp_path / "workspace2" / "new", repo, [workspace])
    # The forbidden root itself can be a symlink, too.
    with pytest.raises(HoldoutPathError):
        check_holdout_path(workspace / "new", repo, [link])
    assert not (workspace / "new").exists()  # guard must not create anything


def test_jump_boundary_and_distribution_not_used_for_jump():
    days = [date(2026, 1, 5), date(2026, 1, 6)]
    records = [PriceRecord("A", days[0], 100, "GBP"), PriceRecord("A", days[1], 125, "GBP")]
    result = build_dataset(days, days[-1], ["A"], records,
                           [DistributionRecord("A", days[-1], 100, "GBP")], [], PARAMS)
    assert result.data_ok and result.report == [] and result.tr_close["A"] == [100, 225]
    records[-1] = replace(records[-1], close=125.001)
    assert not build_dataset(days, days[-1], ["A"], records, [], [], PARAMS).data_ok


def test_exception_digest_covers_invalid_and_unicode_entries():
    days = [date(2026, 1, 5), date(2026, 1, 6)]
    entries = [JumpException("A", days[1], "確認", "2026-01-05"),
               JumpException("A", days[0], "", "bad-date")]
    before = list(entries)
    a = build_dataset(days, days[-1], ["A"], [], [], entries, PARAMS)
    b = build_dataset(days, days[-1], ["A"], [], [], list(reversed(entries)), PARAMS)
    assert a == b and entries == before
    assert not a.data_ok
    changed = build_dataset(days, days[-1], ["A"], [], [], entries[:1], PARAMS)
    assert changed.exceptions_digest != a.exceptions_digest


@pytest.mark.parametrize("value", [None, 0.0, -1.0, float("nan"), float("inf"), True])
def test_invalid_close_blocks_and_excludes(value):
    d = date(2026, 1, 5)
    result = build_dataset([d], d, ["A"], [PriceRecord("A", d, value, "GBP")], [], [], PARAMS)
    assert not result.data_ok and result.tr_close == {"A": [None]}
    assert [r.code for r in result.report] == ["DATA_INVALID_PRICE"]


@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf")])
def test_invalid_distribution_blocks_and_excludes(value):
    d = date(2026, 1, 5)
    result = build_dataset([d], d, ["A"], [PriceRecord("A", d, 10, "GBP")],
                           [DistributionRecord("A", d, value, "GBP")], [], PARAMS)
    assert not result.data_ok and result.trade_close == {"A": None}
    assert [r.code for r in result.report] == ["DATA_INVALID_DISTRIBUTION"]


def test_record_error_precedence():
    d, future = date(2026, 1, 5), date(2026, 1, 6)
    result = build_dataset([d], d, ["A"], [PriceRecord("A", future, -1, "USD"),
                                         PriceRecord("Z", future, -1, "USD")], [], [], PARAMS)
    assert [(r.instrument, r.code) for r in result.report] == [
        ("A", "DATA_FUTURE_RECORD"), ("Z", "DATA_UNKNOWN_INSTRUMENT")]


def test_calendar_tail_does_not_enter_output():
    days, prices = history()
    cutoff = days[-5]
    past = [r for r in prices if r.date <= cutoff]
    a = build_dataset(days, cutoff, ["A", "B"], past, [], [], PARAMS)
    b = build_dataset(days[:-4], cutoff, ["A", "B"], past, [], [], PARAMS)
    assert a == b and a.dates[-1] == cutoff


def test_operational_approval_cutoff_changes_only_authorization():
    case = next(c for c in FIXTURE["cases"] if c["name"].startswith("D6b_"))
    args = inputs(case["inputs"])
    future = build_dataset(**args, params=PARAMS)
    args["exceptions"] = [replace(e, approved=args["t"].isoformat()) for e in args["exceptions"]]
    current = build_dataset(**args, params=PARAMS)
    assert future.tr_close == current.tr_close
    assert not future.data_ok and current.data_ok
    assert future.exceptions_digest != current.exceptions_digest


@pytest.mark.parametrize("root_kind", ["repo", "workspace"])
def test_holdout_case_insensitive_identity(tmp_path, monkeypatch, root_kind):
    import os

    root = tmp_path / "Trading-Bot"
    root.mkdir()
    real_samefile = os.path.samefile
    checked = []

    def case_insensitive_samefile(a, b):
        # Model an existing directory reachable through either case spelling.
        # The destination's new children still do not exist.
        a, b = Path(a), Path(b)
        checked.append(a)
        if str(a).casefold() == str(root).casefold():
            a = root
        if str(b).casefold() == str(root).casefold():
            b = root
        return real_samefile(a, b)

    monkeypatch.setattr(os.path, "samefile", case_insensitive_samefile)
    alias = tmp_path / "trading-bot"
    destination = alias / "new-data" / "holdout"
    repo = root if root_kind == "repo" else tmp_path / "another-repo"
    workspaces = [] if root_kind == "repo" else [root]
    with pytest.raises(HoldoutPathError):
        check_holdout_path(destination, repo, workspaces)
    assert alias in checked
    assert not (root / "new-data").exists()
    check_holdout_path(tmp_path / "trading-bot-other" / "holdout", repo, workspaces)


def test_holdout_identity_error_is_not_ignored(tmp_path, monkeypatch):
    import os

    def denied(a, b):
        raise PermissionError("synthetic access denied")

    monkeypatch.setattr(os.path, "samefile", denied)
    with pytest.raises(PermissionError):
        check_holdout_path(tmp_path / "outside", tmp_path / "repo", [])
