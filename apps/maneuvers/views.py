import asyncio
import contextlib
import subprocess

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from redis import Redis
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from apps.core.models import Project
from apps.core.permissions import IsOperator, IsSuperAdmin
from apps.maneuvers.models import ManeuverLog
from apps.maneuvers.serializers import ManeuverActionSerializer, ManeuverLogSerializer
from apps.protocol.rwk35 import (
    CLOSE_FRAME,
    TRIP_FRAME,
    build_read_class0,
    compute_derived_status,
    extract_hot_fields,
    parse_response,
    recv_dnp3_frame,
    recv_solicited,
)
from apps.telemetry.models import TelemetryRecord
from apps.telemetry.serializers import TelemetryRecordSerializer

REQUIRED_STATUS = {"TRIP": "CLOSED", "CLOSE": "OPEN"}
CHANNEL_SEND_TIMEOUT_SECONDS = 2

def _get_redis():
    return Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)


def _ping_host(ip: str, timeout: float = 1.0) -> bool:
    """Check if host is reachable via ICMP ping."""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(int(timeout)), ip],
            capture_output=True,
            timeout=timeout + 1,
        )
        return result.returncode == 0
    except Exception:
        return False


def _send_control_frame(frame: bytes, ip: str, port: int) -> bytes:
    """Send control frame and return response."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(5)
        sock.connect((ip, port))
        sock.sendall(frame)
        sock.settimeout(10)
        try:
            return recv_dnp3_frame(sock)
        except TimeoutError:
            return b""


def _read_after_command(project: Project) -> tuple[str, dict]:
    """Send out-of-band READ after maneuver and return new status + snapshot."""
    import socket
    import time

    time.sleep(1)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(5)
        sock.connect((str(project.ip), project.port))
        frame = build_read_class0(project.master_id, project.outstation_id, seq=1)
        sock.sendall(frame)
        rx_time = timezone.now()
        resp = recv_solicited(sock, 8)
        if resp:
            pts = parse_response(resp, rx_time)
            hot = extract_hot_fields(pts)
            return compute_derived_status(hot), hot
    return "ERROR", {}


@api_view(["POST"])
@permission_classes([IsOperator])
def maneuver_view(request, project_id):
    action_serializer = ManeuverActionSerializer(data=request.data)
    action_serializer.is_valid(raise_exception=True)
    action = action_serializer.validated_data["action"]
    project = get_object_or_404(Project, pk=project_id, enabled=True)

    mutex_key = f"maneuver:{project.id}"
    cooldown_key = f"cooldown:{project.id}"

    # 1. Check mutex
    try:
        redis_client = _get_redis()
        if not redis_client.set(mutex_key, "1", nx=True, ex=settings.MANEUVER_MUTEX_TTL_SECONDS):
            log = ManeuverLog.objects.create(
                user=request.user,
                project=project,
                action=action,
                pre_status="",
                pre_snapshot={},
                post_status="",
                post_snapshot=None,
                result="fail_locked",
                error_message="Another maneuver is in progress",
            )
            return Response(ManeuverLogSerializer(log).data, status=409)
    except Exception as exc:
        log = ManeuverLog.objects.create(
            user=request.user,
            project=project,
            action=action,
            pre_status="",
            pre_snapshot={},
            post_status="",
            post_snapshot=None,
            result="fail_locked",
            error_message=f"Redis error: {exc}",
        )
        return Response(ManeuverLogSerializer(log).data, status=409)
    try:
        # 2. Check cooldown
        if redis_client.exists(cooldown_key):
            log = ManeuverLog.objects.create(
                user=request.user,
                project=project,
                action=action,
                pre_status="",
                pre_snapshot={},
                post_status="",
                post_snapshot=None,
                result="fail_cooldown",
                error_message="Cooldown active",
            )
            return Response(ManeuverLogSerializer(log).data, status=429)

        # 3. Read pre-status
        pre_record = TelemetryRecord.objects.filter(project=project).order_by("-cycle_timestamp").first()
        if pre_record is None:
            return Response({"detail": "no telemetry available"}, status=404)

        pre_snapshot = TelemetryRecordSerializer(pre_record).data
        required = REQUIRED_STATUS[action]

        if pre_record.derived_status != required:
            log = ManeuverLog.objects.create(
                user=request.user,
                project=project,
                action=action,
                pre_status=pre_record.derived_status,
                pre_snapshot=pre_snapshot,
                post_status=pre_record.derived_status,
                post_snapshot=pre_snapshot,
                result="fail_guard",
                error_message=f"{action} not allowed when status={pre_record.derived_status}",
            )
            return Response(ManeuverLogSerializer(log).data, status=422)

        # 4. Tunnel reachability check
        if not _ping_host(str(project.ip), settings.MANEUVER_TUNNEL_PING_TIMEOUT):
            log = ManeuverLog.objects.create(
                user=request.user,
                project=project,
                action=action,
                pre_status=pre_record.derived_status,
                pre_snapshot=pre_snapshot,
                post_status="",
                post_snapshot=None,
                result="fail_tunnel",
                error_message=f"Tunnel to {project.ip} unreachable",
            )
            return Response(ManeuverLogSerializer(log).data, status=503)

        # 5. Send control frame
        frame = CLOSE_FRAME if action == "CLOSE" else TRIP_FRAME
        try:
            rx_frame = _send_control_frame(frame, str(project.ip), project.port)
        except Exception as exc:
            log = ManeuverLog.objects.create(
                user=request.user,
                project=project,
                action=action,
                pre_status=pre_record.derived_status,
                pre_snapshot=pre_snapshot,
                post_status="",
                post_snapshot=None,
                result="fail_tcp",
                error_message=f"TCP error: {exc}",
                tx_frame=frame.hex().upper(),
            )
            return Response(ManeuverLogSerializer(log).data, status=502)

        # 6. Post-command verification read
        post_status, post_hot = _read_after_command(project)

        # 7. Persist new telemetry record
        with transaction.atomic():
            new_record = TelemetryRecord.objects.create(
                project=project,
                cycle_timestamp=timezone.now(),
                derived_status=post_status,
                **{k: v for k, v in post_hot.items() if v is not None},
            )
            post_snapshot = TelemetryRecordSerializer(new_record).data

        # 8. Write ManeuverLog
        log = ManeuverLog.objects.create(
            user=request.user,
            project=project,
            action=action,
            pre_status=pre_record.derived_status,
            pre_snapshot=pre_snapshot,
            post_status=post_status,
            post_snapshot=post_snapshot,
            result="success" if post_status != "ERROR" else "fail_verify",
            tx_frame=frame.hex().upper(),
            rx_frame=rx_frame.hex().upper() if rx_frame else "",
        )

        # 9. Set cooldown
        with contextlib.suppress(Exception):
            redis_client.set(cooldown_key, "1", ex=settings.MANEUVER_COOLDOWN_SECONDS)

        # 10. Broadcast WS event
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer:
            with contextlib.suppress(Exception):
                asyncio.run(
                    asyncio.wait_for(
                        channel_layer.group_send(
                            f"project_{project.id}",
                            {
                                "type": "maneuver.complete",
                                "project_id": project.id,
                                "result": log.result,
                                "by": request.user.username,
                                "post_status": post_status,
                            },
                        ),
                        timeout=CHANNEL_SEND_TIMEOUT_SECONDS,
                    )
                )

        return Response(ManeuverLogSerializer(log).data, status=200)

    finally:
        with contextlib.suppress(Exception):
            redis_client.delete(mutex_key)


class ManeuverAuditList(ListAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = ManeuverLogSerializer
    queryset = ManeuverLog.objects.all().order_by("-timestamp")

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if project := params.get("project"):
            queryset = queryset.filter(project_id=project)
        if user := params.get("user"):
            queryset = queryset.filter(user_id=user)
        if date_from := params.get("from"):
            queryset = queryset.filter(timestamp__gte=date_from)
        if date_to := params.get("to"):
            queryset = queryset.filter(timestamp__lte=date_to)
        return queryset
