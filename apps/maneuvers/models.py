from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import Project, User


class ManeuverLog(models.Model):
    ACTION_CHOICES = [("TRIP", "TRIP"), ("CLOSE", "CLOSE")]
    RESULT_CHOICES = [
        ("success", "Success"),
        ("fail_guard", "Fail (guard)"),
        ("fail_tcp", "Fail (TCP)"),
        ("fail_verify", "Fail (verify)"),
        ("fail_locked", "Fail (mutex)"),
        ("fail_cooldown", "Fail (cooldown)"),
        ("fail_tunnel", "Fail (tunnel)"),
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="maneuvers")
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="maneuvers")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    pre_status = models.CharField(max_length=10)
    pre_snapshot = models.JSONField()
    post_status = models.CharField(max_length=10, blank=True, default="")
    post_snapshot = models.JSONField(null=True, blank=True)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    error_message = models.TextField(blank=True)
    tx_frame = models.CharField(max_length=200, blank=True)
    rx_frame = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["project", "-timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.timestamp:%Y-%m-%d %H:%M:%S} {self.project} {self.action} {self.result}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("ManeuverLog is append-only; existing entries cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("ManeuverLog is append-only; entries cannot be deleted.")
