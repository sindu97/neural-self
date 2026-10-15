# syntax=docker/dockerfile:1
# Production image. docker-compose.yml overrides the command and mounts the
# source for local development.

# ---- build: install the package and its dependencies into /install ----
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN pip install --prefix=/install .

# ---- runtime: no build tools, non-root user ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    LOG_FORMAT=json \
    UPLOAD_DIR=/app/storage/uploads

RUN useradd --create-home --uid 10001 app
WORKDIR /app

COPY --from=builder /install /usr/local
# Migrations are not part of the installed package; alembic reads them from here.
COPY alembic.ini ./
COPY src/neuralshelf/db/migrations ./src/neuralshelf/db/migrations
RUN mkdir -p /app/storage/uploads && chown -R app:app /app/storage

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=3)"

# Run `alembic upgrade head` (the compose `migrate` service) before starting.
# Behind a reverse proxy, also set FORWARDED_ALLOW_IPS to the proxy's address
# so rate limiting sees real client IPs.
CMD ["uvicorn", "neuralshelf.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-access-log"]
