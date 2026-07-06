from datetime import timedelta
from typing import Any

from django.utils import timezone
from rest_framework import serializers

# Community room constants - must match frontend definitions in types/calendar.ts
# If these values change, update the frontend definition as well.
COMMUNITY_ROOMS = {
    "GROUND_FLOOR": "Gemeinschaftsraum: Erdgeschoss",
    "ROOFTOP": "Gemeinschaftsraum: Dach",
}


class EventInputSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Input validation for calendar event create and update requests.

    Validates and parses incoming JSON data for POST and PUT endpoints.
    DRF handles type coercion (e.g. ISO 8601 strings → datetime objects)
    automatically. Cross-field validation ensures end_date > start_date.

    Additionally validates that community rooms (Erdgeschoss, Dach) are not
    double-booked for overlapping time periods.
    """

    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    location = serializers.CharField(required=False, allow_blank=True, default="")
    url = serializers.URLField(required=False, allow_blank=True, default="")
    all_day = serializers.BooleanField(default=False)
    rrule = serializers.CharField(required=False, allow_blank=True, default="")
    exdate = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate event data including time range and room availability."""
        # Import here to avoid circular dependency
        from .models import CalendarEvent

        # Basic time validation
        if data["start_date"] >= data["end_date"]:
            raise serializers.ValidationError("end_date must be after start_date")

        # Community room double-booking validation
        location = data.get("location", "").strip()

        # Only validate if location is one of the community rooms
        if location in COMMUNITY_ROOMS.values():
            # Get UID from context if updating an existing event
            current_uid = self.context.get("uid")

            # Check for overlapping events in the same room
            # Two events overlap if: start1 < end2 AND start2 < end1
            overlapping_events = CalendarEvent.objects.filter(
                location=location,
                start_date__lt=data["end_date"],
                end_date__gt=data["start_date"],
            )

            # Exclude current event and related events (e.g. existing exceptions)
            exclude_uids = [*self.context.get("exclude_uids", [])]
            if current_uid:
                exclude_uids.append(current_uid)
            if exclude_uids:
                overlapping_events = overlapping_events.exclude(uid__in=exclude_uids)

            if overlapping_events.exists():
                # Get first overlapping event for error message
                conflict = overlapping_events.first()

                # Convert to local timezone for display
                local_start = timezone.localtime(conflict.start_date)
                local_end = timezone.localtime(conflict.end_date)

                # Format dates based on whether it's an all-day event
                if conflict.all_day:
                    # For all-day events, only show the date

                    start_str = local_start.strftime("%d.%m.%Y")
                    # For all-day events, end_date is exclusive (next day at 00:00)
                    # So we subtract one day for display
                    end_date_display = local_end - timedelta(days=1)
                    end_str = end_date_display.strftime("%d.%m.%Y")

                    if start_str == end_str:
                        date_range = f"am {start_str}"
                    else:
                        date_range = f"vom {start_str} bis {end_str}"
                else:
                    # For regular events, show date and time
                    start_str = local_start.strftime("%d.%m.%Y %H:%M")
                    end_str = local_end.strftime("%d.%m.%Y %H:%M")
                    date_range = f"vom {start_str} bis {end_str}"

                raise serializers.ValidationError(
                    {"location": f"{location} ist bereits gebucht {date_range} (Event: {conflict.title})"}
                )

        return data
