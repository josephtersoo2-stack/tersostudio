# Production Dockerfile for Tersuite AI Studio Backend
FROM python:3.12.11-slim-bookworm as base

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:0.8.13 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    PORT=8000 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definitions and lockfile first for layer caching
COPY pyproject.toml uv.lock /app/

# Install frozen production dependencies (excluding dev group)
RUN uv sync --frozen --no-dev

# Copy application source code
COPY . /app/

# Create a non-root user for security and adjust permissions
RUN useradd -m tersuite && chown -R tersuite:tersuite /app
USER tersuite

EXPOSE 8000

# Default entrypoint runs Daphne ASGI server
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
