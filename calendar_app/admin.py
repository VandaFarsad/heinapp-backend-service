from django.contrib import admin

from .models import CalendarEvent


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):  # type: ignore
    list_display = (
        "uid",
        "recurrence_id",
        "title",
        "start_date",
        "end_date",
        "all_day",
        "location",
        "has_recurrence",
        "has_exceptions",
        "created_at",
        "updated_at",
        "last_synced_at",
    )
    search_fields = ("title", "description", "location", "uid", "rrule")
    list_filter = ("all_day", "start_date", "end_date", "last_synced_at")
    ordering = ("start_date",)
    date_hierarchy = "start_date"

    readonly_fields = ("created_at", "updated_at", "last_synced_at")

    fieldsets = (
        ("Basic Information", {"fields": ("uid", "recurrence_id", "title", "description")}),
        ("Date & Time", {"fields": ("start_date", "end_date", "all_day")}),
        ("Location & URL", {"fields": ("location", "url")}),
        ("Recurrence", {"fields": ("rrule", "exdate"), "description": "RFC 5545 recurrence rules and exception dates"}),
        ("Metadata", {"fields": ("created_at", "updated_at", "last_synced_at"), "classes": ("collapse",)}),
    )

    def has_recurrence(self, obj: CalendarEvent) -> bool:
        """Display whether the event has a recurrence rule."""
        return bool(obj.rrule)

    has_recurrence.boolean = True  # type: ignore
    has_recurrence.short_description = "Recurring"  # type: ignore

    def has_exceptions(self, obj: CalendarEvent) -> bool:
        """Display whether the event has exception dates."""
        return bool(obj.exdate)

    has_exceptions.boolean = True  # type: ignore
    has_exceptions.short_description = "Has Exceptions"  # type: ignore
