import pytest
from django.utils import timezone

from apps.core.models import Project
from apps.telemetry.models import AnalogPoint, BinaryPoint, TelemetryRecord


@pytest.fixture
def project(db):
    return Project.objects.create(name="r1", ip="10.9.1.179")


@pytest.mark.django_db
class TestTelemetryRecord:
    def test_create_with_hot_fields(self, project):
        rec = TelemetryRecord.objects.create(
            project=project,
            derived_status="CLOSED",
            ia=12.3,
            ua=7.2,
            ur=7.1,
            freq=60.0,
            breaker_close=True,
            breaker_open=False,
        )
        assert rec.cycle_timestamp is not None
        assert rec.derived_status == "CLOSED"

    def test_index_supports_latest_query(self, project):
        for _ in range(3):
            TelemetryRecord.objects.create(project=project, derived_status="CLOSED")
        latest = TelemetryRecord.objects.filter(project=project).latest("cycle_timestamp")
        assert latest is not None


@pytest.mark.django_db
class TestPoints:
    def test_analog_point_create(self, project):
        rec = TelemetryRecord.objects.create(project=project, derived_status="CLOSED")
        ap = AnalogPoint.objects.create(
            telemetry=rec,
            label="Ia",
            value=12.5,
            count_update=2,
            timestamp=timezone.now(),
        )
        assert ap.label == "Ia"

    def test_binary_point_create(self, project):
        rec = TelemetryRecord.objects.create(project=project, derived_status="CLOSED")
        bp = BinaryPoint.objects.create(
            telemetry=rec,
            label="Breaker close",
            value=True,
            count_update=1,
            timestamp=timezone.now(),
        )
        assert bp.value is True

    def test_cascade_delete(self, project):
        rec = TelemetryRecord.objects.create(project=project, derived_status="CLOSED")
        AnalogPoint.objects.create(
            telemetry=rec, label="Ia", value=1.0, count_update=1, timestamp=timezone.now()
        )
        BinaryPoint.objects.create(
            telemetry=rec, label="b", value=False, count_update=1, timestamp=timezone.now()
        )
        rec.delete()
        assert AnalogPoint.objects.count() == 0
        assert BinaryPoint.objects.count() == 0
