"""Pure canonical-record builder (data specification v1.1 sections 2–7)."""

import hashlib
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from trader.data.params import DataParams
from trader.data.records import DistributionRecord, JumpException, PriceRecord
from trader.errors import InvalidInputError
from trader.numerics import is_finite_number


@dataclass(frozen=True)
class DataIssue:
    code: str
    instrument: str
    date: date


@dataclass(frozen=True)
class DataBuild:
    dates: list[date]
    tr_close: dict[str, list[float | None]]
    trade_close: dict[str, float | None]
    data_ok: bool
    report: list[DataIssue]
    mode: str
    exceptions_version: str | None
    exceptions_digest: str


def _approval_valid(value: str) -> bool:
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def build_dataset(
    calendar: Sequence[date], t: date, universe: Sequence[str],
    prices: Sequence[PriceRecord], distributions: Sequence[DistributionRecord],
    exceptions: Sequence[JumpException], params: DataParams,
    mode: str = "operational", exceptions_version: str | None = None,
) -> DataBuild:
    if (not calendar or any(type(d) is not date for d in calendar)
            or any(a >= b for a, b in zip(calendar, calendar[1:])) or t not in calendar):
        raise InvalidInputError("INVALID_CALENDAR", "Expected increasing sessions containing t")
    if mode not in {"operational", "research"}:
        raise ValueError("mode must be operational or research")
    if mode == "research" and (not isinstance(exceptions_version, str)
                               or not exceptions_version.strip()):
        raise InvalidInputError("INVALID_EXCEPTIONS_VERSION", "Research requires a snapshot version")
    dates = [d for d in calendar if d <= t]
    sessions, names = set(calendar), sorted(set(universe))
    issues: set[DataIssue] = set()
    excluded: set[str] = set()
    price_values, dividends = {}, {}

    def issue(code, instrument, when, exclude=True):
        issues.add(DataIssue(code, instrument, when))
        if exclude and instrument in names:
            excluded.add(instrument)

    # Validate both record kinds in the specified order. A record contributes
    # only its first failure; duplicate keys are counted independently of order.
    for records, is_price in ((prices, True), (distributions, False)):
        def record_date(record):
            return record.date if is_price else record.ex_date

        counts = Counter((r.instrument, record_date(r)) for r in records)
        for r in records:
            d = record_date(r)
            value = r.close if is_price else r.amount
            code = None
            if r.instrument not in names:
                code = "DATA_UNKNOWN_INSTRUMENT"
            elif d > t:
                code = "DATA_FUTURE_RECORD"
            elif d not in sessions:
                code = "DATA_OFF_CALENDAR"
            elif r.unit not in params.UNITS:
                code = "DATA_UNKNOWN_UNIT"
            elif not is_finite_number(value) or (value <= 0 if is_price else value < 0):
                code = "DATA_INVALID_PRICE" if is_price else "DATA_INVALID_DISTRIBUTION"
            elif counts[r.instrument, d] > 1:
                code = "DATA_DUPLICATE"
            elif not is_price and (r.instrument, d) not in price_values:
                code = "DATA_DISTRIBUTION_WITHOUT_PRICE"
            if code:
                issue(code, r.instrument, d)
            else:
                destination = price_values if is_price else dividends
                destination[r.instrument, d] = float(value) * params.UNITS[r.unit]

    entries = sorted(
        [{"instrument": e.instrument, "date": e.date.isoformat(),
          "reason": e.reason, "approved": e.approved} for e in exceptions],
        key=lambda e: (e["instrument"], e["date"]),
    )
    digest = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False).encode("utf-8")).hexdigest()
    approved = set()
    for e in exceptions:
        if (e.instrument not in names or e.date not in sessions
                or not isinstance(e.reason, str) or not e.reason.strip()
                or not _approval_valid(e.approved)):
            issue("DATA_INVALID_EXCEPTION", e.instrument, e.date, exclude=False)
        elif mode == "research" or date.fromisoformat(e.approved) <= t:
            approved.add((e.instrument, e.date))

    tr_close, trade_close = {}, {}
    for name in names:
        values = []
        previous_price = previous_tr = None
        for d in dates:
            price = None if name in excluded else price_values.get((name, d))
            if price is None:
                values.append(None)
                continue
            if previous_price is None:
                tr = price
            else:
                tr = previous_tr * (price + dividends.get((name, d), 0.0)) / previous_price
                if abs(price / previous_price - 1) > params.JUMP_LIMIT:
                    code = "DATA_JUMP_APPROVED" if (name, d) in approved else "DATA_JUMP"
                    issue(code, name, d, exclude=False)
            values.append(tr)
            previous_price, previous_tr = price, tr
        tr_close[name] = values
        trade_close[name] = None if name in excluded else price_values.get((name, t))
        if name not in excluded and trade_close[name] is None:
            issue("DATA_STALE", name, t, exclude=False)
    report = sorted(issues, key=lambda e: (e.instrument, e.date, e.code))
    data_ok = all(e.code in {"DATA_STALE", "DATA_JUMP_APPROVED"} for e in report)
    return DataBuild(dates, tr_close, trade_close, data_ok, report, mode,
                     exceptions_version, digest)
