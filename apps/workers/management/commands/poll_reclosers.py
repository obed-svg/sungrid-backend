import time

from django.core.management.base import BaseCommand

from apps.core.models import Project


class Command(BaseCommand):
    help = "Poll enabled reclosers. Protocol integration is intentionally isolated in apps.protocol."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--interval", type=int, default=120)

    def handle(self, *args, **options):
        while True:
            count = Project.objects.filter(enabled=True).count()
            self.stdout.write(f"poll_reclosers cycle: {count} enabled project(s)")
            if options["once"]:
                return
            time.sleep(options["interval"])

