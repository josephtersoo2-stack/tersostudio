"""Tests for realtime event schemas and WebSocket streaming consumers."""
import unittest
from django.test import TestCase
from channels.testing import WebsocketCommunicator
from apps.realtime.events import NormalizedEvent, EventType
from apps.realtime.consumers import EventStreamConsumer


class NormalizedEventTests(unittest.TestCase):
    """Test suite for NormalizedEvent serialization contracts."""

    def test_event_serialization(self):
        """Verify event is properly converted to dictionary."""
        event = NormalizedEvent(
            event_type=EventType.AGENT_THINKING,
            generation_id="gen-12345",
            agent_run_id="run-9876",
            payload={"thought": "Analyzing WordPress hooks..."},
        )
        data = event.to_dict()

        self.assertEqual(data["event_type"], EventType.AGENT_THINKING)
        self.assertEqual(data["generation_id"], "gen-12345")
        self.assertEqual(data["agent_run_id"], "run-9876")
        self.assertEqual(data["payload"]["thought"], "Analyzing WordPress hooks...")
        self.assertIn("event_id", data)
        self.assertIn("timestamp", data)

    def test_event_deserialization(self):
        """Verify event can be reconstituted from dictionary."""
        raw_dict = {
            "event_id": "evt-001",
            "event_type": EventType.TASK_COMPLETED,
            "generation_id": "gen-555",
            "agent_run_id": "run-444",
            "timestamp": "2026-08-14T20:00:00Z",
            "payload": {"status": "success"},
        }
        event = NormalizedEvent.from_dict(raw_dict)

        self.assertEqual(event.event_id, "evt-001")
        self.assertEqual(event.event_type, EventType.TASK_COMPLETED)
        self.assertEqual(event.payload["status"], "success")


class WebSocketStreamingTests(TestCase):
    """Test suite for WebSocket channel consumer."""

    async def test_websocket_connect_and_ping(self):
        """Verify consumer accepts connection, sends greeting, and responds to ping."""
        communicator = WebsocketCommunicator(
            EventStreamConsumer.as_asgi(),
            "/ws/v1/events/gen-test-123/",
        )
        communicator.scope["url_route"] = {"kwargs": {"channel_name": "gen-test-123"}}

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # 1. First message from server is connection greeting
        response = await communicator.receive_json_from()
        self.assertEqual(response["event_type"], EventType.SYSTEM_PING)
        self.assertEqual(response["payload"]["channel"], "gen-test-123")

        # 2. Send ping to consumer
        await communicator.send_json_to({"type": "ping"})
        pong_response = await communicator.receive_json_from()
        self.assertEqual(pong_response["event_type"], EventType.SYSTEM_PING)
        self.assertTrue(pong_response["payload"]["pong"])

        await communicator.disconnect()
