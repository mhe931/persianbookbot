"""Tests for ``bot.logging_config``: JSON/console formatters, ``log_event``
context attachment, ``log_duration`` timing/error capture, and the secret-key
scrubbing guarantee - all pure/offline (no credentials, no network).
"""
from __future__ import annotations

import json
import logging

import pytest

from bot.logging_config import (
    ConsoleContextFormatter,
    JsonFormatter,
    configure_logging,
    log_duration,
    log_event,
)


def _make_logger(name: str, formatter: logging.Formatter) -> tuple[logging.Logger, list[str]]:
    """A logger wired to an in-memory handler so tests can inspect output
    without touching real stdout/stderr or global logging state.
    """
    records: list[str] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(formatter.format(record))

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.handlers.clear()
    logger.addHandler(_ListHandler())
    return logger, records


def test_json_formatter_includes_context_fields():
    logger, records = _make_logger("test.json.context", JsonFormatter())

    log_event(logger, "job finished", job_id="abc123", user_id=42, duration=1.2345)

    assert len(records) == 1
    payload = json.loads(records[0])
    assert payload["message"] == "job finished"
    assert payload["level"] == "INFO"
    assert payload["job_id"] == "abc123"
    assert payload["user_id"] == 42
    assert payload["duration"] == 1.2345


def test_json_formatter_output_is_valid_single_line_json():
    logger, records = _make_logger("test.json.singleline", JsonFormatter())

    log_event(logger, "message with\nnewline", job_id="j1")

    assert len(records) == 1
    assert "\n" not in records[0]
    json.loads(records[0])  # must not raise


def test_console_formatter_appends_context_bracket():
    logger, records = _make_logger("test.console.context", ConsoleContextFormatter())

    log_event(logger, "job started", job_id="abc123")

    assert len(records) == 1
    assert "job started" in records[0]
    assert "[job_id=abc123]" in records[0]


def test_console_formatter_without_context_has_no_brackets():
    logger, records = _make_logger("test.console.nocontext", ConsoleContextFormatter())

    logger.info("plain message")

    assert len(records) == 1
    assert "[" not in records[0]


@pytest.mark.parametrize("formatter_cls", [JsonFormatter, ConsoleContextFormatter])
def test_forbidden_keys_are_never_rendered(formatter_cls):
    logger, records = _make_logger(f"test.secrets.{formatter_cls.__name__}", formatter_cls())

    log_event(
        logger,
        "job started",
        job_id="abc123",
        bot_token="123:SHOULD-NOT-APPEAR",
        api_key="SHOULD-NOT-APPEAR-EITHER",
    )

    assert len(records) == 1
    assert "SHOULD-NOT-APPEAR" not in records[0]
    assert "bot_token" not in records[0]
    assert "api_key" not in records[0]


def test_log_duration_success_records_duration_and_reraises_nothing():
    logger, records = _make_logger("test.duration.success", JsonFormatter())

    with log_duration(logger, "operation completed", job_id="job-1"):
        pass

    assert len(records) == 1
    payload = json.loads(records[0])
    assert payload["job_id"] == "job-1"
    assert payload["duration"] >= 0
    assert "error" not in payload


def test_log_duration_failure_records_error_and_reraises():
    logger, records = _make_logger("test.duration.failure", JsonFormatter())

    with pytest.raises(RuntimeError, match="boom"):
        with log_duration(logger, "operation failed", job_id="job-2"):
            raise RuntimeError("boom")

    assert len(records) == 1
    payload = json.loads(records[0])
    assert payload["level"] == "ERROR"
    assert payload["job_id"] == "job-2"
    assert payload["error"] == "boom"
    assert payload["duration"] >= 0


def test_configure_logging_console_is_idempotent_and_credential_free():
    configure_logging(log_format="console", level="DEBUG")
    configure_logging(log_format="console", level="INFO")

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, ConsoleContextFormatter)


def test_configure_logging_json_selects_json_formatter():
    configure_logging(log_format="json", level="INFO")

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JsonFormatter)

    # Restore console formatting so subsequent tests/modules aren't left with
    # JSON-formatted root logging as a side effect of this test.
    configure_logging(log_format="console", level="INFO")
