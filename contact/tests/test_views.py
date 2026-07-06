from unittest.mock import MagicMock, patch

import pytest
from django.core import mail
from rest_framework import status
from rest_framework.test import APIClient

from contact.models import ContactMessage

CONTACT_URL = "/api/v1/contact/submit/"


def _valid_payload(**overrides: str) -> dict[str, str]:
    """Return a valid contact form payload, with optional overrides."""
    defaults: dict[str, str] = {
        "first_name": "Max",
        "last_name": "Mustermann",
        "email": "max@example.com",
        "subject": "Testbetreff",
        "message": "Das ist eine ausreichend lange Testnachricht.",
    }
    defaults.update(overrides)
    return defaults


# ── Success cases ──────────────────────────────────────────────


@pytest.mark.django_db
def test_submit_all_fields(api_client: APIClient) -> None:
    """All fields filled — should return 201 and persist the message."""
    response = api_client.post(CONTACT_URL, _valid_payload(), format="json")

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True
    assert "id" in data
    assert ContactMessage.objects.count() == 1


@pytest.mark.django_db
def test_submit_without_names(api_client: APIClient) -> None:
    """Only required fields (email, subject, message) — names are optional."""
    payload = _valid_payload()
    del payload["first_name"]
    del payload["last_name"]

    response = api_client.post(CONTACT_URL, payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    msg = ContactMessage.objects.first()
    assert msg is not None
    assert msg.first_name == ""
    assert msg.last_name == ""


@pytest.mark.django_db
def test_submit_with_empty_names(api_client: APIClient) -> None:
    """Explicitly empty name fields should be accepted."""
    response = api_client.post(
        CONTACT_URL,
        _valid_payload(first_name="", last_name=""),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_submit_only_first_name(api_client: APIClient) -> None:
    """Only first_name given, last_name omitted."""
    payload = _valid_payload(first_name="Anna")
    del payload["last_name"]

    response = api_client.post(CONTACT_URL, payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    msg = ContactMessage.objects.first()
    assert msg is not None
    assert msg.first_name == "Anna"
    assert msg.last_name == ""


@pytest.mark.django_db
def test_success_response_contains_confirmation_hint(api_client: APIClient) -> None:
    """On success the response message should mention confirmation email."""
    response = api_client.post(CONTACT_URL, _valid_payload(), format="json")

    data = response.json()
    assert "Bestätigungs-E-Mail" in data["message"]


@pytest.mark.django_db
def test_emails_sent_on_success(api_client: APIClient) -> None:
    """Admin notification + user confirmation = 2 emails."""
    api_client.post(CONTACT_URL, _valid_payload(), format="json")

    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_ip_address_stored(api_client: APIClient) -> None:
    """The client IP should be saved on the ContactMessage."""
    api_client.post(CONTACT_URL, _valid_payload(), format="json")

    msg = ContactMessage.objects.first()
    assert msg is not None
    assert msg.ip_address is not None


# ── Validation errors ──────────────────────────────────────────


@pytest.mark.django_db
def test_subject_too_short(api_client: APIClient) -> None:
    """Subject shorter than 3 chars should be rejected."""
    response = api_client.post(
        CONTACT_URL,
        _valid_payload(subject="Ab"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "subject" in response.json()["errors"]


@pytest.mark.django_db
def test_message_too_short(api_client: APIClient) -> None:
    """Message shorter than 10 chars should be rejected."""
    response = api_client.post(
        CONTACT_URL,
        _valid_payload(message="Kurz"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "message" in response.json()["errors"]


@pytest.mark.django_db
def test_invalid_email(api_client: APIClient) -> None:
    """An invalid email address should be rejected."""
    response = api_client.post(
        CONTACT_URL,
        _valid_payload(email="keine-email"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.json()["errors"]


@pytest.mark.django_db
def test_missing_required_fields(api_client: APIClient) -> None:
    """Missing email, subject, and message should all produce errors."""
    response = api_client.post(CONTACT_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    errors = response.json()["errors"]
    assert "email" in errors
    assert "subject" in errors
    assert "message" in errors


@pytest.mark.django_db
def test_first_name_too_short(api_client: APIClient) -> None:
    """A single-char first name should be rejected (min 2 when provided)."""
    response = api_client.post(
        CONTACT_URL,
        _valid_payload(first_name="A"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "first_name" in response.json()["errors"]


@pytest.mark.django_db
def test_last_name_too_short(api_client: APIClient) -> None:
    """A single-char last name should be rejected (min 2 when provided)."""
    response = api_client.post(
        CONTACT_URL,
        _valid_payload(last_name="B"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "last_name" in response.json()["errors"]


# ── Edge cases ─────────────────────────────────────────────────


@pytest.mark.django_db
def test_no_message_persisted_on_validation_error(api_client: APIClient) -> None:
    """A failed validation must not create a ContactMessage row."""
    api_client.post(CONTACT_URL, {}, format="json")

    assert ContactMessage.objects.count() == 0
