from typing import Any

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):  # type: ignore
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)

        if extra_fields.get("is_staff") and not extra_fields.get("is_superuser"):
            extra_fields.setdefault("role", User.Role.MEMBER)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user  # type: ignore

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", _("Admin")
        MEMBER = "member", _("Member")
        GUEST = "guest", _("Guest")

    # Disable username field
    username = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.GUEST)
    # Use email as the unique identifier for authentication
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()  # type: ignore

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email
