"""Time utilities for Telegram scraper."""

from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo

UTC = timezone.utc
WIB = ZoneInfo("Asia/Jakarta")


def to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC, handling naive datetimes."""
    if dt.tzinfo is None:
        # Assume UTC for naive datetimes (Telethon returns UTC)
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def format_iso(dt: datetime) -> str:
    """Format datetime as ISO 8601 with Z suffix."""
    utc_dt = to_utc(dt)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_30min_windows(
    start_date: date,
    end_date: date,
) -> list[tuple[datetime, datetime]]:
    """
    Generate list of 30-minute windows between start and end dates.

    Windows are in UTC and cover the entire day (00:00 to 23:59).
    Returns list of (window_start, window_end) tuples.
    """
    windows = []

    # Start at midnight UTC of start_date
    current = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)

    while current < end:
        window_end = current + timedelta(minutes=30)
        if window_end > end:
            window_end = end
        windows.append((current, window_end))
        current = window_end

    return windows


def is_market_hours(dt: datetime, start_hour: int = 9, end_hour: int = 16) -> bool:
    """Check if datetime is within Indonesian market hours (WIB)."""
    wib_dt = dt.astimezone(WIB)
    return start_hour <= wib_dt.hour < end_hour


def chunked(iterable, size: int):
    """Split an iterable into chunks of given size."""
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
