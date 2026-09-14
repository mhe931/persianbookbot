"""Async in-memory job orchestration for PDF -> {txt,docx,epub} conversions.

``JobManager`` tracks ``ConversionJob`` records and drives each job through
the OCR pipeline and format converters, updating status/progress as it goes.
A module-level ``default_job_manager`` singleton is provided so the Telegram
bot handlers and the FastAPI Mini App backend can share the same in-memory
job store when wired together in ``bot.main``.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from common.models import ConversionJob, JobStatus

from ocr.engine import RateLimitError, get_ocr_engine
from ocr.pipeline import process_pdf

from converters.docx_writer import write_docx
from converters.epub_writer import write_epub
from converters.txt import write_txt

from bot.config import Settings, get_settings

logger = logging.getLogger(__name__)


class JobManager:
    """Simple async in-memory manager for conversion jobs."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings
        self._jobs: dict[str, ConversionJob] = {}
        self._lock = asyncio.Lock()

    @property
    def settings(self) -> Settings:
        # Resolved lazily so a manager created at import time picks up
        # settings (and any test monkeypatching) at call time, not import time.
        return self._settings or get_settings()

    async def create_job(self, source_filename: str, chat_id: int | None = None) -> ConversionJob:
        job = ConversionJob(source_filename=source_filename, chat_id=chat_id)
        async with self._lock:
            self._jobs[job.job_id] = job
        return job

    async def get_job(self, job_id: str) -> ConversionJob | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def list_jobs(self) -> list[ConversionJob]:
        async with self._lock:
            return list(self._jobs.values())

    async def run_pipeline(self, job_id: str, pdf_path: str | Path) -> None:
        """Run the full OCR + conversion pipeline for ``job_id``.

        This is the top-level entry point for a background task, so all
        exceptions are caught here and translated into a terminal job status
        rather than propagating and crashing the caller's task.
        """
        job = await self.get_job(job_id)
        if job is None:
            logger.warning("run_pipeline called for unknown job_id=%s", job_id)
            return

        settings = self.settings

        def _on_progress(fraction: float) -> None:
            # process_pdf invokes this synchronously (page-by-page) from the
            # same coroutine/event loop, so a direct call is safe here; it
            # maps OCR progress onto the job's OCR_RUNNING phase.
            job.mark(JobStatus.OCR_RUNNING, progress=fraction)

        try:
            job.mark(JobStatus.PREPROCESSING, progress=0.0)

            book = await process_pdf(
                pdf_path,
                engine=get_ocr_engine(settings.ocr_engine),
                max_retries=settings.rate_limit_max_retries,
                backoff_seconds=settings.rate_limit_backoff_seconds,
                progress_callback=_on_progress,
            )
        except RateLimitError as e:
            job.mark(JobStatus.RATE_LIMITED, error=str(e))
            return
        except Exception as e:  # noqa: BLE001 - top-level job runner must contain all errors
            job.mark(JobStatus.FAILED, error=str(e))
            return

        try:
            job.mark(JobStatus.CONVERTING, progress=0.0)

            job_output_dir = Path(settings.output_dir) / job_id
            output_paths: dict[str, str] = {}

            txt_path = write_txt(book, job_output_dir / "book.txt")
            output_paths["txt"] = str(txt_path)

            docx_path = write_docx(book, job_output_dir / "book.docx", font_name=settings.persian_font_name)
            output_paths["docx"] = str(docx_path)

            epub_path = write_epub(book, job_output_dir / "book.epub", font_name=settings.persian_font_name)
            output_paths["epub"] = str(epub_path)

            job.output_paths = output_paths
            job.mark(JobStatus.DONE, progress=1.0)
        except Exception as e:  # noqa: BLE001 - contain converter failures within the job
            job.mark(JobStatus.FAILED, error=str(e))
            return


# Shared singleton so the Telegram bot handlers and the FastAPI Mini App
# backend can operate on the same in-memory job store when wired together.
default_job_manager = JobManager()
