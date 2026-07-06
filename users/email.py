from django.conf import settings
from djoser import email


class ActivationEmail(email.ActivationEmail):  # type: ignore
    template_name = "djoser/email/activation_email.html"

    def get_context_data(self):
        context = super().get_context_data()
        # Override domain and protocol to use configured values
        context["domain"] = settings.DJOSER.get("EMAIL_FRONTEND_DOMAIN", "localhost:3000")
        context["protocol"] = "https" if not settings.DEBUG else "http"
        return context


class ConfirmationEmail(email.ConfirmationEmail):  # type: ignore
    template_name = "djoser/email/confirmation_email.html"

    def get_context_data(self):
        context = super().get_context_data()
        context["domain"] = settings.DJOSER.get("EMAIL_FRONTEND_DOMAIN", "localhost:3000")
        context["protocol"] = "https" if not settings.DEBUG else "http"
        return context


class PasswordResetEmail(email.PasswordResetEmail):  # type: ignore
    template_name = "djoser/email/password_reset_email.html"

    def get_context_data(self):
        context = super().get_context_data()
        context["domain"] = settings.DJOSER.get("EMAIL_FRONTEND_DOMAIN", "localhost:3000")
        context["protocol"] = "https" if not settings.DEBUG else "http"
        return context
