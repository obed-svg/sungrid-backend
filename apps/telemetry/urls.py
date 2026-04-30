from django.urls import path

from apps.telemetry import views

urlpatterns = [
    path("projects/<int:project_id>/telemetry/latest", views.latest),
    path("projects/<int:project_id>/telemetry/history", views.HistoryView.as_view()),
    path("projects/<int:project_id>/telemetry/<int:rec_id>/points", views.points_detail),
]
