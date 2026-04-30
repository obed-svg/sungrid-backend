import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.core.models import Project, User


@pytest.mark.django_db
class TestUser:
    def test_role_default_is_viewer(self):
        u = User.objects.create_user(username="x", password="pw-very-long-12345")
        assert u.role == "viewer"

    def test_role_choices_enforced(self):
        u = User(username="y", role="invalid")
        with pytest.raises(ValidationError):
            u.full_clean()

    def test_superadmin_creation(self):
        u = User.objects.create_user(
            username="admin", password="pw-very-long-12345", role="superadmin"
        )
        assert u.role == "superadmin"
        assert u.is_active


@pytest.mark.django_db
class TestProject:
    def test_create(self):
        p = Project.objects.create(name="rec1", ip="10.9.1.179", port=8000)
        assert p.enabled is True
        assert p.master_id == 2
        assert p.outstation_id == 1

    def test_name_unique(self):
        Project.objects.create(name="rec1", ip="10.9.1.179")
        with pytest.raises(IntegrityError):
            Project.objects.create(name="rec1", ip="10.9.1.180")

    def test_str(self):
        p = Project.objects.create(name="test", ip="10.0.0.1")
        assert "test" in str(p)
