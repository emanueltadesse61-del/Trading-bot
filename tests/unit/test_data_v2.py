"""T-010 acceptance on synthetic data; never downloads or activates real runs."""

import csv
import hashlib
import inspect
import json
from collections import Counter
from dataclasses import asdict, replace
from datetime import date, datetime

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from trader.backtest import (
    BacktestInputError,
    BacktestParams,
    Market,
    market_from_raw,
    run_backtest,
    scripted,
)
from trader.data.csv_import import HEADERS, HEADERS_V2, _parse_csv_dir, import_csv
from trader.data.raw import DataImportError, DataStoreError, Declaration, RawDataset
from trader.data.records import DistributionRecord, JumpException, PriceRecord
from trader.data.split import run_split
from trader.data.store import (
    SCHEMA,
    SCHEMA_V2,
    SETTINGS,
    dataset_identity,
    read_raw_dataset,
    write_raw_dataset,
)
from trader.registry import SUPPORTED_REAL_SCHEMAS, RegistryError
from trader.registry.cli import main as registry_cli

DAYS = tuple(date(2024, 1, d) for d in (8, 9, 10, 11, 12, 15, 16))
H = DAYS[3]
PROVENANCE = {
    "source": "synthetic",
    "adapter_version": "t010-test",
    "code_commit": "test",
    "retrieved_at": "2026-11-11T00:00:00Z",
}


def dataset(empty=False):
    return RawDataset(
        tuple(
            PriceRecord("SYN_A", d, 100.0, "GBP", None if empty else 100.0)
            for d in DAYS
        ),
        () if empty else (DistributionRecord("SYN_A", DAYS[2], 1.0, "GBP", DAYS[5]),),
        DAYS,
        (
            Declaration(
                "SYN_A",
                "unadjusted_close",
                True,
                DAYS[-1],
                "synthetic evidence",
                DAYS[-1],
            ),
        ),
        "synthetic",
        None,
    )


def export(directory, data, version="v2"):
    directory.mkdir(parents=True)
    headers = HEADERS_V2 if version == "v2" else HEADERS
    for name, records in zip(
        headers, (data.prices, data.distributions, data.calendar, data.declarations)
    ):
        with (directory / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, headers[name])
            writer.writeheader()
            for record in records:
                row = {"date": record} if type(record) is date else asdict(record)
                writer.writerow(
                    {
                        k: str(row[k]).lower() if type(row[k]) is bool else row[k]
                        for k in headers[name]
                    }
                )
    return directory


def change_csv(file, field, value):
    with file.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    rows[0][field] = value
    with file.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(rows)


def error(code, func, *args, **kwargs):
    with pytest.raises(
        (DataImportError, DataStoreError, BacktestInputError, RegistryError)
    ) as caught:
        func(*args, **kwargs)
    assert caught.value.code == code
    return caught.value


def split_args(tmp_path, data, version):
    return dict(
        source=export(tmp_path / "owner/source", data, version),
        holdout_start=H,
        dev_out=tmp_path / "agent/dev",
        holdout_out=tmp_path / "owner/holdout",
        repo_root=tmp_path / "repo",
        agent_workspaces=[tmp_path / "agent"],
        provenance=PROVENANCE,
    )


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_empty_values_preserve_schema_through_split(tmp_path, version):
    data = dataset(empty=True)
    args = split_args(tmp_path, data, version)
    parsed, actual = _parse_csv_dir(args["source"])
    assert (
        actual == version and parsed.prices == data.prices and not parsed.distributions
    )
    manifests = run_split(**args)
    for path, manifest in zip((args["dev_out"], args["holdout_out"]), manifests):
        assert manifest["schema"] == f"trading-bot/raw-dataset/{version}"
        if version == "v1":
            error("BACKTEST_RAW_SCHEMA", market_from_raw, path, (), "test")
        else:
            market, returned = market_from_raw(path, (), "test")
            assert returned == manifest and not market.distributions
            assert all(r.open is None for r in market.prices)
    assert "schema" not in inspect.signature(market_from_raw).parameters


def test_split_preserves_events_and_cross_boundary_pay_date(tmp_path):
    data = dataset()
    args = split_args(tmp_path, data, "v2")
    run_split(**args)
    dev, hold = (read_raw_dataset(args[key])[0] for key in ("dev_out", "holdout_out"))
    for field in ("prices", "distributions", "calendar"):
        assert Counter((*getattr(dev, field), *getattr(hold, field))) == Counter(
            getattr(data, field)
        )
    assert dev.distributions[0].ex_date < H < dev.distributions[0].pay_date
    assert dev.declarations == hold.declarations == data.declarations


def test_public_import_preserves_records_and_signature(tmp_path):
    data = dataset()
    data = replace(data, prices=(replace(data.prices[0], open=None), *data.prices[1:]))
    source = export(tmp_path / "source", data)
    imported = import_csv(source, holdout_start=None, synthetic=True)
    assert type(imported) is RawDataset and imported == data
    assert set(inspect.signature(import_csv).parameters) == {
        "directory",
        "holdout_start",
        "synthetic",
    }
    error(
        "OPEN_PRICES_UNSUPPORTED",
        write_raw_dataset,
        imported,
        tmp_path / "v1",
        provenance=PROVENANCE,
    )


@pytest.mark.parametrize(
    "file,field,value,code",
    [
        ("prices.csv", "open", "abc", "IMPORT_BAD_NUMBER"),
        ("prices.csv", "open", "NaN", "IMPORT_BAD_NUMBER"),
        ("prices.csv", "open", "1e999", "IMPORT_BAD_NUMBER"),
        ("distributions.csv", "pay_date", "", "IMPORT_BAD_DATE"),
        ("distributions.csv", "pay_date", "20240115", "IMPORT_BAD_DATE"),
        ("distributions.csv", "pay_date", "2024-01-09", "IMPORT_PAY_BEFORE_EX"),
    ],
)
def test_bad_csv_values(tmp_path, file, field, value, code):
    source = export(tmp_path / "source", dataset())
    change_csv(source / file, field, value)
    error(code, _parse_csv_dir, source)


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_mixed_headers_refused_with_no_distributions(tmp_path, version):
    source = export(tmp_path / "source", dataset(empty=True), version)
    other = HEADERS if version == "v2" else HEADERS_V2
    (source / "distributions.csv").write_text(
        ",".join(other["distributions.csv"]) + "\n"
    )
    error("IMPORT_BAD_HEADER", _parse_csv_dir, source)


def test_storage_identity_determinism_and_roundtrip(tmp_path):
    data = dataset()
    first = write_raw_dataset(data, tmp_path / "a", provenance=PROVENANCE, schema="v2")
    second = write_raw_dataset(
        replace(data, prices=tuple(reversed(data.prices))),
        tmp_path / "b",
        provenance=PROVENANCE,
        schema="v2",
    )
    assert first == second
    for file in (tmp_path / "a").iterdir():
        assert file.read_bytes() == (tmp_path / "b" / file.name).read_bytes()
    assert read_raw_dataset(tmp_path / "a") == (data, first)
    identity = {
        "schema": SCHEMA_V2,
        "partition": "synthetic",
        "holdout_start": None,
        "files": {k: v["sha256"] for k, v in first["files"].items()},
    }
    assert (
        first["dataset_id"]
        == hashlib.sha256(
            json.dumps(
                identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ).hexdigest()
    )
    empty = dataset(empty=True)
    a = write_raw_dataset(empty, tmp_path / "v1", provenance=PROVENANCE)
    b = write_raw_dataset(empty, tmp_path / "v2", provenance=PROVENANCE, schema="v2")
    assert a["dataset_id"] != b["dataset_id"]
    assert read_raw_dataset(tmp_path / "v1")[0] == read_raw_dataset(tmp_path / "v2")[0]


@pytest.mark.parametrize(
    "pay", [None, "2024-01-15", datetime(2024, 1, 15), date(2024, 1, 9)]
)
def test_writer_refuses_bad_pay_date_before_publication(tmp_path, pay):
    data = dataset()
    data = replace(data, distributions=(replace(data.distributions[0], pay_date=pay),))
    error(
        "PAY_DATE_INVALID",
        write_raw_dataset,
        data,
        tmp_path / "out",
        provenance=PROVENANCE,
        schema="v2",
    )
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("schema", ["v3", SCHEMA_V2, None, [], 2])
def test_unknown_writer_schema(tmp_path, schema):
    error(
        "SCHEMA_UNSUPPORTED",
        write_raw_dataset,
        dataset(),
        tmp_path / "out",
        provenance=PROVENANCE,
        schema=schema,
    )
    assert not (tmp_path / "out").exists()


def test_v1_default_and_pay_date_refusal(tmp_path):
    data = dataset()
    data = replace(data, prices=tuple(replace(r, open=None) for r in data.prices))
    error(
        "PAY_DATES_UNSUPPORTED",
        write_raw_dataset,
        data,
        tmp_path / "out",
        provenance=PROVENANCE,
    )
    assert not (tmp_path / "out").exists()
    a = write_raw_dataset(dataset(True), tmp_path / "default", provenance=PROVENANCE)
    b = write_raw_dataset(
        dataset(True), tmp_path / "explicit", provenance=PROVENANCE, schema="v1"
    )
    assert a == b and a["schema"] == SCHEMA
    for file in (tmp_path / "default").iterdir():
        assert file.read_bytes() == (tmp_path / "explicit" / file.name).read_bytes()


def rewrite_table(directory, name, table):
    file = directory / name
    pq.write_table(table, file, **SETTINGS)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][name]["sha256"] = hashlib.sha256(file.read_bytes()).hexdigest()
    manifest["dataset_id"] = dataset_identity(
        manifest["partition"], manifest["holdout_start"], manifest["files"], schema="v2"
    )
    manifest_path.write_text(json.dumps(manifest))


@pytest.mark.parametrize(
    "pay,arrow_type",
    [
        (date(2024, 1, 9), pa.date32()),
        (None, pa.date32()),
        (datetime(2024, 1, 15), pa.timestamp("us")),
    ],
)
def test_reader_validates_pay_dates_after_rehash(tmp_path, pay, arrow_type):
    out = tmp_path / "out"
    write_raw_dataset(dataset(), out, provenance=PROVENANCE, schema="v2")
    table = pq.read_table(out / "distributions.parquet")
    table = table.set_column(
        table.schema.get_field_index("pay_date"),
        pa.field("pay_date", arrow_type, nullable=pay is None),
        pa.array([pay], type=arrow_type),
    )
    rewrite_table(out, "distributions.parquet", table)
    assert error("DATASET_MANIFEST_MISMATCH", read_raw_dataset, out).field == "pay_date"


def test_bridge_refuses_tampered_open_or_forged_schema(tmp_path):
    out = tmp_path / "out"
    write_raw_dataset(dataset(), out, provenance=PROVENANCE, schema="v2")
    table = pq.read_table(out / "prices.parquet")
    table = table.set_column(
        table.schema.get_field_index("open"), "open", pa.array([101.0] * len(DAYS))
    )
    pq.write_table(table, out / "prices.parquet", **SETTINGS)
    error("DATASET_MANIFEST_MISMATCH", market_from_raw, out, (), "test")
    v1 = tmp_path / "v1"
    write_raw_dataset(dataset(True), v1, provenance=PROVENANCE)
    manifest = json.loads((v1 / "manifest.json").read_text())
    manifest["schema"] = SCHEMA_V2
    (v1 / "manifest.json").write_text(json.dumps(manifest))
    error("DATASET_MANIFEST_MISMATCH", market_from_raw, v1, (), "test")


def simulate(market, end=DAYS[-1]):
    return run_backtest(
        market,
        scripted({DAYS[0]: [("SYN_A", "BUY", 10)]}, instruments=("SYN_A",)),
        BacktestParams(HALF_SPREAD={"SYN_A": 0}),
        start=DAYS[0],
        end=end,
        decision_dates=[DAYS[0]],
    )


@pytest.mark.parametrize("unit,scale", [("GBP", 1), ("GBX", 100)])
def test_bridge_matches_direct_simulation_and_provenance(tmp_path, unit, scale):
    data = dataset()
    data = replace(
        data,
        prices=tuple(
            replace(r, close=r.close * scale, open=r.open * scale, unit=unit)
            for r in data.prices
        ),
        distributions=tuple(
            replace(r, amount=r.amount * scale, unit=unit) for r in data.distributions
        ),
    )
    out = tmp_path / "out"
    written = write_raw_dataset(data, out, provenance=PROVENANCE, schema="v2")
    approvals = (JumpException("SYN_A", DAYS[2], "synthetic", "2026-10-16"),)
    market, manifest = market_from_raw(out, approvals, "frozen-test")
    direct = Market(
        data.calendar, data.prices, data.distributions, approvals, "frozen-test"
    )
    assert market == direct and manifest == written
    result = simulate(market)
    assert result == simulate(direct)
    assert result.ledger[-1]["settled"] == pytest.approx(9006.5)
    assert result.ledger[-1]["unsettled"] == 0
    assert result.inputs["exceptions_version"] == "frozen-test"
    assert result.inputs["exceptions_digest"] == direct.exceptions_digest


@pytest.mark.parametrize("pay", ["2024-01-15", datetime(2024, 1, 15), date(2024, 1, 9)])
@pytest.mark.parametrize("scope", ["inside", "other_instrument", "after_end"])
def test_pay_date_admission_scope(pay, scope):
    data = dataset()
    bad = replace(data.distributions[0], pay_date=pay)
    if scope == "other_instrument":
        bad = replace(bad, instrument="SYN_OTHER")
    if scope == "after_end":
        bad = replace(bad, ex_date=date(2024, 1, 17))
    market = Market(data.calendar, data.prices, (bad,))
    if scope == "inside":
        error("BACKTEST_PAY_DATE", simulate, market)
    else:
        assert simulate(market) == simulate(Market(data.calendar, data.prices))


def test_payment_beyond_run_remains_in_nav():
    data = dataset()
    result = simulate(
        Market(data.calendar, data.prices, data.distributions), end=DAYS[4]
    )
    assert result.ledger[-1]["settled"] == pytest.approx(8996.5)
    assert result.ledger[-1]["unsettled"] == 10
    assert result.ledger[-1]["nav"] == pytest.approx(10006.5)


def test_capability_stays_empty_and_cli_errors_are_neutral(tmp_path, capsys):
    assert SUPPORTED_REAL_SCHEMAS == frozenset()
    assert (
        registry_cli(
            [
                "verify",
                str(tmp_path / "registry"),
                "--checkpoint",
                str(tmp_path / "missing"),
            ]
        )
        == 1
    )
    assert json.loads(capsys.readouterr().err)["code"] == "REGISTRY_CLI_ERROR"


@pytest.mark.skipif(
    pa.__version__ != "23.0.1",
    reason="Byte identity is relative to the pinned writer version",
)
def test_v1_bytes_match_accepted_main_snapshot(tmp_path):
    # Captured independently from main 8098921, before T-010, with the T-007 example.
    days = tuple(date(2020, 1, d) for d in (6, 7, 8, 9))
    data = RawDataset(
        tuple(PriceRecord("SYN_A", d, 100.0, "GBP") for d in days),
        (DistributionRecord("SYN_A", days[1], 1.0, "GBP"),),
        days,
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
        "synthetic",
        None,
    )
    provenance = {
        "source": "synthetic",
        "adapter_version": "test-v1",
        "code_commit": "test",
        "retrieved_at": "2026-10-16T00:00:00Z",
    }
    expected = {
        "prices.parquet": "212a5baceccde1617ed614e435a2ebe6e4f25ca91945d53d1e5654030d368382",
        "distributions.parquet": "1b12830acd82a49d6ef0fb5d0f3c934bcbca9dc0e68a611e6e1ac31ccb84c1d2",
        "calendar.parquet": "c8a431c38b3ded62e94e29eec8e4f89477071be03b2736f9f7dae441e20917bd",
        "declarations.parquet": "6c870b68d74514822f7f6bb13f9d588ea6b3a7726eae3d83c697c0ddc90fc284",
        "manifest.json": "27c0ead057cc5cdcb7959afacf3ed87581de8666d30598d2647733665d222d89",
    }
    out = tmp_path / "v1"
    manifest = write_raw_dataset(data, out, provenance=provenance)
    assert (
        manifest["dataset_id"]
        == "4256992c9931fd5d87923fc52f30f05e092e03f4edbf444e181b475574c6be70"
    )
    assert {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()
    } == expected
    assert read_raw_dataset(out)[0] == data
