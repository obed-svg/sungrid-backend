from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from apps.core.models import Project
from apps.core.permissions import IsViewer
from apps.telemetry.models import TelemetryRecord
from apps.telemetry.serializers import (
    AnalogPointSerializer,
    BinaryPointSerializer,
    TelemetryRecordSerializer,
)

STALENESS_MINUTES = 6


@api_view(["GET"])
@permission_classes([IsViewer])
def latest(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    record = TelemetryRecord.objects.filter(project=project).order_by("-cycle_timestamp").first()
    if record is None:
        return Response({"detail": "no telemetry yet"}, status=404)
    cutoff = timezone.now() - timedelta(minutes=STALENESS_MINUTES)
    if record.cycle_timestamp < cutoff:
        return Response({"detail": "stale"}, status=404)
    return Response(TelemetryRecordSerializer(record).data)


class HistoryView(ListAPIView):
    permission_classes = [IsViewer]
    serializer_class = TelemetryRecordSerializer

    def get_queryset(self):
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])
        queryset = TelemetryRecord.objects.filter(project=project).order_by("-cycle_timestamp")
        date_from = self.request.query_params.get("from")
        date_to = self.request.query_params.get("to")
        if date_from:
            queryset = queryset.filter(cycle_timestamp__gte=date_from)
        if date_to:
            queryset = queryset.filter(cycle_timestamp__lte=date_to)
        return queryset


@api_view(["GET"])
@permission_classes([IsViewer])
def points_detail(request, project_id, rec_id):
    record = get_object_or_404(TelemetryRecord, pk=rec_id, project_id=project_id)
    return Response(
        {
            "analogs": AnalogPointSerializer(record.analogs.all(), many=True).data,
            "binaries": BinaryPointSerializer(record.binaries.all(), many=True).data,
        }
    )

