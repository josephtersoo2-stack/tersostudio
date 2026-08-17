"""Enums for Conversations and Messages."""
from django.db import models


class ConversationStatus(models.TextChoices):
    """Lifecycle status of a project conversation."""

    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class ConversationPurpose(models.TextChoices):
    """Purpose or phase of a conversation."""

    PROJECT_DISCOVERY = "PROJECT_DISCOVERY", "Project Discovery"
    PROJECT_PLANNING = "PROJECT_PLANNING", "Project Planning"
    GENERAL = "GENERAL", "General Project Discussion"


class MessageRole(models.TextChoices):
    """Author role for a message in a conversation."""

    USER = "USER", "User"
    ASSISTANT = "ASSISTANT", "Assistant"
    SYSTEM = "SYSTEM", "System"
    TOOL = "TOOL", "Tool Execution"


class MessageFormat(models.TextChoices):
    """Payload content format of a message."""

    MARKDOWN = "MARKDOWN", "Markdown"
    PLAIN_TEXT = "PLAIN_TEXT", "Plain Text"
    JSON = "JSON", "Structured JSON"
