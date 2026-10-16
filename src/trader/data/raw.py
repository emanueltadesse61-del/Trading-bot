"""Raw import contracts and shared declaration validation (spec 8.4–8.5)."""

from dataclasses import dataclass
from datetime import date

from trader.data.records import DistributionRecord, PriceRecord


class DataImportError(ValueError):
    def __init__(self, code, file=None, line=None):
        self.code, self.file, self.line = code, file, line
        super().__init__(f"{code}: {file or '-'}:{line or 0}")


class DataStoreError(ValueError):
    def __init__(self, code, field):
        self.code, self.field = code, field
        super().__init__(f"{code}: {field}")


@dataclass(frozen=True)
class Declaration:
    instrument: str
    price_semantics: str
    distributions_complete: bool
    corporate_actions_none_through: date
    evidence_source: str
    checked_on: date


@dataclass(frozen=True)
class ParsedImport:
    prices: tuple[PriceRecord, ...]
    distributions: tuple[DistributionRecord, ...]
    calendar: tuple[date, ...]
    declarations: tuple[Declaration, ...]


@dataclass(frozen=True)
class RawDataset(ParsedImport):
    partition: str
    holdout_start: date | None


def declaration_problem(data):
    """Return (code, instrument), or None. Extra copied declarations are allowed.

    A partition can have no market records for a declared source instrument.
    Coverage is checked for every instrument that does have records here.
    """
    latest = {}
    for record in (*data.prices, *data.distributions):
        day = record.date if isinstance(record, PriceRecord) else record.ex_date
        latest[record.instrument] = max(day, latest.get(record.instrument, day))
    seen = set()
    for d in data.declarations:
        if (
            not d.instrument.strip()
            or d.instrument in seen
            or d.price_semantics != "unadjusted_close"
            or d.distributions_complete is not True
            or type(d.corporate_actions_none_through) is not date
            or type(d.checked_on) is not date
            or d.checked_on < d.corporate_actions_none_through
            or not d.evidence_source.strip()
            or (
                d.instrument in latest
                and d.corporate_actions_none_through < latest[d.instrument]
            )
        ):
            return "IMPORT_DECLARATION_INVALID", d.instrument
        seen.add(d.instrument)
    missing = sorted(set(latest) - seen)
    return ("IMPORT_DECLARATION_MISSING", missing[0]) if missing else None
