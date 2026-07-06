# serializers.py (Django Backend)
from datetime import datetime
from typing import Any

from rest_framework import serializers

from .models import WorkshopSlot


class WorkshopSlotSerializer(serializers.ModelSerializer[WorkshopSlot]):
    user_email = serializers.CharField(source="user.email", read_only=True)
    is_current_user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WorkshopSlot
        fields = ["id", "date", "time_slot", "user_email", "is_current_user", "booked_at"]
        read_only_fields = ["id", "user_email", "is_current_user", "booked_at"]

    def get_is_current_user(self, obj: WorkshopSlot) -> bool:
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            return bool(obj.user == request.user)
        return False

    def create(self, validated_data: dict[str, Any]) -> WorkshopSlot:
        request = self.context.get("request")
        if request:
            validated_data["user"] = request.user
        return super().create(validated_data)


class SlotBookingSerializer(serializers.Serializer[None]):
    """Serializer für Slot-Buchung mit slotId Format"""

    slotId = serializers.CharField()

    def validate_slotId(self, value: str) -> dict[str, Any]:
        """Validiere und parse slotId Format: "2025-07-12-10:00" """
        try:
            date_str, time_str = value.rsplit("-", 1)
            workshop_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Validiere Zeit-Slot
            valid_times = ["10:00", "11:00", "12:00"]
            if time_str not in valid_times:
                raise serializers.ValidationError("Ungültiger Zeit-Slot")

            return {"date": workshop_date, "time_slot": time_str}
        except ValueError:
            raise serializers.ValidationError("Ungültiges slotId Format")


class SlotCancelSerializer(serializers.Serializer[None]):
    """Serializer für Slot-Stornierung mit slotId Format"""

    slotId = serializers.CharField()

    def validate_slotId(self, value: str) -> dict[str, Any]:
        """Validiere und parse slotId Format: "2025-07-12-10:00" """
        return SlotBookingSerializer().validate_slotId(value)


class SlotResponseSerializer(serializers.Serializer[None]):
    """Serializer für Slot-Response (verfügbare und gebuchte Slots)"""

    id = serializers.CharField()
    date = serializers.DateField()
    time = serializers.CharField()
    isAvailable = serializers.BooleanField()
    isBooked = serializers.BooleanField()
    bookedBy = serializers.CharField(required=False)
    bookedByCurrentUser = serializers.BooleanField(required=False)
