"""Structured logging for the bot/API layer.

Provides a JSON or human-readable console formatter that can attach
contextual fields (``job_id``, ``user_id``, ``duration``, ``error``, ...)
to log records, plus small helpers (``log_event``/``log_duration``) so call
sites in ``bot.jobs``/``bot.api`` don't need to build ``extra=`` dicts by
hand.

Credential safety: both formatters and ``log_event`` drop any well-known
secret-shaped key (``bot_token``, ``api_key``, ``password``, ...) before a
record is ever rendered, on top of the existing project rule that
``Settings``/credentials are never passed into logging calls in the first
place (defense in depth, not a substitute for that rule).
"""
from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

# Keys that must never appear in a structured log record, even if a caller
# accidentally passes one via ``log_event(..., **extra)``.
_FORBIDDEN_CONTEXT_KEYS = frozenset(
    {
        "bot_token",
        "token",
        "api_key",
        "vision_llm_api_key",
        "password",
        "secret",
        "webhook_url",
    }
)

# Standard attributes every ``logging.LogRecord`` has - used to find the
# "extra" fields a caller attached via ``extra={...}``.
_RESERVED_LOGRECORD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()
) | {"message", "asctime"}


def _extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _RESERVED_LOGRECORD_ATTRS
        and key not in _FORBIDDEN_CONTEXT_KEYS
        and not key.startswith("_")
    }


class JsonFormatter(logging.Formatter):
    """Render each log record as a single-line JSON object.

    Suitable for log aggregation systems that expect structured JSON logs
    (one object per line) rather than free-form text.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_extra_fields(record))
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleContextFormatter(logging.Formatter):
    """Human-readable console format with structured context appended.

    Example: ``2026-09-14 10:00:00 INFO bot.jobs: job finished
    [duration=1.23 job_id=abc123]``
    """

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = _extra_fields(record)
        if not extras:
            return base
        context = " ".join(f"{key}={value}" for key, value in sorted(extras.items()))
        return f"{base} [{context}]"


def configure_logging(*, log_format: str = "console", level: str | int = "INFO") -> None:
    """Configure the root logger once at process startup.

    ``log_format``: ``"json"`` for structured JSON logs (recommended when
    shipping logs to an aggregator), or ``"console"`` (default) for a
    human-readable format with the same contextual fields appended. Safe to
    call more than once (e.g. in tests) - it replaces the handler set rather
    than accumulating duplicate handlers.
    """
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if log_format == "json" else ConsoleContextFormatter())

    root.handlers.clear()
    root.addHandler(handler)


def log_event(
    logger: logging.Logger,
    message: str,
    *,
    level: int = logging.INFO,
    job_id: str | None = None,
    user_id: int | str | None = None,
    duration: float | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    """Emit a structured log record with common job/request context.

    Only pass identifiers/metrics/error strings via ``job_id``/``user_id``/
    ``duration``/``error``/``**extra`` - never a credential or ``Settings``
    object. Any forbidden-looking key in ``**extra`` is silently dropped
    rather than raising, so a logging call itself can never crash a job.
    """
    context: dict[str, Any] = {}
    if job_id is not None:
        context["job_id"] = job_id
    if user_id is not None:
        context["user_id"] = user_id
    if duration is not None:
        context["duration"] = round(duration, 4)
    if error is not None:
        context["error"] = error
    for key, value in extra.items():
        if key in _FORBIDDEN_CONTEXT_KEYS:
            continue
        context[key] = value

    logger.log(level, message, extra=context)


@contextmanager
def log_duration(
    logger: logging.Logger,
    message: str,
    *,
    job_id: str | None = None,
    user_id: int | str | None = None,
    **extra: Any,
) -> Iterator[None]:
    """Log ``message`` on exit with an elapsed ``duration`` (seconds).

    On exception, logs at ``ERROR`` with the ``error`` string attached and
    re-raises the original exception unchanged - this is a logging helper
    only, never a substitute for a job's own error handling.
    """
    start = time.monotonic()
    try:
        yield
    except Exception as exc:  # noqa: BLE001 - re-raised immediately below
        log_event(
            logger,
            message,
            level=logging.ERROR,
            job_id=job_id,
            user_id=user_id,
            duration=time.monotonic() - start,
            error=str(exc),
            **extra,
        )
        raise
    else:
        log_event(
            logger,
            message,
            job_id=job_id,
            user_id=user_id,
            duration=time.monotonic() - start,
            **extra,
        )
