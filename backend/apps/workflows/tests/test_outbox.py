"""Tests for OutboxService transactional enqueue, batch claim, and durable publishing."""
from unittest.mock import MagicMock, patch
import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.generations.models import Generation
from apps.organizations.models import Organization
from apps.products.models import WordPressProduct
from apps.projects.models import Project
from apps.workflows.models import OutboxEvent
from apps.workflows.services.outbox import OutboxService


@pytest.fixture
def outbox_setup(db):
    user = User.objects.create(email="worker@tersuite.com", password="Password123!")
    org = Organization.objects.create(name="Tersuite Lab", slug="tersuite-lab", created_by=user)
    prod = WordPressProduct.objects.create(organization=org, display_name="Plugin A", slug="plugin-a", created_by=user)
    proj = Project.objects.create(organization=org, product=prod, name="Proj A", slug="proj-a", created_by=user)
    gen = Generation.objects.create(organization=org, project=proj, prompt="Build WP plugin", created_by=user)
    return org, user, gen


@pytest.mark.django_db
class TestOutboxService:
    """Test suite for transactional outbox pattern and dispatch."""

    def test_enqueue_and_claim_batch(self, outbox_setup):
        org, user, gen = outbox_setup
        event = OutboxService.enqueue_event(
            organization=org,
            generation=gen,
            aggregate_type="generation",
            aggregate_id=str(gen.id),
            event_type="generation.status_changed",
            payload={"status": "BUILDING"},
        )
        assert event.id is not None
        assert event.published_at is None

        # Claim batch
        claimed = OutboxService.claim_batch(batch_size=10, claim_seconds=60)
        assert len(claimed) == 1
        assert claimed[0].id == event.id
        assert claimed[0].claim_token is not None
        assert claimed[0].claimed_until is not None

        # Second claim should skip already claimed row
        claimed2 = OutboxService.claim_batch(batch_size=10, claim_seconds=60)
        assert len(claimed2) == 0

    @patch("apps.workflows.services.outbox.GenerationEventPublisher.publish_durable")
    def test_publish_batch_success(self, mock_publish, outbox_setup):
        mock_publish.return_value = None
        org, user, gen = outbox_setup

        event = OutboxService.enqueue_event(
            organization=org,
            generation=gen,
            aggregate_type="generation",
            aggregate_id=str(gen.id),
            event_type="generation.status_changed",
            payload={"status": "BUILDING"},
        )

        published_count = OutboxService.publish_batch()
        assert published_count == 1

        event.refresh_from_db()
        assert event.published_at is not None
        assert event.publish_attempts == 1
        assert event.claim_token is None

    @patch("apps.workflows.services.outbox.GenerationEventPublisher.publish_durable")
    def test_publish_batch_failure_triggers_backoff(self, mock_publish, outbox_setup):
        mock_publish.side_effect = RuntimeError("Redis connection error")
        org, user, gen = outbox_setup

        event = OutboxService.enqueue_event(
            organization=org,
            generation=gen,
            aggregate_type="generation",
            aggregate_id=str(gen.id),
            event_type="generation.status_changed",
            payload={"status": "BUILDING"},
        )

        published_count = OutboxService.publish_batch()
        assert published_count == 0

        event.refresh_from_db()
        assert event.published_at is None
        assert event.publish_attempts == 1
        assert "Redis connection error" in event.last_error
        assert event.claim_token is None
        assert event.available_at > timezone.now()
