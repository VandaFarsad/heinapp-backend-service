from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from django.utils import timezone as django_tz
from rest_framework import status
from rest_framework.test import APIClient

from calendar_app.models import CalendarEvent
from calendar_app.services import CalDAVEvent
from conftest import staff_client

EVENTS_URL = "/api/v1/calendar/events/"
CREATE_URL = "/api/v1/calendar/events/create/"


def _valid_event_payload(**overrides: object) -> dict[str, object]:
    """Return a valid event payload, with optional overrides."""
    defaults: dict[str, object] = {
        "title": "Team-Meeting",
        "description": "Wöchentliches Standup",
        "start_date": "2026-03-02T10:00:00Z",
        "end_date": "2026-03-02T11:00:00Z",
        "location": "Büro",
        "all_day": False,
    }
    defaults.update(overrides)
    return defaults


def _make_caldav_event(**overrides: object) -> CalDAVEvent:
    """Create a CalDAVEvent with sensible defaults."""
    defaults = {
        "uid": "test-uid-123",
        "title": "Team-Meeting",
        "description": "Wöchentliches Standup",
        "start_date": datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
        "end_date": datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
        "location": "Büro",
        "url": "",
        "all_day": False,
    }
    defaults.update(overrides)
    return CalDAVEvent(**defaults)  # type: ignore[arg-type]


# ── get_events (cached, no sync) ──────────────────────────────


@pytest.mark.django_db
def test_get_events_as_regular_user(mock_caldav: MagicMock, auth_client: APIClient) -> None:
    """Regular users should be forbidden from accessing events."""
    response = auth_client.get(EVENTS_URL)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_get_events_empty(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """No events → empty list."""
    response = staff_client.get(EVENTS_URL)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["events"] == []


@pytest.mark.django_db
def test_get_events_returns_cached(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Cached events should be returned from database."""
    CalendarEvent.objects.create(
        uid="cached-1",
        title="Cached Event",
        start_date=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
        last_synced_at=django_tz.now(),
    )

    response = staff_client.get(f"{EVENTS_URL}?start_date=2026-03-01&end_date=2026-03-31")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["title"] == "Cached Event"


@pytest.mark.django_db
def test_get_events_with_date_range(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Events outside the requested range should not be returned."""
    now = django_tz.now()
    CalendarEvent.objects.create(
        uid="in-range",
        title="In Range",
        start_date=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 15, 11, 0, tzinfo=timezone.utc),
        last_synced_at=now,
    )
    CalendarEvent.objects.create(
        uid="out-of-range",
        title="Out of Range",
        start_date=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc),
        last_synced_at=now,
    )

    response = staff_client.get(f"{EVENTS_URL}?start_date=2026-03-01&end_date=2026-03-31")

    events = response.json()["events"]
    assert len(events) == 1
    assert events[0]["title"] == "In Range"


# ── create_event ───────────────────────────────────────────────


@pytest.mark.django_db
def test_create_event_success(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Valid payload should create event and return 201."""
    mock_caldav.create_event.return_value = _make_caldav_event()

    response = staff_client.post(CREATE_URL, _valid_event_payload(), format="json")

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True
    assert data["event"]["title"] == "Team-Meeting"
    assert CalendarEvent.objects.filter(uid="test-uid-123").exists()


@pytest.mark.django_db
def test_create_event_caches_locally(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Created event should be saved to local database cache."""
    mock_caldav.create_event.return_value = _make_caldav_event(uid="new-uid")

    staff_client.post(CREATE_URL, _valid_event_payload(), format="json")

    cached = CalendarEvent.objects.get(uid="new-uid")
    assert cached.title == "Team-Meeting"
    assert cached.location == "Büro"


@pytest.mark.django_db
def test_create_event_missing_title(staff_client: APIClient) -> None:
    """Missing title should return 400."""
    payload = _valid_event_payload()
    del payload["title"]

    response = staff_client.post(CREATE_URL, payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "title" in response.json()["errors"]


@pytest.mark.django_db
def test_create_event_end_before_start(staff_client: APIClient) -> None:
    """end_date before start_date should return 400."""
    response = staff_client.post(
        CREATE_URL,
        _valid_event_payload(
            start_date="2026-03-02T12:00:00Z",
            end_date="2026-03-02T11:00:00Z",
        ),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_event_invalid_url(staff_client: APIClient) -> None:
    """Invalid URL should return 400."""
    response = staff_client.post(
        CREATE_URL,
        _valid_event_payload(url="keine-url"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "url" in response.json()["errors"]


@pytest.mark.django_db
def test_create_event_empty_body(staff_client: APIClient) -> None:
    """Empty body should return 400."""
    response = staff_client.post(CREATE_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_event_all_day(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """All-day event should be created successfully."""
    mock_caldav.create_event.return_value = _make_caldav_event(all_day=True)

    response = staff_client.post(
        CREATE_URL,
        _valid_event_payload(all_day=True),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["event"]["all_day"] is True


@pytest.mark.django_db
def test_create_event_optional_fields_default_empty(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Optional fields (description, location, url) should default to empty strings."""
    mock_caldav.create_event.return_value = _make_caldav_event(description="", location="", url="")

    payload = {
        "title": "Minimal Event",
        "start_date": "2026-03-10T09:00:00Z",
        "end_date": "2026-03-10T09:30:00Z",
    }
    response = staff_client.post(CREATE_URL, payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED


# ── update_event ───────────────────────────────────────────────


@pytest.mark.django_db
def test_update_event_success(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Updating an existing event should return 200 and update the cache."""
    CalendarEvent.objects.create(
        uid="update-me",
        title="Old Title",
        start_date=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
    )

    mock_caldav.update_event.return_value = _make_caldav_event(uid="update-me", title="New Title")

    response = staff_client.put(
        f"{EVENTS_URL}update-me/",
        _valid_event_payload(title="New Title"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["event"]["title"] == "New Title"

    cached = CalendarEvent.objects.get(uid="update-me")
    assert cached.title == "New Title"


@pytest.mark.django_db
def test_update_event_invalid_data(staff_client: APIClient) -> None:
    """Invalid payload should return 400."""
    response = staff_client.put(
        f"{EVENTS_URL}some-uid/",
        {"title": "No times"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ── delete_event ───────────────────────────────────────────────


@pytest.mark.django_db
def test_delete_event_success(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Deleting an existing event should return 200 and remove cache."""
    CalendarEvent.objects.create(
        uid="delete-me",
        title="To Delete",
        start_date=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
    )

    mock_caldav.delete_event.return_value = True

    response = staff_client.delete(f"{EVENTS_URL}delete-me/delete/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True
    assert not CalendarEvent.objects.filter(uid="delete-me").exists()


@pytest.mark.django_db
def test_delete_event_not_found(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Deleting a non-existent event should return 404."""
    mock_caldav.delete_event.return_value = False

    response = staff_client.delete(f"{EVENTS_URL}nonexistent/delete/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["success"] is False


# ── create_exception ───────────────────────────────────────────


@pytest.mark.django_db
def test_create_exception_success(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Creating an exception for a recurring event should return 201."""
    CalendarEvent.objects.create(
        uid="recurring-event",
        title="Weekly Meeting",
        start_date=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
        rrule="FREQ=WEEKLY;BYDAY=MO",
    )

    master = _make_caldav_event(
        uid="recurring-event",
        rrule="FREQ=WEEKLY;BYDAY=MO",
        exdate="20260309T100000Z",
    )
    exception = _make_caldav_event(
        uid="recurring-event-exception-20260309T100000Z",
        title="Rescheduled Meeting",
        start_date=datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 9, 15, 0, tzinfo=timezone.utc),
    )
    mock_caldav.create_exception.return_value = (master, exception)

    response = staff_client.post(
        f"{EVENTS_URL}recurring-event/exception/",
        {
            "occurrence_start": "2026-03-09T10:00:00Z",
            "title": "Rescheduled Meeting",
            "start_date": "2026-03-09T14:00:00Z",
            "end_date": "2026-03-09T15:00:00Z",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True
    assert data["master"]["exdate"] == "20260309T100000Z"
    assert data["exception"]["title"] == "Rescheduled Meeting"
    assert CalendarEvent.objects.filter(uid="recurring-event-exception-20260309T100000Z").exists()


@pytest.mark.django_db
def test_create_exception_missing_occurrence_start(staff_client: APIClient) -> None:
    """Creating an exception without occurrence_start should return 400."""
    response = staff_client.post(
        f"{EVENTS_URL}some-uid/exception/",
        {
            "title": "Modified Event",
            "start_date": "2026-03-10T14:00:00Z",
            "end_date": "2026-03-10T15:00:00Z",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "occurrence_start is required"


@pytest.mark.django_db
def test_create_exception_non_recurring_event(staff_client: APIClient) -> None:
    """Creating an exception for a non-recurring event should return 400."""
    CalendarEvent.objects.create(
        uid="one-time-event",
        title="One Time Meeting",
        start_date=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
        rrule="",
    )

    response = staff_client.post(
        f"{EVENTS_URL}one-time-event/exception/",
        {
            "occurrence_start": "2026-03-02T10:00:00Z",
            "title": "Modified",
            "start_date": "2026-03-02T14:00:00Z",
            "end_date": "2026-03-02T15:00:00Z",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "Event is not a recurring event"


@pytest.mark.django_db
def test_create_exception_event_not_found(staff_client: APIClient) -> None:
    """Creating an exception for a non-existent event should return 400."""
    response = staff_client.post(
        f"{EVENTS_URL}nonexistent/exception/",
        {
            "occurrence_start": "2026-03-02T10:00:00Z",
            "title": "Modified",
            "start_date": "2026-03-02T14:00:00Z",
            "end_date": "2026-03-02T15:00:00Z",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "Event is not a recurring event"


@pytest.mark.django_db
def test_create_exception_invalid_event_data(staff_client: APIClient) -> None:
    """Creating an exception with invalid event data should return 400."""
    CalendarEvent.objects.create(
        uid="recurring-event",
        title="Weekly Meeting",
        start_date=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
        rrule="FREQ=WEEKLY;BYDAY=MO",
    )

    response = staff_client.post(
        f"{EVENTS_URL}recurring-event/exception/",
        {
            "occurrence_start": "2026-03-09T10:00:00Z",
            "title": "Modified",
            "start_date": "2026-03-09T14:00:00Z",
            # Missing end_date
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_exception_updates_master_cache(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Master event's EXDATE should be updated in database cache."""
    CalendarEvent.objects.create(
        uid="recurring-event",
        title="Weekly Meeting",
        start_date=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
        rrule="FREQ=WEEKLY;BYDAY=MO",
        exdate="",
    )

    master = _make_caldav_event(
        uid="recurring-event",
        rrule="FREQ=WEEKLY;BYDAY=MO",
        exdate="20260309T100000Z",
    )
    exception = _make_caldav_event(
        uid="recurring-event-exception-20260309T100000Z",
        title="Modified",
    )
    mock_caldav.create_exception.return_value = (master, exception)

    staff_client.post(
        f"{EVENTS_URL}recurring-event/exception/",
        {
            "occurrence_start": "2026-03-09T10:00:00Z",
            "title": "Modified",
            "start_date": "2026-03-09T14:00:00Z",
            "end_date": "2026-03-09T15:00:00Z",
        },
        format="json",
    )

    cached_master = CalendarEvent.objects.get(uid="recurring-event")
    assert cached_master.exdate == "20260309T100000Z"


# ── delete_occurrence ──────────────────────────────────────────


@pytest.mark.django_db
def test_delete_occurrence_success(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Deleting a single occurrence should return 200 and update EXDATE."""
    CalendarEvent.objects.create(
        uid="recurring-event",
        title="Weekly Meeting",
        start_date=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
        rrule="FREQ=WEEKLY;BYDAY=MO",
        exdate="",
    )

    updated_master = _make_caldav_event(
        uid="recurring-event",
        rrule="FREQ=WEEKLY;BYDAY=MO",
        exdate="20260316T100000Z",
    )
    mock_caldav.delete_occurrence.return_value = updated_master

    response = staff_client.delete(f"{EVENTS_URL}recurring-event/occurrence/?occurrence_start=2026-03-16T10:00:00Z")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["master"]["exdate"] == "20260316T100000Z"

    cached = CalendarEvent.objects.get(uid="recurring-event")
    assert cached.exdate == "20260316T100000Z"


@pytest.mark.django_db
def test_delete_occurrence_missing_occurrence_start(staff_client: APIClient) -> None:
    """Deleting an occurrence without occurrence_start should return 400."""
    response = staff_client.delete(f"{EVENTS_URL}some-uid/occurrence/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "occurrence_start is required"


@pytest.mark.django_db
def test_delete_occurrence_updates_cache(mock_caldav: MagicMock, staff_client: APIClient) -> None:
    """Deleting an occurrence should update the database cache."""
    CalendarEvent.objects.create(
        uid="recurring-event",
        title="Weekly Meeting",
        start_date=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 3, 2, 11, 0, tzinfo=timezone.utc),
        rrule="FREQ=WEEKLY;BYDAY=MO",
        exdate="20260309T100000Z",
    )

    updated_master = _make_caldav_event(
        uid="recurring-event",
        rrule="FREQ=WEEKLY;BYDAY=MO",
        exdate="20260309T100000Z,20260323T100000Z",
    )
    mock_caldav.delete_occurrence.return_value = updated_master

    staff_client.delete(f"{EVENTS_URL}recurring-event/occurrence/?occurrence_start=2026-03-23T10:00:00Z")

    cached = CalendarEvent.objects.get(uid="recurring-event")
    assert cached.exdate == "20260309T100000Z,20260323T100000Z"
