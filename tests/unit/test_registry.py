"""T-009 synthetic acceptance: independent vectors, durable lifecycle and pins."""

import copy
import json
import sqlite3
import subprocess
import sys
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from trader.backtest.adapter import Market
from trader.data import DataParams, build_dataset
from trader.data.raw import Declaration, RawDataset
from trader.data.records import PriceRecord
from trader.data.store import read_raw_dataset, write_raw_dataset
from trader.registry import (
    RegistryError,
    RunDescriptor,
    init_registry,
    ops,
    parse_preregistration,
    read_exceptions,
    register_hypothesis,
    registry_summary,
    resolve_descriptors,
    run_registered,
    run_synthetic,
    verify_registry,
)
from trader.registry.canonical import canonical_json, strict_json
from trader.registry.cli import main
from trader.registry.git import GitCheckout, committed_checkpoint
from trader.registry.store import ZERO, row_hash

ROOT = Path(__file__).resolve().parents[2]
VECTORS = json.loads((ROOT / "tests/fixtures/registry_cases.json").read_text())
CONFIG = VECTORS["config_cases"]["configs"]["strategy_V1"]


def CLOCK():
    return "2026-10-16T21:00:00Z"


class FakeGit:
    """Only Git is replaced; storage, parsing, simulator and hashes are real."""

    def __init__(self, root):
        self.root = root
        self.files = {}
        self.is_clean = True

    def commit(self):
        return "7" * 40

    def clean(self):
        return self.is_clean

    def committed(self, relative):
        return self.files.get(relative)

    def save(self, path):
        self.files[path.relative_to(self.root).as_posix()] = path.read_bytes()


def error(code, call, *args, **kwargs):
    with pytest.raises(RegistryError) as caught:
        call(*args, **kwargs)
    assert caught.value.code == code
    return caught.value


def fixture_db(path, rows=None):
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE events(seq INTEGER PRIMARY KEY,prev_hash TEXT,body TEXT,row_hash TEXT)"
        )
        for row in rows or VECTORS["chain"]:
            db.execute(
                "INSERT INTO events VALUES (?,?,?,?)",
                tuple(row[k] for k in ("seq", "prev_hash", "body", "row_hash")),
            )
    return path


def rechain(rows):
    previous = ZERO
    for row in rows:
        row["prev_hash"] = previous
        row["row_hash"] = row_hash(previous, row["body"])
        previous = row["row_hash"]


def test_exact_chain_and_summary(tmp_path):
    previous = ZERO
    for row in VECTORS["chain"]:
        assert canonical_json(strict_json(row["body"])) == row["body"]
        assert row["prev_hash"] == previous
        assert row_hash(previous, row["body"]) == row["row_hash"]
        previous = row["row_hash"]
    path = fixture_db(tmp_path / "vectors.db")
    for cp in (None, *VECTORS["checkpoints"].values()):
        assert verify_registry(path, cp) == VECTORS["checkpoints"]["full"]
        summary = registry_summary(path, cp)
        for key, expected in VECTORS["lifecycle"].items():
            assert summary[key] == expected
        assert summary["checkpoint_used"] == cp


@pytest.mark.parametrize("case", VECTORS["tamper_cases"], ids=lambda c: c["name"])
def test_every_tamper_vector(tmp_path, case):
    rows = copy.deepcopy(VECTORS["chain"])
    name = case["name"]
    if name == "edit_body":
        rows[3]["body"] = rows[3]["body"].replace("completed", "failed")
    elif name == "delete_middle_row":
        del rows[3]
    elif name == "swap_rows":
        rows[2]["body"], rows[4]["body"] = rows[4]["body"], rows[2]["body"]
    elif name.startswith("suffix_deletion"):
        rows.pop()
    elif name == "replacement_log":
        rows = rows[:1]
        body = strict_json(rows[0]["body"])
        body["registry_id"] = "00000000-0000-4000-8000-000000000000"
        rows[0]["body"] = canonical_json(body)
        rechain(rows)
    elif name == "duplicate_finish":
        body = strict_json(rows[3]["body"])
        body["seq"] = 6
        rows.append({"seq": 6, "body": canonical_json(body)})
        rechain(rows)
    path = fixture_db(tmp_path / "tamper.db", rows)
    cp = VECTORS["checkpoints"].get(case["checkpoint"])
    if case["code"]:
        assert error(case["code"], verify_registry, path, cp).detail == case["seq"]
    else:
        verify_registry(path, cp)


@pytest.mark.parametrize(
    "index,field,value",
    [
        (2, "run_id", 2),
        (1, "trial_count_after", 0),
        (4, "supersedes", 4),
        (3, "run_id", 5),
    ],
)
def test_rehashed_lifecycle_corruption(tmp_path, index, field, value):
    rows = copy.deepcopy(VECTORS["chain"])
    body = strict_json(rows[index]["body"])
    body[field] = value
    rows[index]["body"] = canonical_json(body)
    rechain(rows)
    path = fixture_db(tmp_path / "bad.db", rows)
    assert error("REGISTRY_LIFECYCLE", verify_registry, path).detail == index + 1


def test_triggers_and_external_tamper(tmp_path):
    path = tmp_path / "log.db"
    init_registry(path, clock=CLOCK)
    with sqlite3.connect(path) as db:
        for statement in ("UPDATE events SET body='{}'", "DELETE FROM events"):
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                db.execute(statement)
        db.execute("DROP TRIGGER no_update")
        db.execute("UPDATE events SET body='{}'")
    error("REGISTRY_CHAIN_BROKEN", verify_registry, path)


def test_descriptor_vectors_and_immutability():
    for name, config in VECTORS["config_cases"]["configs"].items():
        d = RunDescriptor(config)
        assert d.config_hash == VECTORS["config_cases"]["config_hashes"][name]
        returned = d.config
        returned["params"]["TOP_N"] = 88
        assert d.config["params"]["TOP_N"] == 4
    config = copy.deepcopy(CONFIG)
    d = RunDescriptor(config)
    config["params"]["TOP_N"] = 2
    assert d.config["params"]["TOP_N"] == 4
    error("REGISTRY_UNSUPPORTED_GENERATOR", RunDescriptor, {"generator": "scripted"})


def hypothesis(identifier="H-900", count=3):
    c = copy.deepcopy(CONFIG)
    return {
        "id": identifier,
        "status": "frozen",
        "frozen_by": "docs/decisions/9999-test.md",
        "universe": c["universe"],
        "asset_class": c["asset_class"],
        "benchmarks": {
            "global_equity": {"instrument": "SYN_W"},
            "cash": {},
            "sixty_forty": {"equity": "SYN_W", "bond": "SYN_B"},
            "moving_average_10m": {"universe": "strategy"},
        },
        "params": c["params"],
        "backtest_params": c["backtest_params"],
        "variants": [
            {
                "id": f"V{i + 1}",
                "role": "primary" if i == 0 else "robustness",
                "schedule": "weekly",
                "overrides": {},
            }
            for i in range(count)
        ],
        "cost_multipliers": [1, 2],
        "dataset": {"dataset_id": "e" * 64, "manifest_digest": "f" * 64},
        "period": {"start": "2024-01-08", "end": "2024-01-19"},
        "exceptions": {"version": "test-v1", "digest": "1" * 64},
    }


def write_hypothesis(root, h):
    file = root / "research/hypotheses" / f"{h['id']}.md"
    file.parent.mkdir(parents=True, exist_ok=True)
    target = root / "docs/decisions/9999-test.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("Synthetic owner decision.")
    file.write_text(
        "# Synthetic\n```json preregistration\n" + json.dumps(h) + "\n```\n"
    )
    return file


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "repo"
    git = FakeGit(root)
    h = hypothesis()
    file = write_hypothesis(root, h)
    git.save(file)
    path = tmp_path / "registry.db"
    cp = init_registry(path, clock=CLOCK)

    def provider(git):
        return cp

    return path, git, h, file, provider


def reg(env):
    path, git, _, file, provider = env
    return register_hypothesis(
        path, file, git=git, checkpoint_provider=provider, clock=CLOCK
    )


def test_durable_count_and_repeat(env):
    path, git, h, file, _ = env
    assert reg(env)["trial_count"] == 3
    assert registry_summary(path)["runs"] == {}
    error("REGISTRY_ALREADY_REGISTERED", reg, env)
    for change in ("draft", "rename", "delete"):
        if change == "draft":
            h["status"] = "draft"
            file.write_text(json.dumps(h))
        elif change == "rename":
            file.rename(file.with_suffix(".old"))
        else:
            file.with_suffix(".old").unlink()
        assert registry_summary(path)["trial_count"] == 3
        code = (
            "REGISTRY_HYPOTHESIS_CHANGED"
            if change == "draft"
            else "REGISTRY_HYPOTHESIS_MISSING"
        )
        error(code, run_registered, **real_args(env))


def real_args(env):
    path, git, h, _, provider = env
    return dict(
        path=path,
        hypothesis_id=h["id"],
        variant_or_baseline="V1",
        dataset_dir=git.root.parent / "dataset",
        exceptions_file=git.root.parent / "exceptions.json",
        cost_multiplier=1,
        note="synthetic acceptance",
        git=git,
        checkpoint_provider=provider,
    )


def test_budget(env):
    path, git, _, _, provider = env
    reg(env)
    h = hypothesis("H-901", 18)
    file = write_hypothesis(git.root, h)
    git.save(file)
    before = verify_registry(path)
    error(
        "TRIAL_BUDGET_EXCEEDED",
        register_hypothesis,
        path,
        file,
        git=git,
        checkpoint_provider=provider,
    )
    assert verify_registry(path) == before


@pytest.mark.parametrize(
    "key,value",
    [
        ("TOP_N", 0),
        ("TOP_N", -1),
        ("TOP_N", True),
        ("TOP_N", "4"),
        ("TREND_LOOKBACKS", []),
        ("TREND_LOOKBACKS", [126, 63, 252]),
        ("MOM_LONG", 21),
        ("SLEEVE_MOM", 0.4),
        ("CLASS_CAP", 0),
        ("VOL_WINDOW", True),
        ("ASSET_CLASSES", ["bond"]),
        ("TOL", 0.1),
    ],
)
def test_param_values(env, key, value):
    _, git, h, _, _ = env
    h["params"][key] = value
    file = write_hypothesis(git.root, h)
    assert key in error("REGISTRY_PREREG_INVALID", parse_preregistration, file).detail


@pytest.mark.parametrize(
    "mutation,code",
    [
        (lambda h: h.update(extra=1), "REGISTRY_PREREG_FORMAT"),
        (lambda h: h["variants"][1].update(id="V1"), "REGISTRY_PREREG_INVALID"),
        (lambda h: h["variants"][1].update(role="primary"), "REGISTRY_PREREG_INVALID"),
        (
            lambda h: h["variants"][1].update(schedule="daily"),
            "REGISTRY_PREREG_INVALID",
        ),
        (
            lambda h: h["variants"][1].update(overrides={"oops": 1}),
            "REGISTRY_PREREG_FORMAT",
        ),
        (
            lambda h: h["variants"][1].update(overrides={"TOP_N": 0}),
            "REGISTRY_PREREG_INVALID",
        ),
        (lambda h: h.update(cost_multipliers=[2]), "REGISTRY_PREREG_INVALID"),
        (lambda h: h.update(cost_multipliers=[1, True]), "REGISTRY_PREREG_INVALID"),
        (
            lambda h: h.update(frozen_by="docs/decisions/missing.md"),
            "REGISTRY_PREREG_INVALID",
        ),
        (
            lambda h: h["backtest_params"]["HALF_SPREAD"].update(SYN_A=0.5),
            "REGISTRY_PREREG_INVALID",
        ),
        (lambda h: h["params"].update(TOP_N=None), "REGISTRY_HYPOTHESIS_INCOMPLETE"),
        (
            lambda h: h.update(period={"start": "20240101", "end": "2024-02-01"}),
            "REGISTRY_PREREG_INVALID",
        ),
        (lambda h: h["benchmarks"].update(unknown={}), "REGISTRY_PREREG_FORMAT"),
    ],
)
def test_contract_rules(env, mutation, code):
    _, git, h, _, _ = env
    mutation(h)
    error(code, parse_preregistration, write_hypothesis(git.root, h))


@pytest.mark.parametrize(
    "change", ["duplicate", "nan", "infinity", "overflow", "two_blocks", "no_block"]
)
def test_strict_json_and_fences(env, change):
    _, _, _, file, _ = env
    original = file.read_text()
    modified = {
        "duplicate": original.replace('"id": "H-900"', '"id": "H-900", "id": "H-900"'),
        "nan": original.replace('"TOP_N": 4', '"TOP_N": NaN'),
        "infinity": original.replace('"TOP_N": 4', '"TOP_N": Infinity'),
        "overflow": original.replace('"TOP_N": 4', '"TOP_N": 1e999'),
        "two_blocks": original + original,
        "no_block": "# no contract",
    }[change]
    file.write_text(modified)
    error("REGISTRY_PREREG_FORMAT", parse_preregistration, file)


def test_committed_h001_stays_draft(env):
    path, git, _, _, provider = env
    h = parse_preregistration(ROOT / "research/hypotheses/H-001.md")
    assert h["status"] == "draft"
    file = write_hypothesis(git.root, h)
    git.save(file)
    error(
        "REGISTRY_HYPOTHESIS_NOT_FROZEN",
        register_hypothesis,
        path,
        file,
        git=git,
        checkpoint_provider=provider,
    )
    assert registry_summary(path)["trial_count"] == 0
    h["backtest_params"]["SLIPPAGE"] = 0.6
    error(
        "REGISTRY_PREREG_INVALID", parse_preregistration, write_hypothesis(git.root, h)
    )


def snapshot(path):
    path.write_text(
        json.dumps(
            {
                "schema": "trading-bot/exceptions/v1",
                "version": "test-v1",
                "entries": [
                    {
                        "instrument": "SYN_A",
                        "date": "2024-01-08",
                        "reason": "test",
                        "approved": "2026-10-16",
                    }
                ],
            }
        )
    )
    return read_exceptions(path)


def test_nonempty_exceptions_roundtrip(tmp_path):
    s = snapshot(tmp_path / "exceptions.json")
    assert type(s.entries[0].date) is date
    assert s.entries[0].approved == "2026-10-16"
    assert (
        s.digest == "369a53d5a021701d2e156efe684ea657e9e0a0bcc0d02d143e5c4990a5d793db"
    )
    days = (date(2024, 1, 5), date(2024, 1, 8))
    prices = (
        PriceRecord("SYN_A", days[0], 100, "GBP"),
        PriceRecord("SYN_A", days[1], 150, "GBP"),
    )
    built = build_dataset(
        days,
        days[-1],
        ["SYN_A"],
        prices,
        (),
        s.entries,
        DataParams(),
        mode="research",
        exceptions_version=s.version,
    )
    codes = {r.code for r in built.report}
    assert "DATA_JUMP_APPROVED" in codes
    assert "DATA_INVALID_EXCEPTION" not in codes


@pytest.mark.parametrize(
    "field,value",
    [
        ("date", "2024-02-30"),
        ("approved", "20261016"),
        ("approved", 20261016),
        ("approved", "bad"),
    ],
)
def test_exception_bad_dates(tmp_path, field, value):
    file = tmp_path / "exceptions.json"
    snapshot(file)
    data = json.loads(file.read_text())
    data["entries"][0][field] = value
    file.write_text(json.dumps(data))
    error("REGISTRY_EXCEPTIONS_FORMAT", read_exceptions, file)


@pytest.mark.parametrize(
    "text",
    [
        '{"schema":1,"schema":2}',
        '{"version": NaN}',
        '{"schema":"bad","version":"x","entries":[]}',
    ],
)
def test_exception_strict_json(tmp_path, text):
    file = tmp_path / "exceptions.json"
    file.write_text(text)
    error("REGISTRY_EXCEPTIONS_FORMAT", read_exceptions, file)


def synthetic_market():
    days = tuple(
        date(2024, 1, 8) + timedelta(days=i)
        for i in range(12)
        if (date(2024, 1, 8) + timedelta(days=i)).weekday() < 5
    )
    return Market(
        days,
        tuple(
            PriceRecord(name, day, 100, "GBP", 100)
            for name in ("SYN_A", "SYN_B", "SYN_W")
            for day in days
        ),
    )


def synthetic_args(env):
    path, git, _, _, _ = env
    return dict(
        path=path,
        market=synthetic_market(),
        descriptor=RunDescriptor(CONFIG),
        period={"start": "2024-01-08", "end": "2024-01-19"},
        cost_multiplier=1,
        note="synthetic only",
        clock=CLOCK,
        git=git,
        checkpoint_provider=lambda git: None,
    )


def test_synthetic_success_and_exact_descriptor(env, monkeypatch):
    args = synthetic_args(env)
    args["git"].is_clean = False
    seen = []
    original_build, original_run = ops.build_generator, ops.run_backtest

    def build(d):
        seen.append(d.config)
        return original_build(d)

    def run(*a, **kw):
        assert kw["schedule"] == args["descriptor"].schedule
        # Separate connection sees committed start while simulator is running.
        assert registry_summary(args["path"])["runs"] == {"2": "unfinished"}
        return original_run(*a, **kw)

    monkeypatch.setattr(ops, "build_generator", build)
    monkeypatch.setattr(ops, "run_backtest", run)
    result = run_synthetic(**args)
    assert result.trial_count == 0
    with sqlite3.connect(args["path"]) as db:
        events = [
            strict_json(row[0])
            for row in db.execute("SELECT body FROM events ORDER BY seq")
        ]
    assert seen == [events[1]["config"]]
    assert events[1]["variant_id"] == args["descriptor"].config_hash
    assert events[1]["checkout_clean"] is False
    assert events[2]["metrics"] == result.result.metrics
    assert events[2]["totals"] == result.result.totals
    assert events[2]["error"] is None


def test_configs_distinct_runs_and_factory_values(env, monkeypatch):
    configs = [copy.deepcopy(CONFIG) for _ in range(4)]
    configs[1]["params"]["TOP_N"] = 2
    configs[2]["asset_class"]["SYN_A"] = "bond"
    configs[3]["schedule"] = "monthly"
    ids = set()
    from trader.backtest import generators

    original = generators.strategy_generator
    received = []

    def factory(universe, classes, params):
        received.append((universe, classes, params.TOP_N))
        return original(universe, classes, params)

    monkeypatch.setattr(generators, "strategy_generator", factory)
    for c in configs:
        d = RunDescriptor(c)
        ids.add(d.config_hash)
        run_synthetic(**{**synthetic_args(env), "descriptor": d})
        assert received[-1] == (c["universe"], c["asset_class"], c["params"]["TOP_N"])
    assert len(ids) == 4
    assert len(registry_summary(env[0])["runs_per_variant"]) == 4


def test_failure_and_logging_failure(env, monkeypatch):
    original = ValueError("deliberate simulator failure")

    def fail(*a, **kw):
        raise original

    monkeypatch.setattr(ops, "run_backtest", fail)
    with pytest.raises(ValueError) as caught:
        run_synthetic(**synthetic_args(env))
    assert caught.value is original
    assert registry_summary(env[0])["runs"] == {"2": "failed"}

    def break_log(*a, **kw):
        # Make the append fail at SQL level after run_started committed.
        with sqlite3.connect(env[0]) as db:
            db.execute(
                "CREATE TRIGGER deny_insert BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'unwritable'); END"
            )
        raise original

    monkeypatch.setattr(ops, "run_backtest", break_log)
    caught = error("REGISTRY_WRITE_FAILED", run_synthetic, **synthetic_args(env))
    assert caught.__cause__ is original
    assert registry_summary(env[0])["runs"]["4"] == "unfinished"


def test_supersedes_and_synthetic_guard(env):
    args = synthetic_args(env)
    first = run_synthetic(**args)
    run_synthetic(**args, supersedes=first.run_id)
    assert registry_summary(env[0])["superseded"] == [first.run_id]
    before = verify_registry(env[0])
    error("REGISTRY_LIFECYCLE", run_synthetic, **args, supersedes=999)
    c = copy.deepcopy(CONFIG)
    c["params"]["TOP_N"] = 2
    error(
        "REGISTRY_LIFECYCLE",
        run_synthetic,
        **{**args, "descriptor": RunDescriptor(c)},
        supersedes=first.run_id,
    )
    market = replace(
        args["market"],
        prices=(
            *args["market"].prices,
            PriceRecord("REAL", date(2024, 1, 8), 100, "GBP"),
        ),
    )
    error("REGISTRY_NOT_SYNTHETIC", run_synthetic, **{**args, "market": market})
    error(
        "REGISTRY_UNSUPPORTED_GENERATOR",
        run_synthetic,
        **{**args, "descriptor": object()},
    )
    assert verify_registry(env[0]) == before


def test_real_bindings_before_any_append(env, monkeypatch):
    path, git, h, file, _ = env
    args = real_args(env)
    s = snapshot(args["exceptions_file"])
    h["exceptions"] = {"version": s.version, "digest": s.digest}
    days = synthetic_market().calendar
    raw = RawDataset(
        tuple(PriceRecord("SYN_A", d, 100.0, "GBP") for d in days),
        (),
        days,
        (
            Declaration(
                "SYN_A", "unadjusted_close", True, days[-1], "synthetic", days[-1]
            ),
        ),
        "development",
        date(2024, 1, 22),
    )
    write_raw_dataset(
        raw,
        args["dataset_dir"],
        provenance={
            "source": "synthetic",
            "adapter_version": "test",
            "code_commit": "test",
            "retrieved_at": "2026-10-16T00:00:00Z",
        },
    )
    _, manifest = read_raw_dataset(args["dataset_dir"])
    h["dataset"] = {k: manifest[k] for k in ("dataset_id", "manifest_digest")}
    write_hypothesis(git.root, h)
    git.save(file)
    reg(env)
    before = verify_registry(path)
    monkeypatch.setattr(
        ops, "run_backtest", lambda *a, **kw: pytest.fail("real simulator called")
    )
    error("REGISTRY_REAL_DATA_UNSUPPORTED", run_registered, **args)
    for update, code in [
        ({"variant_or_baseline": "V99"}, "REGISTRY_UNKNOWN_VARIANT"),
        ({"variant_or_baseline": "B:unknown"}, "REGISTRY_UNKNOWN_VARIANT"),
        ({"hypothesis_id": "H-999"}, "REGISTRY_NOT_REGISTERED"),
        ({"cost_multiplier": 1.5}, "REGISTRY_COST_UNDECLARED"),
        ({"checkpoint_provider": lambda git: None}, "REGISTRY_CHECKPOINT_MISSING"),
    ]:
        error(code, run_registered, **{**args, **update})

    def drift(h):
        result = resolve_descriptors(h)
        c = result["V1"].config
        c["params"]["TOP_N"] = 2
        result["V1"] = RunDescriptor(c)
        return result

    error("REGISTRY_CONFIG_MISMATCH", run_registered, **args, resolver=drift)
    git.is_clean = False
    error("REGISTRY_DIRTY_CHECKOUT", run_registered, **args)
    git.is_clean = True
    for field in ("dataset_id", "manifest_digest", "partition"):
        changed = {**manifest, field: "holdout" if field == "partition" else "0" * 64}
        monkeypatch.setattr(ops, "read_raw_dataset", lambda p, m=changed: (raw, m))
        code = (
            "REGISTRY_HOLDOUT" if field == "partition" else "REGISTRY_DATASET_MISMATCH"
        )
        error(code, run_registered, **args)
    monkeypatch.setattr(ops, "read_raw_dataset", lambda p: (raw, manifest))
    body = json.loads(args["exceptions_file"].read_text())
    body["version"] = "changed"
    args["exceptions_file"].write_text(json.dumps(body))
    error("REGISTRY_EXCEPTIONS_MISMATCH", run_registered, **args)
    args["exceptions_file"].write_text("{}")
    error("REGISTRY_EXCEPTIONS_FORMAT", run_registered, **args)
    assert verify_registry(path) == before


def test_location_and_cli(tmp_path, capsys):
    error("REGISTRY_LOCATION", init_registry, ROOT / "must-not-exist.db")
    path = tmp_path / "cli.db"
    assert main(["init", str(path)]) == 0
    cp = json.loads(capsys.readouterr().out)
    file = tmp_path / "checkpoint.json"
    file.write_text(json.dumps(cp))
    assert main(["verify", str(path), "--checkpoint", str(file)]) == 0
    assert json.loads(capsys.readouterr().out) == cp
    assert main(["checkpoint", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == cp
    assert main(["summary", str(path), "--checkpoint", str(file)]) == 0
    assert json.loads(capsys.readouterr().out)["trial_count"] == 0
    assert main(["verify", str(tmp_path / "missing")]) == 1
    assert json.loads(capsys.readouterr().err)["code"] == "REGISTRY_CHAIN_BROKEN"


def test_committed_checkpoint_only(tmp_path):
    root = tmp_path / "git"
    root.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, capture_output=True
        )

    git("init")
    git("config", "user.name", "Synthetic Test")
    git("config", "user.email", "synthetic@example.invalid")
    cp = VECTORS["checkpoints"]["full"]
    path = root / "research/registry-checkpoint.json"
    path.parent.mkdir()
    path.write_text(json.dumps(cp))
    git("add", ".")
    git("commit", "-m", "synthetic checkpoint")
    checkout = GitCheckout(root)
    assert checkout.clean()
    path.write_text(json.dumps(VECTORS["checkpoints"]["mid"]))
    assert not checkout.clean()
    assert committed_checkpoint(checkout) == cp


def test_process_death_durable_start(env):
    path, _, _, _, _ = env
    config_file = path.parent / "config.json"
    config_file.write_text(json.dumps(CONFIG))
    script = """
import json, os, sys
from datetime import date
from trader.registry import RunDescriptor, run_synthetic, ops
from trader.backtest.adapter import Market
ops.run_backtest = lambda *a, **kw: os._exit(23)
run_synthetic(sys.argv[1], market=Market((date(2024,1,8), date(2024,1,19)), ()),
 descriptor=RunDescriptor(json.load(open(sys.argv[2]))),
 period={"start":"2024-01-08","end":"2024-01-19"}, cost_multiplier=1,
 note="process death test", checkpoint_provider=lambda git: None)
"""
    child = subprocess.run(
        [sys.executable, "-c", script, str(path), str(config_file)], capture_output=True
    )
    assert child.returncode == 23, child.stderr.decode()
    assert registry_summary(path)["runs"] == {"2": "unfinished"}


def test_concurrent_budget(env):
    path, git, _, _, provider = env
    for identifier, count in (("H-901", 19), ("H-902", 1), ("H-903", 1)):
        file = write_hypothesis(git.root, hypothesis(identifier, count))
        git.save(file)
        if count == 19:
            register_hypothesis(path, file, git=git, checkpoint_provider=provider)
    cp_file = path.parent / "cp.json"
    cp_file.write_text(json.dumps(verify_registry(path)))
    start = path.parent / "start"
    script = """
import json, sys, time
from pathlib import Path
from trader.registry import register_hypothesis, RegistryError
class Git:
 root = Path(sys.argv[2])
 def commit(self): return "7" * 40
 def clean(self): return True
 def committed(self, name): return (self.root / name).read_bytes()
while not Path(sys.argv[5]).exists(): time.sleep(.01)
try:
 register_hypothesis(sys.argv[1], sys.argv[3], git=Git(),
   checkpoint_provider=lambda git: json.load(open(sys.argv[4])))
 print("registered")
except RegistryError as exc: print(exc.code)
"""
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                script,
                str(path),
                str(git.root),
                str(git.root / f"research/hypotheses/{identifier}.md"),
                str(cp_file),
                str(start),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for identifier in ("H-902", "H-903")
    ]
    start.touch()
    results = [p.communicate(timeout=30) for p in processes]
    assert all(p.returncode == 0 for p in processes), results
    assert sorted(out.strip() for out, _ in results) == [
        "TRIAL_BUDGET_EXCEEDED",
        "registered",
    ]
    assert registry_summary(path)["trial_count"] == 20


@pytest.mark.parametrize(
    "name", ["cash", "global_equity", "sixty_forty", "moving_average_10m"]
)
def test_baseline_factories_run_existing_simulator(env, name):
    descriptor = resolve_descriptors(hypothesis())[f"B:{name}"]
    args = synthetic_args(env)
    # A month boundary gives the equity baselines an executable next-open fill.
    days = (date(2024, 1, 30), date(2024, 1, 31), date(2024, 2, 1), date(2024, 2, 2))
    market = Market(
        days,
        tuple(
            PriceRecord(n, d, 100.0, "GBP", 100.0)
            for n in ("SYN_A", "SYN_B", "SYN_W")
            for d in days
        ),
    )
    result = run_synthetic(
        **{
            **args,
            "descriptor": descriptor,
            "market": market,
            "period": {"start": "2024-01-30", "end": "2024-02-02"},
        }
    )
    assert result.result.inputs["schedule"] == "monthly"
    if name in ("global_equity", "sixty_forty"):
        assert any(row["fills"] for row in result.result.ledger)
    assert registry_summary(env[0])["trial_count"] == 0


def test_registration_preconditions_are_nonwriting(env):
    path, git, _, file, provider = env
    before = verify_registry(path)
    error(
        "REGISTRY_CHECKPOINT_MISSING",
        register_hypothesis,
        path,
        file,
        git=git,
        checkpoint_provider=lambda git: None,
    )
    git.is_clean = False
    error("REGISTRY_DIRTY_CHECKOUT", reg, env)
    git.is_clean = True
    git.files.clear()
    error("REGISTRY_DIRTY_CHECKOUT", reg, env)
    assert verify_registry(path) == before


def test_repository_alias_is_refused(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    link = tmp_path / "alias"
    link.symlink_to(root, target_is_directory=True)
    error("REGISTRY_LOCATION", init_registry, link / "registry.db", repo_root=root)
    assert not (root / "registry.db").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda h: h["params"].pop("TOP_N"),
        lambda h: h["backtest_params"].update(COST_MULTIPLIER=1),
        lambda h: h["asset_class"].pop("SYN_A"),
        lambda h: h["dataset"].update(extra="x"),
        lambda h: h["benchmarks"]["cash"].update(instrument="SYN_A"),
    ],
)
def test_exact_field_sets(env, mutation):
    _, git, h, _, _ = env
    mutation(h)
    error(
        "REGISTRY_PREREG_FORMAT", parse_preregistration, write_hypothesis(git.root, h)
    )


def test_draft_nulls_do_not_hide_other_errors(env):
    _, git, _, _, _ = env
    h = parse_preregistration(ROOT / "research/hypotheses/H-001.md")
    h["backtest_params"]["COMMISSION_MIN"] = -1
    error(
        "REGISTRY_PREREG_INVALID", parse_preregistration, write_hypothesis(git.root, h)
    )


def test_no_period_override_or_checkpoint_argument(env):
    with pytest.raises(TypeError, match="period"):
        run_registered(
            **real_args(env), period={"start": "2024-01-01", "end": "2024-02-01"}
        )
    with pytest.raises(TypeError, match="checkpoint"):
        run_registered(**real_args(env), checkpoint=VECTORS["checkpoints"]["mid"])
