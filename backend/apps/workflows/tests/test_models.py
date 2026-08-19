"""Tests for Workflows domain data models, constraints, and tenant validation."""
import uuid
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import User
from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation
from apps.organizations.models import Organization
from apps.products.models import WordPressProduct
from apps.projects.models import Project
from apps.workflows.enums import (
    AttemptStatus,
    CommandStatus,
    CommandType,
    DependencyType,
    LeaseReleaseReason,
    WorkflowRunStatus,
    WorkPackageStatus,
)
from apps.workflows.models import (
    OutboxEvent,
    WorkflowCommand,
    WorkflowRun,
    WorkPackage,
    WorkPackageAttempt,
    WorkPackageDependency,
    WorkPackageLease,
)


@pytest.fixture
def org_and_user(db):
    user = User.objects.create(email="architect@tersuite.com", password="Password123!")
    org = Organization.objects.create(name="Tersuite Lab", slug="tersuite-lab", created_by=user)
    prod = WordPressProduct.objects.create(organization=org, display_name="Plugin A", slug="plugin-a", created_by=user)
    proj = Project.objects.create(organization=org, product=prod, name="Proj A", slug="proj-a", created_by=user)
    gen = Generation.objects.create(organization=org, project=proj, prompt="Build WP plugin", created_by=user)
    return org, user, gen


@pytest.mark.django_db
class TestWorkflowModels:
    """Test suite for WorkflowRun, WorkPackage, Dependencies, Leases, and Outbox."""

    def test_workflow_run_creation(self, org_and_user):
        org, user, gen = org_and_user
        run = WorkflowRun.objects.create(
            organization=org,
            generation=gen,
            run_number=1,
            created_by=user,
        )
        assert run.status == WorkflowRunStatus.PENDING
        assert run.state_version == 0
        assert str(run).startswith(f"WorkflowRun #1 for Gen {gen.id}")

    def test_workflow_run_unique_run_number(self, org_and_user):
        org, user, gen = org_and_user
        WorkflowRun.objects.create(organization=org, generation=gen, run_number=1, created_by=user)
        with pytest.raises(IntegrityError):
            WorkflowRun.objects.create(organization=org, generation=gen, run_number=1, created_by=user)

    def test_work_package_creation_and_key_unique(self, org_and_user):
        org, user, gen = org_and_user
        run = WorkflowRun.objects.create(organization=org, generation=gen, run_number=1, created_by=user)
        pkg = WorkPackage.objects.create(
            organization=org,
            workflow_run=run,
            key="arch_blueprint",
            name="Architecture Blueprint",
            priority=100,
            created_by=user,
        )
        assert pkg.status == WorkPackageStatus.PENDING
        assert str(pkg) == "Package 'arch_blueprint' (Architecture Blueprint) [PENDING]"

        # Duplicate key in same run must fail
        with pytest.raises(IntegrityError):
            WorkPackage.objects.create(
                organization=org,
                workflow_run=run,
                key="arch_blueprint",
                name="Duplicate Key",
                created_by=user,
            )

    def test_work_package_dependency_creation(self, org_and_user):
        org, user, gen = org_and_user
        run = WorkflowRun.objects.create(organization=org, generation=gen, run_number=1, created_by=user)
        p1 = WorkPackage.objects.create(organization=org, workflow_run=run, key="pkg_1", name="Task 1", created_by=user)
        p2 = WorkPackage.objects.create(organization=org, workflow_run=run, key="pkg_2", name="Task 2", created_by=user)

        dep = WorkPackageDependency.objects.create(
            workflow_run=run,
            predecessor=p1,
            successor=p2,
            dependency_type=DependencyType.HARD,
        )
        assert str(dep) == "Dependency: pkg_1 -> pkg_2 (HARD)"

        # Duplicate edge must fail
        with pytest.raises(IntegrityError):
            WorkPackageDependency.objects.create(
                workflow_run=run,
                predecessor=p1,
                successor=p2,
            )

    def test_work_package_lease_active_constraint(self, org_and_user):
        org, user, gen = org_and_user
        run = WorkflowRun.objects.create(organization=org, generation=gen, run_number=1, created_by=user)
        pkg = WorkPackage.objects.create(organization=org, workflow_run=run, key="pkg_1", name="Task 1", created_by=user)
        attempt1 = WorkPackageAttempt.objects.create(work_package=pkg, attempt_number=1, worker_id="worker_1")

        now = timezone.now()
        expires = now + timezone.timedelta(seconds=60)

        lease1 = WorkPackageLease.objects.create(
            work_package=pkg,
            attempt=attempt1,
            worker_id="worker_1",
            acquired_at=now,
            heartbeat_at=now,
            expires_at=expires,
        )
        assert not lease1.is_expired(now)

        # Creating a second unreleased lease on same package fails unique active constraint
        attempt2 = WorkPackageAttempt.objects.create(work_package=pkg, attempt_number=2, worker_id="worker_2")
        from django.db import transaction
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                WorkPackageLease.objects.create(
                    work_package=pkg,
                    attempt=attempt2,
                    worker_id="worker_2",
                    acquired_at=now,
                    heartbeat_at=now,
                    expires_at=expires,
                )

        # Release first lease
        lease1.released_at = timezone.now()
        lease1.release_reason = LeaseReleaseReason.COMPLETED
        lease1.save()

        # Now second lease can be created
        lease2 = WorkPackageLease.objects.create(
            work_package=pkg,
            attempt=attempt2,
            worker_id="worker_2",
            acquired_at=now,
            heartbeat_at=now,
            expires_at=expires,
        )
        assert lease2.id is not None

    def test_outbox_event_creation(self, org_and_user):
        org, user, gen = org_and_user
        event = OutboxEvent.objects.create(
            organization=org,
            generation=gen,
            aggregate_type="generation",
            aggregate_id=str(gen.id),
            event_type="generation.status_changed",
            payload={"status": "BUILDING"},
        )
        assert event.published_at is None
        assert event.publish_attempts == 0
        assert "PENDING" in str(event)
