"""Tests for Organization models, membership models, and services."""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.organizations.enums import OrganizationRole
from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.services import (
    add_existing_member,
    archive_organization,
    assert_at_least_one_active_owner,
    build_unique_organization_slug,
    change_membership_role,
    ensure_personal_organization,
    remove_membership,
)

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationServices:
    """Test suite for organization creation, personal orgs, and role operations."""

    def test_ensure_personal_organization_creates_org_and_owner(self):
        user = User.objects.create_user(email="alice@example.com", password="password123", first_name="Alice")
        org = ensure_personal_organization(user)

        assert org.is_personal is True
        assert org.is_active is True
        assert org.created_by == user

        membership = OrganizationMembership.objects.get(organization=org, user=user)
        assert membership.role == OrganizationRole.OWNER
        assert membership.is_active is True

        # Calling again returns the same organization
        org2 = ensure_personal_organization(user)
        assert org.id == org2.id

    def test_build_unique_organization_slug(self):
        slug1 = build_unique_organization_slug("Acme Corp")
        assert slug1 == "acme-corp"

        Organization.objects.create(name="Acme Corp", slug=slug1)
        slug2 = build_unique_organization_slug("Acme Corp")
        assert slug2 == "acme-corp-1"

    def test_add_existing_member_success(self):
        owner = User.objects.create_user(email="owner@example.com", password="password123")
        member = User.objects.create_user(email="member@example.com", password="password123")
        org = ensure_personal_organization(owner)

        membership = add_existing_member(org, actor=owner, email="member@example.com", role=OrganizationRole.MEMBER)
        assert membership.user == member
        assert membership.role == OrganizationRole.MEMBER
        assert membership.is_active is True

    def test_add_existing_member_rejects_unknown_email(self):
        owner = User.objects.create_user(email="owner@example.com", password="password123")
        org = ensure_personal_organization(owner)

        with pytest.raises(ValidationError) as exc_info:
            add_existing_member(org, actor=owner, email="nonexistent@example.com")
        assert exc_info.value.code == "registered_user_not_found"

    def test_admin_cannot_promote_to_owner(self):
        owner = User.objects.create_user(email="owner@example.com", password="password123")
        admin = User.objects.create_user(email="admin@example.com", password="password123")
        target = User.objects.create_user(email="target@example.com", password="password123")

        org = Organization.objects.create(name="Team", slug="team", created_by=owner)
        OrganizationMembership.objects.create(organization=org, user=owner, role=OrganizationRole.OWNER)
        OrganizationMembership.objects.create(organization=org, user=admin, role=OrganizationRole.ADMIN)

        with pytest.raises(ValidationError) as exc_info:
            add_existing_member(org, actor=admin, email="target@example.com", role=OrganizationRole.OWNER)
        assert exc_info.value.code == "owner_permission_required"

    def test_last_owner_cannot_be_demoted_or_removed(self):
        owner = User.objects.create_user(email="owner@example.com", password="password123")
        org = ensure_personal_organization(owner)
        membership = OrganizationMembership.objects.get(organization=org, user=owner)

        with pytest.raises(ValidationError) as exc_info:
            change_membership_role(membership, actor=owner, new_role=OrganizationRole.MEMBER)
        assert exc_info.value.code == "last_owner_required"

        with pytest.raises(ValidationError) as exc_info:
            remove_membership(membership, actor=owner)
        assert exc_info.value.code == "last_owner_required"

    def test_personal_organization_cannot_be_archived(self):
        owner = User.objects.create_user(email="owner@example.com", password="password123")
        org = ensure_personal_organization(owner)

        with pytest.raises(ValidationError) as exc_info:
            archive_organization(org, actor=owner)
        assert exc_info.value.code == "cannot_archive_personal_organization"
