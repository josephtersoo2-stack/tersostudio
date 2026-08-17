"""REST API ViewSets for Conversations and Messages."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import Http404
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.organizations.context import OrganizationContextMixin
from apps.organizations.permissions import HasOrganizationWriteAccess
from apps.projects.models import Project
from .models import Conversation, ConversationMessage
from .serializers import (
    ConversationMessageCreateSerializer,
    ConversationMessageSerializer,
    ConversationSerializer,
)
from .services import ConversationMessageService


class ConversationViewSet(OrganizationContextMixin, viewsets.ModelViewSet):
    """ViewSet for managing project discussions and message threads."""

    permission_classes = [permissions.IsAuthenticated, HasOrganizationWriteAccess]
    serializer_class = ConversationSerializer
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Conversation.objects.none()

        org = self.get_organization()
        qs = Conversation.objects.select_related("project", "organization").filter(organization=org)

        project_id = self.request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param.upper())

        search = self.request.query_params.get("search")
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(project__name__icontains=search)
            )

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        project_id = serializer.validated_data.get("project_id")
        project = Project.objects.filter(
            id=project_id,
            organization=self.get_organization(),
            is_archived=False,
        ).first()

        if not project:
            raise Http404("Project not found in this organization.")

        serializer.save(
            organization=self.get_organization(),
            project=project,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, id=None):
        """Archive a conversation to close discussion."""
        conv = self.get_object()
        archived = ConversationMessageService.archive_conversation(conv, request.user)
        return Response(ConversationSerializer(archived).data)

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, id=None):
        """List or append user messages in this conversation."""
        conv = self.get_object()

        if request.method == "GET":
            qs = ConversationMessage.objects.select_related("author", "conversation", "organization").filter(
                conversation=conv,
                organization=self.get_organization(),
            ).order_by("sequence", "created_at")
            return Response(ConversationMessageSerializer(qs, many=True).data)

        elif request.method == "POST":
            serializer = ConversationMessageCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            try:
                msg, created = ConversationMessageService.append_user_message(
                    conversation=conv,
                    author=request.user,
                    content=serializer.validated_data["content"],
                    client_message_id=serializer.validated_data.get("client_message_id"),
                    content_format=serializer.validated_data.get("content_format", "MARKDOWN"),
                    metadata=serializer.validated_data.get("metadata", {}),
                )
            except DjangoValidationError as exc:
                raise ValidationError({"detail": exc.message}, code=getattr(exc, "code", "error"))

            res_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(ConversationMessageSerializer(msg).data, status=res_status)


class ConversationMessageViewSet(
    OrganizationContextMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only viewset for querying recorded conversation messages."""

    permission_classes = [permissions.IsAuthenticated, HasOrganizationWriteAccess]
    serializer_class = ConversationMessageSerializer
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return ConversationMessage.objects.none()

        org = self.get_organization()
        qs = ConversationMessage.objects.select_related("author", "conversation", "organization").filter(
            organization=org
        )

        conv_id = self.request.query_params.get("conversation_id")
        if conv_id:
            qs = qs.filter(conversation_id=conv_id)

        return qs.order_by("sequence", "created_at")
