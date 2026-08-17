"""Views for Organization and Membership management."""
import uuid
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import Http404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .context import ORGANIZATION_HEADER
from .enums import MEMBER_MANAGER_ROLES, OWNER_ONLY_ROLES
from .models import Organization, OrganizationMembership
from .serializers import (
    MembershipCreateSerializer,
    MembershipRoleSerializer,
    OrganizationCreateSerializer,
    OrganizationMembershipSerializer,
    OrganizationSerializer,
)
from .services import (
    add_existing_member,
    archive_organization,
    build_unique_organization_slug,
    change_membership_role,
    remove_membership,
)


class OrganizationViewSet(viewsets.GenericViewSet):
    """ViewSet for managing organizations and their memberships."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def _get_org_for_user(self, org_id, required_roles=None) -> tuple[Organization, OrganizationMembership]:
        """Fetch organization and verify authenticated user's active membership and required roles."""
        try:
            parsed_id = uuid.UUID(str(org_id))
        except (ValueError, TypeError):
            raise Http404("Organization not found.")

        # Check tenant header if provided
        header_val = self.request.META.get(ORGANIZATION_HEADER)
        if header_val:
            try:
                header_uuid = uuid.UUID(header_val.strip())
                if header_uuid != parsed_id:
                    raise Http404("Organization context does not match path ID.")
            except (ValueError, TypeError):
                raise Http404("Invalid organization header.")

        membership = OrganizationMembership.objects.select_related("organization").filter(
            organization_id=parsed_id,
            user=self.request.user,
            is_active=True,
            organization__is_active=True,
        ).first()

        if not membership:
            raise Http404("Organization not found.")

        if required_roles and membership.role not in required_roles:
            raise ValidationError(
                {"detail": "You do not have permission to perform this action in this organization."},
                code="permission_denied",
            )

        return membership.organization, membership

    def list(self, request):
        """List all organizations where the authenticated user has an active membership."""
        include_inactive = request.query_params.get("include_inactive", "").lower() in ("true", "1")

        qs = Organization.objects.filter(
            memberships__user=request.user,
            memberships__is_active=True,
        )
        if not include_inactive:
            qs = qs.filter(is_active=True)

        serializer = OrganizationSerializer(qs.distinct(), many=True)
        return Response(serializer.data)

    def create(self, request):
        """Create a new non-personal organization with the caller as OWNER."""
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data["name"]
        metadata = serializer.validated_data.get("metadata", {})
        slug = build_unique_organization_slug(name)

        with transaction.atomic():
            org = Organization.objects.create(
                name=name,
                slug=slug,
                is_personal=False,
                is_active=True,
                metadata=metadata,
                created_by=request.user,
                updated_by=request.user,
            )
            OrganizationMembership.objects.create(
                organization=org,
                user=request.user,
                role="OWNER",
                is_active=True,
                created_by=request.user,
            )

        return Response(OrganizationSerializer(org).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, id=None):
        """Retrieve details of an organization."""
        org, _ = self._get_org_for_user(id)
        return Response(OrganizationSerializer(org).data)

    def partial_update(self, request, id=None):
        """Update an organization's name or metadata (OWNER or ADMIN)."""
        org, _ = self._get_org_for_user(id, required_roles=MEMBER_MANAGER_ROLES)
        serializer = OrganizationSerializer(org, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        org.name = serializer.validated_data.get("name", org.name)
        if "metadata" in serializer.validated_data:
            org.metadata = serializer.validated_data["metadata"]
        org.updated_by = request.user
        org.save(update_fields=["name", "metadata", "updated_by", "updated_at"])

        return Response(OrganizationSerializer(org).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, id=None):
        """Archive a non-personal organization (OWNER only)."""
        org, _ = self._get_org_for_user(id, required_roles=OWNER_ONLY_ROLES)
        try:
            archived_org = archive_organization(org, request.user)
        except DjangoValidationError as exc:
            raise ValidationError({"detail": exc.message}, code=getattr(exc, "code", "error"))

        return Response(OrganizationSerializer(archived_org).data)

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, id=None):
        """List or add members in an organization."""
        if request.method == "GET":
            org, membership = self._get_org_for_user(id)
            include_inactive = request.query_params.get("include_inactive", "").lower() in ("true", "1")

            qs = OrganizationMembership.objects.select_related("user", "organization").filter(organization=org)
            if not (include_inactive and membership.role in MEMBER_MANAGER_ROLES):
                qs = qs.filter(is_active=True)

            serializer = OrganizationMembershipSerializer(qs.order_by("-created_at"), many=True)
            return Response(serializer.data)

        elif request.method == "POST":
            org, _ = self._get_org_for_user(id, required_roles=MEMBER_MANAGER_ROLES)
            serializer = MembershipCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            try:
                new_membership = add_existing_member(
                    organization=org,
                    actor=request.user,
                    email=serializer.validated_data["email"],
                    role=serializer.validated_data["role"],
                )
            except DjangoValidationError as exc:
                raise ValidationError({"detail": exc.message}, code=getattr(exc, "code", "error"))

            return Response(
                OrganizationMembershipSerializer(new_membership).data,
                status=status.HTTP_201_CREATED,
            )

    @action(detail=True, methods=["patch", "delete"], url_path="members/(?P<membership_id>[^/.]+)")
    def member_detail(self, request, id=None, membership_id=None):
        """Update member role or remove member from organization."""
        org, _ = self._get_org_for_user(id)

        try:
            target_mem_id = uuid.UUID(str(membership_id))
        except (ValueError, TypeError):
            raise Http404("Membership not found.")

        target_membership = OrganizationMembership.objects.select_related("organization", "user").filter(
            id=target_mem_id,
            organization=org,
            is_active=True,
        ).first()

        if not target_membership:
            raise Http404("Membership not found.")

        if request.method == "PATCH":
            serializer = MembershipRoleSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                updated = change_membership_role(
                    membership=target_membership,
                    actor=request.user,
                    new_role=serializer.validated_data["role"],
                )
            except DjangoValidationError as exc:
                raise ValidationError({"detail": exc.message}, code=getattr(exc, "code", "error"))

            return Response(OrganizationMembershipSerializer(updated).data)

        elif request.method == "DELETE":
            try:
                remove_membership(membership=target_membership, actor=request.user)
            except DjangoValidationError as exc:
                raise ValidationError({"detail": exc.message}, code=getattr(exc, "code", "error"))

            return Response(status=status.HTTP_204_NO_CONTENT)
