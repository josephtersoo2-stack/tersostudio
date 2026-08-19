"""Real Django MigrationExecutor tests for B3 Workflow Kernel schema and data migrations."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class B3WorkflowKernelMigrationExecutorTests(TransactionTestCase):
    """Verifies forward and reverse execution of B3 migrations using historical app states."""

    databases = {"default"}

    def get_executor(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        return executor

    def test_b3_migration_forward_and_backward(self):
        """Verify full forward state backfill and reversible legacy status restoration."""
        # Target B2 baseline state
        b2_targets = [
            ("accounts", "0001_initial"),
            ("organizations", "0002_backfill_personal_organizations"),
            ("products", "0001_initial"),
            ("sites", "0001_initial"),
            ("projects", "0002_organization_product_ownership"),
            ("conversations", "0001_initial"),
            ("generations", "0002_organization_audit_ownership"),
            ("workflows", None),
        ]
        b2_nodes = [
            ("accounts", "0001_initial"),
            ("organizations", "0002_backfill_personal_organizations"),
            ("products", "0001_initial"),
            ("sites", "0001_initial"),
            ("projects", "0002_organization_product_ownership"),
            ("conversations", "0001_initial"),
            ("generations", "0002_organization_audit_ownership"),
        ]

        try:
            # 1. Migrate backward to B2 baseline schema
            executor = self.get_executor()
            executor.migrate(b2_targets)
            old_apps = executor.loader.project_state(b2_nodes).apps

            OldUser = old_apps.get_model("accounts", "User")
            OldOrg = old_apps.get_model("organizations", "Organization")
            OldProduct = old_apps.get_model("products", "WordPressProduct")
            OldProject = old_apps.get_model("projects", "Project")
            OldGeneration = old_apps.get_model("generations", "Generation")
            OldStep = old_apps.get_model("generations", "GenerationStep")

            # 2. Populate historical B2 records
            u = OldUser.objects.create(
                email="dev.operator@tersuite.com",
                password="Password123!",
                first_name="Dev",
                last_name="Operator",
                is_active=True,
            )
            org = OldOrg.objects.create(
                name="Tersuite Lab",
                slug="tersuite-lab",
                created_by=u,
                updated_by=u,
            )
            product = OldProduct.objects.create(
                organization=org,
                display_name="Affiliate Suite",
                slug="affiliate-suite",
                kind="PLUGIN",
                created_by=u,
                updated_by=u,
            )
            project = OldProject.objects.create(
                organization=org,
                product=product,
                name="Affiliate Pro",
                slug="affiliate-pro",
                created_by=u,
                updated_by=u,
            )

            # Create generations with historical status names
            g_plan = OldGeneration.objects.create(
                project=project,
                organization=org,
                prompt="Affiliate plugin",
                status="PLANNING",
                created_by=u,
                updated_by=u,
            )
            g_spec = OldGeneration.objects.create(
                project=project,
                organization=org,
                prompt="Spec plugin",
                status="SPECIFICATION",
                created_by=u,
                updated_by=u,
            )
            g_test = OldGeneration.objects.create(
                project=project,
                organization=org,
                prompt="Test plugin",
                status="TESTING",
                created_by=u,
                updated_by=u,
            )
            g_pack = OldGeneration.objects.create(
                project=project,
                organization=org,
                prompt="Pack plugin",
                status="PACKAGING",
                created_by=u,
                updated_by=u,
            )

            step = OldStep.objects.create(
                generation=g_plan,
                step_number=1,
                name="Architecture Spec",
                agent_role="architect",
                status="PENDING",
            )

            # 3. Migrate forward to latest B3 schema
            executor = self.get_executor()
            executor.loader.build_graph()
            latest_targets = executor.loader.graph.leaf_nodes()
            executor.migrate(latest_targets)
            new_apps = executor.loader.project_state(latest_targets).apps

            NewGeneration = new_apps.get_model("generations", "Generation")
            NewTransition = new_apps.get_model("generations", "GenerationStateTransition")
            NewWorkflowRun = new_apps.get_model("workflows", "WorkflowRun")
            NewWorkPackage = new_apps.get_model("workflows", "WorkPackage")

            # 4. Verify forward migrations
            gen_plan_migrated = NewGeneration.objects.get(id=g_plan.id)
            assert gen_plan_migrated.status == "PLAN_DRAFT"
            assert gen_plan_migrated.state_version == 1
            assert gen_plan_migrated.status_changed_at is not None
            assert gen_plan_migrated.next_transition_sequence == 2

            gen_spec_migrated = NewGeneration.objects.get(id=g_spec.id)
            assert gen_spec_migrated.status == "SPECIFICATION_DRAFT"

            gen_test_migrated = NewGeneration.objects.get(id=g_test.id)
            assert gen_test_migrated.status == "SANDBOX_QA"

            gen_pack_migrated = NewGeneration.objects.get(id=g_pack.id)
            assert gen_pack_migrated.status == "RELEASE_CANDIDATE"

            # Verify initial state transition record was created
            t_plan = NewTransition.objects.filter(generation=gen_plan_migrated).first()
            assert t_plan is not None
            assert t_plan.sequence == 1
            assert t_plan.to_status == "PLAN_DRAFT"

            NewStep = new_apps.get_model("generations", "GenerationStep")
            step_migrated = NewStep.objects.get(id=step.id)
            assert step_migrated.milestone_id is not None

            # Verify workflows models are operational
            wf_run = NewWorkflowRun.objects.create(
                generation=gen_plan_migrated,
                organization_id=gen_plan_migrated.organization_id,
                run_number=1,
                status="PENDING",
            )
            pkg = NewWorkPackage.objects.create(
                workflow_run=wf_run,
                generation_step=step_migrated,
                organization_id=wf_run.organization_id,
                key="pkg_1",
                name="Architecture Task",
                status="PENDING",
            )
            assert wf_run.id is not None
            assert pkg.id is not None
            assert pkg.generation_step_id == step_migrated.id

            pkg.delete()
            wf_run.delete()

            # 5. Migrate backward to B2 baseline
            executor = self.get_executor()
            executor.loader.build_graph()
            executor.migrate(b2_targets)
            reverted_apps = executor.loader.project_state(b2_nodes).apps

            RevGen = reverted_apps.get_model("generations", "Generation")
            rev_plan = RevGen.objects.get(id=g_plan.id)
            assert rev_plan.status == "PLANNING"

            rev_spec = RevGen.objects.get(id=g_spec.id)
            assert rev_spec.status == "SPECIFICATION"

            rev_test = RevGen.objects.get(id=g_test.id)
            assert rev_test.status == "TESTING"

            rev_pack = RevGen.objects.get(id=g_pack.id)
            assert rev_pack.status == "PACKAGING"

        finally:
            # Re-apply all migrations to leave database in clean final state
            final_executor = self.get_executor()
            final_executor.loader.build_graph()
            final_executor.migrate(final_executor.loader.graph.leaf_nodes())
