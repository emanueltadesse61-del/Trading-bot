"""Exchange-calendar period ends; never infer an end for the last session."""

from datetime import date

from .errors import BacktestInputError


def validate_calendar(calendar):
    if (
        not calendar
        or any(type(d) is not date for d in calendar)
        or any(a >= b for a, b in zip(calendar, calendar[1:]))
    ):
        raise BacktestInputError(
            "BACKTEST_CALENDAR", "expected increasing unique session dates"
        )


def decision_sessions(calendar, kind):
    validate_calendar(calendar)
    if kind not in ("weekly", "monthly"):
        raise BacktestInputError("BACKTEST_SCHEDULE", str(kind))

    def period(d):
        return d.isocalendar()[:2] if kind == "weekly" else (d.year, d.month)

    return [a for a, b in zip(calendar, calendar[1:]) if period(a) != period(b)]
