from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_VIEWER = "viewer"
    ROLE_OPERATOR = "operator"
    ROLE_SUPERADMIN = "superadmin"
    ROLE_CHOICES = [
        (ROLE_VIEWER, "Viewer"),
        (ROLE_OPERATOR, "Operator"),
        (ROLE_SUPERADMIN, "SuperAdmin"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_VIEWER)

    def save(self, *args, **kwargs):
        if self.is_superuser and self.role == self.ROLE_VIEWER:
            self.role = self.ROLE_SUPERADMIN
        super().save(*args, **kwargs)


class Project(models.Model):
    name = models.CharField(max_length=100, unique=True)
    ip = models.GenericIPAddressField()
    port = models.PositiveIntegerField(default=8000)
    master_id = models.PositiveSmallIntegerField(default=2)
    outstation_id = models.PositiveSmallIntegerField(default=1)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.ip}:{self.port})"

