"""Deterministic raw Parquet datasets. Integrity is relative to a pinned manifest."""

import hashlib
import json
import os
import shutil
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from trader.data.raw import DataStoreError, Declaration, RawDataset, declaration_problem
from trader.data.records import DistributionRecord, PriceRecord

SCHEMA = "trading-bot/raw-dataset/v1"
SCHEMAS = {
    "prices.parquet": pa.schema(
        [
            ("instrument", pa.string()),
            ("date", pa.date32()),
            ("close", pa.float64()),
            ("unit", pa.string()),
        ]
    ),
    "distributions.parquet": pa.schema(
        [
            ("instrument", pa.string()),
            ("ex_date", pa.date32()),
            ("amount", pa.float64()),
            ("unit", pa.string()),
        ]
    ),
    "calendar.parquet": pa.schema([("date", pa.date32())]),
    "declarations.parquet": pa.schema(
        [
            ("instrument", pa.string()),
            ("price_semantics", pa.string()),
            ("distributions_complete", pa.bool_()),
            ("corporate_actions_none_through", pa.date32()),
            ("evidence_source", pa.string()),
            ("checked_on", pa.date32()),
        ]
    ),
}
SCHEMA_V2 = "trading-bot/raw-dataset/v2"
SCHEMAS_V2 = {
    **SCHEMAS,
    "prices.parquet": SCHEMAS["prices.parquet"].append(pa.field("open", pa.float64())),
    "distributions.parquet": SCHEMAS["distributions.parquet"].append(
        pa.field("pay_date", pa.date32(), nullable=False)
    ),
}
VERSIONS = {"v1": (SCHEMA, SCHEMAS), "v2": (SCHEMA_V2, SCHEMAS_V2)}
SETTINGS = {
    "compression": "NONE",
    "row_group_size": 65536,
    "version": "2.6",
    "use_dictionary": False,
    "write_statistics": True,
}
WRITER = {"library": "pyarrow", "version": pa.__version__, "settings": SETTINGS}


def _json(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def dataset_identity(partition, holdout_start, files, *, schema="v1"):
    schema_name, schemas = _version(schema)
    return _sha(
        _json(
            {
                "schema": schema_name,
                "partition": partition,
                "holdout_start": holdout_start,
                "files": {name: files[name]["sha256"] for name in schemas},
            }
        )
    )


def _fail(field):
    raise DataStoreError("DATASET_MANIFEST_MISMATCH", field)


def _version(schema):
    if not isinstance(schema, str) or schema not in VERSIONS:
        raise DataStoreError("SCHEMA_UNSUPPORTED", "schema")
    return VERSIONS[schema]


def _valid_pay_date(record):
    return (
        type(record.pay_date) is date
        and type(record.ex_date) is date
        and record.pay_date >= record.ex_date
    )


def _validate_dataset(data):
    if not data.calendar or any(type(d) is not date for d in data.calendar):
        _fail("calendar")
    if data.partition not in ("development", "holdout", "synthetic"):
        _fail("partition")
    if data.partition == "synthetic":
        if data.holdout_start is not None:
            _fail("holdout_start")
        if any(
            not r.instrument.startswith("SYN_")
            for r in (*data.prices, *data.distributions, *data.declarations)
        ):
            _fail("partition")
    else:
        if type(data.holdout_start) is not date:
            _fail("holdout_start")
        events = [
            *data.calendar,
            *(r.date for r in data.prices),
            *(r.ex_date for r in data.distributions),
        ]
        for day in events:
            if type(day) is not date or (
                (day < data.holdout_start) != (data.partition == "development")
            ):
                _fail("partition")
    if declaration_problem(data):
        _fail("declarations")


def _summary(data):
    names = sorted({r.instrument for r in (*data.prices, *data.distributions)})
    instruments = {}
    for name in names:
        prices = [r for r in data.prices if r.instrument == name]
        dividends = [r for r in data.distributions if r.instrument == name]
        instruments[name] = {
            "units_seen": sorted({r.unit for r in (*prices, *dividends)}),
            "price_rows": len(prices),
            "distribution_rows": len(dividends),
        }
    return (
        {
            "first": min(data.calendar).isoformat(),
            "last": max(data.calendar).isoformat(),
        },
        instruments,
    )


def _provenance(value):
    keys = {"source", "adapter_version", "code_commit", "retrieved_at"}
    if set(value) != keys or any(
        not isinstance(value[k], str) or not value[k].strip() for k in keys
    ):
        _fail("provenance")
    try:
        timestamp = datetime.fromisoformat(value["retrieved_at"].replace("Z", "+00:00"))
        if timestamp.utcoffset() != timedelta(0):
            _fail("retrieved_at")
    except ValueError:
        _fail("retrieved_at")


def _tables(data, schemas=SCHEMAS):
    rows = {
        "prices.parquet": [asdict(r) for r in data.prices],
        "distributions.parquet": [asdict(r) for r in data.distributions],
        "calendar.parquet": [{"date": d} for d in data.calendar],
        "declarations.parquet": [asdict(r) for r in data.declarations],
    }
    if schemas is SCHEMAS:
        # Preserve the exact pre-v2 v1 row ordering and bytes.
        for row in rows["distributions.parquet"]:
            row.pop("pay_date")
    for name, records in rows.items():
        # Full-row tie-breaker keeps duplicate/invalid input order from changing
        # identity. Rows are preserved, never deduplicated or filled.
        records.sort(
            key=lambda r: (
                r.get("instrument", ""),
                r.get("date", r.get("ex_date", date.min)),
                repr(sorted(r.items())),
            )
        )
        yield name, pa.Table.from_pylist(records, schema=schemas[name])


def write_raw_dataset(dataset, directory, *, provenance, schema="v1"):
    """Write only into a new directory. CLI provides staging/publication."""
    schema_name, schemas = _version(schema)
    if schema == "v1":
        if any(r.open is not None for r in dataset.prices):
            raise DataStoreError("OPEN_PRICES_UNSUPPORTED", "prices")
        if any(r.pay_date is not None for r in dataset.distributions):
            raise DataStoreError("PAY_DATES_UNSUPPORTED", "pay_date")
    elif any(not _valid_pay_date(r) for r in dataset.distributions):
        raise DataStoreError("PAY_DATE_INVALID", "pay_date")
    _validate_dataset(dataset)
    _provenance(provenance)
    directory = Path(directory)
    directory.mkdir()  # never overwrite or remove a pre-existing destination
    try:
        files = {}
        for name, table in _tables(dataset, schemas):
            path = directory / name
            pq.write_table(table, path, **SETTINGS)
            with path.open("rb") as stream:
                os.fsync(stream.fileno())
            files[name] = {"sha256": _sha(path.read_bytes()), "rows": table.num_rows}
        boundary = dataset.holdout_start.isoformat() if dataset.holdout_start else None
        date_range, instruments = _summary(dataset)
        manifest = {
            "schema": schema_name,
            "partition": dataset.partition,
            "holdout_start": boundary,
            "files": files,
            "dataset_id": dataset_identity(
                dataset.partition, boundary, files, schema=schema
            ),
            "date_range": date_range,
            "instruments": instruments,
            **provenance,
            "writer": WRITER,
        }
        content = _json(manifest)
        (directory / "manifest.json").write_bytes(content)
        with (directory / "manifest.json").open("rb") as stream:
            os.fsync(stream.fileno())
        _sync_directory(directory)
        return {**manifest, "manifest_digest": _sha(content)}
    except BaseException:
        shutil.rmtree(directory)
        raise


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("manifest.json")
        result[key] = value
    return result


def read_raw_dataset(directory):
    """Validate bytes, typed schemas, summaries, declarations and every event."""
    directory = Path(directory)
    field = "files"
    try:
        if {p.name for p in directory.iterdir()} != {"manifest.json", *SCHEMAS}:
            _fail(field)
        if any(not p.is_file() or p.is_symlink() for p in directory.iterdir()):
            _fail(field)
        field = "manifest.json"
        content = (directory / field).read_bytes()
        manifest = json.loads(content, object_pairs_hook=_unique_pairs)
        expected = {
            "schema",
            "partition",
            "holdout_start",
            "files",
            "dataset_id",
            "date_range",
            "instruments",
            "source",
            "adapter_version",
            "code_commit",
            "retrieved_at",
            "writer",
        }
        if not isinstance(manifest, dict) or set(manifest) != expected:
            _fail(field)
        version = next(
            (v for v, (name, _) in VERSIONS.items() if name == manifest["schema"]), None
        )
        if version is None:
            _fail("schema")
        _, schemas = VERSIONS[version]
        _provenance(
            {
                k: manifest[k]
                for k in ("source", "adapter_version", "code_commit", "retrieved_at")
            }
        )
        writer = manifest["writer"]
        if (
            not isinstance(writer, dict)
            or set(writer) != {"library", "version", "settings"}
            or writer["library"] != "pyarrow"
            or not isinstance(writer["version"], str)
            or not writer["version"]
            or writer["settings"] != SETTINGS
        ):
            _fail("writer")
        if set(manifest["files"]) != set(SCHEMAS):
            _fail("files")
        tables = {}
        for name, schema in schemas.items():
            field = name
            info = manifest["files"][name]
            if (
                set(info) != {"sha256", "rows"}
                or type(info["rows"]) is not int
                or info["rows"] < 0
            ):
                _fail(name)
            # Decode the very bytes hashed, avoiding a second mutable-path read.
            data = (directory / name).read_bytes()
            if _sha(data) != info["sha256"]:
                _fail(name)
            table = pq.read_table(pa.BufferReader(data))
            if version == "v2" and name == "distributions.parquet":
                if (
                    "pay_date" not in table.column_names
                    or table.schema.field("pay_date").type != pa.date32()
                    or table["pay_date"].null_count
                ):
                    _fail("pay_date")
            if (
                not table.schema.equals(schema, check_metadata=True)
                or table.num_rows != info["rows"]
            ):
                _fail(name)
            for column in table.column_names:
                if column not in ("close", "open") and table[column].null_count:
                    _fail(name)
            tables[name] = table.to_pylist()
        field = "dataset_id"
        if (
            dataset_identity(
                manifest["partition"],
                manifest["holdout_start"],
                manifest["files"],
                schema=version,
            )
            != manifest["dataset_id"]
        ):
            _fail(field)
        field = "holdout_start"
        boundary = manifest["holdout_start"]
        day = None if boundary is None else date.fromisoformat(boundary)
        if day is not None and day.isoformat() != boundary:
            _fail(field)
        dataset = RawDataset(
            tuple(PriceRecord(**r) for r in tables["prices.parquet"]),
            tuple(DistributionRecord(**r) for r in tables["distributions.parquet"]),
            tuple(r["date"] for r in tables["calendar.parquet"]),
            tuple(Declaration(**r) for r in tables["declarations.parquet"]),
            manifest["partition"],
            day,
        )
        if version == "v2" and any(
            not _valid_pay_date(r) for r in dataset.distributions
        ):
            _fail("pay_date")
        _validate_dataset(dataset)
        ranges, instruments = _summary(dataset)
        for field, actual in [("date_range", ranges), ("instruments", instruments)]:
            if _json(actual) != _json(manifest[field]):
                _fail(field)
        return dataset, {**manifest, "manifest_digest": _sha(content)}
    except DataStoreError:
        raise
    except (
        pa.ArrowException,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        OverflowError,
    ) as exc:
        raise DataStoreError("DATASET_MANIFEST_MISMATCH", field) from exc
