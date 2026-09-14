"""Application configuration for the bot/Mini App subsystem.

All configuration is loaded from environment variables (optionally via a
``.env`` file) using ``pydantic-settings``. Nothing here requires a real
Telegram bot token: ``bot_token`` defaults to ``None`` so importing this
module, running tests, or running the FastAPI Mini App backend alone never
needs a credential.
"""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The dotenv path used by ``Settings`` is resolved once at import time from
# the ``BOT_ENV_FILE`` environment variable so tests can make configuration
# loading hermetic (immune to an ambient local ``.env``) without ever
# touching the file itself:
#   - unset (default)      -> load "./.env" as usual (real runtime behavior).
#   - set to "" (empty)    -> dotenv loading is disabled entirely.
#   - set to a path        -> that path is used instead of "./.env".
# ``tests/conftest.py`` sets ``BOT_ENV_FILE=""`` before any test imports
# ``bot.config``, so the test suite never reads real secrets from a local
# ``.env`` file, regardless of what a developer has in their workspace.
_env_file_override = os.environ.get("BOT_ENV_FILE")
_DOTENV_PATH: str | None = ".env" if _env_file_override is None else (_env_file_override or None)


class Settings(BaseSettings):
    """Runtime configuration, sourced from environment variables / ``.env``."""

    # Telegram bot token from @BotFather. ``None`` disables the bot (API/Mini
    # App only mode) - safe default so no credential is ever required.
    bot_token: str | None = None

    # Host/port for the local FastAPI Mini App backend.
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # OCR engine backend: "dummy" (deterministic offline fallback), "tesseract",
    # "paddle", or "vision_llm".
    ocr_engine: str = "dummy"

    # PaddleOCR backend options (only used when ocr_engine="paddle"). GPU is
    # off by default so the safe/offline default never assumes CUDA.
    paddle_use_gpu: bool = False
    paddle_lang: str = "fa"

    # Vision-LLM backend options (only used when ocr_engine="vision_llm").
    # "gemini" or "claude"; api key must be supplied via env/.env, never
    # hardcoded, and is None by default so the engine fails clearly instead
    # of silently running unauthenticated.
    vision_llm_provider: str = "gemini"
    vision_llm_api_key: str | None = None
    vision_llm_model: str = "gemini-1.5-flash"

    # Directories for generated output artifacts and uploaded PDFs.
    output_dir: str = "./data/output"
    upload_dir: str = "./data/uploads"

    # Maximum accepted upload size in megabytes.
    max_file_size_mb: int = 20

    # Telegram/OCR rate-limit retry policy.
    rate_limit_max_retries: int = 3
    rate_limit_backoff_seconds: float = 2.0

    # Optional webhook URL if running the bot in webhook mode instead of polling.
    webhook_url: str | None = None

    # Optional Persian font family name used by DOCX/EPUB converters.
    persian_font_name: str | None = None

    # Structured logging (see ``bot.logging_config``): "console" (default,
    # human-readable with appended context) or "json" (one JSON object per
    # line, for log aggregation). Level is a standard ``logging`` level name.
    log_format: str = "console"
    log_level: str = "INFO"

    # How long (seconds) a finished job (done/failed/rate_limited) and its
    # associated upload/output files are kept before ``JobManager``'s
    # cleanup hook considers them stale and prunes them. Default: 24h.
    job_retention_seconds: int = 24 * 60 * 60

    model_config = SettingsConfigDict(
        env_file=_DOTENV_PATH,
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("bot_token", mode="before")
    @classmethod
    def _normalize_empty_bot_token(cls, value: object) -> object:
        """Treat empty/whitespace-only ``BOT_TOKEN`` values as unset.

        ``.env`` files commonly declare ``BOT_TOKEN=`` as a safe placeholder,
        which pydantic-settings loads as ``""`` rather than leaving the field
        unset. Normalize that (and any accidental ``"None"`` string) to
        ``None`` so credential-free defaults hold regardless of how the
        empty value was sourced.
        """
        if isinstance(value, str) and value.strip() in ("", "None"):
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    Cached so repeated calls (across handlers/modules) reuse the same
    parsed configuration instead of re-reading the environment each time.
    """
    return Settings()


def reset_settings_cache() -> None:
    """Clear the ``get_settings`` cache.

    Useful for tests that monkeypatch environment variables and need
    ``get_settings()`` to pick up the new values on the next call.
    """
    get_settings.cache_clear()
