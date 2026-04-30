from django.urls import path

from apps.core import views_auth

urlpatterns = [
    path("login", views_auth.login_view),
    path("logout", views_auth.logout_view),
    path("me", views_auth.me_view),
]
