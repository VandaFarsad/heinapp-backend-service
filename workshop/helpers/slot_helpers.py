"""Helper functions for workshop slot management."""

from datetime import timedelta
from typing import Any

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from users.models import User
from workshop.models import WorkshopSlot


def generate_available_slots(user: User | AnonymousUser) -> list[dict[str, Any]]:
    """Generate available workshop slots for the next 4 Saturdays.

    Args:
        user: The current user requesting the slots.

    Returns:
        List of slot dictionaries with id, date, time, availability, and booking status.
    """
    # Find the next Saturday
    today = timezone.now().date()
    days_until_saturday = (5 - today.weekday()) % 7
    next_saturday = today + timedelta(days=days_until_saturday)

    slots = []
    time_choices = [choice[0] for choice in WorkshopSlot.SLOT_CHOICES]

    # Generate slots for the next 4 Saturdays
    for week in range(4):
        workshop_date = next_saturday + timedelta(weeks=week)

        # Fetch existing bookings for this date
        existing_bookings = WorkshopSlot.objects.filter(date=workshop_date)
        booked_times = {booking.time_slot: booking for booking in existing_bookings}

        for time_slot in time_choices:
            slot_id = f"{workshop_date}-{time_slot}"
            is_booked = time_slot in booked_times
            booking = booked_times.get(time_slot)

            slot_data = {
                "id": slot_id,
                "date": workshop_date.isoformat(),
                "time": f"{time_slot} - {int(time_slot[:2]) + 1:02d}:00",
                "isAvailable": not is_booked,
                "isBooked": is_booked,
            }

            if is_booked and booking:
                slot_data["bookedByCurrentUser"] = booking.user == user

            slots.append(slot_data)

    return slots
