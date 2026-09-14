"""Entrypoint that wires together the Telegram bot and the FastAPI Mini App
backend, sharing a single ``JobManager`` between both.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path

import uvicorn

from bot import api
from bot.config import Settings, get_settings
from bot.jobs import JobManager, default_job_manager
from bot.logging_config import configure_logging, log_event
from bot.telegram_handlers import build_application

logger = logging.getLogger(__name__)


async def periodic_cleanup_worker(
    job_manager: JobManager,
    settings: Settings,
    *,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Periodically invoke ``job_manager.cleanup_stale_jobs()``.

    Runs forever (once per ``settings.cleanup_interval_seconds``, default 1
    hour) until cancelled or ``stop_event`` is set, so a long-running
    ``bot.main`` process prunes finished jobs/files automatically instead of
    requiring an on-demand call. Requires no credentials/network access -
    only the in-memory ``job_manager`` and local filesystem paths already
    used by ``cleanup_stale_jobs()``.

    Set ``settings.cleanup_interval_seconds`` to a non-positive value to
    disable the periodic sweep entirely (the coroutine returns immediately
    without ever running the cleanup); it remains callable on demand via
    ``job_manager.cleanup_stale_jobs()``.

    ``asyncio.CancelledError`` (raised when the caller cancels the task,
    e.g. during shutdown) is allowed to propagate after logging so the
    worker's task completes cleanly rather than being swallowed.
    """
    interval = settings.cleanup_interval_seconds
    if interval <= 0:
        logger.info("Periodic cleanup worker disabled (cleanup_interval_seconds <= 0).")
        return

    log_event(
        logger,
        "periodic cleanup worker started",
        interval_seconds=interval,
        ttl_seconds=settings.job_retention_seconds,
    )
    try:
        while stop_event is None or not stop_event.is_set():
            try:
                if stop_event is not None:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=interval)
                        break  # stop_event was set while waiting.
                    except asyncio.TimeoutError:
                        pass
                else:
                    await asyncio.sleep(interval)
            except asyncio.CancelledError:
                raise

            try:
                await job_manager.cleanup_stale_jobs()
            except Exception as e:  # noqa: BLE001 - never let one bad sweep kill the worker.
                log_event(
                    logger,
                    "periodic cleanup sweep failed",
                    level=logging.ERROR,
                    error=str(e),
                )
    except asyncio.CancelledError:
        log_event(logger, "periodic cleanup worker cancelled")
        raise
    finally:
        log_event(logger, "periodic cleanup worker stopped")


def main() -> None:
    settings = get_settings()
    configure_logging(log_format=settings.log_format, level=settings.log_level)

    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    if settings.bot_token:
        application = build_application(settings, default_job_manager)

        # Run the FastAPI Mini App backend in a background thread so the
        # Telegram bot's blocking `run_polling()` can own the main thread,
        # per python-telegram-bot's synchronous-friendly design.
        api_thread = threading.Thread(
            target=uvicorn.run,
            args=(api.app,),
            kwargs={"host": settings.api_host, "port": settings.api_port, "log_level": "info"},
            daemon=True,
        )
        api_thread.start()

        # `run_polling()` owns its own event loop and runs post-init/
        # post-shutdown hooks around it, so the periodic cleanup worker is
        # scheduled/cancelled there rather than via a second loop.
        async def _post_init(app) -> None:  # noqa: ANN001 - PTB callback signature
            app.bot_data["cleanup_task"] = asyncio.ensure_future(
                periodic_cleanup_worker(default_job_manager, settings)
            )

        async def _post_shutdown(app) -> None:  # noqa: ANN001 - PTB callback signature
            task = app.bot_data.pop("cleanup_task", None)
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        application.post_init = _post_init
        application.post_shutdown = _post_shutdown

        application.run_polling()
    else:
        logger.warning(
            "BOT_TOKEN is not configured; running the Mini App API only (bot disabled)."
        )

        async def _run_api_with_cleanup() -> None:
            config = uvicorn.Config(
                api.app, host=settings.api_host, port=settings.api_port, log_level="info"
            )
            server = uvicorn.Server(config)

            cleanup_task = asyncio.ensure_future(
                periodic_cleanup_worker(default_job_manager, settings)
            )
            try:
                await server.serve()
            finally:
                cleanup_task.cancel()
                try:
                    await cleanup_task
                except asyncio.CancelledError:
                    pass

        asyncio.run(_run_api_with_cleanup())


if __name__ == "__main__":
    main()
