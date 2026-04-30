import pytest
from django.test import Client
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from apps.core.models import Project, User
from apps.maneuvers.models import ManeuverLog
from apps.telemetry.models import TelemetryRecord


def _redis_available():
    try:
        client = Redis.from_url("redis://localhost:6379/0", socket_connect_timeout=1, socket_timeout=1)
        return client.ping()
    except RedisConnectionError:
        return False


pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def project(db):
    return Project.objects.create(name="r1", ip="10.9.1.179")


@pytest.fixture
def operator(client):
    user = User.objects.create_user(
        username="operator", password="OperatorPass-12345", role="operator"
    )
    client.force_login(user)
    return user


@pytest.fixture
def viewer(client):
    user = User.objects.create_user(username="viewer", password="pw-very-long-12345")
    client.force_login(user)
    return user


@pytest.fixture
def superadmin(client):
    user = User.objects.create_user(
        username="admin", password="admin-ChangeMe-12345", role="superadmin"
    )
    client.force_login(user)
    return user


@pytest.fixture(autouse=True)
def _clear_redis():
    if _redis_available():
        Redis.from_url("redis://localhost:6379/0").flushdb()


@pytest.mark.skipif(not _redis_available(), reason="Redis not available")
class TestManeuverGuard:
    @pytest.fixture(autouse=True)
    def _override_redis_url(self, settings):
        settings.REDIS_URL = "redis://localhost:6379/0"

    def test_no_telemetry(self, client, operator, project):
        resp = client.post(
            f"/api/projects/{project.id}/maneuver/",
            {"action": "TRIP"},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_guard_trip_needs_closed(self, client, operator, project):
        TelemetryRecord.objects.create(project=project, derived_status="OPEN")
        resp = client.post(
            f"/api/projects/{project.id}/maneuver/",
            {"action": "TRIP"},
            content_type="application/json",
        )
        assert resp.status_code == 422
        assert resp.json()["result"] == "fail_guard"

    def test_guard_close_needs_open(self, client, operator, project):
        TelemetryRecord.objects.create(project=project, derived_status="CLOSED")
        resp = client.post(
            f"/api/projects/{project.id}/maneuver/",
            {"action": "CLOSE"},
            content_type="application/json",
        )
        assert resp.status_code == 422
        assert resp.json()["result"] == "fail_guard"

    def test_viewer_cannot_maneuver(self, client, viewer, project):
        TelemetryRecord.objects.create(project=project, derived_status="CLOSED")
        resp = client.post(
            f"/api/projects/{project.id}/maneuver/",
            {"action": "TRIP"},
            content_type="application/json",
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestManeuverAudit:
    def test_audit_list(self, client, superadmin, project, operator):
        client.force_login(superadmin)
        ManeuverLog.objects.create(
            user=operator,
            project=project,
            action="TRIP",
            pre_status="CLOSED",
            pre_snapshot={},
            post_status="OPEN",
            post_snapshot={},
            result="success",
        )
        resp = client.get("/api/maneuvers/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    def test_audit_unauthorized(self, client, viewer):
        resp = client.get("/api/maneuvers/")
        assert resp.status_code == 403
