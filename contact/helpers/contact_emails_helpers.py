import logging

from django.conf import settings
from django.core.mail import send_mail

from contact.models import ContactMessage

logger = logging.getLogger(__name__)


def _get_sender_name(contact_message: ContactMessage) -> str:
    """Get the display name of the sender."""
    full_name = f"{contact_message.first_name} {contact_message.last_name}".strip()
    return full_name if full_name else contact_message.email


def _get_admin_panel_url(contact_message: ContactMessage) -> str:
    """Build the admin panel URL dynamically."""
    base_url = settings.BACKEND_BASE_URL
    return f"{base_url}/admin/contact/contactmessage/{contact_message.pk}/"


def send_admin_notification(contact_message: ContactMessage) -> None:
    """Send email notification to admins.

    Raises:
        SMTPException: If the email delivery fails.
        ConnectionError: If the mail server is unreachable.
    """
    sender_name = _get_sender_name(contact_message)
    subject = f"Neue Kontakt-Nachricht von {sender_name}"

    admin_message = f"""
Neue Kontakt-Nachricht erhalten:

Von: {sender_name} ({contact_message.email})
Betreff: {contact_message.subject}
Datum: {contact_message.created_at.strftime("%d.%m.%Y %H:%M")}

Nachricht:
{contact_message.message}

---
Admin-Panel: {_get_admin_panel_url(contact_message)}
    """

    admin_email = settings.ADMIN_EMAIL

    send_mail(
        subject=subject,
        message=admin_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[admin_email],
        fail_silently=False,
    )


def send_confirmation_email(contact_message: ContactMessage) -> None:
    """Send confirmation email to the sender."""
    subject = "Deine Nachricht wurde erfolgreich übermittelt"
    greeting_name = _get_sender_name(contact_message)

    confirmation_message = f"""
Hallo {greeting_name},

vielen Dank für deine Nachricht! Wir haben deine Anfrage erfolgreich erhalten und werden uns so schnell wie möglich bei dir melden.

Deine Angaben:
Betreff: {contact_message.subject}
Datum: {contact_message.created_at.strftime("%d.%m.%Y %H:%M")}
Nachricht:
{contact_message.message}

Viele Grüße
Dein HeiNa
"""

    send_mail(
        subject=subject,
        message=confirmation_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[contact_message.email],
        fail_silently=True,
    )
