import asyncio
import contextlib
import signal
import threading
import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.models import Project
from apps.protocol.rwk35 import (
    AI_LABELS,
    BI_LABELS,
    build_read_class0,
    compute_derived_status,
    extract_hot_fields,
    flush_socket_async,
    parse_response,
    recv_solicited_async,
)
from apps.telemetry.models import AnalogPoint, BinaryPoint, TelemetryRecord

shutdown_event = threading.Event()
CHANNEL_SEND_TIMEOUT_SECONDS = 2


def _signal_handler(signum, frame):
    shutdown_event.set()


async def _safe_group_send(channel_layer, group: str, message: dict):
    await asyncio.wait_for(
        channel_layer.group_send(group, message),
        timeout=CHANNEL_SEND_TIMEOUT_SECONDS,
    )


async def poll_device(project: Project) -> list[dict]:
    """Async per-device poll: connect, read class 0."""
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(str(project.ip), project.port),
        timeout=5,
    )
    try:
        await flush_socket_async(reader, 0.5)

        # Read class 0 (1 retry on empty)
        points = []
        for attempt in range(2):
            writer.write(
                build_read_class0(
                    project.master_id, project.outstation_id, seq=attempt + 1
                )
            )
            await writer.drain()
            rx_time = timezone.now()
            resp = await recv_solicited_async(reader, timeout=10)
            if resp:
                pts = parse_response(resp, rx_time)
                if pts:
                    points = pts
                    break
            await flush_socket_async(reader, 0.5)

        return points
    finally:
        writer.close()
        await writer.wait_closed()


def persist_points(project: Project, points: list[dict]) -> TelemetryRecord:
    """Persist points to DB and return the telemetry record."""
    online_analogs = [
        p for p in points if p.get("quality_online") and p["id"] in AI_LABELS
    ]
    online_binaries = [
        p for p in points if p.get("quality_online") and p["id"] in BI_LABELS
    ]

    hot = extract_hot_fields(points)
    derived_status = compute_derived_status(hot)

    with transaction.atomic():
        rec = TelemetryRecord.objects.create(
            project=project,
            cycle_timestamp=timezone.now(),
            derived_status=derived_status,
            **{k: v for k, v in hot.items() if v is not None},
        )
        AnalogPoint.objects.bulk_create(
            [
                AnalogPoint(
                    telemetry=rec,
                    label=AI_LABELS[p["id"]],
                    value=p["value"],
                    count_update=p.get("count_update", 0),
                    timestamp=p["timestamp"],
                )
                for p in online_analogs
            ]
        )
        BinaryPoint.objects.bulk_create(
            [
                BinaryPoint(
                    telemetry=rec,
                    label=BI_LABELS[p["id"]],
                    value=p["value"],
                    count_update=p.get("count_update", 0),
                    timestamp=p["timestamp"],
                )
                for p in online_binaries
            ]
        )
    return rec


async def broadcast_telemetry(project: Project, rec: TelemetryRecord):
    """Broadcast a persisted telemetry record via Channels."""
    from channels.layers import get_channel_layer


    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            await _safe_group_send(
                channel_layer,
                f"project_{project.id}",
                {
                    "type": "telemetry.update",
                    "project_id": project.id,
                    "data": {
                        "id": rec.id,
                        "project": project.id,
                        "cycle_timestamp": rec.cycle_timestamp.isoformat(),
                        "derived_status": rec.derived_status,
                        "ia": rec.ia,
                        "ib": rec.ib,
                        "ic": rec.ic,
                        "i_neutral": rec.i_neutral,
                        "ua": rec.ua,
                        "ub": rec.ub,
                        "uc": rec.uc,
                        "ur": rec.ur,
                        "us": rec.us,
                        "ut": rec.ut,
                        "freq": rec.freq,
                        "pf": rec.pf,
                        "p": rec.p,
                        "q": rec.q,
                        "breaker_close": rec.breaker_close,
                        "breaker_open": rec.breaker_open,
                    },
                },
            )
            await _safe_group_send(
                channel_layer,
                "telemetry",
                {
                    "type": "telemetry.update",
                    "project_id": project.id,
                    "data": {
                        "id": rec.id,
                        "project": project.id,
                        "cycle_timestamp": rec.cycle_timestamp.isoformat(),
                        "derived_status": rec.derived_status,
                    },
                },
            )
        except Exception:
            pass  # Redis unavailable, skip broadcast


async def mark_offline(project: Project, exc: Exception):
    """Broadcast device offline event."""
    import contextlib

    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if channel_layer:
        with contextlib.suppress(Exception):
            await _safe_group_send(
                channel_layer,
                f"project_{project.id}",
                {
                    "type": "device.offline",
                    "project_id": project.id,
                    "reason": f"{exc.__class__.__name__}: {exc}",
                },
            )


class Command(BaseCommand):
    help = "Poll enabled reclosers via RWK35 DNP3 protocol (asyncio)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--interval", type=int, default=120)

    def _prune(self):
        from apps.workers.management.commands.prune_telemetry import Command as PruneCmd

        prune = PruneCmd()
        prune.handle(days=365)

    def handle(self, *args, **options):
        shutdown_event.clear()
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, _signal_handler)
            signal.signal(signal.SIGINT, _signal_handler)

        last_prune = None

        while not shutdown_event.is_set():
            cycle_start = time.monotonic()

            projects = list(Project.objects.filter(enabled=True))
            self.stdout.write(f"poll_reclosers cycle: {len(projects)} enabled project(s)")

            results = asyncio.run(self._poll_projects(projects))

            for project, result in zip(projects, results, strict=False):
                if isinstance(result, Exception):
                    self.stdout.write(
                        self.style.ERROR(
                            f"  {project.name}: poll failed – {result.__class__.__name__}: {result}"
                        )
                    )
                    asyncio.run(mark_offline(project, result))
                elif result:
                    rec = persist_points(project, result)
                    asyncio.run(broadcast_telemetry(project, rec))
                    analogs = [p for p in result if p.get("type") == "analog"]
                    binaries = [p for p in result if p.get("type") == "binary"]
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  {project.name}: {len(analogs)} analogs, {len(binaries)} binaries"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  {project.name}: no points received")
                    )

            # Daily prune
            if (
                not options["once"]
                and (last_prune is None or timezone.now() - last_prune > timedelta(days=1))
            ):
                self._prune()
                last_prune = timezone.now()

            if options["once"]:
                return

            elapsed = time.monotonic() - cycle_start
            sleep_time = max(0, options["interval"] - elapsed)
            shutdown_event.wait(sleep_time)

    async def _poll_projects(self, projects: list[Project]) -> list[list[dict] | Exception]:
        return await asyncio.gather(
            *[poll_device(p) for p in projects],
            return_exceptions=True,
        )
