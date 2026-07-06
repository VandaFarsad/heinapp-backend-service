# admin.py (Django Backend)
from django.contrib import admin
from django.http import HttpRequest

from .models import WorkshopSlot


@admin.register(WorkshopSlot)
class WorkshopSlotAdmin(admin.ModelAdmin):  # type: ignore
    list_display = ["user", "date", "time_slot", "booked_at"]
    list_filter = ["date", "time_slot"]
    search_fields = ["user__email"]
    ordering = ["-date", "time_slot"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj: WorkshopSlot | None = None) -> bool:
        return request.user.is_superuser

    def has_delete_permission(self, request: HttpRequest, obj: WorkshopSlot | None = None) -> bool:
        return request.user.is_superuser
