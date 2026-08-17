"""Tests for WordPressSite and SiteProfileSnapshot models."""
import pytest
from django.contrib.auth import get_user_model
from apps.organizations.services import ensure_personal_organization
from apps.sites.enums import SiteConnectionStatus, SiteEnvironment
from apps.sites.models import SiteProfileSnapshot, WordPressSite
from apps.sites.services import create_site_profile_snapshot

User = get_user_model()


@pytest.mark.django_db
class TestSiteModels:
    """Test suite for site models."""

    def setup_method(self):
        self.user = User.objects.create_user(email="admin@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)

    def test_create_site(self):
        site = WordPressSite.objects.create(
            organization=self.org,
            name="Production Blog",
            url="https://example.com/",
            environment=SiteEnvironment.PRODUCTION,
            created_by=self.user,
            updated_by=self.user,
        )

        assert site.organization == self.org
        assert site.connection_status == SiteConnectionStatus.UNVERIFIED
        assert site.next_profile_version == 1
        assert site.last_profiled_at is None

    def test_create_snapshot_advances_version(self):
        site = WordPressSite.objects.create(
            organization=self.org,
            name="Staging Site",
            url="https://staging.example.com/",
            created_by=self.user,
            updated_by=self.user,
        )

        snap1 = create_site_profile_snapshot(
            site=site,
            actor=self.user,
            payload={
                "wordpress_version": "6.7",
                "php_version": "8.2",
                "active_theme": {"name": "twentytwentyfour"},
                "active_plugins": [{"slug": "woocommerce", "version": "9.0"}],
            },
        )

        assert snap1.version == 1
        assert snap1.wordpress_version == "6.7"
        assert len(snap1.checksum_sha256) == 64

        site.refresh_from_db()
        assert site.next_profile_version == 2
        assert site.last_profiled_at is not None

        snap2 = create_site_profile_snapshot(
            site=site,
            actor=self.user,
            payload={
                "wordpress_version": "6.7.1",
                "php_version": "8.2",
                "active_theme": {"name": "twentytwentyfour"},
                "active_plugins": [],
            },
        )
        assert snap2.version == 2
