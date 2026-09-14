"""Telegram bot handlers (python-telegram-bot v22 async API).

Registers ``/start``, ``/status``, and a document (PDF) upload handler that
kicks off the OCR/conversion pipeline via a shared ``JobManager``.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

from telegram import Update
from telegram.error import NetworkError, RetryAfter, TimedOut
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bot.config import Settings
from bot.jobs import JobManager, default_job_manager

logger = logging.getLogger(__name__)

T = TypeVar("T")

START_MESSAGE = (
    "\U0001F4D6 برای تبدیل کتاب اسکن‌شده به EPUB، DOCX و TXT، فایل PDF را ارسال کنید.\n"
    "پس از پردازش، لینک دانلود فرمت‌های مختلف در اختیار شما قرار می‌گیرد.\n\n"
    "\U0001F4D6 Send a scanned PDF to convert it into EPUB, DOCX, and TXT.\n"
    "Once processed, you will receive a job id and download links for each format."
)


async def _send_with_retry(coro_factory: Callable[[], Awaitable[T]], max_retries: int = 3) -> T:
    """Call ``coro_factory()`` with retries for Telegram rate-limit/network errors.

    ``coro_factory`` must be a zero-arg callable returning a fresh coroutine
    each time it is invoked, since a single coroutine object cannot be
    awaited twice.
    """
    attempt = 0
    while True:
        try:
            return await coro_factory()
        except RetryAfter as e:
            # Explicit Telegram rate-limit handling: honor the server's
            # requested backoff before retrying.
            await asyncio.sleep(e.retry_after)
            attempt += 1
            if attempt > max_retries:
                raise
        except (TimedOut, NetworkError):
            attempt += 1
            if attempt > max_retries:
                raise
            await asyncio.sleep(min(2**attempt, 10))


def _get_job_manager(context: ContextTypes.DEFAULT_TYPE) -> JobManager:
    # Prefer the manager stashed on the application (so the bot and the
    # FastAPI Mini App backend share state), falling back to the module-level
    # singleton on demand if the application wasn't wired up with one.
    manager = context.application.bot_data.get("job_manager")
    if manager is None:
        manager = default_job_manager
    return manager


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_with_retry(lambda: update.message.reply_text(START_MESSAGE))


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _send_with_retry(
            lambda: update.message.reply_text(
                "لطفا شناسه کار را وارد کنید / Please provide a job id: /status <job_id>"
            )
        )
        return

    job_id = context.args[0]
    job_manager = _get_job_manager(context)
    job = await job_manager.get_job(job_id)

    if job is None:
        await _send_with_retry(
            lambda: update.message.reply_text(f"کار با شناسه {job_id} پیدا نشد. / Job not found.")
        )
        return

    message = (
        f"وضعیت / Status: {job.status.value}\n"
        f"پیشرفت / Progress: {job.progress:.0%}"
    )
    if job.error:
        message += f"\nخطا / Error: {job.error}"

    await _send_with_retry(lambda: update.message.reply_text(message))


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    document = update.message.document

    filename = document.file_name or "document.pdf"
    is_pdf = (document.mime_type == "application/pdf") or filename.lower().endswith(".pdf")
    if not is_pdf:
        await _send_with_retry(
            lambda: update.message.reply_text(
                "فقط فایل PDF پذیرفته می‌شود. / Only PDF files are accepted."
            )
        )
        return

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    # Explicit large-file handling: check the declared size and reject
    # before downloading anything, to avoid wasting bandwidth/disk.
    if document.file_size and document.file_size > max_bytes:
        await _send_with_retry(
            lambda: update.message.reply_text(
                f"حجم فایل بیش از حد مجاز ({settings.max_file_size_mb}MB) است. / "
                f"File exceeds the maximum allowed size ({settings.max_file_size_mb}MB)."
            )
        )
        return

    await _send_with_retry(
        lambda: update.message.reply_text("\u23F3 پردازش آغاز شد... / Processing started...")
    )

    job_manager = _get_job_manager(context)
    job = await job_manager.create_job(source_filename=filename, chat_id=update.effective_chat.id)

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / f"{job.job_id}_{filename}"

    telegram_file = await _send_with_retry(lambda: context.bot.get_file(document.file_id))
    await _send_with_retry(lambda: telegram_file.download_to_drive(custom_path=str(pdf_path)))

    asyncio.create_task(job_manager.run_pipeline(job.job_id, pdf_path))

    await _send_with_retry(
        lambda: update.message.reply_text(
            f"\u2705 شناسه کار / Job id: {job.job_id}\n"
            "برای مشاهده وضعیت / To check status: /status " + job.job_id
        )
    )


def build_application(settings: Settings, job_manager: JobManager | None) -> Application:
    """Build and configure the ``telegram.ext.Application``.

    Raises ``ValueError`` if ``settings.bot_token`` is not configured;
    callers (e.g. ``bot.main``) must check for a token before invoking this.
    """
    if not settings.bot_token:
        raise ValueError("BOT_TOKEN is not configured")

    application = Application.builder().token(settings.bot_token).build()

    application.bot_data["settings"] = settings
    application.bot_data["job_manager"] = job_manager or default_job_manager

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    return application
