from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.models import Project
from apps.telemetry.models import TelemetryRecord


@api_view(["GET"])
@permission_classes([])
def live(request):
    return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([])
def ready(request):
    checks = {"database": False, "redis": False}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = True
    except Exception as exc:
        checks["database_error"] = exc.__class__.__name__

    try:
        from redis import Redis

        client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        checks["redis"] = bool(client.ping())
    except Exception as exc:
        checks["redis_error"] = exc.__class__.__name__

    status_code = 200 if checks["database"] and checks["redis"] else 503
    return Response(
        {"status": "ok" if status_code == 200 else "degraded", "checks": checks},
        status=status_code,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def devices(request):
    """Return per-project online state based on last successful poll."""
    timeout_seconds = 300  # 5 minutes without data = offline
    cutoff = timezone.now() - __import__("datetime").timedelta(seconds=timeout_seconds)

    projects = Project.objects.filter(enabled=True)
    result = []
    for project in projects:
        latest = (
            TelemetryRecord.objects.filter(project=project)
            .order_by("-cycle_timestamp")
            .first()
        )
        is_online = latest is not None and latest.cycle_timestamp >= cutoff
        result.append(
            {
                "project_id": project.id,
                "name": project.name,
                "online": is_online,
                "last_seen": latest.cycle_timestamp.isoformat() if latest else None,
                "derived_status": latest.derived_status if latest else "OFFLINE",
            }
        )

    return Response({"status": "ok", "devices": result})
