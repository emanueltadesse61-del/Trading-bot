"""Registry operations: durable registration and two-transaction synthetic runs."""

from dataclasses import dataclass
from pathlib import Path

from trader.backtest.params import BacktestParams
from trader.backtest.simulator import run_backtest
from trader.data.store import read_raw_dataset

from .canonical import sha256
from .descriptor import RunDescriptor, build_generator
from .errors import RegistryError
from .exceptions_file import read_exceptions
from .git import GitCheckout, committed_checkpoint
from .prereg import parse_preregistration, resolve_descriptors
from .store import append_event, transaction, utc_now
from .summary import registry_summary
from .validation import iso_date, number, validate_backtest, validate_period

SUPPORTED_REAL_SCHEMAS = frozenset()


def _checkpoint(git, provider, required):
    cp = provider(git)
    if required and cp is None:
        raise RegistryError("REGISTRY_CHECKPOINT_MISSING")
    return cp


def _clean(git):
    if not git.clean():
        raise RegistryError("REGISTRY_DIRTY_CHECKOUT")


def _trial_count(events):
    return sum(
        len(e["variants"]) for e in events if e["type"] == "hypothesis_registered"
    )


def register_hypothesis(
    path,
    hypothesis_file,
    *,
    clock=utc_now,
    checkpoint_provider=committed_checkpoint,
    resolver=resolve_descriptors,
    git=None,
):
    git = git or GitCheckout()
    cp = _checkpoint(git, checkpoint_provider, True)
    with transaction(path, cp, repo_root=git.root) as (db, events):
        _clean(git)
        file = Path(hypothesis_file).resolve()
        h = parse_preregistration(file, repo_root=git.root)
        expected = git.root / "research/hypotheses" / f"{h['id']}.md"
        if file != expected.resolve():
            raise RegistryError("REGISTRY_PREREG_FORMAT", "hypothesis path")
        content = file.read_bytes()
        if git.committed(expected.relative_to(git.root).as_posix()) != content:
            raise RegistryError(
                "REGISTRY_DIRTY_CHECKOUT", "hypothesis not committed unchanged"
            )
        if h["status"] != "frozen":
            raise RegistryError("REGISTRY_HYPOTHESIS_NOT_FROZEN")
        if any(
            e.get("hypothesis_id") == h["id"] and e["type"] == "hypothesis_registered"
            for e in events
        ):
            raise RegistryError("REGISTRY_ALREADY_REGISTERED")
        count = _trial_count(events) + len(h["variants"])
        if count > 20:
            raise RegistryError("TRIAL_BUDGET_EXCEEDED", count)
        descriptors = resolver(h)
        event = append_event(
            db,
            {
                "type": "hypothesis_registered",
                "hypothesis_id": h["id"],
                "file_sha256": sha256(content),
                "hypothesis_commit": git.commit(),
                "frozen_by": h["frozen_by"],
                "variants": [
                    {
                        "variant_id": v["id"],
                        "role": v["role"],
                        "schedule": v["schedule"],
                        "config_hash": descriptors[v["id"]].config_hash,
                    }
                    for v in h["variants"]
                ],
                "baselines": [
                    {"baseline_id": key, "config_hash": descriptors[key].config_hash}
                    for key in sorted(descriptors)
                    if key.startswith("B:")
                ],
                "dataset": h["dataset"],
                "period": h["period"],
                "exceptions": h["exceptions"],
                "cost_multipliers": h["cost_multipliers"],
                "trial_count_after": count,
                "timestamp_utc": clock(),
            },
        )
    return {"registration": event, "trial_count": count, "checkpoint_used": cp}


@dataclass(frozen=True)
class RecordedRun:
    result: object
    run_id: int
    trial_count: int
    checkpoint_used: dict | None


def run_synthetic(
    path,
    *,
    market,
    descriptor,
    period,
    cost_multiplier,
    note,
    supersedes=None,
    clock=utc_now,
    checkpoint_provider=committed_checkpoint,
    git=None,
):
    git = git or GitCheckout()
    cp = _checkpoint(git, checkpoint_provider, False)
    with transaction(path, cp, repo_root=git.root) as (db, events):
        if type(descriptor) is not RunDescriptor:
            raise RegistryError("REGISTRY_UNSUPPORTED_GENERATOR")
        ids = descriptor.instrument_ids | {
            r.instrument
            for r in (*market.prices, *market.distributions, *market.exceptions)
        }
        if any(not isinstance(x, str) or not x.startswith("SYN_") for x in ids):
            raise RegistryError("REGISTRY_NOT_SYNTHETIC")
        validate_period(period)
        period = dict(period)
        c = descriptor.config
        validate_backtest(
            c["backtest_params"], descriptor.instrument_ids, [cost_multiplier]
        )
        event = append_event(
            db,
            {
                "type": "run_started",
                "hypothesis_id": "SYNTHETIC",
                "variant_id": descriptor.config_hash,
                "kind": c["kind"],
                "generator": c["generator"],
                "timestamp_utc": clock(),
                "code_commit": git.commit(),
                "checkout_clean": git.clean(),
                "config_hash": descriptor.config_hash,
                "config": c,
                "data": {
                    "kind": "synthetic",
                    "dataset_id": None,
                    "manifest_digest": None,
                    "partition": "synthetic",
                },
                "period": period,
                "cost_multiplier": cost_multiplier,
                "exceptions": {
                    "version": market.exceptions_version,
                    "digest": market.exceptions_digest,
                },
                "hypothesis_commit": None,
                "hypothesis_sha256": None,
                "supersedes": supersedes,
                "note": note,
            },
        )
        count = _trial_count(events)
    # Deliberately outside transaction 1: process death must leave the start.
    run_id = event["run_id"]

    def finish(outcome, metrics, totals, error):
        with transaction(
            path, _checkpoint(git, checkpoint_provider, False), repo_root=git.root
        ) as (db, _):
            append_event(
                db,
                {
                    "type": "run_finished",
                    "run_id": run_id,
                    "outcome": outcome,
                    "timestamp_utc": clock(),
                    "metrics": metrics,
                    "totals": totals,
                    "error": error,
                },
            )

    try:
        generator = build_generator(descriptor)
        result = run_backtest(
            market,
            generator,
            BacktestParams(**c["backtest_params"], COST_MULTIPLIER=cost_multiplier),
            start=iso_date(period["start"]),
            end=iso_date(period["end"]),
            schedule=descriptor.schedule,
        )
    except Exception as exc:
        try:
            finish("failed", None, None, getattr(exc, "code", type(exc).__name__))
        except Exception:
            raise RegistryError("REGISTRY_WRITE_FAILED", run_id) from exc
        raise
    try:
        finish("completed", result.metrics, result.totals, None)
    except Exception as exc:
        raise RegistryError("REGISTRY_WRITE_FAILED", run_id) from exc
    # Include registrations made while the simulator ran in the displayed count.
    count = registry_summary(path, cp)["trial_count"]
    return RecordedRun(result, run_id, count, cp)


def run_registered(
    path,
    *,
    hypothesis_id,
    variant_or_baseline,
    dataset_dir,
    exceptions_file,
    cost_multiplier,
    note,
    supersedes=None,
    clock=utc_now,
    checkpoint_provider=committed_checkpoint,
    resolver=resolve_descriptors,
    git=None,
):
    git = git or GitCheckout()
    cp = _checkpoint(git, checkpoint_provider, True)
    with transaction(path, cp, repo_root=git.root) as (_, events):
        _clean(git)
        registration = next(
            (
                e
                for e in events
                if e["type"] == "hypothesis_registered"
                and e["hypothesis_id"] == hypothesis_id
            ),
            None,
        )
        if registration is None:
            raise RegistryError("REGISTRY_NOT_REGISTERED")
        file = git.root / "research/hypotheses" / f"{hypothesis_id}.md"
        if not file.is_file():
            raise RegistryError("REGISTRY_HYPOTHESIS_MISSING")
        if sha256(file.read_bytes()) != registration["file_sha256"]:
            raise RegistryError("REGISTRY_HYPOTHESIS_CHANGED")
        pins = {v["variant_id"]: v["config_hash"] for v in registration["variants"]}
        pins.update(
            {v["baseline_id"]: v["config_hash"] for v in registration["baselines"]}
        )
        if variant_or_baseline not in pins:
            raise RegistryError("REGISTRY_UNKNOWN_VARIANT")
        descriptors = resolver(parse_preregistration(file, repo_root=git.root))
        descriptor = descriptors.get(variant_or_baseline)
        if (
            type(descriptor) is not RunDescriptor
            or descriptor.config_hash != pins[variant_or_baseline]
        ):
            raise RegistryError("REGISTRY_CONFIG_MISMATCH")
        if (
            not number(cost_multiplier)
            or cost_multiplier not in registration["cost_multipliers"]
        ):
            raise RegistryError("REGISTRY_COST_UNDECLARED")
        _, manifest = read_raw_dataset(dataset_dir)
        if any(
            manifest[k] != registration["dataset"][k]
            for k in ("dataset_id", "manifest_digest")
        ):
            raise RegistryError("REGISTRY_DATASET_MISMATCH")
        if manifest["partition"] != "development":
            raise RegistryError("REGISTRY_HOLDOUT")
        snapshot = read_exceptions(exceptions_file)
        if {"version": snapshot.version, "digest": snapshot.digest} != registration[
            "exceptions"
        ]:
            raise RegistryError("REGISTRY_EXCEPTIONS_MISMATCH")
        # No adapter or simulator call exists here. Even fully matching v1 data
        # lacks executable opening prices. Future capability needs its own card.
        raise RegistryError("REGISTRY_REAL_DATA_UNSUPPORTED", manifest["schema"])
