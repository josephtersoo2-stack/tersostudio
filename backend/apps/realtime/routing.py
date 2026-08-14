"""WebSocket URL routing for realtime channels."""
from django.urls import re_path
from .consumers import EventStreamConsumer

websocket_urlpatterns = [
    re_path(r"^ws/v1/events/(?P<channel_name>[\w-]+)/$", EventStreamConsumer.as_asgi()),
    re_path(r"^ws/v1/events/$", EventStreamConsumer.as_asgi()),
]
