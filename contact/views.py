from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from contact.helpers import send_admin_notification, send_confirmation_email

from .serializers import ContactMessageSerializer


def get_client_ip(request: Request) -> str:
    """Extract the client's IP address from the request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip or ""


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def submit_contact_form(request: Request) -> Response:
    """
    Public API endpoint for submitting the contact form.
    """

    serializer = ContactMessageSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    contact_message = serializer.save(ip_address=get_client_ip(request))

    send_admin_notification(contact_message)
    send_confirmation_email(contact_message)

    return Response(
        {
            "success": True,
            "message": "Deine Nachricht wurde erfolgreich übermittelt. Du erhältst in Kürze eine Bestätigungs-E-Mail.",
            "id": contact_message.pk,
        },
        status=status.HTTP_201_CREATED,
    )
