from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class WorkshopSlot(models.Model):
    SLOT_CHOICES = [
        ("10:00", "10:00 - 11:00"),
        ("11:00", "11:00 - 12:00"),
        ("12:00", "12:00 - 13:00"),
    ]

    date = models.DateField()
    time_slot = models.CharField(max_length=5, choices=SLOT_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["date", "time_slot"], name="unique_slot_per_date"),
        ]
        ordering = ["date", "time_slot"]

    def clean(self) -> None:
        """Django Model hook for custom validation.

        This method is automatically called by Django forms, admin, and DRF
        serializers during validation. It is also explicitly called in save()
        to ensure validation runs even when saving programmatically.

        Raises:
            ValidationError: If the date is not a Saturday or the user
                already has a booking on the given date.
        """
        # Validation: Only Saturdays
        if self.date.weekday() != 5:
            raise ValidationError("Werkstatt ist nur samstags geöffnet.")

        # Validation: Only one booking per day
        existing_booking = WorkshopSlot.objects.filter(user=self.user, date=self.date).exclude(pk=self.pk)
        if existing_booking.exists():
            raise ValidationError("Du hast bereits eine Buchung für diesen Tag.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.user.email} - {self.date} {self.time_slot}"
