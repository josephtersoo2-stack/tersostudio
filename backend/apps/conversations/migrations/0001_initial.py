# Generated for conversations initial models
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import apps.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
        ("projects", "0002_organization_product_ownership"),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, help_text="Unique identifier (UUIDv4)", primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when record was last updated")),
                ("title", models.CharField(help_text="Topic or human-readable title of the conversation.", max_length=255)),
                ("purpose", models.CharField(choices=[("PROJECT_DISCOVERY", "Project Discovery"), ("PROJECT_PLANNING", "Project Planning"), ("GENERAL", "General Project Discussion")], db_index=True, default="PROJECT_DISCOVERY", help_text="Functional purpose of the conversation.", max_length=30)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("ARCHIVED", "Archived")], db_index=True, default="ACTIVE", help_text="Active or archived status.", max_length=20)),
                ("next_message_sequence", models.PositiveBigIntegerField(default=1, help_text="Monotonically increasing sequence index for next message.")),
                ("last_message_at", models.DateTimeField(blank=True, db_index=True, help_text="Timestamp when the most recent message was added.", null=True)),
                ("metadata", models.JSONField(blank=True, default=dict, help_text="Safe metadata and conversation tags.", validators=[apps.core.validators.validate_safe_json_object])),
                ("created_by", models.ForeignKey(blank=True, help_text="User who created this resource.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(help_text="Tenant organization that owns this resource.", on_delete=django.db.models.deletion.PROTECT, related_name="%(app_label)s_%(class)s_records", to="organizations.organization")),
                ("project", models.ForeignKey(help_text="Parent project for this conversation.", on_delete=django.db.models.deletion.CASCADE, related_name="conversations", to="projects.project")),
                ("updated_by", models.ForeignKey(blank=True, help_text="User who last updated this resource.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Conversation",
                "verbose_name_plural": "Conversations",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ConversationMessage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, help_text="Unique identifier (UUIDv4)", primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, help_text="Timestamp when record was created")),
                ("updated_at", models.DateTimeField(auto_now=True, help_text="Timestamp when record was last updated")),
                ("sequence", models.PositiveBigIntegerField(help_text="Deterministic 1-indexed order within the conversation.")),
                ("role", models.CharField(choices=[("USER", "User"), ("ASSISTANT", "Assistant"), ("SYSTEM", "System"), ("TOOL", "Tool Execution")], db_index=True, default="USER", help_text="Author role tier.", max_length=20)),
                ("content", models.TextField(help_text="Body content of the message.")),
                ("content_format", models.CharField(choices=[("MARKDOWN", "Markdown"), ("PLAIN_TEXT", "Plain Text"), ("JSON", "Structured JSON")], default="MARKDOWN", help_text="Content serialization format.", max_length=20)),
                ("client_message_id", models.UUIDField(blank=True, help_text="Client-supplied idempotency key (UUIDv4).", null=True)),
                ("metadata", models.JSONField(blank=True, default=dict, help_text="Safe structured metadata (attachments, UI flags).", validators=[apps.core.validators.validate_safe_json_object])),
                ("author", models.ForeignKey(blank=True, help_text="User who authored this message (if role is USER).", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="conversation_messages", to=settings.AUTH_USER_MODEL)),
                ("conversation", models.ForeignKey(help_text="Parent conversation containing this message.", on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="conversations.conversation")),
                ("organization", models.ForeignKey(help_text="Tenant organization owning the message.", on_delete=django.db.models.deletion.PROTECT, related_name="conversation_messages", to="organizations.organization")),
            ],
            options={
                "verbose_name": "Conversation Message",
                "verbose_name_plural": "Conversation Messages",
                "ordering": ["sequence", "created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(fields=["organization", "project", "status"], name="conversatio_organiz_e1ff9e_idx"),
        ),
        migrations.AddIndex(
            model_name="conversationmessage",
            index=models.Index(fields=["organization", "conversation", "sequence"], name="conversatio_organiz_57f66a_idx"),
        ),
        migrations.AddConstraint(
            model_name="conversationmessage",
            constraint=models.UniqueConstraint(fields=("conversation", "sequence"), name="unique_conversation_sequence"),
        ),
        migrations.AddConstraint(
            model_name="conversationmessage",
            constraint=models.UniqueConstraint(condition=models.Q(client_message_id__isnull=False), fields=("conversation", "client_message_id"), name="unique_conversation_client_message_id"),
        ),
    ]
