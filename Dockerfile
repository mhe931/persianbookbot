# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: builder - install Python dependencies into a virtualenv using
# build tooling that is NOT needed at runtime (keeps the final image small).
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Build-time system packages: a C toolchain is occasionally required to
# build source distributions for transitive dependencies that don't ship a
# manylinux wheel for the current platform (e.g. on non-amd64 hosts).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /build
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: runtime - minimal image with only the libraries needed to run the
# app (PyMuPDF/Pillow image codecs, optional Tesseract OCR backend), a
# non-root user, and the pre-built virtualenv from the builder stage.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="persianbookbot" \
      org.opencontainers.image.description="Telegram bot + Mini App that converts scanned Persian PDF books into EPUB/DOCX/TXT." \
      org.opencontainers.image.source="https://github.com/persianbookbot/persianbookbot"

# Runtime system libraries:
#   - libjpeg62-turbo, zlib1g, libopenjp2-7, libtiff6, libfreetype6: image
#     codecs used transitively by Pillow/PyMuPDF for JPEG/PNG/JP2/TIFF
#     decoding and font rendering.
#   - fontconfig: font discovery for DOCX/EPUB text rendering fallbacks.
#   - curl: used by the container HEALTHCHECK to probe GET /api/health.
#   - tesseract-ocr + tesseract-ocr-fas: OPTIONAL system packages so
#     OCR_ENGINE=tesseract works out of the box with Persian language data;
#     the default OCR_ENGINE=dummy never touches these, so they add image
#     size but no runtime requirement/credential.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
        libopenjp2-7 \
        libtiff6 \
        libfreetype6 \
        fontconfig \
        curl \
        tesseract-ocr \
        tesseract-ocr-fas \
    && rm -rf /var/lib/apt/lists/*

# Non-root application user - fixed UID/GID 1000 so bind-mounted
# ./data host directories can be given matching ownership on the host
# without relying on user namespace remapping.
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Bring in the pre-built virtualenv (no build toolchain in the final image).
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

# Safe runtime environment defaults. BOT_TOKEN/VISION_LLM_API_KEY are
# deliberately NOT set here - they must be injected at container run time
# (env_file/-e/secrets manager), never baked into the image. These mirror
# bot.config.Settings defaults so the container behaves the same as a bare
# `python -m bot.main` run with no .env present.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    BOT_ENV_FILE="" \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    OCR_ENGINE=dummy \
    UPLOAD_DIR=/app/data/uploads \
    OUTPUT_DIR=/app/data/output \
    LOG_FORMAT=console \
    LOG_LEVEL=INFO \
    JOB_RETENTION_SECONDS=86400 \
    CLEANUP_INTERVAL_SECONDS=3600

# Application source (only what's needed at runtime).
COPY --chown=app:app src/ ./src/
COPY --chown=app:app web/ ./web/
COPY --chown=app:app pyproject.toml ./

# Persistent runtime data directories, owned by the non-root app user with
# no group/other write access beyond what the app itself needs.
RUN mkdir -p /app/data/uploads /app/data/output \
    && chown -R app:app /app/data \
    && chmod -R 750 /app/data

USER app

EXPOSE 8000

# Liveness probe against the dependency-free GET /api/health endpoint (see
# src/bot/api.py). A generous start-period allows for slow-starting hosts
# without falsely marking the container unhealthy during boot.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail --silent "http://localhost:${API_PORT}/api/health" || exit 1

ENTRYPOINT ["python", "-m", "bot.main"]
