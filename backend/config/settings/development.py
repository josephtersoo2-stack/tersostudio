"""Development settings for Tersuite AI Studio backend."""
from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# CORS permissive in development
CORS_ALLOW_ALL_ORIGINS = True

# Fallback in-memory channel layer for offline dev if Redis is not reachable
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# If Redis is explicitly available, use Redis channel layer
if os.getenv("USE_REDIS_CHANNELS", "False").lower() in ("true", "1"):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [os.getenv("REDIS_URL", "redis://localhost:6379/0")],
            },
        },
    }

# Development email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
