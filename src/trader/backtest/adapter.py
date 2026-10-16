"""Only this adapter exposes market observations to decision generators."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date

from trader.data import DataParams, build_dataset


@dataclass(frozen=True)
class Market:
    calendar: tuple
    prices: tuple
    distributions: tuple = ()
    exceptions: tuple = ()
    exceptions_version: str = "synthetic-v1"

    def __post_init__(self):
        for name in ("calendar", "prices", "distributions", "exceptions"):
            object.__setattr__(self, name, tuple(getattr(self, name)))

    def at(self, d, instruments):
        names = set(instruments)
        return Market(
            tuple(x for x in self.calendar if x <= d),
            tuple(r for r in self.prices if r.instrument in names and r.date <= d),
            tuple(
                r
                for r in self.distributions
                if r.instrument in names and r.ex_date <= d
            ),
            tuple(r for r in self.exceptions if r.instrument in names and r.date <= d),
            self.exceptions_version,
        )

    def build(self, d, instruments):
        bounded = self.at(d, instruments)
        return build_dataset(
            bounded.calendar,
            d,
            instruments,
            bounded.prices,
            bounded.distributions,
            bounded.exceptions,
            DataParams(),
            mode="research",
            exceptions_version=self.exceptions_version,
        )

    @property
    def exceptions_digest(self):
        entries = sorted(
            [
                dict(
                    instrument=e.instrument,
                    date=e.date.isoformat(),
                    reason=e.reason,
                    approved=e.approved,
                )
                for e in self.exceptions
            ],
            key=lambda e: (e["instrument"], e["date"]),
        )
        return hashlib.sha256(
            json.dumps(
                entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class DecisionMarket:
    """Bounded observations plus known month-end dates (no future observations)."""

    data: Market
    monthly_sessions: tuple[date, ...]

    def build(self, d, instruments):
        return self.data.build(d, instruments)
