import datetime

import pytest
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User
from workshop.models import WorkshopSlot

AVAILABLE_URL = "/api/v1/workshop/slots/available-slots/"
BOOK_URL = "/api/v1/workshop/slots/book-slot/"
CANCEL_URL = "/api/v1/workshop/slots/cancel-slot/"

# The frozen date (2026-02-23) is a Monday → next Saturday = 2026-02-28
NEXT_SATURDAY = "2026-02-28"
FROZEN_DATE = "2026-02-23"


# ── available_slots ────────────────────────────────────────────


@freeze_time(FROZEN_DATE)
@pytest.mark.django_db
def test_available_slots_returns_4_weeks(auth_client: APIClient) -> None:
    """Should return 12 slots (3 time slots × 4 Saturdays)."""
    response = auth_client.get(AVAILABLE_URL)

    assert response.status_code == status.HTTP_200_OK
    slots = response.json()["slots"]
    assert len(slots) == 12


@freeze_time(FROZEN_DATE)
@pytest.mark.django_db
def test_available_slots_all_free_initially(auth_client: APIClient) -> None:
    """Without bookings all slots should be available."""
    response = auth_client.get(AVAILABLE_URL)

    slots = response.json()["slots"]
    assert all(s["isAvailable"] for s in slots)
    assert all(not s["isBooked"] for s in slots)


@freeze_time(FROZEN_DATE)
@pytest.mark.django_db
def test_available_slots_shows_booked(auth_client: APIClient, user: User) -> None:
    """A booked slot should appear as isBooked=True, isAvailable=False."""
    WorkshopSlot.objects.create(date=datetime.date(2026, 2, 28), time_slot="10:00", user=user)

    response = auth_client.get(AVAILABLE_URL)

    slots = response.json()["slots"]
    booked = [s for s in slots if s["id"] == f"{NEXT_SATURDAY}-10:00"]
    assert len(booked) == 1
    assert booked[0]["isBooked"] is True
    assert booked[0]["isAvailable"] is False
    assert booked[0]["bookedByCurrentUser"] is True


@freeze_time(FROZEN_DATE)
@pytest.mark.django_db
def test_available_slots_other_user_booking(auth_client: APIClient) -> None:
    """Booking by another user: isBooked=True, bookedByCurrentUser=False."""
    other = User.objects.create_user(email="other@example.com", password="pass123")
    WorkshopSlot.objects.create(date=datetime.date(2026, 2, 28), time_slot="10:00", user=other)

    response = auth_client.get(AVAILABLE_URL)

    slot = next(s for s in response.json()["slots"] if s["id"] == f"{NEXT_SATURDAY}-10:00")
    assert slot["isBooked"] is True
    assert slot["bookedByCurrentUser"] is False


@freeze_time(FROZEN_DATE)
@pytest.mark.django_db
def test_available_slots_correct_dates(auth_client: APIClient) -> None:
    """Slots should be on the next 4 Saturdays."""
    response = auth_client.get(AVAILABLE_URL)

    dates = sorted(set(s["date"] for s in response.json()["slots"]))
    assert dates == ["2026-02-28", "2026-03-07", "2026-03-14", "2026-03-21"]


@pytest.mark.django_db
def test_available_slots_unauthenticated(api_client: APIClient) -> None:
    """Unauthenticated request should be rejected."""
    response = api_client.get(AVAILABLE_URL)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ── book_slot ──────────────────────────────────────────────────


@pytest.mark.django_db
def test_book_slot_success(auth_client: APIClient) -> None:
    """Booking a valid Saturday slot should succeed."""
    response = auth_client.post(BOOK_URL, {"slotId": f"{NEXT_SATURDAY}-10:00"}, format="json")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["booking"]["date"] == NEXT_SATURDAY
    assert data["booking"]["time_slot"] == "10:00"
    assert WorkshopSlot.objects.count() == 1


@pytest.mark.django_db
def test_book_slot_persists_user(auth_client: APIClient, user: User) -> None:
    """The booking should be linked to the authenticated user."""
    auth_client.post(BOOK_URL, {"slotId": f"{NEXT_SATURDAY}-10:00"}, format="json")

    booking = WorkshopSlot.objects.first()
    assert booking is not None
    assert booking.user == user


@pytest.mark.django_db
def test_book_slot_duplicate_rejected(auth_client: APIClient) -> None:
    """Booking the same slot twice should fail (UniqueConstraint)."""
    auth_client.post(BOOK_URL, {"slotId": f"{NEXT_SATURDAY}-10:00"}, format="json")
    response = auth_client.post(BOOK_URL, {"slotId": f"{NEXT_SATURDAY}-10:00"}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_book_slot_second_slot_same_day_rejected(auth_client: APIClient) -> None:
    """One user can only book one slot per day."""
    auth_client.post(BOOK_URL, {"slotId": f"{NEXT_SATURDAY}-10:00"}, format="json")
    response = auth_client.post(BOOK_URL, {"slotId": f"{NEXT_SATURDAY}-11:00"}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in response.json()


@pytest.mark.django_db
def test_book_slot_not_saturday(auth_client: APIClient) -> None:
    """Booking on a non-Saturday should fail."""
    # 2026-03-02 is a Monday
    response = auth_client.post(BOOK_URL, {"slotId": "2026-03-02-10:00"}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in response.json()


@pytest.mark.django_db
def test_book_slot_invalid_format(auth_client: APIClient) -> None:
    """Invalid slotId format should return 400."""
    response = auth_client.post(BOOK_URL, {"slotId": "ungültig"}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_book_slot_invalid_time(auth_client: APIClient) -> None:
    """A time slot not in SLOT_CHOICES should be rejected."""
    response = auth_client.post(BOOK_URL, {"slotId": f"{NEXT_SATURDAY}-14:00"}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_book_slot_missing_field(auth_client: APIClient) -> None:
    """Missing slotId field should return 400."""
    response = auth_client.post(BOOK_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_book_slot_unauthenticated(api_client: APIClient) -> None:
    """Unauthenticated request should be rejected."""
    response = api_client.post(BOOK_URL, {"slotId": f"{NEXT_SATURDAY}-10:00"}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


# ── cancel_slot ────────────────────────────────────────────────


@pytest.mark.django_db
def test_cancel_slot_success(auth_client: APIClient) -> None:
    """Cancelling an existing booking should succeed."""
    auth_client.post(BOOK_URL, {"slotId": f"{NEXT_SATURDAY}-10:00"}, format="json")

    response = auth_client.delete(f"{CANCEL_URL}?slotId={NEXT_SATURDAY}-10:00")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True
    assert WorkshopSlot.objects.count() == 0


@pytest.mark.django_db
def test_cancel_slot_not_found(auth_client: APIClient) -> None:
    """Cancelling a non-existent booking should return 404."""
    response = auth_client.delete(f"{CANCEL_URL}?slotId={NEXT_SATURDAY}-10:00")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "error" in response.json()


@pytest.mark.django_db
def test_cancel_slot_other_users_booking(auth_client: APIClient) -> None:
    """A user cannot cancel another user's booking."""
    other = User.objects.create_user(email="other@example.com", password="pass123")
    WorkshopSlot.objects.create(date=datetime.date(2026, 2, 28), time_slot="10:00", user=other)

    response = auth_client.delete(f"{CANCEL_URL}?slotId={NEXT_SATURDAY}-10:00")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert WorkshopSlot.objects.count() == 1  # Not deleted


@pytest.mark.django_db
def test_cancel_slot_invalid_format(auth_client: APIClient) -> None:
    """Invalid slotId format should return 400."""
    response = auth_client.delete(f"{CANCEL_URL}?slotId=ungültig")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_cancel_slot_missing_param(auth_client: APIClient) -> None:
    """Missing slotId query param should return 400."""
    response = auth_client.delete(CANCEL_URL)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_cancel_slot_unauthenticated(api_client: APIClient) -> None:
    """Unauthenticated request should be rejected."""
    response = api_client.delete(f"{CANCEL_URL}?slotId={NEXT_SATURDAY}-10:00")

    assert response.status_code == status.HTTP_403_FORBIDDEN
