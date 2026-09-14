"""FastAPI backend for the Telegram Mini App.

Exposes upload/status/download endpoints under ``/api`` and serves the
static Mini App frontend (``web/``) at ``/``. Fully importable and testable
without a bot token or network access.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from common.models import JobStatus

from bot.config import get_settings
from bot.jobs import default_job_manager

logger = logging.getLogger(__name__)

app = FastAPI(title="Persian Book Bot API")

# Shared singleton so the Telegram bot side and the API side operate on the
# same in-memory job store when wired together in ``bot.main``.
job_manager = default_job_manager

_VALID_FORMATS = {"txt", "docx", "epub"}


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
