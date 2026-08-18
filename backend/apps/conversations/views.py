"""REST API ViewSets for Conversations and Messages."""
import uuid
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import Http404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.organizations.context import OrganizationContextMixin
from apps.organizations.permissions import HasOrganizationReadAccess, HasOrganizationWriteAccess
from apps.projects.models import Project
from .models import Conversation, ConversationMessage
from .serializers import (
    ConversationMessageCreateSerializer,
    ConversationMessageSerializer,
    ConversationSerializer,
)
from .services import ConversationMessageService


class ConversationViewSet(OrganizationContextMixin, viewsets.ModelViewSet):
    """ViewSet for managing project discussions and message threads (List, Create, Retrieve, Patch, Archive).
    Root DELETE and PUT return 405 Method Not Allowed.
    """

    http_method_names = ["get", "post", "patch", "head", "options"]
    serializer_class = ConversationSerializer
    lookup_field = "id"

    def get_permissions(self):
        if self.action in ("list", "retrieve", "messages", "message_detail"):
            if self.request.method in permissions.SAFE_METHODS:
                return [permissions.IsAuthenticated(), HasOrganizationReadAccess()]
        return [permissions.IsAuthenticated(), HasOrganizationWriteAccess()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Conversation.objects.none()

        org = self.get_organization()
        qs = Conversation.objects.select_related("project", "organization").filter(organization=org)

        project_id = self.request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)

        purpose = self.request.query_params.get("purpose")
        if purpose:
            qs = qs.filter(purpose=purpose.upper())

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

    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user,
        )

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, id=None):
        """Archive a conversation (idempotent)."""
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

            data = ConversationMessageSerializer(msg).data
            data["idempotent_replay"] = not created
            res_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(data, status=res_status)

    @action(detail=True, methods=["get"], url_path="messages/(?P<message_id>[^/.]+)")
    def message_detail(self, request, id=None, message_id=None):
        """Retrieve a specific message in this conversation."""
        conv = self.get_object()

        try:
            parsed_msg_id = uuid.UUID(str(message_id))
        except (ValueError, TypeError):
            raise Http404("Message not found.")

        msg = ConversationMessage.objects.filter(
            id=parsed_msg_id,
            conversation=conv,
            organization=self.get_organization(),
        ).first()

        if not msg:
            raise Http404("Message not found.")

        return Response(ConversationMessageSerializer(msg).data)
