"""Event processing and serialization helper functions"""

import logging
from typing import Any

from ..models import CalendarEvent

logger = logging.getLogger(__name__)


def apply_field_updates(event_obj: CalendarEvent, new_fields: dict[str, Any]) -> None:
    """
    Apply field updates to CalendarEvent in-place (memory only, not saved). Used with bulk_update() for efficiency.

    Args:
        event_obj: CalendarEvent instance to update.
        new_fields: Dictionary of field names to new values.
    """
    for field, value in new_fields.items():
        setattr(event_obj, field, value)


def cleanup_zombie_events(existing_events: dict[str, CalendarEvent], active_event_uids: set[str]) -> None:
    """
    Delete cached events that no longer exist on CalDAV server (zombie events). Performs set difference to find
    events in database but not in CalDAV response, then bulk-deletes by ID.

    Args:
        existing_events: Dict of uid -> CalendarEvent from database (before state).
        active_event_uids: Set of UIDs from CalDAV server (after state, source of truth).

    Side Effects:
        Deletes CalendarEvent records and logs deletion count.
    """
    zombie_uids = set(existing_events.keys()) - active_event_uids
    if zombie_uids:
        zombie_ids = [existing_events[uid].id for uid in zombie_uids]
        deleted_count = CalendarEvent.objects.filter(id__in=zombie_ids).delete()[0]
        logger.info(f"Deleted {deleted_count} zombie events")


def serialize_event_for_response(event: CalendarEvent) -> dict[str, Any]:
    """
    Serialize CalendarEvent to JSON-compatible dict for API response. Converts datetimes to ISO 8601 strings.
    Since we only return master events, UID is returned directly.

    Args:
        event: CalendarEvent model instance (master event only).

    Returns:
        dict[str, Any]: API response dict with uid, title, description, start_date, end_date,
                       location, all_day, url, rrule, exdate.
    """
    return {
        "uid": event.uid,
        "recurrence_id": event.recurrence_id,  # Should always be None for master events
        "title": event.title,
        "description": event.description,
        "start_date": event.start_date.isoformat(),
        "end_date": event.end_date.isoformat(),
        "location": event.location,
        "all_day": event.all_day,
        "url": event.url,
        "rrule": event.rrule or "",
        "exdate": event.exdate or "",
    }
