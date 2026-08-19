"""Real multi-threaded PostgreSQL concurrency tests for durable workflow kernel."""
import threading
from typing import List
import pytest
from django.db import connection, close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation, GenerationMilestone, GenerationStep
from apps.generations.services.state_machine import GenerationStateMachine
from apps.organizations.models import Organization
from apps.products.models import WordPressProduct
from apps.projects.models import Project
from apps.workflows.enums import CommandType, WorkflowRunStatus, WorkPackageStatus
from apps.workflows.models import (
    OutboxEvent,
    WorkflowCommand,
    WorkflowRun,
    WorkPackage,
    WorkPackageAttempt,
    WorkPackageLease,
)
from apps.workflows.services.commands import WorkflowCommandService
from apps.workflows.services.outbox import OutboxService
from apps.workflows.services.scheduler import WorkflowSchedulerService


class WorkflowConcurrencyTests(TransactionTestCase):
    """Test suite asserting PostgreSQL concurrency safety across workers, commands, outbox, and transitions."""

    databases = {"default"}

    def setUp(self):
        super().setUp()
        self.user = User.objects.create(email="concurrent@tersuite.com", password="Password123!")
        self.org = Organization.objects.create(name="Concurrent Lab", slug="concurrent-lab", created_by=self.user)
        self.prod = WordPressProduct.objects.create(organization=self.org, display_name="Prod", slug="prod", created_by=self.user)
        self.proj = Project.objects.create(organization=self.org, product=self.prod, name="Proj", slug="proj", created_by=self.user)
        self.gen = Generation.objects.create(
            organization=self.org,
            project=self.proj,
            prompt="Build WP Plugin",
            status=GenerationStatus.BUILDING,
            created_by=self.user,
        )
        self.milestone = GenerationMilestone.objects.create(generation=self.gen, name="Milestone 1", sequence=1)
        self.step = GenerationStep.objects.create(
            generation=self.gen,
            milestone=self.milestone,
            step_number=1,
            name="Architecture Step",
            agent_role="architect",
        )
        self.run = WorkflowRun.objects.create(
            organization=self.org,
            generation=self.gen,
            run_number=1,
            status=WorkflowRunStatus.RUNNING,
            created_by=self.user,
        )

    def test_concurrent_package_claim_single_winner(self):
        """Two simultaneous worker threads attempt to claim the exact same READY package."""
        pkg = WorkPackage.objects.create(
            organization=self.org,
            workflow_run=self.run,
            generation_step=self.step,
            key="concurrent_pkg",
            name="Concurrent Task",
            status=WorkPackageStatus.READY,
            priority=100,
            ready_at=timezone.now(),
            created_by=self.user,
        )

        barrier = threading.Barrier(2)
        results = [None, None]
        errors: List[Exception] = []

        def worker_claim(worker_idx: int, worker_name: str):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                claim = WorkflowSchedulerService.claim_next(
                    worker_id=worker_name,
                    workflow_run_id=self.run.id,
                )
                results[worker_idx] = claim
            except Exception as e:
                errors.append(e)
            finally:
                close_old_connections()

        t1 = threading.Thread(target=worker_claim, args=(0, "worker_alpha"))
        t2 = threading.Thread(target=worker_claim, args=(1, "worker_beta"))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0, f"Encountered thread errors: {errors}"
        # Exactly one worker wins
        winners = [r for r in results if r is not None]
        assert len(winners) == 1, "Exactly one worker must successfully claim the package"

        winner_pkg, winner_attempt, winner_lease = winners[0]
        assert winner_pkg.id == pkg.id

        pkg.refresh_from_db()
        assert pkg.attempt_count == 1
        assert pkg.status == WorkPackageStatus.RUNNING
        assert WorkPackageLease.objects.filter(work_package=pkg, released_at__isnull=True).count() == 1
        assert WorkPackageAttempt.objects.filter(work_package=pkg).count() == 1

    def test_concurrent_same_idempotency_key_safe(self):
        """Two simultaneous threads execute identical command with identical idempotency key."""
        idempotency_key = "concurrent_key_001"
        barrier = threading.Barrier(2)
        results = [None, None]
        errors: List[Exception] = []

        def execute_cmd(idx: int):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                res = WorkflowCommandService.execute_command(
                    generation=self.gen,
                    command_type=CommandType.PAUSE,
                    idempotency_key=idempotency_key,
                    payload={"reason": "Concurrent pause"},
                    actor=self.user,
                )
                results[idx] = res
            except Exception as e:
                errors.append(e)
            finally:
                close_old_connections()

        t1 = threading.Thread(target=execute_cmd, args=(0,))
        t2 = threading.Thread(target=execute_cmd, args=(1,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert results[0] is not None
        assert results[1] is not None

        # Both returned same command ID
        assert results[0]["command_id"] == results[1]["command_id"]
        # Exactly one command record created
        assert WorkflowCommand.objects.filter(organization=self.org, idempotency_key=idempotency_key).count() == 1

        self.gen.refresh_from_db()
        assert self.gen.status == GenerationStatus.PAUSED

    def test_concurrent_outbox_claims_are_disjoint(self):
        """Two dispatcher threads claim batches of outbox events concurrently."""
        events = []
        for i in range(10):
            ev = OutboxService.enqueue_event(
                organization=self.org,
                generation=self.gen,
                aggregate_type="work_package",
                aggregate_id=str(self.gen.id),
                event_type="work_package.ready",
                payload={"index": i},
            )
            events.append(ev)

        barrier = threading.Barrier(2)
        claimed_ids_t1: List[str] = []
        claimed_ids_t2: List[str] = []
        errors: List[Exception] = []

        def claim_dispatcher(out_list: List[str]):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                batch = OutboxService.claim_batch(batch_size=5, claim_seconds=60)
                out_list.extend([str(e.id) for e in batch])
            except Exception as e:
                errors.append(e)
            finally:
                close_old_connections()

        t1 = threading.Thread(target=claim_dispatcher, args=(claimed_ids_t1,))
        t2 = threading.Thread(target=claim_dispatcher, args=(claimed_ids_t2,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        # Assert no overlapping event IDs
        overlap = set(claimed_ids_t1).intersection(set(claimed_ids_t2))
        assert len(overlap) == 0, f"Disjoint claim violation: overlapping IDs {overlap}"
        assert len(claimed_ids_t1) + len(claimed_ids_t2) == 10

    def test_concurrent_generation_transitions_serialized_safely(self):
        """Two concurrent operations attempt transitions on same generation."""
        self.gen.status = GenerationStatus.APPROVED
        self.gen.state_version = 5
        self.gen.next_transition_sequence = 6
        self.gen.save()

        barrier = threading.Barrier(2)
        results = [None, None]
        errors: List[Exception] = []

        def do_transition(idx: int):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                gen = GenerationStateMachine.transition(
                    generation=self.gen,
                    target_status=GenerationStatus.SCHEDULED,
                    reason="Scheduled by concurrent worker",
                )
                results[idx] = gen
            except Exception as e:
                errors.append(e)
            finally:
                close_old_connections()

        t1 = threading.Thread(target=do_transition, args=(0,))
        t2 = threading.Thread(target=do_transition, args=(1,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.gen.refresh_from_db()
        assert self.gen.status == GenerationStatus.SCHEDULED
        # Exactly one transition from APPROVED to SCHEDULED was recorded
        transitions = list(self.gen.state_transitions.filter(to_status=GenerationStatus.SCHEDULED))
        assert len(transitions) == 1
        assert self.gen.state_version == 6
