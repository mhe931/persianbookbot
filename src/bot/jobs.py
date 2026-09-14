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
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from common.models import ConversionJob, JobStatus

from ocr.engine import RateLimitError, get_ocr_engine
from ocr.pipeline import process_pdf

from converters.docx_writer import write_docx
from converters.epub_writer import write_epub
from converters.txt import write_txt

from bot.config import Settings, get_settings
from bot.logging_config import log_event

logger = logging.getLogger(__name__)

# Job statuses eligible for retention cleanup: the pipeline has stopped
# making progress on these, so it is safe to prune them (and their files)
# once they are older than the configured TTL. Actively in-flight statuses
# are deliberately excluded so a slow/stalled job is never pruned mid-run.
_PRUNABLE_STATUSES = (JobStatus.DONE, JobStatus.FAILED, JobStatus.RATE_LIMITED)


@dataclass
class CleanupResult:
    """Summary of one ``JobManager.cleanup_stale_jobs()`` run."""

    removed_job_ids: list[str] = field(default_factory=list)
    files_removed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def removed_count(self) -> int:
        return len(self.removed_job_ids)


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
        log_event(logger, "job created", job_id=job.job_id, user_id=chat_id, source_filename=source_filename)
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
        user_id = job.chat_id
        pipeline_started = time.monotonic()
        log_event(logger, "job pipeline started", job_id=job_id, user_id=user_id)

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
            log_event(
                logger,
                "job rate limited",
                level=logging.WARNING,
                job_id=job_id,
                user_id=user_id,
                duration=time.monotonic() - pipeline_started,
                error=str(e),
            )
            return
        except Exception as e:  # noqa: BLE001 - top-level job runner must contain all errors
            job.mark(JobStatus.FAILED, error=str(e))
            log_event(
                logger,
                "job failed during OCR/preprocessing",
                level=logging.ERROR,
                job_id=job_id,
                user_id=user_id,
                duration=time.monotonic() - pipeline_started,
                error=str(e),
            )
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
            log_event(
                logger,
                "job pipeline finished",
                job_id=job_id,
                user_id=user_id,
                duration=time.monotonic() - pipeline_started,
                pages=len(book.pages),
            )
        except Exception as e:  # noqa: BLE001 - contain converter failures within the job
            job.mark(JobStatus.FAILED, error=str(e))
            log_event(
                logger,
                "job failed during conversion",
                level=logging.ERROR,
                job_id=job_id,
                user_id=user_id,
                duration=time.monotonic() - pipeline_started,
                error=str(e),
            )
            return

    async def cleanup_stale_jobs(
        self, *, ttl_seconds: float | None = None, now: float | None = None
    ) -> CleanupResult:
        """Prune finished jobs (and their upload/output files) past their TTL.

        Only jobs in a finished state (``DONE``, ``FAILED``, or
        ``RATE_LIMITED``) whose ``updated_at`` is older than ``ttl_seconds``
        (defaults to ``settings.job_retention_seconds``) are removed -
        actively in-flight jobs are never touched, regardless of age. File
        removal errors are caught per-path and recorded in the result rather
        than raised, so one bad path (permission error, already-deleted
        file, ...) never aborts cleanup of the remaining jobs.
        """
        settings = self.settings
        ttl = settings.job_retention_seconds if ttl_seconds is None else ttl_seconds
        current_time = time.time() if now is None else now
        result = CleanupResult()

        async with self._lock:
            stale_ids = [
                job_id
                for job_id, job in self._jobs.items()
                if job.status in _PRUNABLE_STATUSES and (current_time - job.updated_at) >= ttl
            ]
            for job_id in stale_ids:
                stale_job = self._jobs.pop(job_id)
                result.removed_job_ids.append(job_id)
                result.files_removed += self._remove_job_files(stale_job, settings, result.errors)

        if result.removed_job_ids or result.errors:
            log_event(
                logger,
                "job retention cleanup completed",
                level=logging.WARNING if result.errors else logging.INFO,
                removed_count=result.removed_count,
                files_removed=result.files_removed,
                error_count=len(result.errors),
                ttl_seconds=ttl,
            )
        return result

    @staticmethod
    def _remove_job_files(job: ConversionJob, settings: Settings, errors: list[str]) -> int:
        """Best-effort removal of a stale job's on-disk artifacts.

        Removes any known output files, the job's output directory, and any
        matching uploaded source file(s). Every deletion is wrapped so an
        ``OSError`` (permission denied, already gone, ...) is recorded in
        ``errors`` and skipped rather than raised.
        """
        removed = 0

        for path_str in set(job.output_paths.values()):
            path = Path(path_str)
            try:
                if path.exists():
                    path.unlink()
                    removed += 1
            except OSError as e:
                errors.append(f"{job.job_id}: failed to remove output file {path}: {e}")

        job_output_dir = Path(settings.output_dir) / job.job_id
        try:
            if job_output_dir.exists():
                shutil.rmtree(job_output_dir)
                removed += 1
        except OSError as e:
            errors.append(f"{job.job_id}: failed to remove output dir {job_output_dir}: {e}")

        upload_dir = Path(settings.upload_dir)
        try:
            if upload_dir.exists():
                for upload_path in upload_dir.glob(f"{job.job_id}_*"):
                    try:
                        upload_path.unlink()
                        removed += 1
                    except OSError as e:
                        errors.append(f"{job.job_id}: failed to remove upload {upload_path}: {e}")
        except OSError as e:
            errors.append(f"{job.job_id}: failed to scan upload dir {upload_dir}: {e}")

        return removed


# Shared singleton so the Telegram bot handlers and the FastAPI Mini App
# backend can operate on the same in-memory job store when wired together.
default_job_manager = JobManager()
