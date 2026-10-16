"""Local CSV boundaries. No network and no provider-specific interpretation."""

import csv
import math
import re
from datetime import date
from pathlib import Path

from trader.data.raw import (
    DataImportError,
    Declaration,
    ParsedImport,
    RawDataset,
    declaration_problem,
)
from trader.data.records import DistributionRecord, PriceRecord

HEADERS = {
    "prices.csv": ("instrument", "date", "close", "unit"),
    "distributions.csv": ("instrument", "ex_date", "amount", "unit"),
    "calendar.csv": ("date",),
    "declarations.csv": (
        "instrument",
        "price_semantics",
        "distributions_complete",
        "corporate_actions_none_through",
        "evidence_source",
        "checked_on",
    ),
}
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


def _day(text, file, line):
    try:
        result = date.fromisoformat(text)
        if result.isoformat() != text:
            raise ValueError
        return result
    except ValueError:
        raise DataImportError("IMPORT_BAD_DATE", file, line) from None


def _number(text, file, line, nullable=False):
    if nullable and text == "":
        return None
    if not NUMBER.fullmatch(text):
        raise DataImportError("IMPORT_BAD_NUMBER", file, line)
    value = float(text)
    if not math.isfinite(value):
        raise DataImportError("IMPORT_BAD_NUMBER", file, line)
    return value


def _checked_lines(stream, file):
    # csv.reader(strict=True) still accepts quotes inside an unquoted field.
    # Enforce quote placement while preserving multiline quoted fields.
    state = "start"
    for line_number, text in enumerate(stream, 1):
        for char in text:
            if state == "quoted":
                if char == '"':
                    state = "closed"
            elif state == "closed":
                if char == '"':
                    state = "quoted"
                elif char in ",\r\n":
                    state = "start"
                else:
                    raise DataImportError("IMPORT_MALFORMED_ROW", file, line_number)
            elif char == '"':
                if state != "start":
                    raise DataImportError("IMPORT_MALFORMED_ROW", file, line_number)
                state = "quoted"
            elif char in ",\r\n":
                state = "start"
            else:
                state = "unquoted"
        yield text


def _rows(directory, file):
    path = Path(directory) / file
    try:
        stream = path.open(encoding="utf-8", newline="")
    except FileNotFoundError:
        raise DataImportError("IMPORT_MISSING_FILE", file, 0) from None
    with stream:
        reader = csv.reader(_checked_lines(stream, file), strict=True)
        try:
            header = next(reader, [])
            if len(header) != len(HEADERS[file]) or set(header) != set(HEADERS[file]):
                raise DataImportError("IMPORT_BAD_HEADER", file, 1)
            while True:
                line = reader.line_num + 1
                row = next(reader, None)
                if row is None:
                    break
                if len(row) != len(header):
                    raise DataImportError("IMPORT_MALFORMED_ROW", file, line)
                yield dict(zip(header, row)), line
        except (csv.Error, UnicodeError):
            raise DataImportError(
                "IMPORT_MALFORMED_ROW", file, reader.line_num or 1
            ) from None


def _parse_csv_dir(directory, *, cutoff=None, synthetic=False):
    """Private full-history parser; only the owner CLI uses it without a cutoff.

    Public synthetic import is the other deliberate full-range test path.
    """
    output = {name: [] for name in HEADERS}
    locations = {}
    for file in HEADERS:
        for row, line in _rows(directory, file):
            if "instrument" in row:
                name = row["instrument"]
                if not name.strip():
                    raise DataImportError("IMPORT_MALFORMED_ROW", file, line)
                if synthetic and not name.startswith("SYN_"):
                    raise DataImportError("IMPORT_NOT_SYNTHETIC", file, line)
            if file != "declarations.csv":
                day = _day(row.get("date", row.get("ex_date")), file, line)
                if cutoff is not None and day >= cutoff:
                    raise DataImportError("IMPORT_HOLDOUT_LEAK", file, line)
                if file == "prices.csv":
                    record = PriceRecord(
                        name, day, _number(row["close"], file, line, True), row["unit"]
                    )
                elif file == "distributions.csv":
                    record = DistributionRecord(
                        name, day, _number(row["amount"], file, line), row["unit"]
                    )
                else:
                    record = day
            else:
                if row["distributions_complete"] not in ("true", "false"):
                    raise DataImportError("IMPORT_DECLARATION_INVALID", file, line)
                record = Declaration(
                    name,
                    row["price_semantics"],
                    row["distributions_complete"] == "true",
                    _day(row["corporate_actions_none_through"], file, line),
                    row["evidence_source"],
                    _day(row["checked_on"], file, line),
                )
                locations[name] = line
            output[file].append(record)
    parsed = ParsedImport(*(tuple(output[file]) for file in HEADERS))
    problem = declaration_problem(parsed)
    if problem:
        code, name = problem
        raise DataImportError(code, "declarations.csv", locations.get(name, 0))
    names = {r.instrument for r in (*parsed.prices, *parsed.distributions)}
    for declaration in parsed.declarations:
        if declaration.instrument not in names:
            raise DataImportError(
                "IMPORT_DECLARATION_INVALID",
                "declarations.csv",
                locations[declaration.instrument],
            )
    return parsed


def import_csv(directory, *, holdout_start, synthetic=False):
    """Development-only import; synthetic mode requires SYN_ ids throughout."""
    if holdout_start is None and not synthetic:
        raise DataImportError("IMPORT_HOLDOUT_REQUIRED")
    if holdout_start is not None and type(holdout_start) is not date:
        raise DataImportError("IMPORT_BAD_DATE", "holdout_start", 0)
    parsed = _parse_csv_dir(
        directory, cutoff=None if synthetic else holdout_start, synthetic=synthetic
    )
    return RawDataset(
        parsed.prices,
        parsed.distributions,
        parsed.calendar,
        parsed.declarations,
        "synthetic" if synthetic else "development",
        None if synthetic else holdout_start,
    )
