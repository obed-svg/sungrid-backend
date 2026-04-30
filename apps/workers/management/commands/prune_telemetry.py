from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.telemetry.models import TelemetryRecord


class Command(BaseCommand):
    help = "Prune TelemetryRecord rows older than retention period."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=365)

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        deleted, _ = TelemetryRecord.objects.filter(cycle_timestamp__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Pruned {deleted} telemetry objects older than {cutoff.isoformat()}"))

