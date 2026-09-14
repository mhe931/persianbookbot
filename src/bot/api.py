"""FastAPI backend for the Telegram Mini App.

Exposes upload/status/download endpoints under ``/api`` and serves the
static Mini App frontend (``web/``) at ``/``. Fully importable and testable
without a bot token or network access.

Also exposes ``POST /api/telegram/webhook`` for webhook-mode deployments
(see ``bot.main`` and README.md "Webhook mode"); it is a no-op (503) unless
``bot.main`` wires a built ``telegram.ext.Application`` into
``app.state.telegram_application``, so importing/testing this module never
requires a bot token or network access.
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from telegram import Update
from telegram.ext import Application

from common.models import JobStatus

from bot.config import get_settings
from bot.jobs import default_job_manager

logger = logging.getLogger(__name__)

app = FastAPI(title="Persian Book Bot API")

# Populated by ``bot.main`` (webhook mode only) with the built
# ``telegram.ext.Application`` so the webhook route below can dispatch
# updates through the same handlers used by polling mode. Left ``None`` in
# polling mode and API-only mode, in which case the route below responds
# 503 instead of ever attempting to process an update.
app.state.telegram_application = None

# Process start time (monotonic clock) for the health endpoint's uptime
# figure - set at import time, never touched by requests.
_process_started_at = time.monotonic()

# Shared singleton so the Telegram bot side and the API side operate on the
# same in-memory job store when wired together in ``bot.main``.
job_manager = default_job_manager

_VALID_FORMATS = {"txt", "docx", "epub"}

# Path Telegram posts updates to in webhook mode - see README.md "Webhook
# mode" and ``bot.main``. Registered unconditionally (present even in
# polling/API-only mode) so its behavior is consistent and testable; it
# simply has nothing to dispatch to (503) unless webhook mode wired an
# ``Application`` into ``app.state.telegram_application``.
TELEGRAM_WEBHOOK_PATH = "/api/telegram/webhook"

_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


@app.post(TELEGRAM_WEBHOOK_PATH)
async def telegram_webhook(request: Request) -> dict:
    """Receive a Telegram update pushed by a webhook (reverse-proxy) setup.

    Validates ``X-Telegram-Bot-Api-Secret-Token`` against
    ``settings.webhook_secret`` *before* touching the request body: a
    missing header returns 401, and a present-but-wrong (or unconfigured)
    secret returns 403. The secret value is never logged, echoed, or
    included in any response. Only after validation does this parse the
    JSON body into a ``telegram.Update`` and dispatch it through the same
    ``Application`` (and therefore the same handlers) polling mode uses.
    """
    settings = get_settings()
    provided = request.headers.get(_SECRET_HEADER)

    if provided is None:
        raise HTTPException(status_code=401, detail="Missing secret token.")
    if not settings.webhook_secret or provided != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret token.")

    application: Application | None = app.state.telegram_application
    if application is None:
        raise HTTPException(
            status_code=503, detail="Telegram webhook is not active on this instance."
        )

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body.") from exc

    try:
        update = Update.de_json(payload, application.bot)
    except (TypeError, ValueError) as exc:
        # Telegram's Bot API guarantees well-formed updates, but a
        # misconfigured/forged request could post an unrelated JSON body;
        # fail with a clean 400 instead of a 500 traceback.
        raise HTTPException(status_code=400, detail="Invalid update payload.") from exc
    if update is None:
        raise HTTPException(status_code=400, detail="Invalid update payload.")

    await application.process_update(update)
    return {"ok": True}


@app.get("/api/health")
async def health() -> dict:
    """Lightweight liveness probe.

    Deliberately does no I/O and requires no configuration/credentials, so
    it stays fast and reliable for uptime checks/load balancers even if a
    downstream dependency (OCR engine, disk) is degraded. Never exposes
    configuration values or secrets - only a status flag and uptime.
    """
    return {
        "status": "ok",
        "uptime_seconds": round(time.monotonic() - _process_started_at, 3),
    }


@app.get("/api/config")
async def get_config() -> dict:
    """Expose the handful of settings the Mini App frontend needs to
    validate uploads client-side (max size, accepted formats) without
    hardcoding them separately from ``Settings``.
    """
    settings = get_settings()
    return {
        "max_file_size_mb": settings.max_file_size_mb,
        "formats": sorted(_VALID_FORMATS),
    }


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict:
    settings = get_settings()

    filename = file.filename or "document.pdf"
    is_pdf = (file.content_type == "application/pdf") or filename.lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    max_bytes = settings.max_file_size_mb * 1024 * 1024

    # Read in chunks so we can reject an oversized upload without buffering
    # the whole file in memory.
    chunk_size = 1024 * 1024
    data = bytearray()
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the maximum allowed size ({settings.max_file_size_mb}MB).",
            )

    job = await job_manager.create_job(source_filename=filename)

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / f"{job.job_id}_{filename}"
    pdf_path.write_bytes(bytes(data))

    asyncio.create_task(job_manager.run_pipeline(job.job_id, pdf_path))

    return {"job_id": job.job_id}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str) -> dict:
    job = await job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.to_dict()


@app.get("/api/download/{job_id}/{fmt}")
async def download_result(job_id: str, fmt: str) -> FileResponse:
    if fmt not in _VALID_FORMATS:
        raise HTTPException(status_code=404, detail="Unknown format.")

    job = await job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status != JobStatus.DONE:
        raise HTTPException(status_code=404, detail="Job is not finished yet.")

    path = job.output_paths.get(fmt)
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="Output file not available.")

    filename = f"{job.source_filename or 'book'}.{fmt}"
    return FileResponse(path, filename=filename)


# Mounted last so the /api/... routes above take precedence over the
# catch-all static file mount. Computed relative to this file's location
# (src/bot/api.py -> repo_root/web) and skipped gracefully if the directory
# doesn't exist (e.g. in minimal test environments).
_web_dir = Path(__file__).resolve().parents[2] / "web"
if _web_dir.exists():
    app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="web")
