# syntax=docker/dockerfile:1

# Base image pinned to the multi-arch index digest of the official python:3.12-slim tag.
# Source: https://hub.docker.com/v2/repositories/library/python/tags/3.12-slim
# Consulted and user-verified 2026-11-18; media_type=application/vnd.oci.image.index.v1+json.
# Per-architecture digests from the tag's "images" array are deliberately not used.
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN python -m venv /opt/venv

COPY requirements.lock ./

# Only hash-pinned runtime dependencies are installed. The project itself is not
# installed: its source tree is copied read-only into the runtime stage.
RUN /opt/venv/bin/pip install --no-cache-dir --require-hashes -r requirements.lock

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH="/opt/venv/bin:$PATH"

# CVE-2026-85091 (HIGH): zlib1g 1:1.3.dfsg+really1.3.1-1+b1 has a heap buffer
# overflow in gz_vacate. Pin the patched version from Debian 13 security.
# Remove this layer when the pinned base digest already ships the fix;
# Dependabot will propose the new digest for docker.
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade \
        zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1 \
    && rm -rf /var/lib/apt/lists/*

# CVE-2026-124851 (HIGH): libzstd1 1.5.7+dfsg-1 has a vulnerability.
# Pin the patched version from Debian 13 security.
# Remove this layer when the pinned base digest already ships the fix.
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade \
        libzstd1=1.5.7+dfsg-1+deb13u1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

# Everything below is owned by root with read/execute permissions only for uid 10001.
# No chown/chmod is used: Docker's default 0644/0755 modes already deny writes to the app.
COPY --from=builder /opt/venv /opt/venv
COPY src /app/src

WORKDIR /app
USER 10001:10001
EXPOSE 8000

CMD ["uvicorn", "thehouse_genai.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header", "--workers", "1"]
