"""CalDAV synchronization helper functions"""

import logging

from django.utils import timezone as django_tz

from ..models import CalendarEvent
from ..services import CalDAVEvent
from .event_helpers import apply_field_updates

logger = logging.getLogger(__name__)


def process_caldav_sync(
    caldav_events: list[CalDAVEvent], existing_events: dict[str, CalendarEvent]
) -> tuple[set[str], list[CalendarEvent], list[CalendarEvent]]:
    """
    Differential sync between CalDAV (source of truth) and database. Categorizes events into create/update/delete
    operations using UID as key (master events only). Sets last_synced_at on all synced events.

    Args:
        caldav_events: List of CalDAVEvent instances from CalDAV service (master events only).
        existing_events: Dict of uid -> CalendarEvent from database (before state).

    Returns:
        tuple: (active_event_uids, events_to_create, events_to_update)
            - active_event_uids: Set of UIDs from CalDAV for zombie cleanup
            - events_to_create: New CalendarEvent instances (unsaved, with last_synced_at set)
            - events_to_update: Existing instances with last_synced_at set (and field changes if any)

    Performance:
        O(n) in-memory processing, no database I/O.
    """
    now = django_tz.now()
    active_event_uids = set()
    events_to_create = []
    events_to_update = []

    for event in caldav_events:
        uid = event.uid
        active_event_uids.add(uid)

        event_fields = event.to_model_fields()

        if uid in existing_events:
            event_obj = existing_events[uid]
            apply_field_updates(event_obj, event_fields)

            event_obj.last_synced_at = now
            events_to_update.append(event_obj)
        else:
            events_to_create.append(
                CalendarEvent(
                    uid=uid,
                    recurrence_id=None,  # Master events only
                    last_synced_at=now,
                    **event_fields,
                )
            )

    return active_event_uids, events_to_create, events_to_update


def perform_bulk_operations(events_to_create: list[CalendarEvent], events_to_update: list[CalendarEvent]) -> None:
    """
    Execute bulk database operations with batch size 100. Uses bulk_create() with ON CONFLICT DO UPDATE
    (UPSERT) for performance and bulk_update() for existing events.

    Args:
        events_to_create: New CalendarEvent instances (unsaved, no PKs).
        events_to_update: Existing instances with modified fields (have PKs).

    Side Effects:
        Database inserts/updates and INFO logging. Updates updated_at timestamps automatically.
    """
    if events_to_create:
        # Use bulk_create with update_conflicts for UPSERT behavior (single INSERT with ON CONFLICT DO UPDATE)
        CalendarEvent.objects.bulk_create(
            events_to_create,
            batch_size=100,
            update_conflicts=True,
            update_fields=[
                "title",
                "description",
                "start_date",
                "end_date",
                "location",
                "url",
                "all_day",
                "rrule",
                "exdate",
                "last_synced_at",
            ],
            unique_fields=["uid", "recurrence_id"],
        )
        logger.info(f"Upserted {len(events_to_create)} events")

    if events_to_update:
        CalendarEvent.objects.bulk_update(
            events_to_update,
            [
                "title",
                "description",
                "start_date",
                "end_date",
                "location",
                "url",
                "all_day",
                "rrule",
                "exdate",
                "last_synced_at",
            ],
            batch_size=100,
        )
        logger.info(f"Updated {len(events_to_update)} events")
