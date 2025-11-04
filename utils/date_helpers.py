"""Date and time utility functions."""
from datetime import date, datetime, timedelta
from typing import Optional

import pytz
from constants import DATE_FORMAT_DISPLAY, DATETIME_FORMAT_DISPLAY


def calculate_business_days(
    start_date: date,
    end_date: date,
    exclude_weekends: bool = True
) -> int:
    """
    Calculate number of business days between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        exclude_weekends: Whether to exclude weekends
        
    Returns:
        Number of business days
    """
    if end_date < start_date:
        return 0
    
    if not exclude_weekends:
        return (end_date - start_date).days
    
    # Count days excluding weekends
    days = 0
    current = start_date
    
    while current <= end_date:
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            days += 1
        current += timedelta(days=1)
    
    return days


def is_weekend(check_date: date) -> bool:
    """
    Check if date falls on a weekend.
    
    Args:
        check_date: Date to check
        
    Returns:
        True if Saturday or Sunday
    """
    return check_date.weekday() >= 5  # Saturday = 5, Sunday = 6


def is_business_day(check_date: date) -> bool:
    """
    Check if date is a business day (Monday-Friday).
    
    Args:
        check_date: Date to check
        
    Returns:
        True if Monday through Friday
    """
    return not is_weekend(check_date)


def add_business_days(start_date: date, days: int) -> date:
    """
    Add business days to a date, skipping weekends.
    
    Args:
        start_date: Starting date
        days: Number of business days to add
        
    Returns:
        New date after adding business days
    """
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
    """
    Format date for display to users.
    
    Args:
        dt: Date or datetime to format
        include_time: Whether to include time
        
    Returns:
        Formatted date string, or empty string if None
    """
    if dt is None:
        return ""
    
    if include_time:
        if isinstance(dt, date) and not isinstance(dt, datetime):
            # Convert date to datetime at midnight
            dt = datetime.combine(dt, datetime.min.time())
        return dt.strftime(DATETIME_FORMAT_DISPLAY)
    else:
        if isinstance(dt, datetime):
            dt = dt.date()
        return dt.strftime(DATE_FORMAT_DISPLAY)


def get_current_utc() -> datetime:
    """
    Get current UTC datetime.
    
    Returns:
        Current UTC datetime
    """
    return datetime.now(pytz.UTC)


def convert_to_timezone(
    dt: datetime,
    timezone_str: str = "America/Los_Angeles"
) -> datetime:
    """
    Convert datetime to specific timezone.
    
    Args:
        dt: Datetime to convert (assumed UTC if naive)
        timezone_str: Target timezone
        
    Returns:
        Datetime in target timezone
    """
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = pytz.UTC.localize(dt)
    
    target_tz = pytz.timezone(timezone_str)
    return dt.astimezone(target_tz)


def days_between(start: date, end: date) -> int:
    """
    Calculate days between two dates.
    
    Args:
        start: Start date
        end: End date
        
    Returns:
        Number of days (can be negative if end < start)
    """
    return (end - start).days


def hours_until(target_datetime: datetime) -> float:
    """
    Calculate hours until a target datetime.
    
    Args:
        target_datetime: Target datetime
        
    Returns:
        Hours until target (negative if in the past)
    """
    now = get_current_utc()
    
    # Ensure target is timezone-aware
    if target_datetime.tzinfo is None:
        target_datetime = pytz.UTC.localize(target_datetime)
    
    delta = target_datetime - now
    return delta.total_seconds() / 3600


def is_past_due(due_date: date, grace_hours: int = 0) -> bool:
    """
    Check if a due date has passed.
    
    Args:
        due_date: Due date to check
        grace_hours: Optional grace period in hours
        
    Returns:
        True if past due (accounting for grace period)
    """
    now = get_current_utc().date()
    
    if grace_hours > 0:
        # Add grace period
        due_datetime = datetime.combine(due_date, datetime.max.time())
        due_datetime = pytz.UTC.localize(due_datetime)
        due_datetime += timedelta(hours=grace_hours)
        return get_current_utc() > due_datetime
    
    return now > due_date


def get_date_range_days(start: date, end: date) -> list[date]:
    """
    Get list of all dates in a range.
    
    Args:
        start: Start date
        end: End date
        
    Returns:
        List of dates from start to end (inclusive)
    """
    if end < start:
        return []
    
    dates = []
    current = start
    
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    
    return dates

