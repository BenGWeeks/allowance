"""Calendar recurrence anchored to the original local start."""

from calendar import monthrange
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_INTERVALS = {
    "minutely": timedelta(minutes=1),
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}


def next_occurrence(
    start: datetime, frequency: str, after: datetime, timezone_name: str = "UTC"
) -> datetime | None:
    """Return the next occurrence, or None for a completed one-off schedule.

    Missed periods are skipped, rather than replayed. Calendar dates clamp to
    the end of shorter months, always using the original day as their anchor.
    Legacy naive timestamps are UTC, as in the existing scheduler.
    """
    start = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start
    after = after.replace(tzinfo=timezone.utc) if after.tzinfo is None else after
    zone = ZoneInfo(timezone_name)
    after_utc = after.astimezone(timezone.utc)
    start, after = start.astimezone(zone), after.astimezone(zone)
    if frequency not in (*_INTERVALS, "monthly", "yearly", "once"):
        raise ValueError(f"Unsupported allowance frequency: {frequency}")
    if after_utc < start.astimezone(timezone.utc):
        return start.astimezone(timezone.utc)
    if frequency == "once":
        return None
    if frequency in _INTERVALS:
        interval = _INTERVALS[frequency]
        if frequency in ("minutely", "hourly"):
            anchor = start.astimezone(timezone.utc)
            return anchor + ((after_utc - anchor) // interval + 1) * interval
        candidate = start + ((after - start) // interval) * interval
        while candidate.astimezone(timezone.utc) <= after_utc:
            candidate += interval
        return candidate.astimezone(timezone.utc)

    step = 1 if frequency == "monthly" else 12
    elapsed_months = (after.year - start.year) * 12 + after.month - start.month
    months = elapsed_months // step * step
    year, month = divmod(start.year * 12 + start.month - 1 + months, 12)
    candidate = start.replace(
        year=year,
        month=month + 1,
        day=min(start.day, monthrange(year, month + 1)[1]),
    )
    if candidate.astimezone(timezone.utc) <= after_utc:
        year, month = divmod(start.year * 12 + start.month - 1 + months + step, 12)
        candidate = start.replace(
            year=year,
            month=month + 1,
            day=min(start.day, monthrange(year, month + 1)[1]),
        )
    return candidate.astimezone(timezone.utc)
