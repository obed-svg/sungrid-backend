from django.db import models
from django.utils import timezone

from apps.core.models import Project


class TelemetryRecord(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="telemetry")
    cycle_timestamp = models.DateTimeField(default=timezone.now)
    derived_status = models.CharField(max_length=10)

    ia = models.FloatField(null=True, blank=True)
    ib = models.FloatField(null=True, blank=True)
    ic = models.FloatField(null=True, blank=True)
    i_neutral = models.FloatField(null=True, blank=True)
    ua = models.FloatField(null=True, blank=True)
    ub = models.FloatField(null=True, blank=True)
    uc = models.FloatField(null=True, blank=True)
    ur = models.FloatField(null=True, blank=True)
    us = models.FloatField(null=True, blank=True)
    ut = models.FloatField(null=True, blank=True)
    freq = models.FloatField(null=True, blank=True)
    pf = models.FloatField(null=True, blank=True)
    p = models.FloatField(null=True, blank=True)
    q = models.FloatField(null=True, blank=True)
    breaker_close = models.BooleanField(null=True, blank=True)
    breaker_open = models.BooleanField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["project", "-cycle_timestamp"])]

    def __str__(self) -> str:
        return f"{self.project} @ {self.cycle_timestamp:%Y-%m-%d %H:%M:%S}"


class AnalogPoint(models.Model):
    telemetry = models.ForeignKey(TelemetryRecord, on_delete=models.CASCADE, related_name="analogs")
    label = models.CharField(max_length=20)
    value = models.FloatField()
    count_update = models.PositiveIntegerField()
    timestamp = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["telemetry", "label"])]

    def __str__(self) -> str:
        return f"{self.label}={self.value}"


class BinaryPoint(models.Model):
    telemetry = models.ForeignKey(TelemetryRecord, on_delete=models.CASCADE, related_name="binaries")
    label = models.CharField(max_length=50)
    value = models.BooleanField()
    count_update = models.PositiveIntegerField()
    timestamp = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["telemetry", "label"])]

    def __str__(self) -> str:
        return f"{self.label}={self.value}"
