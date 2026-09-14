"""Tests for Telegram bot handlers (``bot.telegram_handlers``): non-PDF and
oversized-file rejection (mocked, no real Telegram network calls), the
BOT_TOKEN-required guard, and RetryAfter-based rate-limit retry behavior.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.error import RetryAfter

from bot.config import Settings
from bot.jobs import JobManager
from bot.telegram_handlers import _send_with_retry, build_application, handle_document


def _make_context(settings: Settings, job_manager: JobManager) -> MagicMock:
    context = MagicMock()
    context.application.bot_data = {"settings": settings, "job_manager": job_manager}
    context.bot.get_file = AsyncMock()
    return context


def _make_update(mime_type: str, file_name: str, file_size: int) -> MagicMock:
    update = MagicMock()
    document = MagicMock()
    document.mime_type = mime_type
    document.file_name = file_name
    document.file_size = file_size
    document.file_id = "fake-file-id"
    update.message.document = document
    update.message.reply_text = AsyncMock()
    update.effective_chat.id = 12345
    return update


async def test_handle_document_rejects_non_pdf(tmp_path):
    settings = Settings(upload_dir=str(tmp_path / "uploads"), output_dir=str(tmp_path / "output"))
    job_manager = JobManager(settings=settings)
    context = _make_context(settings, job_manager)
    update = _make_update("image/png", "photo.png", 1000)

    await handle_document(update, context)

    update.message.reply_text.assert_awaited_once()
    context.bot.get_file.assert_not_called()
    assert await job_manager.list_jobs() == []


async def test_handle_document_rejects_oversized_file_without_downloading(tmp_path):
    settings = Settings(
        upload_dir=str(tmp_path / "uploads"),
        output_dir=str(tmp_path / "output"),
        max_file_size_mb=1,
    )
    job_manager = JobManager(settings=settings)
    context = _make_context(settings, job_manager)
    update = _make_update("application/pdf", "big.pdf", 5 * 1024 * 1024)

    await handle_document(update, context)

    update.message.reply_text.assert_awaited_once()
    context.bot.get_file.assert_not_called()
    assert await job_manager.list_jobs() == []


async def test_handle_document_accepts_pdf_and_starts_a_job(tmp_path):
    import asyncio

    settings = Settings(upload_dir=str(tmp_path / "uploads"), output_dir=str(tmp_path / "output"))
    job_manager = JobManager(settings=settings)
    context = _make_context(settings, job_manager)
    update = _make_update("application/pdf", "book.pdf", 1000)

    fake_file = MagicMock()
    fake_file.download_to_drive = AsyncMock()
    context.bot.get_file = AsyncMock(return_value=fake_file)

    await handle_document(update, context)

    context.bot.get_file.assert_awaited_once_with("fake-file-id")
    fake_file.download_to_drive.assert_awaited_once()

    jobs = await job_manager.list_jobs()
    assert len(jobs) == 1

    # Let the background pipeline task run (and fail harmlessly, since the
    # download was mocked and no real PDF bytes were written to disk) rather
    # than leaving a dangling unawaited task.
    await asyncio.sleep(0.2)


def test_build_application_requires_bot_token():
    settings = Settings(bot_token=None)
    with pytest.raises(ValueError):
        build_application(settings, None)


def test_build_application_succeeds_with_a_token():
    settings = Settings(bot_token="123456:FAKE-TEST-TOKEN")
    application = build_application(settings, None)
    assert application.bot_data["settings"] is settings


async def test_send_with_retry_honors_retry_after_then_succeeds():
    calls = {"count": 0}

    async def flaky():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RetryAfter(0.01)
        return "ok"

    result = await _send_with_retry(flaky, max_retries=2)

    assert result == "ok"
    assert calls["count"] == 2


async def test_send_with_retry_raises_after_exhausting_retries():
    async def always_rate_limited():
        raise RetryAfter(0.01)

    with pytest.raises(RetryAfter):
        await _send_with_retry(always_rate_limited, max_retries=1)
