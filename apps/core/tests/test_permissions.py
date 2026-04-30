import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.core.models import User
from apps.core.permissions import IsOperator, IsSuperAdmin, IsViewer


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def viewer_user():
    return User(username="viewer", role="viewer")


@pytest.fixture
def operator_user():
    return User(username="operator", role="operator")


@pytest.fixture
def superadmin_user():
    return User(username="admin", role="superadmin")


class TestIsViewer:
    def test_allows_viewer(self, rf, viewer_user):
        request = rf.get("/")
        request.user = viewer_user
        assert IsViewer().has_permission(request, None) is True

    def test_allows_operator(self, rf, operator_user):
        request = rf.get("/")
        request.user = operator_user
        assert IsViewer().has_permission(request, None) is True

    def test_allows_superadmin(self, rf, superadmin_user):
        request = rf.get("/")
        request.user = superadmin_user
        assert IsViewer().has_permission(request, None) is True

    def test_denies_anonymous(self, rf):
        request = rf.get("/")
        request.user = AnonymousUser()
        assert IsViewer().has_permission(request, None) is False


class TestIsOperator:
    def test_denies_viewer(self, rf, viewer_user):
        request = rf.get("/")
        request.user = viewer_user
        assert IsOperator().has_permission(request, None) is False

    def test_allows_operator(self, rf, operator_user):
        request = rf.get("/")
        request.user = operator_user
        assert IsOperator().has_permission(request, None) is True

    def test_allows_superadmin(self, rf, superadmin_user):
        request = rf.get("/")
        request.user = superadmin_user
        assert IsOperator().has_permission(request, None) is True


class TestIsSuperAdmin:
    def test_denies_viewer(self, rf, viewer_user):
        request = rf.get("/")
        request.user = viewer_user
        assert IsSuperAdmin().has_permission(request, None) is False

    def test_denies_operator(self, rf, operator_user):
        request = rf.get("/")
        request.user = operator_user
        assert IsSuperAdmin().has_permission(request, None) is False

    def test_allows_superadmin(self, rf, superadmin_user):
        request = rf.get("/")
        request.user = superadmin_user
        assert IsSuperAdmin().has_permission(request, None) is True
