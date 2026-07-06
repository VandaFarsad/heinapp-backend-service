from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):  # type: ignore
    list_display = ["email", "first_name", "last_name", "subject", "created_at", "status"]
    list_filter = ["created_at", "status"]
    date_hierarchy = "created_at"
    search_fields = ["first_name", "last_name", "email", "subject", "message"]
    readonly_fields = [
        "created_at",
        "ip_address",
        "email",
        "first_name",
        "last_name",
        "subject",
        "message",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        ("Absender", {"fields": ("first_name", "last_name", "email", "ip_address")}),
        ("Nachricht", {"fields": ("created_at", "subject", "message", "status", "admin_notes")}),
    )
