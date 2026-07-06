from django.contrib.auth.models import Group
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.viewsets import ModelViewSet

from users.models import User
from users.serializers import GroupSerializer, UserSerializer


class IsAdminOrReadOnlySelf(permissions.BasePermission):
    """
    - Admins (is_superuser) have full access to all users.
    - Authenticated users can only retrieve/update their own profile.
    """

    def has_permission(self, request: Request, view: "UserViewSet") -> bool:  # type: ignore[override]
        if not request.user or not request.user.is_authenticated:
            return False
        # Admins can do everything
        if request.user.is_superuser:
            return True
        # Non-admins may only list (filtered to self) and retrieve/update self
        if view.action in ("list", "retrieve", "update", "partial_update"):
            return True
        return False

    def has_object_permission(self, request: Request, view: "UserViewSet", obj: User) -> bool:  # type: ignore[override]
        if request.user.is_superuser:
            return True
        # Non-admins can only access their own user object
        return obj.pk == request.user.pk


class UserViewSet(ModelViewSet):  # type: ignore
    """
    API endpoint that allows users to be viewed or edited.
    - Admins: full CRUD on all users.
    - Members/Guests: read and update own profile only.
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrReadOnlySelf]
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "role",
    ]
    filterset_fields = [
        "first_name",
        "last_name",
        "email",
        "role",
    ]

    def get_queryset(self):  # type: ignore
        """Non-admins only see themselves."""
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(pk=self.request.user.pk)


class GroupViewSet(ModelViewSet):  # type: ignore
    """
    API endpoint that allows groups to be viewed or edited.
    Only accessible by admins.
    """

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAdminUser]
