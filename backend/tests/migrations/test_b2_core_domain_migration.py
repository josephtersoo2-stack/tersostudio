from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.conversations.models import Conversation
from apps.conversations.services import ConversationMessageService
from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation
from apps.organizations.models import OrganizationMembership
from apps.organizations.services import ensure_personal_organization
from apps.projects.models import ProjectSite
from apps.projects.services import ProjectService
from apps.sites.enums import SiteEnvironment
from apps.sites.models import WordPressSite
from apps.sites.services import create_site_profile_snapshot


User = get_user_model()


class B2CoreDomainMigrationIntegrationTests(TestCase):
    """Verifies complete end-to-end integrity of B2 domain models, migrations, and tenant isolation."""

    databases = {"default"}

    def setUp(self):
        # 1. Create Users
        self.user_a = User.objects.create_user(
            email="tenant.alpha@tersuite.com",
            password="AlphaPassword123!",
            first_name="Alpha",
            last_name="Owner",
        )
        self.user_b = User.objects.create_user(
            email="tenant.beta@tersuite.com",
            password="BetaPassword123!",
            first_name="Beta",
            last_name="Owner",
        )

        # 2. Ensure Personal Organizations
        self.org_a = ensure_personal_organization(self.user_a)
        self.org_b = ensure_personal_organization(self.user_b)

    def test_personal_organization_creation_and_membership(self):
        """Verify personal organization and OWNER membership are properly provisioned."""
        self.assertTrue(self.org_a.is_personal)
        self.assertEqual(self.org_a.name, "Alpha Owner's Workspace")

        membership = OrganizationMembership.objects.get(
            organization=self.org_a,
            user=self.user_a,
        )
        self.assertEqual(membership.role, "OWNER")
        self.assertTrue(membership.is_active)

    def test_project_product_and_plugin_target_cohesion(self):
        """Verify ProjectService provisions Project, WordPressProduct, and PluginTarget consistently."""
        project = ProjectService.create_project(
            organization=self.org_a,
            actor=self.user_a,
            name="Advanced Affiliate Hub",
            description="Multi-tier affiliate tracking",
            plugin_slug="advanced-affiliate-hub",
            wordpress_version="6.7",
            php_version="8.3",
        )

        self.assertEqual(project.organization, self.org_a)
        self.assertEqual(project.created_by, self.user_a)
        self.assertIsNotNone(project.product)
        self.assertEqual(project.product.kind, "PLUGIN")
        self.assertEqual(project.product.wordpress_version, "6.7")
        self.assertEqual(project.product.php_version, "8.3")

        # PluginTarget verification
        plugin_target = project.product.plugin_target
        self.assertEqual(plugin_target.plugin_slug, "advanced-affiliate-hub")
        self.assertEqual(plugin_target.namespace_prefix, "AdvancedAffiliateHub")

        # Backward compatibility properties
        self.assertEqual(project.plugin_slug, "advanced-affiliate-hub")
        self.assertEqual(project.wordpress_version, "6.7")
        self.assertEqual(project.php_version, "8.3")
        self.assertEqual(project.user, self.user_a)

    def test_site_and_profile_snapshot_creation(self):
        """Verify WordPressSite and immutable SiteProfileSnapshot creation with SHA-256 checksum."""
        site = WordPressSite.objects.create(
            organization=self.org_a,
            created_by=self.user_a,
            name="Staging Store",
            url="https://staging.example.com",
            environment=SiteEnvironment.STAGING,
        )

        sections = {
            "server": {"php_version": "8.3.0", "web_server": "nginx/1.24"},
            "wordpress": {"core_version": "6.7.1", "multisite": False},
            "active_plugins": [{"name": "WooCommerce", "version": "9.4.0"}],
        }

        snapshot = create_site_profile_snapshot(
            site=site,
            sections=sections,
            actor=self.user_a,
            source="manual",
        )

        self.assertEqual(snapshot.site, site)
        self.assertEqual(snapshot.version, 1)
        self.assertEqual(len(snapshot.checksum_sha256), 64)

        # Create second snapshot to test version incrementation
        snapshot_v2 = create_site_profile_snapshot(
            site=site,
            sections=sections,
            actor=self.user_a,
            source="manual",
        )
        self.assertEqual(snapshot_v2.version, 2)

    def test_project_site_linkage(self):
        """Verify linking WordPressSite to Project via ProjectSite junction."""
        project = ProjectService.create_project(
            organization=self.org_a,
            actor=self.user_a,
            name="Affiliate Pro",
        )
        site = WordPressSite.objects.create(
            organization=self.org_a,
            created_by=self.user_a,
            name="Alpha Dev Site",
            url="https://dev.example.com",
        )

        link = ProjectSite.objects.create(
            project=project,
            site=site,
            organization=self.org_a,
            purpose="target",
        )

        self.assertEqual(link.project, project)
        self.assertEqual(link.site, site)
        self.assertEqual(project.project_sites.count(), 1)

    def test_conversation_and_message_append_order(self):
        """Verify strictly ordered, idempotent conversation message appending."""
        project = ProjectService.create_project(
            organization=self.org_a,
            actor=self.user_a,
            name="Chat Project",
        )

        conversation = Conversation.objects.create(
            organization=self.org_a,
            project=project,
            created_by=self.user_a,
            title="Design Discussion",
        )

        msg1, created1 = ConversationMessageService.append_user_message(
            conversation=conversation,
            author=self.user_a,
            content="Please design an affiliate tracking cookie handler.",
            client_message_id="msg-uuid-001",
        )
        self.assertTrue(created1)
        self.assertEqual(msg1.sequence, 1)

        # Idempotency test with same client_message_id
        msg1_dup, created1_dup = ConversationMessageService.append_user_message(
            conversation=conversation,
            author=self.user_a,
            content="Please design an affiliate tracking cookie handler.",
            client_message_id="msg-uuid-001",
        )
        self.assertFalse(created1_dup)
        self.assertEqual(msg1.id, msg1_dup.id)

        # Next message increments sequence
        msg2, created2 = ConversationMessageService.append_user_message(
            conversation=conversation,
            author=self.user_a,
            content="Add nonce verification to the REST endpoint.",
            client_message_id="msg-uuid-002",
        )
        self.assertTrue(created2)
        self.assertEqual(msg2.sequence, 2)

    def test_generation_tenant_scoping_and_querysets(self):
        """Verify Generation tenant scoping matches parent project organization."""
        project_a = ProjectService.create_project(
            organization=self.org_a,
            actor=self.user_a,
            name="Project A",
        )
        gen_a = Generation.objects.create(
            organization=self.org_a,
            project=project_a,
            created_by=self.user_a,
            prompt="Build Project A plugin.",
            status=GenerationStatus.DRAFT,
        )

        # Mismatch organization must raise ValueError on save()
        with self.assertRaises(ValueError):
            Generation.objects.create(
                organization=self.org_b,
                project=project_a,
                created_by=self.user_b,
                prompt="Illegal cross-tenant generation",
            )

        # QuerySet filters
        self.assertEqual(Generation.objects.for_organization(self.org_a).count(), 1)
        self.assertEqual(Generation.objects.for_organization(self.org_b).count(), 0)
