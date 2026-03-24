"""Date and time utility functions."""
from datetime import date, datetime, timedelta
from typing import Optional

import pytz
from constants import DATE_FORMAT_DISPLAY, DATETIME_FORMAT_DISPLAY


def is_weekend(check_date: date) -> bool:
    """Return True if date falls on a weekend."""
    return check_date.weekday() >= 5  # Saturday = 5, Sunday = 6


def add_business_days(start_date: date, days: int) -> date:
    """Add business days to a date, skipping weekends."""
    current = start_date
    days_added = 0

    while days_added < days:
        current += timedelta(days=1)
        if is_business_day(current):
            days_added += 1

    return current


def format_date_display(
    dt: Optional[date | datetime],
    include_time: bool = False
) -> str:
    """Format date for display; returns empty string if None."""
    if dt is None:
        return ""

    if include_time:
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())
        return dt.strftime(DATETIME_FORMAT_DISPLAY)
    else:
        if isinstance(dt, datetime):
            dt = dt.date()
        return dt.strftime(DATE_FORMAT_DISPLAY)


def get_current_utc() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(pytz.UTC)


def convert_to_timezone(
    dt: datetime,
    timezone_str: str = "America/Los_Angeles"
) -> datetime:
    """Convert datetime to specified timezone (assumes UTC if naive)."""
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)

    target_tz = pytz.timezone(timezone_str)
    return dt.astimezone(target_tz)


def days_between(start: date, end: date) -> int:
    """Return number of days between two dates (negative if end < start)."""
    return (end - start).days


def hours_until(target_datetime: datetime) -> float:
    """Return hours until target datetime (negative if in the past)."""
    now = get_current_utc()

    if target_datetime.tzinfo is None:
        target_datetime = pytz.UTC.localize(target_datetime)

    delta = target_datetime - now
    return delta.total_seconds() / 3600


def is_past_due(due_date: date, grace_hours: int = 0) -> bool:
    """Return True if due date has passed, accounting for optional grace period."""
    now = get_current_utc().date()

    if grace_hours > 0:
        due_datetime = datetime.combine(due_date, datetime.max.time())
        due_datetime = pytz.UTC.localize(due_datetime)
        due_datetime += timedelta(hours=grace_hours)
        return get_current_utc() > due_datetime

    return now > due_date


def get_date_range_days(start: date, end: date) -> list[date]:
    """Return list of all dates from start to end (inclusive)."""
    if end < start:
        return []

    dates = []
    current = start

    while current <= end:
        dates.append(current)
        current += timedelta(days=1)

    return dates
