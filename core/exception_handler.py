"""Custom DRF exception handler.

Centralises error handling so that individual views don't need repetitive
try/except blocks.  Unhandled exceptions are logged and returned as a
generic 500 response without leaking internal details to the client.
"""

import logging
from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """Handle exceptions raised during DRF request processing.

    Delegates to DRF's default handler first (covers APIException subclasses
    like ValidationError, AuthenticationFailed, PermissionDenied, etc.).
    If DRF returns None the exception is unhandled — log it and return a
    safe 500 response.
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        return response

    # Unhandled exception — log full traceback, return generic message
    view = context.get("view")
    view_name = view.__class__.__name__ if view else "unknown view"
    logger.error(f"Unhandled exception in {view_name}: {exc}", exc_info=True)

    return Response(
        {"success": False, "error": "Entschuldigung, es ist ein Fehler aufgetreten. Bitte versuche es später erneut."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
