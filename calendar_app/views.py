import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone as django_tz
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response

from .helpers import (
    cleanup_zombie_events,
    get_cached_events,
    mark_range_synced,
    parse_date_params,
    perform_bulk_operations,
    process_caldav_sync,
    serialize_event_for_response,
    should_sync_with_caldav,
)
from .models import CalendarEvent
from .serializers import EventInputSerializer
from .services import CalDAVService

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def get_events(request: Request) -> Response:
    """Get calendar events with robust database caching and zombie cleanup.

    Uses a function-based view because the calendar CRUD operates against an
    external CalDAV service rather than standard Django ORM models, making
    ModelViewSet's built-in queryset handling unsuitable.

    Returns:
        Response with status 200 and JSON body:

        >>> {
        ...     "success": true,
        ...     "events": [{...}],
        ...     "synced": false
        ... }

        Note: `synced` indicates whether a CalDAV sync was performed or served from cache.
    """
    # Parse and validate URL query parameters
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    force_sync = request.GET.get("force_sync", "false").lower() == "true"
    start_date, end_date = parse_date_params(start_date_str, end_date_str)

    # Fetch events once; reuse for sync check and sync logic
    cached_events = list(get_cached_events(start_date, end_date))
    should_sync = should_sync_with_caldav(
        force_sync, cached_events, cache_minutes=15, start_date=start_date, end_date=end_date
    )

    if should_sync:
        try:
            with CalDAVService() as caldav_service:
                caldav_events = caldav_service.get_events(start_date, end_date)

            existing_events = {e.uid: e for e in cached_events}
            active_event_uids, events_to_create, events_to_update = process_caldav_sync(caldav_events, existing_events)

            # Use a transaction to ensure atomicity of database operations during sync
            with transaction.atomic():
                perform_bulk_operations(events_to_create, events_to_update)
                cleanup_zombie_events(existing_events, active_event_uids)

            mark_range_synced(start_date, end_date, cache_minutes=15)

            # All active events are already in memory after sync
            response_events = sorted(events_to_create + events_to_update, key=lambda e: e.start_date)
        except Exception:
            logger.warning("CalDAV sync failed, serving from cache", exc_info=True)
            response_events = cached_events
    else:
        # No sync needed, reuse cached data
        response_events = cached_events

    events = [serialize_event_for_response(event) for event in response_events]

    return Response({"success": True, "events": events, "synced": should_sync}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def create_event(request: Request) -> Response:
    """Create a new calendar event on the CalDAV server and cache it locally.

    Returns:
        Response with status 201 on success:

        >>> {"success": true, "event": {...}}

        Response with status 400 on validation error:

        >>> {"success": false, "errors": {...}}
    """
    serializer = EventInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    with CalDAVService() as caldav_service:
        event = caldav_service.create_event(serializer.validated_data)

        # Save to database cache
        CalendarEvent.objects.update_or_create(
            uid=event.uid,
            recurrence_id=None,  # New events don't have recurrence_id
            defaults={**event.to_model_fields(), "last_synced_at": django_tz.now()},
        )

        return Response({"success": True, "event": event.to_response_dict()}, status=status.HTTP_201_CREATED)


@api_view(["PUT"])
@permission_classes([IsAdminUser])
def update_event(request: Request, uid: str) -> Response:
    """Update an existing calendar event on the CalDAV server and refresh the local cache.

    Returns:
        Response with status 200 on success:

        >>> {"success": true, "event": {...}}

        Response with status 400 on validation error:

        >>> {"success": false, "errors": {...}}
    """
    # Build exclude list for the double-booking validator so that related
    # events in the same room don't trigger false conflicts.
    event_to_update = CalendarEvent.objects.filter(uid=uid).first()
    exclude_uids: list[str] = []
    if event_to_update:
        location = request.data.get("location", "") or event_to_update.location
        if location:
            base_qs = CalendarEvent.objects.filter(location=location).exclude(uid=uid)

            if event_to_update.rrule:
                # Updating a series: exclude standalone/exception events that
                # sit in the same room (they were derived from this series).
                exclude_uids = list(base_qs.filter(Q(rrule__isnull=True) | Q(rrule="")).values_list("uid", flat=True))
            else:
                # Updating an exception/standalone event: exclude recurring
                # master events whose DB-stored dates (first occurrence only)
                # may coincidentally overlap.
                exclude_uids = list(base_qs.exclude(Q(rrule__isnull=True) | Q(rrule="")).values_list("uid", flat=True))

    serializer = EventInputSerializer(data=request.data, context={"uid": uid, "exclude_uids": exclude_uids})
    if not serializer.is_valid():
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    with CalDAVService() as caldav_service:
        event = caldav_service.update_event(uid, serializer.validated_data)

        # Update database cache
        CalendarEvent.objects.filter(uid=uid).update(**event.to_model_fields(), last_synced_at=django_tz.now())

        return Response({"success": True, "event": event.to_response_dict()}, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def delete_event(request: Request, uid: str) -> Response:
    """Delete a calendar event from the CalDAV server and remove it from the local cache.

    Returns:
        Response with status 200 on success:

        >>> {"success": true, "message": "Event deleted successfully"}

        Response with status 404 when event not found:

        >>> {"success": false, "error": "Event not found"}
    """
    with CalDAVService() as caldav_service:
        success = caldav_service.delete_event(uid)

        if success:
            # Delete from database cache
            CalendarEvent.objects.filter(uid=uid).delete()
            return Response({"success": True, "message": "Event deleted successfully"}, status=status.HTTP_200_OK)
        else:
            return Response({"success": False, "error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def create_exception(request: Request, uid: str) -> Response:
    """Create an exception for a single occurrence of a recurring event.

    Adds EXDATE to the master event to suppress the original occurrence,
    then creates a standalone event with the new data.

    Returns:
        Response with status 201 on success:

        >>> {"success": true, "master": {...}, "exception": {...}}

        Response with status 400 on validation error:

        >>> {"success": false, "errors": {...}}
    """
    occurrence_start = request.data.get("occurrence_start")
    if not occurrence_start:
        return Response(
            {"success": False, "error": "occurrence_start is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Only recurring events can have exceptions
    master_event = CalendarEvent.objects.filter(uid=uid).first()
    if not master_event or not master_event.rrule:
        return Response(
            {"success": False, "error": "Event is not a recurring event"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    event_data = {k: v for k, v in request.data.items() if k != "occurrence_start"}

    # Find existing exception events that overlap with the occurrence being replaced,
    # so the double-booking check doesn't reject them as conflicts.
    exclude_uids: list[str] = []
    if event_data.get("location"):
        duration = master_event.end_date - master_event.start_date
        occ_start = django_tz.datetime.fromisoformat(occurrence_start.replace("Z", "+00:00"))
        occ_end = occ_start + duration
        existing_exceptions = (
            CalendarEvent.objects.filter(
                location=event_data["location"],
                start_date__lt=occ_end,
                end_date__gt=occ_start,
            )
            .exclude(uid=uid)
            .values_list("uid", flat=True)
        )
        exclude_uids = list(existing_exceptions)

    serializer = EventInputSerializer(data=event_data, context={"uid": uid, "exclude_uids": exclude_uids})
    if not serializer.is_valid():
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    with CalDAVService() as caldav_service:
        updated_master, exception_event = caldav_service.create_exception(
            uid, occurrence_start, serializer.validated_data
        )

        # Update master DB cache with new EXDATE
        CalendarEvent.objects.filter(uid=uid).update(exdate=updated_master.exdate, last_synced_at=django_tz.now())

        # Create exception event DB entry
        CalendarEvent.objects.update_or_create(
            uid=exception_event.uid,
            recurrence_id=None,
            defaults={**exception_event.to_model_fields(), "last_synced_at": django_tz.now()},
        )

        return Response(
            {
                "success": True,
                "master": updated_master.to_response_dict(),
                "exception": exception_event.to_response_dict(),
            },
            status=status.HTTP_201_CREATED,
        )


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def delete_occurrence(request: Request, uid: str) -> Response:
    """Remove a single occurrence from a recurring event by adding EXDATE.

    Returns:
        Response with status 200 on success:

        >>> {"success": true, "master": {...}}

        Response with status 400 when occurrence_start is missing:

        >>> {"success": false, "error": "occurrence_start is required"}
    """
    occurrence_start = request.GET.get("occurrence_start")
    if not occurrence_start:
        return Response(
            {"success": False, "error": "occurrence_start is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with CalDAVService() as caldav_service:
        updated_master = caldav_service.delete_occurrence(uid, occurrence_start)

        # Update master DB cache with new EXDATE
        CalendarEvent.objects.filter(uid=uid).update(exdate=updated_master.exdate, last_synced_at=django_tz.now())

        return Response(
            {"success": True, "master": updated_master.to_response_dict()},
            status=status.HTTP_200_OK,
        )
