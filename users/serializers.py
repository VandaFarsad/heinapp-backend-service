from typing import Any

from django.contrib.auth.models import Group
from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer
from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from users.models import User


class UserCreateSerializer(DjoserUserCreateSerializer[User]):  # type: ignore
    class Meta(DjoserUserCreateSerializer.Meta):  # type: ignore
        model = User
        fields = list(DjoserUserCreateSerializer.Meta.fields) + [
            "first_name",
            "last_name",
        ]


class UserSerializer(DjoserUserSerializer[User]):  # type: ignore
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "role",
            "is_staff",
            "groups",
        ]
        read_only_fields = ["email", "role", "is_staff"]


class GroupSerializer(serializers.ModelSerializer[Group]):
    class Meta:
        model = Group
        fields = ["id", "name"]


class UserTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate the user and return a token pair along with user data."""
        data: dict[str, Any] = super().validate(attrs)

        user: User = self.user  # type: ignore

        data["user"] = {
            "pk": user.pk,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
        }
        data["groups"] = list(user.groups.values_list("name", flat=True))
        data.pop("refresh", None)

        return data
