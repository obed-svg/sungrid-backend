from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


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
    except Exception as exc:  # pragma: no cover - returned for ops visibility
        checks["database_error"] = exc.__class__.__name__

    try:
        from redis import Redis

        client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        checks["redis"] = bool(client.ping())
    except Exception as exc:  # pragma: no cover - depends on deployed Redis
        checks["redis_error"] = exc.__class__.__name__

    status_code = 200 if checks["database"] and checks["redis"] else 503
    return Response({"status": "ok" if status_code == 200 else "degraded", "checks": checks}, status=status_code)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def devices(request):
    return Response({"status": "ok"})

