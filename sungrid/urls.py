from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.core.urls_auth")),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.telemetry.urls")),
    path("api/", include("apps.maneuvers.urls")),
]
