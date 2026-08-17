"""Real Django MigrationExecutor tests for B2 Core Domain schema and data migrations."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class B2CoreDomainMigrationExecutorTests(TransactionTestCase):
    """Verifies forward and reverse execution of B2 migrations using historical app states."""

    databases = {"default"}

    def get_executor(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        return executor

    def test_b2_migration_forward_and_backward(self):
        """Verify full forward backfill (slug collision, metadata, org isolation) and reversible legacy field restoration."""
        # Target B1 baseline state
        b1_targets = [
            ("accounts", "0001_initial"),
            ("projects", "0001_initial"),
            ("generations", "0001_initial"),
            ("organizations", None),
            ("products", None),
            ("sites", None),
            ("conversations", None),
        ]
        b1_nodes = [
            ("accounts", "0001_initial"),
            ("projects", "0001_initial"),
            ("generations", "0001_initial"),
        ]

        try:
            # 1. Migrate backward to B1 baseline schema
            executor = self.get_executor()
            executor.migrate(b1_targets)
            old_apps = executor.loader.project_state(b1_nodes).apps

            OldUser = old_apps.get_model("accounts", "User")
            OldProject = old_apps.get_model("projects", "Project")
            OldGeneration = old_apps.get_model("generations", "Generation")
            OldStep = old_apps.get_model("generations", "GenerationStep")
            OldRun = old_apps.get_model("generations", "AgentRun")
            OldArtifact = old_apps.get_model("generations", "Artifact")

            # 2. Populate historical B1 records
            u1 = OldUser.objects.create(
                email="alice.owner@tersuite.com",
                password="Password123!",
                first_name="Alice",
                last_name="Owner",
                is_active=True,
            )
            u2 = OldUser.objects.create(
                email="bob.owner@tersuite.com",
                password="Password123!",
                first_name="Bob",
                last_name="Owner",
                is_active=True,
            )
            u3 = OldUser.objects.create(
                email="charlie.idle@tersuite.com",
                password="Password123!",
                first_name="Charlie",
                last_name="Idle",
                is_active=True,
            )

            # User 1 with 2 projects sharing the same historical plugin_slug
            p1_1 = OldProject.objects.create(
                user=u1,
                name="WooCommerce Stripe Gateway",
                slug="woo-stripe-gateway",
                plugin_slug="woo-stripe",
                wordpress_version="6.7",
                php_version="8.2",
                metadata={"feature": "checkout"},
            )
            p1_2 = OldProject.objects.create(
                user=u1,
                name="WooCommerce Stripe Connect",
                slug="woo-stripe-connect",
                plugin_slug="woo-stripe",
                wordpress_version="6.6",
                php_version="8.1",
                metadata={"feature": "marketplace"},
            )

            # User 2 with a project
            p2 = OldProject.objects.create(
                user=u2,
                name="Affiliate Pro",
                slug="affiliate-pro",
                plugin_slug="affiliate-pro",
                wordpress_version="6.7",
                php_version="8.2",
            )

            # Generation for User 1's project
            gen = OldGeneration.objects.create(
                project=p1_1,
                user=u1,
                prompt="Build Stripe checkout gateway plugin.",
                status="DRAFT",
            )
            step = OldStep.objects.create(
                generation=gen,
                step_number=1,
                name="Discovery",
                agent_role="feature_discovery",
            )
            run = OldRun.objects.create(
                step=step,
                run_number=1,
                prompt="Discover capabilities",
            )
            artifact = OldArtifact.objects.create(
                generation=gen,
                name="readme.txt",
                file_path="readme.txt",
                storage_key="readme-storage-key",
            )

            # 3. Migrate forward to the leaf graph
            executor = self.get_executor()
            leaf_targets = executor.loader.graph.leaf_nodes()
            executor.migrate(leaf_targets)

            new_apps = executor.loader.project_state(leaf_targets).apps
            NewOrg = new_apps.get_model("organizations", "Organization")
            NewMembership = new_apps.get_model("organizations", "OrganizationMembership")
            NewProject = new_apps.get_model("projects", "Project")
            NewProduct = new_apps.get_model("products", "WordPressProduct")
            NewPluginTarget = new_apps.get_model("products", "PluginTarget")
            NewGeneration = new_apps.get_model("generations", "Generation")

            # Assert personal organizations and OWNER memberships created
            org1 = NewOrg.objects.filter(created_by_id=u1.id, is_personal=True).first()
            self.assertIsNotNone(org1)
            self.assertTrue(NewMembership.objects.filter(organization=org1, user_id=u1.id, role="OWNER", is_active=True).exists())

            org2 = NewOrg.objects.filter(created_by_id=u2.id, is_personal=True).first()
            self.assertIsNotNone(org2)
            self.assertTrue(NewMembership.objects.filter(organization=org2, user_id=u2.id, role="OWNER", is_active=True).exists())

            org3 = NewOrg.objects.filter(created_by_id=u3.id, is_personal=True).first()
            self.assertIsNotNone(org3)
            self.assertTrue(NewMembership.objects.filter(organization=org3, user_id=u3.id, role="OWNER", is_active=True).exists())

            # Assert project migration and product slug collision resolution
            proj1 = NewProject.objects.get(id=p1_1.id)
            proj2 = NewProject.objects.get(id=p1_2.id)

            self.assertEqual(proj1.organization_id, org1.id)
            self.assertEqual(proj2.organization_id, org1.id)
            self.assertEqual(proj1.created_by_id, u1.id)
            self.assertEqual(proj2.created_by_id, u1.id)

            prod1 = NewProduct.objects.get(id=proj1.product_id)
            prod2 = NewProduct.objects.get(id=proj2.product_id)

            self.assertEqual(prod1.slug, "woo-stripe")
            self.assertEqual(prod2.slug, "woo-stripe-2")

            # Check original slug stored in metadata for collided product
            self.assertEqual(prod2.metadata.get("migration", {}).get("legacy_plugin_slug"), "woo-stripe")
            self.assertEqual(prod2.metadata.get("feature"), "marketplace")

            # Check PluginTarget invariants
            pt1 = NewPluginTarget.objects.get(product_id=prod1.id)
            pt2 = NewPluginTarget.objects.get(product_id=prod2.id)
            self.assertEqual(pt1.plugin_slug, "woo-stripe")
            self.assertEqual(pt2.plugin_slug, "woo-stripe-2")
            self.assertEqual(pt1.text_domain, "woo-stripe")
            self.assertEqual(pt2.text_domain, "woo-stripe-2")

            # Check Generation ownership
            migrated_gen = NewGeneration.objects.get(id=gen.id)
            self.assertEqual(migrated_gen.organization_id, org1.id)
            self.assertEqual(migrated_gen.created_by_id, u1.id)

            # 4. Migrate backward to B1 baseline schema
            executor = self.get_executor()
            executor.migrate(b1_targets)

            rev_apps = executor.loader.project_state(b1_nodes).apps
            RevProject = rev_apps.get_model("projects", "Project")
            RevUser = rev_apps.get_model("accounts", "User")
            RevGeneration = rev_apps.get_model("generations", "Generation")

            rev_p1 = RevProject.objects.get(id=p1_1.id)
            rev_p2 = RevProject.objects.get(id=p1_2.id)

            self.assertEqual(rev_p1.user_id, u1.id)
            self.assertEqual(rev_p2.user_id, u1.id)
            self.assertEqual(rev_p1.plugin_slug, "woo-stripe")
            self.assertEqual(rev_p2.plugin_slug, "woo-stripe")
            self.assertEqual(rev_p1.wordpress_version, "6.7")
            self.assertEqual(rev_p2.wordpress_version, "6.6")
            self.assertEqual(rev_p1.php_version, "8.2")
            self.assertEqual(rev_p2.php_version, "8.1")

            self.assertTrue(RevUser.objects.filter(id=u1.id).exists())
            self.assertTrue(RevUser.objects.filter(id=u2.id).exists())
            self.assertTrue(RevUser.objects.filter(id=u3.id).exists())
            self.assertTrue(RevGeneration.objects.filter(id=gen.id).exists())

        finally:
            # 5. Restore full leaf state for remaining test runs
            executor = self.get_executor()
            executor.migrate(executor.loader.graph.leaf_nodes())

    def test_unmarked_personal_organization_survives_reversal(self):
        """Verify pre-existing unmarked personal org at organizations.0001 state survives organizations.0002 rollback."""
        # State right at organizations.0001
        org_0001_targets = [
            ("accounts", "0001_initial"),
            ("organizations", "0001_initial"),
            ("projects", "0001_initial"),
            ("generations", "0001_initial"),
            ("products", None),
            ("sites", None),
            ("conversations", None),
        ]
        org_0001_nodes = [
            ("accounts", "0001_initial"),
            ("organizations", "0001_initial"),
            ("projects", "0001_initial"),
            ("generations", "0001_initial"),
        ]

        try:
            executor = self.get_executor()
            executor.migrate(org_0001_targets)
            apps_0001 = executor.loader.project_state(org_0001_nodes).apps

            User_0001 = apps_0001.get_model("accounts", "User")
            Org_0001 = apps_0001.get_model("organizations", "Organization")

            user_unmarked = User_0001.objects.create(
                email="preexisting@tersuite.com",
                password="Password123!",
                is_active=True,
            )
            # Create unmarked pre-existing personal org
            unmarked_org = Org_0001.objects.create(
                name="Preexisting Org",
                slug="preexisting-org",
                is_personal=True,
                is_active=True,
                created_by=user_unmarked,
                updated_by=user_unmarked,
                metadata={},
            )

            # Another user without an org
            user_without_org = User_0001.objects.create(
                email="newbie@tersuite.com",
                password="Password123!",
                is_active=True,
            )

            # Migrate forward to organizations.0002
            executor = self.get_executor()
            executor.migrate([("organizations", "0002_backfill_personal_organizations")])

            # Migrate backward to organizations.0001
            executor = self.get_executor()
            executor.migrate(org_0001_targets)

            apps_after_rev = executor.loader.project_state(org_0001_nodes).apps
            Org_after_rev = apps_after_rev.get_model("organizations", "Organization")

            # Unmarked org must still exist!
            self.assertTrue(Org_after_rev.objects.filter(id=unmarked_org.id).exists())

        finally:
            executor = self.get_executor()
            executor.migrate(executor.loader.graph.leaf_nodes())
