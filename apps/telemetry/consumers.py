"""Django Channels WebSocket consumer for telemetry updates."""

import json

from channels.generic.websocket import AsyncWebsocketConsumer


class TelemetryConsumer(AsyncWebsocketConsumer):
    """Broadcasts telemetry updates and maneuver events to connected clients.

    Routes:
        /ws/telemetry/          — global subscription (all projects)
        /ws/telemetry/<pid>/    — per-project subscription
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.project_id = self.scope["url_route"]["kwargs"].get("project_id")
        self.groups = []

        if self.project_id is not None:
            group = f"project_{self.project_id}"
            await self.channel_layer.group_add(group, self.channel_name)
            self.groups.append(group)
        else:
            await self.channel_layer.group_add("telemetry", self.channel_name)
            self.groups.append("telemetry")

        await self.accept()

    async def disconnect(self, close_code):
        for group in getattr(self, "groups", []):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # No client-initiated messages expected
        pass

    async def telemetry_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "telemetry.update",
                    "project_id": event["project_id"],
                    "data": event["data"],
                }
            )
        )

    async def maneuver_complete(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "maneuver.complete",
                    "project_id": event["project_id"],
                    "result": event["result"],
                    "by": event["by"],
                    "post_status": event.get("post_status", ""),
                }
            )
        )

    async def device_offline(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "device.offline",
                    "project_id": event["project_id"],
                    "reason": event.get("reason", "timeout"),
                }
            )
        )
