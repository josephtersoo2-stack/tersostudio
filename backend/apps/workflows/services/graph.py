"""Workflow DAG graph validation, topological sorting, and dependency management."""
from collections import defaultdict, deque
from typing import List, Set
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.workflows.enums import DependencyType, WorkflowRunStatus
from apps.workflows.models import (
    WorkflowRun,
    WorkPackage,
    WorkPackageDependency,
)


class WorkflowGraphService:
    """Service managing work package DAG relationships and validation."""

    @classmethod
    def add_dependency(
        cls,
        predecessor: WorkPackage,
        successor: WorkPackage,
        dependency_type: str = DependencyType.HARD,
    ) -> WorkPackageDependency:
        """Add a directed dependency edge (predecessor -> successor) in the DAG.

        Raises:
            ValidationError: If graph is frozen, self-edge, cross-run, duplicate, or creates a cycle.
        """
        run = predecessor.workflow_run
        if run.status != WorkflowRunStatus.PENDING:
            raise ValidationError(
                f"Cannot modify workflow graph when run status is '{run.status}'. Graph is frozen.",
                code="graph_frozen",
            )

        if predecessor.id == successor.id:
            raise ValidationError(
                "A work package cannot depend on itself.",
                code="self_dependency",
            )

        if predecessor.workflow_run_id != successor.workflow_run_id:
            raise ValidationError(
                "Dependencies can only link work packages within the same workflow run.",
                code="cross_run_dependency",
            )

        with transaction.atomic():
            # Check existing dependencies for this run
            existing_deps = list(
                WorkPackageDependency.objects.filter(workflow_run=run)
                .values_list("predecessor_id", "successor_id")
            )

            # Check if adding (predecessor.id, successor.id) creates a cycle
            adj = defaultdict(list)
            for p_id, s_id in existing_deps:
                adj[p_id].append(s_id)
            adj[predecessor.id].append(successor.id)

            # Detect cycle using DFS
            visited: Set[int] = set()
            rec_stack: Set[int] = set()

            def has_cycle(node_id: int) -> bool:
                visited.add(node_id)
                rec_stack.add(node_id)
                for neighbor_id in adj.get(node_id, []):
                    if neighbor_id not in visited:
                        if has_cycle(neighbor_id):
                            return True
                    elif neighbor_id in rec_stack:
                        return True
                rec_stack.remove(node_id)
                return False

            all_nodes = set(adj.keys()) | {p for vals in adj.values() for p in vals}
            for n in all_nodes:
                if n not in visited:
                    if has_cycle(n):
                        raise ValidationError(
                            f"Adding dependency from '{predecessor.key}' to '{successor.key}' creates a cycle in the DAG.",
                            code="cyclic_dependency",
                        )

            dep, created = WorkPackageDependency.objects.get_or_create(
                workflow_run=run,
                predecessor=predecessor,
                successor=successor,
                defaults={"dependency_type": dependency_type},
            )
            if not created and dep.dependency_type != dependency_type:
                dep.dependency_type = dependency_type
                dep.save(update_fields=["dependency_type", "updated_at"])

            return dep

    @classmethod
    def validate_graph(cls, workflow_run: WorkflowRun) -> None:
        """Validate entire DAG for cycles and orphaned constraints.

        Raises:
            ValidationError: If cycle is detected.
        """
        packages = list(WorkPackage.objects.filter(workflow_run=workflow_run))
        pkg_ids = {p.id for p in packages}

        deps = list(
            WorkPackageDependency.objects.filter(workflow_run=workflow_run)
            .values_list("predecessor_id", "successor_id")
        )

        in_degree = {p_id: 0 for p_id in pkg_ids}
        adj = defaultdict(list)

        for p_id, s_id in deps:
            if p_id in pkg_ids and s_id in pkg_ids:
                adj[p_id].append(s_id)
                in_degree[s_id] = in_degree.get(s_id, 0) + 1

        # Kahn's algorithm
        queue = deque([p_id for p_id in pkg_ids if in_degree[p_id] == 0])
        visited_count = 0

        while queue:
            node_id = queue.popleft()
            visited_count += 1
            for neighbor_id in adj.get(node_id, []):
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)

        if visited_count != len(pkg_ids):
            raise ValidationError(
                "Circular dependency detected in workflow DAG.",
                code="cyclic_dependency",
            )

    @classmethod
    def topological_order(cls, workflow_run: WorkflowRun) -> List[WorkPackage]:
        """Return packages in a deterministic topological sort order (priority DESC, key ASC).

        Raises:
            ValidationError: If DAG contains cycles.
        """
        cls.validate_graph(workflow_run)

        packages_map = {
            p.id: p for p in WorkPackage.objects.filter(workflow_run=workflow_run)
        }
        deps = list(
            WorkPackageDependency.objects.filter(workflow_run=workflow_run)
            .values_list("predecessor_id", "successor_id")
        )

        in_degree = {p_id: 0 for p_id in packages_map}
        adj = defaultdict(list)

        for p_id, s_id in deps:
            if p_id in packages_map and s_id in packages_map:
                adj[p_id].append(s_id)
                in_degree[s_id] = in_degree.get(s_id, 0) + 1

        # Ready queue sorted deterministically by (priority DESC, key ASC)
        ordered: List[WorkPackage] = []
        ready_ids = [p_id for p_id, deg in in_degree.items() if deg == 0]
        ready_ids.sort(key=lambda pid: (-packages_map[pid].priority, packages_map[pid].key))

        while ready_ids:
            # Pop highest priority
            curr_id = ready_ids.pop(0)
            ordered.append(packages_map[curr_id])

            new_ready = []
            for nxt_id in adj.get(curr_id, []):
                in_degree[nxt_id] -= 1
                if in_degree[nxt_id] == 0:
                    new_ready.append(nxt_id)

            if new_ready:
                ready_ids.extend(new_ready)
                ready_ids.sort(key=lambda pid: (-packages_map[pid].priority, packages_map[pid].key))

        return ordered

    @classmethod
    def freeze_graph(cls, workflow_run: WorkflowRun) -> None:
        """Validate DAG and transition workflow run from PENDING to RUNNING."""
        cls.validate_graph(workflow_run)
        if workflow_run.status == WorkflowRunStatus.PENDING:
            workflow_run.status = WorkflowRunStatus.RUNNING
            workflow_run.started_at = timezone.now()
            workflow_run.save(update_fields=["status", "started_at", "updated_at"])
