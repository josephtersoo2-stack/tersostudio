"""Test settings for Tersuite AI Studio backend.

Per project architecture rules, PostgreSQL is configured as the primary database
for testing PostgreSQL-specific features, schemas, and migrations.
"""
import os
from .base import *  # noqa: F403

DEBUG = False
TESTING = True

# Fast password hasher for test speed
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# PostgreSQL Test Database Configuration (Default)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://tersuite:tersuite_pass@localhost:5432/tersuite_test_db"),
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("TEST_DB_NAME", "tersuite_test_db"),
        "USER": os.getenv("DB_USER", "tersuite"),
        "PASSWORD": os.getenv("DB_PASSWORD", "tersuite_pass"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "TEST": {
            "NAME": os.getenv("TEST_DB_NAME", "tersuite_test_db"),
        },
        "OPTIONS": {
            "connect_timeout": 2,
        },
    }
}

if TEST_DATABASE_URL and TEST_DATABASE_URL.startswith("postgresql://"):
    try:
        import dj_database_url
        DATABASES["default"] = dj_database_url.parse(
            TEST_DATABASE_URL,
            engine="django.db.backends.postgresql",
            conn_max_age=0,
        )
        DATABASES["default"]["TEST"] = {"NAME": DATABASES["default"]["NAME"]}
        DATABASES["default"]["OPTIONS"] = {"connect_timeout": 2}
    except ImportError:
        pass

# Fallback switch for offline local test runs when PostgreSQL container is not booted
if os.getenv("TEST_USE_SQLITE", "0") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# In-memory channel layer for test isolation
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Celery eager task execution in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable verbose logging during tests
LOGGING["handlers"]["console"]["level"] = "ERROR"  # noqa: F405
