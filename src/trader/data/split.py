"""Owner-only local CSV split. No broker, download, or agent authorization."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from trader.data.build import build_dataset
from trader.data.csv_import import HEADERS, _parse_csv_dir
from trader.data.holdout import HoldoutPathError, check_holdout_path
from trader.data.params import DataParams
from trader.data.raw import DataImportError, DataStoreError, RawDataset
from trader.data.store import _sync_directory, read_raw_dataset, write_raw_dataset
from trader.errors import InvalidInputError


class SplitError(ValueError):
    def __init__(self, code, paths=()):
        self.code, self.paths = code, tuple(str(p) for p in paths)
        super().__init__(f"{code}: {', '.join(self.paths)}")


@dataclass(frozen=True)
class HoldoutProposal:
    end: date
    holdout_start: date | None
    instruments: dict


def propose_holdout(parsed, years=4, min_dev_sessions=1009):
    calendar = parsed.calendar
    if (
        not calendar
        or any(type(d) is not date for d in calendar)
        or any(a >= b for a, b in zip(calendar, calendar[1:]))
    ):
        raise InvalidInputError("INVALID_CALENDAR")
    if (
        type(years) is not int
        or years <= 0
        or type(min_dev_sessions) is not int
        or min_dev_sessions < 1
    ):
        raise ValueError("years and min_dev_sessions must be positive integers")
    end = calendar[-1]
    target = end.replace(
        year=end.year - years, day=28 if (end.month, end.day) == (2, 29) else end.day
    )
    boundary = next(d for d in calendar if d >= target)
    names = sorted(d.instrument for d in parsed.declarations)
    build = build_dataset(
        calendar, end, names, parsed.prices, parsed.distributions, (), DataParams()
    )
    non_excluding = {
        "DATA_STALE",
        "DATA_JUMP",
        "DATA_JUMP_APPROVED",
        "DATA_INVALID_EXCEPTION",
    }
    report = {}
    for name in names:
        codes = sorted(
            {
                i.code
                for i in build.report
                if i.instrument == name and i.code not in non_excluding
            }
        )
        if codes:
            report[name] = {
                "development": None,
                "holdout": None,
                "codes": codes,
                "sufficient": False,
            }
        else:
            dates = {r.date for r in parsed.prices if r.instrument == name}
            dev, hold = (
                sum(d < boundary for d in dates),
                sum(d >= boundary for d in dates),
            )
            report[name] = {
                "development": dev,
                "holdout": hold,
                "codes": [],
                "sufficient": dev >= min_dev_sessions and hold >= 1,
            }
    sufficient = bool(names) and all(r["sufficient"] for r in report.values())
    return HoldoutProposal(end, boundary if sufficient else None, report)


def split_records(parsed, holdout_start):
    if type(holdout_start) is not date:
        raise ValueError("holdout_start must be a date")
    partitions = []
    for development in (True, False):
        calendar = tuple(
            d for d in parsed.calendar if (d < holdout_start) == development
        )
        if not calendar:
            raise SplitError("SPLIT_EMPTY_PARTITION")
        partitions.append(
            RawDataset(
                tuple(
                    r for r in parsed.prices if (r.date < holdout_start) == development
                ),
                tuple(
                    r
                    for r in parsed.distributions
                    if (r.ex_date < holdout_start) == development
                ),
                calendar,
                parsed.declarations,
                "development" if development else "holdout",
                holdout_start,
            )
        )
    return tuple(partitions)


def _case_insensitive(directory):
    # Probe existing identity without creating a sentinel. Missing output leaves
    # cannot be compared with samefile, but their existing volume can be.
    for ancestor in (directory, *directory.parents):
        alternate = (
            ancestor.with_name(ancestor.name.swapcase()) if ancestor.name else ancestor
        )
        if alternate != ancestor:
            try:
                return os.path.samefile(ancestor, alternate)
            except (FileNotFoundError, NotADirectoryError):
                return False
    return False


def _future_key(path):
    path = Path(path).resolve()
    suffix = []
    while not path.exists():
        suffix.insert(0, path.name)
        path = path.parent
    stat = path.stat()
    if _case_insensitive(path):
        suffix = [name.casefold() for name in suffix]
    return (stat.st_dev, stat.st_ino), tuple(suffix)


def _overlap(a, b):
    root_a, parts_a = _future_key(a)
    root_b, parts_b = _future_key(b)
    if root_a == root_b and (
        parts_a == parts_b[: len(parts_a)] or parts_b == parts_a[: len(parts_b)]
    ):
        return True
    for child, root in ((a, b), (b, a)):
        try:
            check_holdout_path(child, root, ())
        except HoldoutPathError:
            return True
    return False


def _guard_source(source, repo_root, workspaces):
    if not workspaces:
        raise SplitError("SPLIT_WORKSPACES_REQUIRED")
    for path in (source, *(source / name for name in HEADERS)):
        check_holdout_path(path, repo_root, workspaces)


def _staging(output):
    return output.with_name(output.name + f".staging-{os.getpid()}")


def preflight(source, dev_out, holdout_out, repo_root, agent_workspaces):
    """Stat/identity checks only: no source contents are read here."""
    source, dev_out, holdout_out = map(Path, (source, dev_out, holdout_out))
    _guard_source(source, repo_root, agent_workspaces)
    check_holdout_path(holdout_out, repo_root, agent_workspaces)
    roots = (source, dev_out, holdout_out)
    if any(_overlap(a, b) for i, a in enumerate(roots) for b in roots[i + 1 :]):
        raise SplitError("SPLIT_PATHS_OVERLAP", roots)
    existing = [p for p in (dev_out, holdout_out) if os.path.lexists(p)]
    if existing:
        raise SplitError("SPLIT_OUTPUT_EXISTS", existing)
    leftovers = []
    for output in (dev_out, holdout_out):
        if output.parent.exists():
            leftovers.extend(
                p
                for p in output.parent.iterdir()
                if p.name.startswith(output.name + ".staging-")
            )
    if leftovers:
        raise SplitError("SPLIT_STAGING_EXISTS", sorted(leftovers))
    # Staging paths also need containment checks, before the source is read.
    check_holdout_path(_staging(holdout_out), repo_root, agent_workspaces)
    all_paths = (*roots, _staging(dev_out), _staging(holdout_out))
    if any(_overlap(a, b) for i, a in enumerate(all_paths) for b in all_paths[i + 1 :]):
        raise SplitError("SPLIT_PATHS_OVERLAP", all_paths)


def _publish(staging, target):
    # Existing-output checks are repeated at publication; concurrent runs are
    # unsupported. No replace() call may overwrite an existing owner dataset.
    if os.path.lexists(target):
        raise SplitError("SPLIT_OUTPUT_EXISTS", [target])
    staging.rename(target)


def run_split(
    source,
    holdout_start,
    dev_out,
    holdout_out,
    *,
    repo_root,
    agent_workspaces,
    provenance,
):
    source, dev_out, holdout_out = map(Path, (source, dev_out, holdout_out))
    preflight(source, dev_out, holdout_out, repo_root, agent_workspaces)
    parsed = _parse_csv_dir(source)
    development, holdout = split_records(parsed, holdout_start)
    stages = (_staging(dev_out), _staging(holdout_out))
    owned = []
    published = []
    try:
        for dataset, stage in zip((development, holdout), stages):
            stage.parent.mkdir(parents=True, exist_ok=True)
            write_raw_dataset(dataset, stage, provenance=provenance)
            owned.append(stage)
        loaded = [read_raw_dataset(stage)[0] for stage in stages]
        for field in ("prices", "distributions", "calendar"):
            if Counter(getattr(parsed, field)) != Counter(
                (*getattr(loaded[0], field), *getattr(loaded[1], field))
            ):
                raise SplitError("SPLIT_PARTITION_MISMATCH")
        for data in loaded:
            if Counter(data.declarations) != Counter(parsed.declarations):
                raise SplitError("SPLIT_PARTITION_MISMATCH")
        for stage, target in ((stages[1], holdout_out), (stages[0], dev_out)):
            _publish(stage, target)
            published.append(target)
            _sync_directory(target.parent)
        return tuple(read_raw_dataset(p)[1] for p in (dev_out, holdout_out))
    except BaseException:
        # Only remove paths created by this call. os._exit/power loss bypasses
        # this handler; preflight refuses the orphan on the next invocation.
        for path in (*owned, *published):
            if path.exists():
                shutil.rmtree(path)
        raise


def _parser():
    parser = argparse.ArgumentParser(
        description=(
            "OWNER ONLY: full-history CSV input must remain outside every agent workspace. "
            "Jump checks do not detect splits; unsupported corporate actions block use."
        )
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--agent-workspace", action="append", type=Path, default=[])
    parser.add_argument("--propose-holdout", action="store_true")
    parser.add_argument("--holdout-start", type=date.fromisoformat)
    parser.add_argument("--dev-out", type=Path)
    parser.add_argument("--holdout-out", type=Path)
    parser.add_argument("--source-label")
    parser.add_argument("--adapter-version")
    parser.add_argument("--retrieved-at")
    return parser


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    options = (
        "holdout_start",
        "dev_out",
        "holdout_out",
        "source_label",
        "adapter_version",
        "retrieved_at",
    )
    if args.propose_holdout:
        if any(getattr(args, key) is not None for key in options):
            parser.error("proposal mode takes no boundary, output or provenance flags")
    elif any(getattr(args, key) is None for key in options):
        parser.error(
            "split mode requires boundary, both outputs and all provenance flags"
        )
    print(
        "OWNER ONLY: full history is read locally; no agent or broker access is authorised. "
        "Split adjustment is unsupported; declarations are required.",
        file=sys.stderr,
    )
    try:
        if args.propose_holdout:
            _guard_source(args.source, args.repo_root, args.agent_workspace)
            proposal = propose_holdout(_parse_csv_dir(args.source))
            print(json.dumps(asdict(proposal), default=str, sort_keys=True))
            return 0 if proposal.holdout_start else 1
        # Pin the installed checkout, not an arbitrary --repo-root's git HEAD.
        code_commit = subprocess.run(
            [
                "git",
                "-C",
                str(Path(__file__).resolve().parents[3]),
                "rev-parse",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        manifests = run_split(
            args.source,
            args.holdout_start,
            args.dev_out,
            args.holdout_out,
            repo_root=args.repo_root,
            agent_workspaces=args.agent_workspace,
            provenance={
                "source": args.source_label,
                "adapter_version": args.adapter_version,
                "retrieved_at": args.retrieved_at,
                "code_commit": code_commit,
            },
        )
        print(
            json.dumps(
                [
                    {
                        "dataset_id": m["dataset_id"],
                        "manifest_digest": m["manifest_digest"],
                    }
                    for m in manifests
                ],
                sort_keys=True,
            )
        )
        return 0
    except (
        DataImportError,
        DataStoreError,
        SplitError,
        HoldoutPathError,
        InvalidInputError,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
