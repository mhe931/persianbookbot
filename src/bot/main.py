"""Entrypoint that wires together the Telegram bot and the FastAPI Mini App
backend, sharing a single ``JobManager`` between both.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

import uvicorn

from bot import api
from bot.config import get_settings
from bot.jobs import default_job_manager
from bot.logging_config import configure_logging
from bot.telegram_handlers import build_application

logger = logging.getLogger(__name__)


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

        application.run_polling()
    else:
        logger.warning(
            "BOT_TOKEN is not configured; running the Mini App API only (bot disabled)."
        )
        uvicorn.run(api.app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()
