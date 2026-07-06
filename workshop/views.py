import logging

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from workshop.helpers.slot_helpers import generate_available_slots
from workshop.models import WorkshopSlot
from workshop.serializers import SlotBookingSerializer, SlotCancelSerializer

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def available_slots(request: Request) -> Response:
    """Return available workshop slots for the next 4 Saturdays.

    Uses a function-based view for consistency with the other apps. No CRUD
    resource semantics are needed — only three standalone endpoints.

    Returns:
        Response with status 200 and JSON body:

        >>> {
        ...     "slots": [
        ...         {
        ...             "id": "2026-02-28-10:00",
        ...             "date": "2026-02-28",
        ...             "time": "10:00 - 11:00",
        ...             "isAvailable": true,
        ...             "isBooked": false
        ...         }
        ...     ]
        ... }

        Note: `bookedByCurrentUser` field is only present when `isBooked` is true.
    """
    slots = generate_available_slots(request.user)
    return Response({"slots": slots})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def book_slot(request: Request) -> Response:
    """Book a workshop slot for the current user.

    Returns:
        Response with status 200 on success:

        >>> {
        ...     "success": true,
        ...     "message": "Slot erfolgreich gebucht",
        ...     "booking": {
        ...         "id": 42,
        ...         "date": "2026-02-28",
        ...         "time_slot": "10:00",
        ...         "user": "user@example.com"
        ...     }
        ... }

        Response with status 400 on validation error:

        >>> {"error": "Werkstatt ist nur samstags geöffnet."}

        Possible errors: invalid slot format, slot already booked, not a Saturday.
    """
    serializer = SlotBookingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        slot_data = serializer.validated_data["slotId"]
        workshop_date = slot_data["date"]
        time_slot = slot_data["time_slot"]

        # Create booking
        booking = WorkshopSlot(date=workshop_date, time_slot=time_slot, user=request.user)  # type: ignore
        booking.save()

        return Response(
            {
                "success": True,
                "message": "Slot erfolgreich gebucht",
                "booking": {
                    "id": booking.id,
                    "date": booking.date.isoformat(),
                    "time_slot": booking.time_slot,
                    "user": booking.user.email,
                },
            }
        )

    except ValidationError as e:
        error_message = "; ".join(e.messages)
        return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def cancel_slot(request: Request) -> Response:
    """Cancel a workshop booking by slot ID (passed as query param).

    Returns:
        Response with status 200 on success:

        >>> {"success": true, "message": "Buchung erfolgreich storniert"}

        Response with status 400 for invalid or missing slot ID.

        Response with status 404 when booking not found:

        >>> {"error": "Buchung nicht gefunden"}
    """
    serializer = SlotCancelSerializer(data={"slotId": request.query_params.get("slotId", "")})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    slot_data = serializer.validated_data["slotId"]

    try:
        booking = WorkshopSlot.objects.get(
            date=slot_data["date"],
            time_slot=slot_data["time_slot"],
            user=request.user,  # type: ignore
        )
        booking.delete()
        return Response({"success": True, "message": "Buchung erfolgreich storniert"})

    except WorkshopSlot.DoesNotExist:
        return Response({"error": "Buchung nicht gefunden"}, status=status.HTTP_404_NOT_FOUND)
