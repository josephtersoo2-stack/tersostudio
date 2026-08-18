"""Tests for organization context resolution and header rules."""
import uuid
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from apps.organizations.context import (
    ORGANIZATION_HEADER,
    InvalidOrganizationContext,
    OrganizationContextRequired,
    OrganizationNotFound,
    resolve_request_organization,
)
from apps.organizations.enums import OrganizationRole
from apps.organizations.models import Organization, OrganizationMembership

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationContextResolution:
    """Test suite for organization context header parsing and resolution rules."""

    def setup_method(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(email="user@example.com", password="password123")
        self.org1 = Organization.objects.create(name="Org One", slug="org-one", created_by=self.user)
        self.mem1 = OrganizationMembership.objects.create(
            organization=self.org1,
            user=self.user,
            role=OrganizationRole.OWNER,
            is_active=True,
        )

    def test_single_membership_defaults_safely_without_header(self):
        request = self.factory.get("/api/v1/projects/")
        request.user = self.user

        org, membership = resolve_request_organization(request)
        assert org.id == self.org1.id
        assert membership.id == self.mem1.id
        assert request.tersuite_organization.id == self.org1.id
        assert request.tersuite_membership.id == self.mem1.id

    def test_multiple_memberships_require_header(self):
        org2 = Organization.objects.create(name="Org Two", slug="org-two", created_by=self.user)
        OrganizationMembership.objects.create(
            organization=org2,
            user=self.user,
            role=OrganizationRole.MEMBER,
            is_active=True,
        )

        request = self.factory.get("/api/v1/projects/")
        request.user = self.user

        with pytest.raises(OrganizationContextRequired) as exc_info:
            resolve_request_organization(request)
        assert exc_info.value.default_code == "organization_context_required"

    def test_valid_header_resolves_specified_organization(self):
        org2 = Organization.objects.create(name="Org Two", slug="org-two", created_by=self.user)
        mem2 = OrganizationMembership.objects.create(
            organization=org2,
            user=self.user,
            role=OrganizationRole.MEMBER,
            is_active=True,
        )

        request = self.factory.get("/api/v1/projects/", HTTP_X_TERSUITE_ORGANIZATION_ID=str(org2.id))
        request.user = self.user

        org, membership = resolve_request_organization(request)
        assert org.id == org2.id
        assert membership.id == mem2.id

    def test_malformed_header_raises_invalid_context(self):
        request = self.factory.get("/api/v1/projects/", HTTP_X_TERSUITE_ORGANIZATION_ID="not-a-uuid")
        request.user = self.user

        with pytest.raises(InvalidOrganizationContext) as exc_info:
            resolve_request_organization(request)
        assert exc_info.value.default_code == "invalid_organization_context"

    def test_unknown_or_unaffiliated_organization_raises_not_found(self):
        random_uuid = str(uuid.uuid4())
        request = self.factory.get("/api/v1/projects/", HTTP_X_TERSUITE_ORGANIZATION_ID=random_uuid)
        request.user = self.user

        with pytest.raises(OrganizationNotFound) as exc_info:
            resolve_request_organization(request)
        assert exc_info.value.default_code == "organization_not_found"

    def test_inactive_membership_raises_not_found(self):
        self.mem1.is_active = False
        self.mem1.save(update_fields=["is_active"])

        request = self.factory.get("/api/v1/projects/", HTTP_X_TERSUITE_ORGANIZATION_ID=str(self.org1.id))
        request.user = self.user

        with pytest.raises(OrganizationNotFound) as exc_info:
            resolve_request_organization(request)
        assert exc_info.value.default_code == "organization_not_found"

    def test_inactive_organization_raises_not_found(self):
        self.org1.is_active = False
        self.org1.save(update_fields=["is_active"])

        request = self.factory.get("/api/v1/projects/", HTTP_X_TERSUITE_ORGANIZATION_ID=str(self.org1.id))
        request.user = self.user

        with pytest.raises(OrganizationNotFound) as exc_info:
            resolve_request_organization(request)
        assert exc_info.value.default_code == "organization_not_found"
