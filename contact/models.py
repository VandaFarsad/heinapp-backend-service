from django.db import models


class ContactMessage(models.Model):
    """Model for contact messages."""

    class Status(models.TextChoices):
        NEW = "new", "Neu"
        READ = "read", "Gelesen"
        REPLIED = "replied", "Beantwortet"
        CLOSED = "closed", "Geschlossen"

    # Sender information
    first_name = models.CharField(max_length=100, verbose_name="First Name", blank=True, default="")
    last_name = models.CharField(max_length=100, verbose_name="Last Name", blank=True, default="")
    email = models.EmailField(verbose_name="E-Mail")

    # Message fields
    subject = models.CharField(max_length=200, verbose_name="Subject")
    message = models.TextField(verbose_name="Message")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")

    # IP address for spam protection
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Address")

    # Admin fields
    admin_notes = models.TextField(blank=True, verbose_name="Admin Notes")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, verbose_name="Status")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kontakt-Nachricht"
        verbose_name_plural = "Kontakt-Nachrichten"

    def __str__(self) -> str:
        return f"{self.email} - {self.subject}"
