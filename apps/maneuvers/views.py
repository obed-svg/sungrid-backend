from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from apps.core.models import Project
from apps.core.permissions import IsOperator, IsSuperAdmin
from apps.maneuvers.models import ManeuverLog
from apps.maneuvers.serializers import ManeuverActionSerializer, ManeuverLogSerializer
from apps.telemetry.models import TelemetryRecord
from apps.telemetry.serializers import TelemetryRecordSerializer

REQUIRED_STATUS = {"TRIP": "CLOSED", "CLOSE": "OPEN"}


@api_view(["POST"])
@permission_classes([IsOperator])
def maneuver_view(request, project_id):
    action_serializer = ManeuverActionSerializer(data=request.data)
    action_serializer.is_valid(raise_exception=True)
    action = action_serializer.validated_data["action"]
    project = get_object_or_404(Project, pk=project_id, enabled=True)
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

    # Hardware TCP execution is intentionally isolated for the worker/protocol layer.
    # Until real frames are wired, record an auditable guarded request as fail_tcp.
    log = ManeuverLog.objects.create(
        user=request.user,
        project=project,
        action=action,
        pre_status=pre_record.derived_status,
        pre_snapshot=pre_snapshot,
        post_status="",
        post_snapshot=None,
        result="fail_tcp",
        error_message="TCP control path not configured",
    )
    return Response(ManeuverLogSerializer(log).data, status=502)


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

