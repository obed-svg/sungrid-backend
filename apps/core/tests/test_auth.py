import pytest
from django.test import Client

from apps.core.models import User


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def superadmin():
    return User.objects.create_user(
        username="admin", password="admin-ChangeMe-12345", role="superadmin"
    )


@pytest.fixture
def operator():
    return User.objects.create_user(
        username="operator", password="OperatorPass-12345", role="operator"
    )


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, client, superadmin):
        resp = client.post(
            "/api/auth/login",
            {"username": "admin", "password": "admin-ChangeMe-12345"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"
        assert resp.json()["role"] == "superadmin"

    def test_login_wrong_password(self, client, superadmin):
        resp = client.post(
            "/api/auth/login",
            {"username": "admin", "password": "wrong"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_login_inactive_user(self, client):
        User.objects.create_user(
            username="inactive", password="pw-very-long-12345", is_active=False
        )
        resp = client.post(
            "/api/auth/login",
            {"username": "inactive", "password": "pw-very-long-12345"},
            content_type="application/json",
        )
        assert resp.status_code == 401


@pytest.mark.django_db
class TestLogout:
    def test_logout(self, client, superadmin):
        client.force_login(superadmin)
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 204


@pytest.mark.django_db
class TestMe:
    def test_me_authenticated(self, client, operator):
        client.force_login(operator)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["username"] == "operator"

    def test_me_anonymous(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 403
