from rest_framework import viewsets

from apps.core.models import Project, User
from apps.core.permissions import IsSuperAdmin, IsViewer
from apps.core.serializers import ProjectSerializer, UserCreateSerializer, UserSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by("name")
    serializer_class = ProjectSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewer()]
        return [IsSuperAdmin()]

    def perform_destroy(self, instance):
        instance.enabled = False
        instance.save(update_fields=["enabled", "updated_at"])


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("username")

    def get_permissions(self):
        return [IsSuperAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])

