from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core import views_health
from apps.core.views import ProjectViewSet, UserViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet)
router.register("users", UserViewSet)

urlpatterns = [
    path("health/live", views_health.live, name="health-live"),
    path("health/ready", views_health.ready, name="health-ready"),
    path("health/devices", views_health.devices, name="health-devices"),
    path("", include(router.urls)),
]
