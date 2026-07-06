"""Date and time related helper functions"""

import logging
from datetime import datetime, timedelta

from django.core.cache import cache
from django.db.models import Q, QuerySet
from django.utils import timezone as django_tz

from ..models import CalendarEvent

logger = logging.getLogger(__name__)


def get_cached_events(start_date: datetime | None, end_date: datetime | None) -> QuerySet[CalendarEvent]:
    """
    Get calendar events queryset filtered by date range. Both parameters are optional and can be used independently.

    Only returns master events (recurrence_id=None). Recurring event instances are handled by the frontend
    using the RRULE from the master event.

    Recurring master events are always included regardless of start_date filter, because their
    DB-stored start_date only represents the first occurrence — occurrences may extend far beyond it.

    Args:
        start_date: Earliest start date for events (inclusive). None means no lower bound.
        end_date: Latest end date for events (inclusive). None means no upper bound.

    Returns:
        QuerySet[CalendarEvent]: Filtered queryset of master events only. Returns all master events if both dates are None.
    """
    # Only return master events (no recurrence_id) - frontend will expand RRULEs
    query = CalendarEvent.objects.filter(recurrence_id__isnull=True)
    has_rrule = ~Q(rrule__isnull=True) & ~Q(rrule="")
    if start_date:
        # Recurring events must always be included: their start_date is the
        # first occurrence and may be long before the requested range.
        query = query.filter(Q(start_date__gte=start_date) | has_rrule)
    if end_date:
        query = query.filter(Q(end_date__lte=end_date) | has_rrule)
    return query


def parse_date_params(start_date_str: str | None, end_date_str: str | None) -> tuple[datetime | None, datetime | None]:
    """
    Parse ISO 8601 date strings from HTTP request into timezone-aware datetime objects.
    Handles Zulu time notation (Z) by converting to +00:00 offset.

    Args:
        start_date_str: ISO 8601 date string (e.g., "2025-01-01T00:00:00Z"). None/empty returns None.
        end_date_str: ISO 8601 date string (e.g., "2025-12-31T23:59:59Z"). None/empty returns None.

    Returns:
        tuple[datetime | None, datetime | None]: (start_date, end_date) as timezone-aware datetime objects.

    Raises:
        ValueError: If date strings are malformed.

    Example:
    >>> start_date_str = "2025-01-01T00:+01:00"
    >>> end_date_str = "2025-12-31T23:59:59Z"
    >>> parse_date_params(start_date_str, end_date_str)
    (datetime.datetime(2025, 1, 1, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(seconds=3600))),
     datetime.datetime(2025, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc))
    """
    start_date = None
    end_date = None

    if start_date_str:
        start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
    if end_date_str:
        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))

    return start_date, end_date


def _synced_months_key(start_date: datetime | None, end_date: datetime | None) -> list[str]:
    """Return Django cache keys for each month covered by the date range."""
    if not start_date or not end_date:
        return []
    keys = []
    current = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while current <= end_date:
        keys.append(f"caldav_synced_{current.year}_{current.month:02d}")
        # Advance to first day of next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return keys


def mark_range_synced(start_date: datetime | None, end_date: datetime | None, cache_minutes: int = 15) -> None:
    """Mark all months in the date range as synced in Django cache."""
    for key in _synced_months_key(start_date, end_date):
        cache.set(key, True, timeout=cache_minutes * 60)


def should_sync_with_caldav(
    force_sync: bool,
    cached_events: list[CalendarEvent],
    cache_minutes: int = 15,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> bool:
    """
    Determine if CalDAV sync is needed based on cache staleness.

    Uses per-month cache keys to track which date ranges have already been synced.
    This prevents recurring events (always included in queries) from masking
    un-synced date ranges where non-recurring events may exist.

    Args:
        force_sync: If True, always returns True (manual refresh).
        cached_events: Pre-fetched list of CalendarEvent instances for the target range.
        cache_minutes: Cache TTL in minutes. Default 15.
        start_date: Start of the requested date range (used for range-tracking).
        end_date: End of the requested date range (used for range-tracking).

    Returns:
        bool: True if sync needed, False if cached data is fresh.
    """
    if force_sync:
        return True

    if not cached_events:
        return True

    # Check if all months in the range have been synced recently
    month_keys = _synced_months_key(start_date, end_date)
    if month_keys and not all(cache.get(key) for key in month_keys):
        return True

    # Check if data is stale based on the oldest last_synced_at in range
    oldest_sync = min(
        (e.last_synced_at for e in cached_events if e.last_synced_at is not None),
        default=None,
    )
    if oldest_sync is None or (django_tz.now() - oldest_sync > timedelta(minutes=cache_minutes)):
        return True

    return False
