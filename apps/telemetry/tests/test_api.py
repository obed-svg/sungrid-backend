from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.core.models import Project, User
from apps.telemetry.models import AnalogPoint, BinaryPoint, TelemetryRecord


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def project(db):
    return Project.objects.create(name="r1", ip="10.9.1.179")


@pytest.fixture
def viewer(client, project):
    user = User.objects.create_user(username="viewer", password="pw-very-long-12345")
    client.force_login(user)
    return user


@pytest.fixture
def superadmin(client):
    user = User.objects.create_user(
        username="admin", password="admin-ChangeMe-12345", role="superadmin"
    )
    client.login(username="admin", password="admin-ChangeMe-12345")
    return user


@pytest.mark.django_db
class TestTelemetryLatest:
    def test_latest_returns_record(self, client, viewer, project):
        TelemetryRecord.objects.create(project=project, derived_status="CLOSED")
        resp = client.get(f"/api/projects/{project.id}/telemetry/latest")
        assert resp.status_code == 200
        assert resp.json()["derived_status"] == "CLOSED"

    def test_latest_no_telemetry(self, client, viewer, project):
        resp = client.get(f"/api/projects/{project.id}/telemetry/latest")
        assert resp.status_code == 404

    def test_latest_stale_telemetry(self, client, viewer, project):
        old = timezone.now() - timedelta(minutes=7)
        TelemetryRecord.objects.create(project=project, derived_status="CLOSED", cycle_timestamp=old)
        resp = client.get(f"/api/projects/{project.id}/telemetry/latest")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "stale"

    def test_latest_unauthorized(self, client, project):
        resp = client.get(f"/api/projects/{project.id}/telemetry/latest")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestTelemetryHistory:
    def test_history_paginated(self, client, viewer, project):
        for _ in range(5):
            TelemetryRecord.objects.create(project=project, derived_status="CLOSED")
        resp = client.get(f"/api/projects/{project.id}/telemetry/history")
        assert resp.status_code == 200
        assert resp.json()["count"] == 5


@pytest.mark.django_db
class TestTelemetryPoints:
    def test_points_detail(self, client, viewer, project):
        rec = TelemetryRecord.objects.create(project=project, derived_status="CLOSED")
        from django.utils import timezone as tz
        AnalogPoint.objects.create(
            telemetry=rec, label="Ia", value=10.0, count_update=1, timestamp=tz.now()
        )
        BinaryPoint.objects.create(
            telemetry=rec, label="Breaker close", value=True, count_update=1, timestamp=tz.now()
        )
        resp = client.get(f"/api/projects/{project.id}/telemetry/{rec.id}/points")
        assert resp.status_code == 200
        assert len(resp.json()["analogs"]) == 1
        assert len(resp.json()["binaries"]) == 1
