"""UTC recurrence anchored to the original start, independent of worker delays."""

from calendar import monthrange
from datetime import datetime, timedelta, timezone

_INTERVALS = {
    "minutely": timedelta(minutes=1),
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}


def next_occurrence(
    start: datetime, frequency: str, after: datetime
) -> datetime | None:
    """Return the next occurrence, or None for a completed one-off schedule.

    Missed periods are skipped, rather than replayed. Calendar dates clamp to
    the end of shorter months, always using the original day as their anchor.
    Legacy naive timestamps are UTC, as in the existing scheduler.
    """
    start = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start
    after = after.replace(tzinfo=timezone.utc) if after.tzinfo is None else after
    start, after = start.astimezone(timezone.utc), after.astimezone(timezone.utc)
    if frequency not in (*_INTERVALS, "monthly", "yearly", "once"):
        raise ValueError(f"Unsupported allowance frequency: {frequency}")
    if after < start:
        return start
    if frequency == "once":
        return None
    if frequency in _INTERVALS:
        interval = _INTERVALS[frequency]
        return start + ((after - start) // interval + 1) * interval

    step = 1 if frequency == "monthly" else 12
    elapsed_months = (after.year - start.year) * 12 + after.month - start.month
    months = elapsed_months // step * step
    year, month = divmod(start.year * 12 + start.month - 1 + months, 12)
    candidate = start.replace(
        year=year,
        month=month + 1,
        day=min(start.day, monthrange(year, month + 1)[1]),
    )
    if candidate <= after:
        year, month = divmod(start.year * 12 + start.month - 1 + months + step, 12)
        candidate = start.replace(
            year=year,
            month=month + 1,
            day=min(start.day, monthrange(year, month + 1)[1]),
        )
    return candidate
