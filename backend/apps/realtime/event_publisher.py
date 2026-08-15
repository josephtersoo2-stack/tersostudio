"""Single choke point for pushing NormalizedEvents onto Django Channels.

The audit found `group_send` was never called anywhere — the Channels
transport (consumers.py, routing.py) existed with nothing producing into
it. This is that producer.

Every future event source (this execution pipeline, and later the
multi-agent coordinator, security scans, packaging, etc.) should publish
through GenerationEventPublisher rather than calling
channel_layer.group_send directly, so the event contract stays owned in
one place — see AGENTS.md's realtime event normalization boundary.
"""
import asyncio
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .events import NormalizedEvent

logger = logging.getLogger("tersuite.realtime")


class GenerationEventPublisher:
    """Broadcasts NormalizedEvents to the Channels group for their generation.

    Groups are named `events_<generation_id>`, matching the
    `channel_name` URL kwarg that EventStreamConsumer.connect() joins
    (see routing.py: `ws/v1/events/<channel_name>/`). A client that opens
    `ws/v1/events/<generation_id>/` receives every event published here
    for that generation.
    """

    def __init__(self):
        self._channel_layer = get_channel_layer()

    def publish(self, event: NormalizedEvent) -> None:
        """Broadcast `event` to its generation's group.

        Never raises — a Redis/Channels hiccup must not take down agent
        execution. The AgentRun/GenerationStep rows are the source of
        truth; this is a best-effort side channel for live UI updates.
        Handles execution from synchronous threads and active event loops.
        """
        if self._channel_layer is None:
            logger.warning(
                "No channel layer configured; dropping event %s", event.event_type,
            )
            return

        if not event.generation_id:
            logger.warning(
                "Event %s has no generation_id; cannot route it to a group",
                event.event_type,
            )
            return

        group_name = f"events_{event.generation_id}"
        message = {"type": "broadcast_event", "data": event.to_dict()}

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                asyncio.ensure_future(
                    self._channel_layer.group_send(group_name, message),
                    loop=loop,
                )
            else:
                async_to_sync(self._channel_layer.group_send)(
                    group_name,
                    message,
                )
        except Exception:
            logger.exception(
                "Failed to publish event %s to group %s", event.event_type, group_name,
            )
