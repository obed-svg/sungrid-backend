from django.urls import path

from apps.maneuvers import views

urlpatterns = [
    path("projects/<int:project_id>/maneuver/", views.maneuver_view),
    path("maneuvers/", views.ManeuverAuditList.as_view()),
]
