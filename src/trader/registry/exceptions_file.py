"""Decode jump approvals without changing the builder's canonical types."""

from dataclasses import dataclass
from pathlib import Path

from trader.data.build import exceptions_digest
from trader.data.records import JumpException

from .canonical import strict_json
from .errors import RegistryError
from .validation import exact, iso_date, text


@dataclass(frozen=True)
class ExceptionsSnapshot:
    version: str
    entries: tuple[JumpException, ...]

    @property
    def digest(self):
        return exceptions_digest(self.entries)


def read_exceptions(path):
    try:
        value = strict_json(Path(path).read_text(encoding="utf-8"))
        exact(value, {"schema", "version", "entries"}, "exceptions")
        if value["schema"] != "trading-bot/exceptions/v1" or not isinstance(
            value["entries"], list
        ):
            raise ValueError("schema/entries")
        text(value["version"], "version")
        entries = []
        for entry in value["entries"]:
            exact(entry, {"instrument", "date", "reason", "approved"}, "entry")
            for key in ("instrument", "reason"):
                text(entry[key], key)
            iso_date(entry["approved"])
            entries.append(JumpException(**{**entry, "date": iso_date(entry["date"])}))
        return ExceptionsSnapshot(value["version"], tuple(entries))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise RegistryError("REGISTRY_EXCEPTIONS_FORMAT", str(exc)) from exc
