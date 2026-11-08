# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies (curl for healthchecks, security tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, reliable package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create unprivileged system group and user
RUN groupadd -g 10001 verity && \
    useradd -u 10001 -g verity -m -s /bin/bash verity

# Copy dependency specifications first to leverage Docker layer caching
COPY pyproject.toml requirements.txt ./

# Install dependencies into system Python environment
RUN uv pip install --system -r requirements.txt

# Create storage directories and set permissions for unprivileged user
RUN mkdir -p /app/data/sqlite /app/data/faiss /app/data/uploads /app/data/quarantine && \
    chown -R verity:verity /app/data

# Copy application source code
COPY --chown=verity:verity . .

# Drop privileges to non-root user
USER verity

# Expose backend API service port
EXPOSE 8000

# Health check configuration (non-blocking liveness probe)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Production startup command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
