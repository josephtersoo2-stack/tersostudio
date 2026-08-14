"""End-to-end integration test validating Phase 1 system capabilities."""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from runtime.adapters.mock_adapter import MockAgentRuntime
from runtime.interfaces.session import SessionConfig


class Phase1SystemIntegrationTests(TestCase):
    """End-to-end integration test of Phase 1 foundation."""

    def setUp(self):
        self.client = APIClient()
        self.runtime = MockAgentRuntime()

    def test_complete_foundation_flow(self):
        """Test full sequence: Liveness -> User Register -> Auth Check -> Agent Runtime Dispatch."""
        # 1. Health Probe
        health_resp = self.client.get(reverse("health_live"))
        self.assertEqual(health_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(health_resp.json()["status"], "alive")

        # 2. User Registration
        user_payload = {
            "email": "lead.architect@tersuite.com",
            "password": "ProductionPassword2026!",
            "first_name": "Tersoo",
            "last_name": "Joseph",
        }
        reg_resp = self.client.post(reverse("auth_register"), user_payload)
        self.assertEqual(reg_resp.status_code, status.HTTP_201_CREATED)
        token = reg_resp.json()["token"]
        self.assertIsNotNone(token)

        # 3. Authenticated Identity Query
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        me_resp = self.client.get(reverse("auth_me"))
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.json()["user"]["email"], "lead.architect@tersuite.com")

        # 4. Agent Runtime Session & Task Execution
        session_config = SessionConfig(
            generation_id="gen-system-integ-001",
            agent_run_id="run-system-integ-001",
            model="anthropic/claude-sonnet-4-5-20250929",
            system_prompt="You are a WordPress core engineer.",
        )
        session = self.runtime.create_session(session_config)
        self.assertIsNotNone(session.session_id)

        task_result = self.runtime.send_task(
            session_id=session.session_id,
            prompt="Initialize WordPress custom post type architecture.",
        )
        self.assertTrue(task_result.success)

        events = self.runtime.observe_events(session.session_id)
        self.assertTrue(len(events) >= 3)
        self.assertEqual(events[0].generation_id, "gen-system-integ-001")

        # 5. Clean teardown
        self.runtime.close_session(session.session_id)
