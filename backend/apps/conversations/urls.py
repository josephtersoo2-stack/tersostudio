"""URL routes for Conversations domain."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import ConversationMessageViewSet, ConversationViewSet

router = DefaultRouter()
router.register("messages", ConversationMessageViewSet, basename="conversation-message")
router.register("", ConversationViewSet, basename="conversation")

urlpatterns = [
    path("", include(router.urls)),
]
