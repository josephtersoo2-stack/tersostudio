"""Django Channels consumers for live agent event streaming."""
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from .events import NormalizedEvent, EventType

logger = logging.getLogger("tersuite")


class EventStreamConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for streaming normalized agent & generation events."""

    async def connect(self):
        # Extract channel identifier from URL kwargs, default to 'global'
        self.channel_identifier = self.scope["url_route"]["kwargs"].get(
            "channel_name", "global"
        )
        self.room_group_name = f"events_{self.channel_identifier}"

        # Join the channel layer group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        # Send initial connected ack
        ack_event = NormalizedEvent(
            event_type=EventType.SYSTEM_PING,
            payload={
                "message": "Connected to Tersuite realtime event stream.",
                "channel": self.channel_identifier,
            },
        )
        await self.send_json(ack_event.to_dict())

    async def disconnect(self, close_code):
        # Leave the channel layer group
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive_json(self, content):
        """Handle incoming client messages (e.g. client pings or subscriptions)."""
        msg_type = content.get("type", "ping")
        if msg_type == "ping":
            pong = NormalizedEvent(
                event_type=EventType.SYSTEM_PING,
                payload={"pong": True},
            )
            await self.send_json(pong.to_dict())

    async def broadcast_event(self, event):
        """Handler for group messages forwarded from channel layer."""
        # 'event' dictionary contains 'data'
        event_data = event.get("data", {})
        await self.send_json(event_data)
