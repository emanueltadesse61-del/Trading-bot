"""Canonical adapter inputs. Dates are exchange-session dates, not timestamps."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PriceRecord:
    instrument: str
    date: date
    close: float | None
    unit: str


@dataclass(frozen=True)
class DistributionRecord:
    instrument: str
    ex_date: date
    amount: float
    unit: str


@dataclass(frozen=True)
class JumpException:
    instrument: str
    date: date
    reason: str
    approved: str
