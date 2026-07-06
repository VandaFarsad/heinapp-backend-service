from rest_framework import serializers

from .models import ContactMessage


class ContactMessageSerializer(serializers.ModelSerializer[ContactMessage]):
    """Serializer for the public contact form.

    Field-level validation is handled via `validate_<fieldname>` methods,
    which are automatically called by DRF during `serializer.is_valid()`.
    """

    class Meta:
        model = ContactMessage
        fields = ["first_name", "last_name", "email", "subject", "message"]

    def validate_message(self, value: str) -> str:
        """Validate the message field."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Die Nachricht muss mindestens 10 Zeichen lang sein.")
        return value.strip()

    def validate_subject(self, value: str) -> str:
        """Validate the subject field."""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Der Betreff muss mindestens 3 Zeichen lang sein.")
        return value.strip()

    def validate_first_name(self, value: str) -> str:
        """Validate the first name field."""
        if value.strip() and len(value.strip()) < 2:
            raise serializers.ValidationError("Der Vorname muss mindestens 2 Zeichen lang sein.")
        return value.strip()

    def validate_last_name(self, value: str) -> str:
        """Validate the last name field."""
        if value.strip() and len(value.strip()) < 2:
            raise serializers.ValidationError("Der Nachname muss mindestens 2 Zeichen lang sein.")
        return value.strip()
