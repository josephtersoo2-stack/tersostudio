"""Business services for Organization lifecycle and membership management."""
import re
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from .enums import (
    MEMBER_MANAGER_ROLES,
    OWNER_ONLY_ROLES,
    OrganizationRole,
)
from .models import Organization, OrganizationMembership

User = get_user_model()


def build_unique_organization_slug(name: str, *, seed: str | None = None) -> str:
    """Generate a unique, collision-safe slug for an organization."""
    base_slug = slugify(name) or "org"
    if seed:
        base_slug = f"{base_slug}-{slugify(str(seed))[:8]}"

    slug = base_slug
    counter = 1
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def ensure_personal_organization(user) -> Organization:
    """Ensure a user has exactly one personal organization and an active OWNER membership."""
    with transaction.atomic():
        # Lock the user row to prevent race conditions during registration/backfill
        locked_user = User.objects.select_for_update().get(id=user.id)

        existing_membership = OrganizationMembership.objects.select_related("organization").filter(
            user=locked_user,
            organization__is_personal=True,
            role=OrganizationRole.OWNER,
            is_active=True,
        ).first()

        if existing_membership:
            return existing_membership.organization

        # Also check if a personal org was created with created_by=user
        existing_org = Organization.objects.filter(
            created_by=locked_user,
            is_personal=True,
        ).first()

        if existing_org:
            membership, _ = OrganizationMembership.objects.get_or_create(
                organization=existing_org,
                user=locked_user,
                defaults={
                    "role": OrganizationRole.OWNER,
                    "is_active": True,
                    "created_by": locked_user,
                },
            )
            if not membership.is_active or membership.role != OrganizationRole.OWNER:
                membership.is_active = True
                membership.role = OrganizationRole.OWNER
                membership.save(update_fields=["is_active", "role", "updated_at"])
            return existing_org

        # Create new personal organization
        user_display = (locked_user.full_name or locked_user.email.split("@")[0]).strip()
        org_name = f"{user_display}'s Workspace"
        org_slug = build_unique_organization_slug(org_name, seed=str(locked_user.id)[:8])

        org = Organization.objects.create(
            name=org_name,
            slug=org_slug,
            is_personal=True,
            is_active=True,
            created_by=locked_user,
            updated_by=locked_user,
        )

        OrganizationMembership.objects.create(
            organization=org,
            user=locked_user,
            role=OrganizationRole.OWNER,
            is_active=True,
            created_by=locked_user,
        )

        return org


def assert_at_least_one_active_owner(organization: Organization, exclude_membership_id=None) -> None:
    """Validate that the organization will retain at least one active OWNER membership."""
    qs = OrganizationMembership.objects.filter(
        organization=organization,
        role=OrganizationRole.OWNER,
        is_active=True,
    )
    if exclude_membership_id:
        qs = qs.exclude(id=exclude_membership_id)

    if not qs.exists():
        raise ValidationError(
            "An organization must always retain at least one active owner.",
            code="last_owner_required",
        )


def add_existing_member(
    organization: Organization,
    actor,
    email: str,
    role: str = OrganizationRole.MEMBER,
) -> OrganizationMembership:
    """Add a registered user to an organization by email address."""
    normalized_email = email.lower().strip()

    with transaction.atomic():
        # Validate actor's permission in the organization
        actor_membership = OrganizationMembership.objects.select_for_update().filter(
            organization=organization,
            user=actor,
            is_active=True,
        ).first()

        if not actor_membership or actor_membership.role not in MEMBER_MANAGER_ROLES:
            raise ValidationError(
                "You do not have permission to manage members in this organization.",
                code="permission_denied",
            )

        if role == OrganizationRole.OWNER and actor_membership.role != OrganizationRole.OWNER:
            raise ValidationError(
                "Only an organization owner can assign the OWNER role.",
                code="owner_permission_required",
            )

        target_user = User.objects.filter(email=normalized_email).first()
        if not target_user:
            raise ValidationError(
                "No registered user found with the provided email address.",
                code="registered_user_not_found",
            )

        membership = OrganizationMembership.objects.select_for_update().filter(
            organization=organization,
            user=target_user,
        ).first()

        if membership:
            if membership.is_active:
                raise ValidationError(
                    "This user is already an active member of the organization.",
                    code="member_already_exists",
                )
            # Reactivate existing inactive membership
            membership.is_active = True
            membership.role = role
            membership.created_by = actor
            membership.save(update_fields=["is_active", "role", "created_by", "updated_at"])
            return membership

        membership = OrganizationMembership.objects.create(
            organization=organization,
            user=target_user,
            role=role,
            is_active=True,
            created_by=actor,
        )
        return membership


def change_membership_role(
    membership: OrganizationMembership,
    actor,
    new_role: str,
) -> OrganizationMembership:
    """Change the role of an existing organization membership."""
    with transaction.atomic():
        org = membership.organization
        # Lock all memberships in this org to prevent concurrent last-owner removal
        list(OrganizationMembership.objects.select_for_update().filter(organization=org))

        actor_membership = OrganizationMembership.objects.filter(
            organization=org,
            user=actor,
            is_active=True,
        ).first()

        if not actor_membership or actor_membership.role not in MEMBER_MANAGER_ROLES:
            raise ValidationError(
                "You do not have permission to change member roles in this organization.",
                code="permission_denied",
            )

        # Admin cannot modify an Owner's role
        if membership.role == OrganizationRole.OWNER and actor_membership.role != OrganizationRole.OWNER:
            raise ValidationError(
                "Admins cannot modify the role of an organization owner.",
                code="cannot_modify_owner",
            )

        # Admin cannot promote anyone to Owner
        if new_role == OrganizationRole.OWNER and actor_membership.role != OrganizationRole.OWNER:
            raise ValidationError(
                "Only an organization owner can promote a member to owner.",
                code="owner_permission_required",
            )

        # If demoting an owner, ensure at least one other active owner remains
        if membership.role == OrganizationRole.OWNER and new_role != OrganizationRole.OWNER:
            assert_at_least_one_active_owner(org, exclude_membership_id=membership.id)

        membership.role = new_role
        membership.save(update_fields=["role", "updated_at"])
        return membership


def remove_membership(membership: OrganizationMembership, actor) -> None:
    """Soft-deactivate a membership from an organization."""
    with transaction.atomic():
        org = membership.organization
        list(OrganizationMembership.objects.select_for_update().filter(organization=org))

        actor_membership = OrganizationMembership.objects.filter(
            organization=org,
            user=actor,
            is_active=True,
        ).first()

        if not actor_membership or actor_membership.role not in MEMBER_MANAGER_ROLES:
            # Check if user is leaving on their own
            if membership.user_id != actor.id:
                raise ValidationError(
                    "You do not have permission to remove members from this organization.",
                    code="permission_denied",
                )

        if membership.role == OrganizationRole.OWNER:
            if actor_membership and actor_membership.role != OrganizationRole.OWNER and membership.user_id != actor.id:
                raise ValidationError(
                    "Admins cannot remove an organization owner.",
                    code="cannot_remove_owner",
                )
            assert_at_least_one_active_owner(org, exclude_membership_id=membership.id)

        membership.is_active = False
        membership.save(update_fields=["is_active", "updated_at"])


def archive_organization(organization: Organization, actor) -> Organization:
    """Soft-archive a non-personal organization."""
    if organization.is_personal:
        raise ValidationError(
            "Personal workspaces cannot be archived.",
            code="cannot_archive_personal_organization",
        )

    with transaction.atomic():
        membership = OrganizationMembership.objects.select_for_update().filter(
            organization=organization,
            user=actor,
            is_active=True,
        ).first()

        if not membership or membership.role not in OWNER_ONLY_ROLES:
            raise ValidationError(
                "Only an active owner can archive an organization.",
                code="owner_permission_required",
            )

        organization.is_active = False
        organization.updated_by = actor
        organization.save(update_fields=["is_active", "updated_by", "updated_at"])
        return organization
