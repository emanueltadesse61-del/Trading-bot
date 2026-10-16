"""Synthetic T-007 acceptance and regression cases; never downloads data."""

import csv
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, replace
from datetime import date, timedelta

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from trader.data import DataParams, build_dataset
from trader.data.csv_import import HEADERS, _parse_csv_dir, import_csv
from trader.data.raw import (
    DataImportError,
    DataStoreError,
    Declaration,
    ParsedImport,
    RawDataset,
)
from trader.data.records import DistributionRecord, PriceRecord
from trader.data.split import main, propose_holdout, run_split, split_records
from trader.data.store import (
    SCHEMAS,
    dataset_identity,
    read_raw_dataset,
    write_raw_dataset,
)
from trader.errors import InvalidInputError

DAYS = tuple(date(2020, 1, d) for d in (6, 7, 8, 9))
H = DAYS[2]
PROVENANCE = {
    "source": "synthetic",
    "adapter_version": "test-v1",
    "code_commit": "test",
    "retrieved_at": "2026-10-16T00:00:00Z",
}


def example():
    return ParsedImport(
        tuple(PriceRecord("SYN_A", d, 100.0, "GBP") for d in DAYS),
        (DistributionRecord("SYN_A", DAYS[1], 1.0, "GBP"),),
        DAYS,
        (
            Declaration(
                "SYN_A",
                "unadjusted_close",
                True,
                date(2026, 10, 15),
                "synthetic evidence",
                date(2026, 10, 16),
            ),
        ),
    )


def raw(parsed=None):
    parsed = parsed or example()
    return RawDataset(
        parsed.prices,
        parsed.distributions,
        parsed.calendar,
        parsed.declarations,
        "synthetic",
        None,
    )


def export(directory, parsed=None):
    parsed = parsed or example()
    directory.mkdir(parents=True)
    for file, records in zip(
        HEADERS,
        (parsed.prices, parsed.distributions, parsed.calendar, parsed.declarations),
    ):
        with (directory / file).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=HEADERS[file])
            writer.writeheader()
            for record in records:
                row = {"date": record} if type(record) is date else asdict(record)
                if isinstance(record, PriceRecord):
                    assert row.pop("open") is None  # v1 CSV has no open column
                row = {
                    k: (str(v).lower() if type(v) is bool else v)
                    for k, v in row.items()
                }
                writer.writerow(row)
    return directory


def change_csv(path, key, value, index=0):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    rows[index][key] = value
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def split_args(tmp_path):
    return dict(
        source=export(tmp_path / "owner" / "source"),
        holdout_start=H,
        dev_out=tmp_path / "agent" / "dev",
        holdout_out=tmp_path / "owner" / "holdout",
        repo_root=tmp_path / "repo",
        agent_workspaces=[tmp_path / "agent"],
        provenance=PROVENANCE,
    )


def assert_error(exc, code, function, *args, **kwargs):
    with pytest.raises(exc) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code
    return caught.value


def test_import_roundtrip_and_unadjusted_bad_data(tmp_path):
    source = export(tmp_path / "source")
    assert import_csv(source, holdout_start=None, synthetic=True) == raw()
    change_csv(source / "prices.csv", "close", "")
    data = import_csv(source, holdout_start=None, synthetic=True)
    assert data.prices[0].close is None
    built = build_dataset(
        data.calendar,
        DAYS[-1],
        ["SYN_A"],
        data.prices,
        data.distributions,
        (),
        DataParams(),
    )
    assert "DATA_INVALID_PRICE" in {r.code for r in built.report}


@pytest.mark.parametrize("file", HEADERS)
def test_missing_files_and_bad_headers(tmp_path, file):
    source = export(tmp_path / "source")
    (source / file).unlink()
    error = assert_error(DataImportError, "IMPORT_MISSING_FILE", _parse_csv_dir, source)
    assert (error.file, error.line) == (file, 0)
    (source / file).write_text("bad,header\n")
    error = assert_error(DataImportError, "IMPORT_BAD_HEADER", _parse_csv_dir, source)
    assert (error.file, error.line) == (file, 1)


@pytest.mark.parametrize(
    "header",
    [
        "instrument,date,close,unit,extra",
        "instrument,date,close,close",
        "instrument,date,close",
    ],
)
def test_extra_duplicate_missing_columns(tmp_path, header):
    source = export(tmp_path / "source")
    (source / "prices.csv").write_text(header + "\n")
    assert_error(DataImportError, "IMPORT_BAD_HEADER", _parse_csv_dir, source)


@pytest.mark.parametrize(
    "row",
    [
        "SYN_A,2020-01-06,100\n",
        "SYN_A,2020-01-06,100,GBP,extra\n",
        '"unterminated,2020-01-06,100,GBP\n',
    ],
)
def test_malformed_rows(tmp_path, row):
    source = export(tmp_path / "source")
    (source / "prices.csv").write_text(",".join(HEADERS["prices.csv"]) + "\n" + row)
    error = assert_error(
        DataImportError, "IMPORT_MALFORMED_ROW", _parse_csv_dir, source
    )
    assert error.file == "prices.csv" and error.line == 2


@pytest.mark.parametrize("text", ["20200106", "2020-1-06", "2020-02-31", "not-date"])
def test_bad_date(tmp_path, text):
    source = export(tmp_path / "source")
    change_csv(source / "prices.csv", "date", text)
    error = assert_error(DataImportError, "IMPORT_BAD_DATE", _parse_csv_dir, source)
    assert (error.file, error.line) == ("prices.csv", 2)


@pytest.mark.parametrize("text", ["oops", "NaN", "inf", "1_000", "1e999", " 1"])
def test_bad_number(tmp_path, text):
    source = export(tmp_path / "source")
    change_csv(source / "prices.csv", "close", text)
    error = assert_error(DataImportError, "IMPORT_BAD_NUMBER", _parse_csv_dir, source)
    assert (error.file, error.line) == ("prices.csv", 2)


@pytest.mark.parametrize(
    "field,value",
    [
        ("price_semantics", "adjusted"),
        ("distributions_complete", "false"),
        ("distributions_complete", "yes"),
        ("corporate_actions_none_through", "2019-01-01"),
        ("evidence_source", ""),
        ("checked_on", "2020-01-01"),
    ],
)
def test_declaration_invalid(tmp_path, field, value):
    source = export(tmp_path / "source")
    change_csv(source / "declarations.csv", field, value)
    error = assert_error(
        DataImportError, "IMPORT_DECLARATION_INVALID", _parse_csv_dir, source
    )
    assert (error.file, error.line) == ("declarations.csv", 2)


def test_declaration_missing(tmp_path):
    source = export(tmp_path / "source")
    (source / "declarations.csv").write_text(
        ",".join(HEADERS["declarations.csv"]) + "\n"
    )
    error = assert_error(
        DataImportError, "IMPORT_DECLARATION_MISSING", _parse_csv_dir, source
    )
    assert (error.file, error.line) == ("declarations.csv", 0)


def test_public_requires_boundary_before_read(tmp_path):
    assert_error(
        DataImportError,
        "IMPORT_HOLDOUT_REQUIRED",
        import_csv,
        tmp_path / "does-not-exist",
        holdout_start=None,
    )


@pytest.mark.parametrize(
    "file,key",
    [
        ("prices.csv", "date"),
        ("distributions.csv", "ex_date"),
        ("calendar.csv", "date"),
    ],
)
@pytest.mark.parametrize("offset", [0, 1])
def test_market_boundary_all_files(tmp_path, file, key, offset):
    development = split_records(example(), H)[0]
    source = export(tmp_path / "source", development)
    change_csv(source / file, key, str(H + timedelta(days=offset)))
    error = assert_error(
        DataImportError, "IMPORT_HOLDOUT_LEAK", import_csv, source, holdout_start=H
    )
    assert (error.file, error.line) == (file, 2)


def test_attestations_after_boundary_unchanged(tmp_path):
    development = split_records(example(), H)[0]
    source = export(tmp_path / "source", development)
    imported = import_csv(source, holdout_start=H)
    assert imported == development
    write_raw_dataset(imported, tmp_path / "dataset", provenance=PROVENANCE)
    assert read_raw_dataset(tmp_path / "dataset")[0] == development


@pytest.mark.parametrize(
    "file", ["prices.csv", "distributions.csv", "declarations.csv"]
)
def test_synthetic_ids(tmp_path, file):
    source = export(tmp_path / "source")
    change_csv(source / file, "instrument", "REAL")
    error = assert_error(
        DataImportError,
        "IMPORT_NOT_SYNTHETIC",
        import_csv,
        source,
        holdout_start=None,
        synthetic=True,
    )
    assert (error.file, error.line) == (file, 2)


def test_storage_determinism_identity_and_build(tmp_path):
    manifests = [
        write_raw_dataset(raw(), tmp_path / n, provenance=PROVENANCE)
        for n in ("a", "b")
    ]
    assert manifests[0] == manifests[1]
    for p in (tmp_path / "a").iterdir():
        assert p.read_bytes() == (tmp_path / "b" / p.name).read_bytes()
    manifest = manifests[0]
    payload = {
        "schema": "trading-bot/raw-dataset/v1",
        "partition": "synthetic",
        "holdout_start": None,
        "files": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (tmp_path / "a").glob("*.parquet")
        },
    }
    independent = hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    assert independent == manifest["dataset_id"]
    assert (
        manifest["manifest_digest"]
        == hashlib.sha256((tmp_path / "a" / "manifest.json").read_bytes()).hexdigest()
    )
    loaded, read_manifest = read_raw_dataset(tmp_path / "a")
    assert loaded == raw() and read_manifest == manifest

    def build(data):
        return build_dataset(
            data.calendar,
            DAYS[-1],
            ["SYN_A"],
            data.prices,
            data.distributions,
            (),
            DataParams(),
        )

    assert build(loaded) == build(raw())
    assert (
        len(
            {
                dataset_identity(p, h, manifest["files"])
                for p, h in [
                    ("development", "2020-01-08"),
                    ("holdout", "2020-01-08"),
                    ("development", "2020-01-09"),
                ]
            }
        )
        == 3
    )
    changed = write_raw_dataset(
        raw(), tmp_path / "c", provenance={**PROVENANCE, "source": "other evidence"}
    )
    assert changed["dataset_id"] == manifest["dataset_id"]
    assert changed["manifest_digest"] != manifest["manifest_digest"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema", "wrong"),
        ("dataset_id", "0" * 64),
        ("date_range", {"first": "2020-01-06", "last": "2020-01-07"}),
        ("instruments", {}),
        ("partition", "holdout"),
        ("holdout_start", "2019-01-01"),
    ],
)
def test_manifest_tampering(tmp_path, field, value):
    root = tmp_path / "dataset"
    write_raw_dataset(raw(), root, provenance=PROVENANCE)
    m = json.loads((root / "manifest.json").read_text())
    m[field] = value
    (root / "manifest.json").write_text(json.dumps(m))
    assert_error(DataStoreError, "DATASET_MANIFEST_MISMATCH", read_raw_dataset, root)


@pytest.mark.parametrize(
    "kind", ["byte", "missing", "extra", "count", "boolean_count", "symlink"]
)
def test_file_tampering(tmp_path, kind):
    root = tmp_path / "dataset"
    write_raw_dataset(raw(), root, provenance=PROVENANCE)
    path = root / "prices.parquet"
    if kind == "byte":
        data = bytearray(path.read_bytes())
        data[10] ^= 1
        path.write_bytes(data)
    elif kind == "missing":
        path.unlink()
    elif kind == "extra":
        (root / "extra").write_text("x")
    elif kind == "symlink":
        target = tmp_path / "outside"
        path.rename(target)
        path.symlink_to(target)
    else:
        m = json.loads((root / "manifest.json").read_text())
        m["files"]["prices.parquet"]["rows"] = 8 if kind == "count" else True
        (root / "manifest.json").write_text(json.dumps(m))
    assert_error(DataStoreError, "DATASET_MANIFEST_MISMATCH", read_raw_dataset, root)


def rehash(root):
    m = json.loads((root / "manifest.json").read_text())
    for name in SCHEMAS:
        m["files"][name] = {
            "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
            "rows": pq.read_table(root / name).num_rows,
        }
    m["dataset_id"] = dataset_identity(m["partition"], m["holdout_start"], m["files"])
    (root / "manifest.json").write_text(json.dumps(m))


@pytest.mark.parametrize("kind", ["market", "declaration", "null", "schema"])
def test_rehashed_invalid_content_still_rejected(tmp_path, kind):
    root = tmp_path / "dataset"
    dev = split_records(example(), H)[0]
    write_raw_dataset(dev, root, provenance=PROVENANCE)
    name = "declarations.parquet" if kind == "declaration" else "prices.parquet"
    records = pq.read_table(root / name).to_pylist()
    if kind == "market":
        records[0]["date"] = H
    elif kind == "declaration":
        records[0]["checked_on"] = date(2010, 1, 1)
    elif kind == "null":
        records[0]["instrument"] = None
    if kind == "schema":
        table = pa.table({"wrong": [1]})
    else:
        table = pa.Table.from_pylist(records, schema=SCHEMAS[name])
    pq.write_table(table, root / name)
    rehash(root)
    assert_error(DataStoreError, "DATASET_MANIFEST_MISMATCH", read_raw_dataset, root)


def test_split_partition_and_empty_dividends(tmp_path):
    args = split_args(tmp_path)
    manifests = run_split(**args)
    dev, _ = read_raw_dataset(args["dev_out"])
    hold, _ = read_raw_dataset(args["holdout_out"])
    assert dev.calendar == DAYS[:2] and hold.calendar == DAYS[2:]
    assert dev.prices + hold.prices == example().prices
    assert dev.declarations == hold.declarations == example().declarations
    assert hold.distributions == ()
    assert manifests[0]["partition"] == "development"


@pytest.mark.parametrize("boundary", [DAYS[0], DAYS[-1] + timedelta(days=1)])
def test_split_empty_partition(tmp_path, boundary):
    args = split_args(tmp_path)
    args["holdout_start"] = boundary
    from trader.data.split import SplitError

    assert_error(SplitError, "SPLIT_EMPTY_PARTITION", run_split, **args)
    assert not args["dev_out"].exists() and not args["holdout_out"].exists()


@pytest.mark.parametrize(
    "case,code",
    [
        ("source_workspace", "HOLDOUT_PATH_FORBIDDEN"),
        ("symlink_file", "HOLDOUT_PATH_FORBIDDEN"),
        ("holdout_repo", "HOLDOUT_PATH_FORBIDDEN"),
        ("equal", "SPLIT_PATHS_OVERLAP"),
        ("nested", "SPLIT_PATHS_OVERLAP"),
        ("inside_source", "SPLIT_PATHS_OVERLAP"),
        ("exists", "SPLIT_OUTPUT_EXISTS"),
        ("staging", "SPLIT_STAGING_EXISTS"),
        ("workspaces", "SPLIT_WORKSPACES_REQUIRED"),
        ("alias", "SPLIT_PATHS_OVERLAP"),
    ],
)
def test_preflight_before_read(tmp_path, monkeypatch, case, code):
    args = split_args(tmp_path)
    (args["source"] / "prices.csv").write_text("not,csv\n")
    if case == "source_workspace":
        args["agent_workspaces"].append(args["source"].parent)
    elif case == "symlink_file":
        target = tmp_path / "agent" / "private.csv"
        target.parent.mkdir()
        target.write_text("bad")
        path = args["source"] / "prices.csv"
        path.unlink()
        path.symlink_to(target)
    elif case == "holdout_repo":
        args["holdout_out"] = args["repo_root"] / "hold"
    elif case == "equal":
        args["dev_out"] = args["holdout_out"]
    elif case == "nested":
        args["dev_out"] = args["holdout_out"] / "dev"
    elif case == "inside_source":
        args["holdout_out"] = args["source"] / "hold"
    elif case == "exists":
        args["holdout_out"].mkdir()
    elif case == "staging":
        args["holdout_out"].with_name("holdout.staging-123").mkdir()
    elif case == "workspaces":
        args["agent_workspaces"] = []
    elif case == "alias":
        alias = tmp_path / "alias"
        alias.symlink_to(args["source"], target_is_directory=True)
        args["holdout_out"] = alias / "hold"

    def no_read(*a, **kw):
        pytest.fail("preflight must refuse before any source content is read")

    monkeypatch.setattr("trader.data.split._parse_csv_dir", no_read)
    with pytest.raises(ValueError) as error:
        run_split(**args)
    assert error.value.code == code


def test_read_error_publishes_nothing(tmp_path, monkeypatch):
    args = split_args(tmp_path)

    def denied(*a, **kw):
        raise PermissionError("synthetic permission refusal")

    monkeypatch.setattr("trader.data.split._parse_csv_dir", denied)
    with pytest.raises(PermissionError):
        run_split(**args)
    assert not args["dev_out"].exists() and not args["holdout_out"].exists()


def test_caught_failure_rolls_back(tmp_path, monkeypatch):
    import trader.data.split as split

    args = split_args(tmp_path)
    publish = split._publish

    def fail_second(stage, target):
        if target == args["dev_out"]:
            raise OSError("simulated rename failure")
        publish(stage, target)

    monkeypatch.setattr(split, "_publish", fail_second)
    with pytest.raises(OSError):
        run_split(**args)
    assert not args["dev_out"].exists() and not args["holdout_out"].exists()
    assert not list(tmp_path.rglob("*.staging-*"))


def test_interruption_retry_and_owner_recovery(tmp_path):
    from trader.data.split import SplitError

    args = split_args(tmp_path)
    script = """
import os,sys
from pathlib import Path
from datetime import date
import trader.data.split as s
root=Path(sys.argv[1]); publish=s._publish
def interrupt(stage,target):
    publish(stage,target)
    os._exit(17)
s._publish=interrupt
s.run_split(root/'owner/source',date(2020,1,8),root/'agent/dev',root/'owner/holdout',
 repo_root=root/'repo',agent_workspaces=[root/'agent'],provenance={
 'source':'synthetic','adapter_version':'test-v1','code_commit':'test',
 'retrieved_at':'2026-10-16T00:00:00Z'})
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)])
    assert result.returncode == 17
    assert args["holdout_out"].exists() and not args["dev_out"].exists()
    error = assert_error(SplitError, "SPLIT_OUTPUT_EXISTS", run_split, **args)
    assert str(args["holdout_out"]) in error.paths
    import shutil

    shutil.rmtree(args["holdout_out"])
    error = assert_error(SplitError, "SPLIT_STAGING_EXISTS", run_split, **args)
    for path in error.paths:
        shutil.rmtree(path)
    run_split(**args)
    assert args["dev_out"].exists() and args["holdout_out"].exists()


def history(start=date(2018, 1, 1), end=date(2025, 12, 31)):
    days = tuple(
        start + timedelta(days=i)
        for i in range((end - start).days + 1)
        if (start + timedelta(days=i)).weekday() < 5
    )
    return ParsedImport(
        tuple(PriceRecord("SYN_A", d, 100.0, "GBP") for d in days),
        (),
        days,
        (Declaration("SYN_A", "unadjusted_close", True, end, "synthetic", end),),
    )


def test_proposal_reference_counts_and_leap():
    sufficient = propose_holdout(history())
    assert sufficient.holdout_start == date(2021, 12, 31)
    assert sufficient.instruments["SYN_A"] == {
        "development": 1044,
        "holdout": 1044,
        "sufficient": True,
        "codes": [],
    }
    short = propose_holdout(history(date(2019, 1, 1)))
    assert (
        short.holdout_start is None and short.instruments["SYN_A"]["development"] == 783
    )
    leap = propose_holdout(history(end=date(2028, 2, 29)))
    assert leap.holdout_start == date(2024, 2, 28)


@pytest.mark.parametrize(
    "bad,code",
    [
        ("duplicate", "DATA_DUPLICATE"),
        ("unit", "DATA_UNKNOWN_UNIT"),
        ("zero", "DATA_INVALID_PRICE"),
        ("off_calendar", "DATA_OFF_CALENDAR"),
    ],
)
def test_proposal_bad_records_insufficient(bad, code):
    data = history()
    prices = list(data.prices)
    if bad == "duplicate":
        prices.append(prices[0])
    elif bad == "unit":
        prices[0] = replace(prices[0], unit="USD")
    elif bad == "zero":
        prices[0] = replace(prices[0], close=0.0)
    else:
        prices[0] = replace(prices[0], date=date(2018, 1, 6))
    result = propose_holdout(replace(data, prices=tuple(prices)))
    assert result.holdout_start is None
    assert code in result.instruments["SYN_A"]["codes"]
    assert result.instruments["SYN_A"]["development"] is None


def test_proposal_unsorted_calendar():
    data = history()
    assert_error(
        InvalidInputError,
        "INVALID_CALENDAR",
        propose_holdout,
        replace(data, calendar=tuple(reversed(data.calendar))),
    )


def test_invalid_mode_named():
    data = example()
    assert_error(
        InvalidInputError,
        "INVALID_MODE",
        build_dataset,
        data.calendar,
        DAYS[-1],
        ["SYN_A"],
        data.prices,
        data.distributions,
        (),
        DataParams(),
        mode="invalid",
    )


def test_cli_proposal_and_split(tmp_path, capsys):
    source = export(tmp_path / "owner" / "source", history())
    base = [
        "--source",
        str(source),
        "--repo-root",
        str(tmp_path / "repo"),
        "--agent-workspace",
        str(tmp_path / "agent"),
    ]
    assert main(["--propose-holdout", *base]) == 0
    assert json.loads(capsys.readouterr().out)["holdout_start"] == "2021-12-31"
    assert not list(tmp_path.rglob("*.parquet"))
    args = [
        *base,
        "--holdout-start",
        "2021-12-31",
        "--dev-out",
        str(tmp_path / "agent/dev"),
        "--holdout-out",
        str(tmp_path / "owner/hold"),
        "--source-label",
        "synthetic",
        "--adapter-version",
        "test-v1",
        "--retrieved-at",
        PROVENANCE["retrieved_at"],
    ]
    assert main(args) == 0
    assert len(json.loads(capsys.readouterr().out)) == 2
    assert main(args) == 1
    assert "SPLIT_OUTPUT_EXISTS" in capsys.readouterr().err


@pytest.mark.parametrize(
    "row", ['SYN_"A,2020-01-06,100,GBP\n', '"SYN_A"x,2020-01-06,100,GBP\n']
)
def test_bare_and_trailing_quotes_rejected(tmp_path, row):
    source = export(tmp_path / "source")
    (source / "prices.csv").write_text(",".join(HEADERS["prices.csv"]) + "\n" + row)
    assert_error(DataImportError, "IMPORT_MALFORMED_ROW", _parse_csv_dir, source)


def test_multiline_quoted_evidence(tmp_path):
    data = example()
    data = replace(
        data,
        declarations=(
            replace(
                data.declarations[0],
                evidence_source='synthetic "issuer", evidence\nsecond line',
            ),
        ),
    )
    assert _parse_csv_dir(export(tmp_path / "source", data)) == data


def test_prospective_case_alias_refused_before_parse(tmp_path, monkeypatch):
    from trader.data.split import SplitError

    args = split_args(tmp_path)
    args["dev_out"] = tmp_path / "owner" / "HOLDOUT"
    monkeypatch.setattr("trader.data.split._case_insensitive", lambda p: True)

    def no_read(*a, **kw):
        pytest.fail("aliased nonexistent outputs must fail before content reads")

    monkeypatch.setattr("trader.data.split._parse_csv_dir", no_read)
    assert_error(SplitError, "SPLIT_PATHS_OVERLAP", run_split, **args)


def test_directory_sync_failure_rolls_back(tmp_path, monkeypatch):
    args = split_args(tmp_path)

    def fail_sync(path):
        raise OSError("synthetic sync failure after rename")

    monkeypatch.setattr("trader.data.split._sync_directory", fail_sync)
    with pytest.raises(OSError):
        run_split(**args)
    assert not args["dev_out"].exists() and not args["holdout_out"].exists()
    assert not list(tmp_path.rglob("*.staging-*"))


def test_record_order_does_not_change_identity(tmp_path):
    data = raw()
    first = write_raw_dataset(data, tmp_path / "a", provenance=PROVENANCE)
    second = write_raw_dataset(
        replace(data, prices=tuple(reversed(data.prices))),
        tmp_path / "b",
        provenance=PROVENANCE,
    )
    assert first["dataset_id"] == second["dataset_id"]


def test_existing_destination_never_removed(tmp_path):
    root = tmp_path / "existing"
    root.mkdir()
    (root / "owner-file").write_text("preserve")
    with pytest.raises(FileExistsError):
        write_raw_dataset(raw(), root, provenance=PROVENANCE)
    assert (root / "owner-file").read_text() == "preserve"


def test_duplicate_declarations_rejected(tmp_path):
    data = example()
    data = replace(data, declarations=data.declarations * 2)
    source = export(tmp_path / "source", data)
    assert_error(DataImportError, "IMPORT_DECLARATION_INVALID", _parse_csv_dir, source)


def test_partial_instrument_partition_keeps_source_declaration(tmp_path):
    data = example()
    extra = PriceRecord("SYN_B", DAYS[-1], 100.0, "GBP")
    data = replace(
        data,
        prices=(*data.prices, extra),
        declarations=(
            *data.declarations,
            replace(data.declarations[0], instrument="SYN_B"),
        ),
    )
    args = split_args(tmp_path)
    import shutil

    shutil.rmtree(args["source"])
    export(args["source"], data)
    run_split(**args)
    development, _ = read_raw_dataset(args["dev_out"])
    assert len(development.declarations) == 2
    assert all(p.instrument == "SYN_A" for p in development.prices)


# T-008 follow-ups: storage remains v1 despite the richer canonical record.
def test_storage_refuses_opens_before_publication(tmp_path):
    dataset = raw()
    dataset = replace(dataset, prices=(replace(dataset.prices[0], open=100.), *dataset.prices[1:]))
    assert_error(DataStoreError, 'OPEN_PRICES_UNSUPPORTED', write_raw_dataset,
                 dataset, tmp_path / 'out', provenance=PROVENANCE)
    assert not (tmp_path / 'out').exists()


def test_csv_open_column_still_refused(tmp_path):
    source = export(tmp_path / 'source')
    path = source / 'prices.csv'
    path.write_text(path.read_text().replace('instrument,date,close,unit', 'instrument,date,close,unit,open'))
    assert_error(DataImportError, 'IMPORT_BAD_HEADER', _parse_csv_dir, source)


def test_arrow_exception_named(tmp_path, monkeypatch):
    directory = tmp_path / 'dataset'
    write_raw_dataset(raw(), directory, provenance=PROVENANCE)
    def damaged(*a, **kw):
        raise pa.ArrowException('synthetic damaged metadata')
    monkeypatch.setattr(pq, 'read_table', damaged)
    assert_error(DataStoreError, 'DATASET_MANIFEST_MISMATCH', read_raw_dataset, directory)


def test_unreadable_source_publishes_nothing(tmp_path):
    import os
    if os.geteuid() == 0:
        pytest.skip('root bypasses chmod permissions')
    args = split_args(tmp_path)
    path = args['source'] / 'prices.csv'
    path.chmod(0)
    try:
        with pytest.raises((OSError, DataImportError)):
            run_split(**args)
    finally:
        path.chmod(0o600)
    assert not args['dev_out'].exists() and not args['holdout_out'].exists()
    assert not list(tmp_path.rglob('*.staging-*'))


def test_all_leftovers_reported(tmp_path):
    from trader.data.split import SplitError, preflight
    args = split_args(tmp_path)
    outputs = [args['dev_out'], args['holdout_out']]
    leftovers = [p.with_name(p.name + '.staging-old') for p in outputs]
    for p in [*outputs, *leftovers]:
        p.mkdir(parents=True)
    check = {k: v for k, v in args.items() if k not in ('holdout_start', 'provenance')}
    exc = assert_error(SplitError, 'SPLIT_OUTPUT_EXISTS', preflight, **check)
    assert set(exc.paths) == set(map(str, [*outputs, *leftovers]))
    for p in outputs:
        p.rmdir()
    exc = assert_error(SplitError, 'SPLIT_STAGING_EXISTS', preflight, **check)
    assert set(exc.paths) == set(map(str, leftovers))


def test_dirty_checkout_refused_before_read(tmp_path, monkeypatch, capsys):
    import trader.data.split as split
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    def git(*args):
        return subprocess.run(['git', '-C', str(checkout), *args], check=True, capture_output=True, text=True).stdout.strip()
    git('init')
    git('config', 'user.name', 'Synthetic Test')
    git('config', 'user.email', 'synthetic@example.invalid')
    tracked = checkout / 'tracked.txt'
    tracked.write_text('one')
    git('add', '.')
    git('commit', '-m', 'synthetic initial')
    monkeypatch.setattr(split, '_code_checkout', lambda: checkout)
    assert split._clean_commit() == git('rev-parse', 'HEAD')
    (checkout / 'untracked.txt').write_text('ignored by the specified tracked-only guard')
    assert split._clean_commit() == git('rev-parse', 'HEAD')
    tracked.write_text('two')
    monkeypatch.setattr(split, '_parse_csv_dir', lambda *a: pytest.fail('must refuse before reading'))
    assert split.main(['--source', str(tmp_path / 'source'), '--repo-root', str(checkout),
                       '--agent-workspace', str(tmp_path / 'agent'), '--propose-holdout']) == 1
    assert 'SPLIT_DIRTY_CHECKOUT' in capsys.readouterr().err
    git('add', '.')
    assert_error(split.SplitError, 'SPLIT_DIRTY_CHECKOUT', split._clean_commit)
