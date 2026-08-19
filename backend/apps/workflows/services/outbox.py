"""Transactional Outbox service ensuring durable, at-least-once event delivery to Channels."""
from datetime import timedelta
import logging
from typing import Any, Dict, List, Optional
import uuid
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.organizations.models import Organization
from apps.realtime.event_publisher import GenerationEventPublisher
from apps.realtime.events import NormalizedEvent
from apps.workflows.models import OutboxEvent

logger = logging.getLogger("tersuite.outbox")


class OutboxService:
    """Service handling transactional outbox recording, batch claiming, and publishing."""

    @classmethod
    def enqueue_event(
        cls,
        organization: Organization,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
        generation: Optional[Any] = None,
        event_id: Optional[uuid.UUID] = None,
        now=None,
    ) -> OutboxEvent:
        """Enqueue an event in the transactional outbox table within current transaction."""
        current_time = now or timezone.now()
        sanitized = sanitize_payload_for_json(payload)
        outbox_event = OutboxEvent.objects.create(
            event_id=event_id or uuid.uuid4(),
            organization=organization,
            generation=generation,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            event_type=event_type,
            payload=sanitized,
            occurred_at=current_time,
            available_at=current_time,
        )
        return outbox_event

    @classmethod
    def claim_batch(
        cls,
        batch_size: Optional[int] = None,
        claim_seconds: Optional[int] = None,
        now=None,
    ) -> List[OutboxEvent]:
        """Claim a batch of unpublished available events with exclusive skip-locked row locks."""
        current_time = now or timezone.now()
        limit = batch_size or getattr(settings, "OUTBOX_BATCH_SIZE", 100)
        duration = claim_seconds or getattr(settings, "OUTBOX_CLAIM_SECONDS", 60)
        token = uuid.uuid4()
        expires = current_time + timedelta(seconds=duration)

        with transaction.atomic():
            events = list(
                OutboxEvent.objects.filter(
                    published_at__isnull=True,
                    available_at__lte=current_time,
                )
                .filter(
                    models_q_unclaimed(current_time)
                )
                .order_by("available_at", "id")
                .select_for_update(skip_locked=True)[:limit]
            )

            for event in events:
                event.claim_token = token
                event.claimed_until = expires
                event.save(update_fields=["claim_token", "claimed_until", "updated_at"])

            return events

    @classmethod
    def publish_batch(
        cls,
        batch_size: Optional[int] = None,
        claim_seconds: Optional[int] = None,
        now=None,
    ) -> int:
        """Claim and publish a batch of events through GenerationEventPublisher."""
        current_time = now or timezone.now()
        events = cls.claim_batch(batch_size=batch_size, claim_seconds=claim_seconds, now=current_time)
        if not events:
            return 0

        publisher = GenerationEventPublisher()
        published_count = 0

        for event in events:
            norm_event = NormalizedEvent(
                event_id=str(event.event_id),
                event_type=event.event_type,
                payload=event.payload,
                generation_id=str(event.generation_id) if event.generation_id else None,
                timestamp=event.occurred_at.isoformat(),
            )

            try:
                publisher.publish_durable(norm_event)
                # Ack success
                with transaction.atomic():
                    OutboxEvent.objects.filter(
                        id=event.id,
                        claim_token=event.claim_token,
                    ).update(
                        published_at=timezone.now(),
                        claim_token=None,
                        claimed_until=None,
                        publish_attempts=event.publish_attempts + 1,
                        last_error="",
                        updated_at=timezone.now(),
                    )
                published_count += 1
            except Exception as exc:
                logger.warning("Failed to publish outbox event %s: %s", event.event_id, exc)
                # Record failure & backoff
                attempts = event.publish_attempts + 1
                backoff_secs = min(30 * (2 ** (attempts - 1)), 600)
                with transaction.atomic():
                    OutboxEvent.objects.filter(
                        id=event.id,
                        claim_token=event.claim_token,
                    ).update(
                        publish_attempts=attempts,
                        last_error=str(exc)[:500],
                        claim_token=None,
                        claimed_until=None,
                        available_at=timezone.now() + timedelta(seconds=backoff_secs),
                        updated_at=timezone.now(),
                    )

        return published_count


def models_q_unclaimed(current_time):
    from django.db.models import Q
    return Q(claimed_until__isnull=True) | Q(claimed_until__lte=current_time)


def sanitize_payload_for_json(obj: Any) -> Any:
    """Recursively convert UUIDs, datetimes, and nested containers to JSON-safe primitives."""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): sanitize_payload_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_payload_for_json(v) for v in obj]
    return obj
