"""Django admin configuration for Conversations domain."""
from django.contrib import admin
from .models import Conversation, ConversationMessage


class ConversationMessageInline(admin.TabularInline):
    model = ConversationMessage
    extra = 0
    readonly_fields = ("sequence", "role", "author", "content", "client_message_id", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "purpose", "status", "organization", "next_message_sequence", "last_message_at", "created_at")
    list_filter = ("purpose", "status", "created_at")
    search_fields = ("title", "project__name", "organization__name")
    readonly_fields = ("id", "next_message_sequence", "last_message_at", "created_at", "updated_at")
    inlines = [ConversationMessageInline]


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sequence", "role", "author", "client_message_id", "created_at")
    list_filter = ("role", "content_format", "created_at")
    search_fields = ("conversation__title", "content", "author__email", "client_message_id")
    readonly_fields = ("id", "sequence", "created_at", "updated_at")
