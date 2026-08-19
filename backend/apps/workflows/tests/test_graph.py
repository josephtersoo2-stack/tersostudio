"""Tests for WorkflowGraphService DAG validation, cycle detection, and topological sorting."""
import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.generations.models import Generation
from apps.organizations.models import Organization
from apps.products.models import WordPressProduct
from apps.projects.models import Project
from apps.workflows.enums import DependencyType, WorkflowRunStatus
from apps.workflows.models import WorkflowRun, WorkPackage
from apps.workflows.services.graph import WorkflowGraphService


@pytest.fixture
def run_and_packages(db):
    user = User.objects.create(email="architect@tersuite.com", password="Password123!")
    org = Organization.objects.create(name="Tersuite Lab", slug="tersuite-lab", created_by=user)
    prod = WordPressProduct.objects.create(organization=org, display_name="Plugin A", slug="plugin-a", created_by=user)
    proj = Project.objects.create(organization=org, product=prod, name="Proj A", slug="proj-a", created_by=user)
    gen = Generation.objects.create(organization=org, project=proj, prompt="Build WP plugin", created_by=user)
    run = WorkflowRun.objects.create(organization=org, generation=gen, run_number=1, created_by=user)

    p1 = WorkPackage.objects.create(organization=org, workflow_run=run, key="pkg_1", name="Task 1", priority=100, created_by=user)
    p2 = WorkPackage.objects.create(organization=org, workflow_run=run, key="pkg_2", name="Task 2", priority=90, created_by=user)
    p3 = WorkPackage.objects.create(organization=org, workflow_run=run, key="pkg_3", name="Task 3", priority=80, created_by=user)
    p4 = WorkPackage.objects.create(organization=org, workflow_run=run, key="pkg_4", name="Task 4", priority=70, created_by=user)

    return run, p1, p2, p3, p4


@pytest.mark.django_db
class TestWorkflowGraphService:
    """Tests for DAG edge validation, cycle prevention, and topological ordering."""

    def test_add_dependency_and_topological_sort(self, run_and_packages):
        run, p1, p2, p3, p4 = run_and_packages

        # Linear DAG: p1 -> p2 -> p3 -> p4
        WorkflowGraphService.add_dependency(p1, p2)
        WorkflowGraphService.add_dependency(p2, p3)
        WorkflowGraphService.add_dependency(p3, p4)

        order = WorkflowGraphService.topological_order(run)
        keys = [p.key for p in order]
        assert keys == ["pkg_1", "pkg_2", "pkg_3", "pkg_4"]

    def test_branching_dag_topological_sort(self, run_and_packages):
        run, p1, p2, p3, p4 = run_and_packages

        # Branching DAG: p1 -> p2, p1 -> p3; p2 -> p4, p3 -> p4
        WorkflowGraphService.add_dependency(p1, p2)
        WorkflowGraphService.add_dependency(p1, p3)
        WorkflowGraphService.add_dependency(p2, p4)
        WorkflowGraphService.add_dependency(p3, p4)

        order = WorkflowGraphService.topological_order(run)
        keys = [p.key for p in order]
        # p1 first, then p2 (higher priority 90) before p3 (priority 80), then p4
        assert keys == ["pkg_1", "pkg_2", "pkg_3", "pkg_4"]

    def test_self_dependency_rejected(self, run_and_packages):
        run, p1, p2, p3, p4 = run_and_packages
        with pytest.raises(ValidationError) as exc:
            WorkflowGraphService.add_dependency(p1, p1)
        assert exc.value.code == "self_dependency"

    def test_direct_cycle_rejected(self, run_and_packages):
        run, p1, p2, p3, p4 = run_and_packages
        WorkflowGraphService.add_dependency(p1, p2)
        with pytest.raises(ValidationError) as exc:
            WorkflowGraphService.add_dependency(p2, p1)
        assert exc.value.code == "cyclic_dependency"

    def test_multi_node_cycle_rejected(self, run_and_packages):
        run, p1, p2, p3, p4 = run_and_packages
        WorkflowGraphService.add_dependency(p1, p2)
        WorkflowGraphService.add_dependency(p2, p3)
        WorkflowGraphService.add_dependency(p3, p4)
        with pytest.raises(ValidationError) as exc:
            WorkflowGraphService.add_dependency(p4, p1)
        assert exc.value.code == "cyclic_dependency"

    def test_modifying_frozen_graph_rejected(self, run_and_packages):
        run, p1, p2, p3, p4 = run_and_packages
        WorkflowGraphService.freeze_graph(run)
        assert run.status == WorkflowRunStatus.RUNNING

        with pytest.raises(ValidationError) as exc:
            WorkflowGraphService.add_dependency(p1, p2)
        assert exc.value.code == "graph_frozen"
