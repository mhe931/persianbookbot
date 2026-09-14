"""Tests for ``bot.jobs.JobManager``: successful pipeline runs, failure
containment, and rate-limit fallback behavior - all using the offline
``DummyOCREngine`` (or monkeypatched engines) so no credentials/network are
ever required.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from bot.config import Settings
from bot.jobs import JobManager
from common.models import JobStatus
from ocr.engine import RateLimitError


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        output_dir=str(tmp_path / "output"),
        upload_dir=str(tmp_path / "uploads"),
        ocr_engine="dummy",
        rate_limit_max_retries=1,
        rate_limit_backoff_seconds=0.0,
    )


async def test_create_and_get_job_roundtrip(tmp_path):
    manager = JobManager(settings=_settings(tmp_path))

    job = await manager.create_job("book.pdf")
    fetched = await manager.get_job(job.job_id)

    assert fetched is job
    assert job.status == JobStatus.PENDING
    assert (await manager.list_jobs()) == [job]


async def test_get_job_returns_none_for_unknown_id(tmp_path):
    manager = JobManager(settings=_settings(tmp_path))
    assert await manager.get_job("does-not-exist") is None


async def test_run_pipeline_succeeds_and_produces_all_formats(tmp_path, sample_pdf_path):
    manager = JobManager(settings=_settings(tmp_path))
    job = await manager.create_job("sample.pdf")

    await manager.run_pipeline(job.job_id, sample_pdf_path)

    assert job.status == JobStatus.DONE
    assert job.progress == 1.0
    assert job.error is None
    assert set(job.output_paths) == {"txt", "docx", "epub"}
    for path_str in job.output_paths.values():
        assert Path(path_str).exists()
        assert Path(path_str).stat().st_size > 0


async def test_run_pipeline_unknown_job_id_is_a_noop(tmp_path, sample_pdf_path):
    manager = JobManager(settings=_settings(tmp_path))
    # Must not raise even though no job with this id was created.
    await manager.run_pipeline("does-not-exist", sample_pdf_path)


async def test_run_pipeline_marks_failed_on_render_error(tmp_path):
    manager = JobManager(settings=_settings(tmp_path))
    job = await manager.create_job("missing.pdf")

    await manager.run_pipeline(job.job_id, tmp_path / "does-not-exist.pdf")

    assert job.status == JobStatus.FAILED
    assert job.error


async def test_run_pipeline_marks_rate_limited_when_engine_exhausts_retries(
    tmp_path, sample_pdf_path, monkeypatch
):
    manager = JobManager(settings=_settings(tmp_path))
    job = await manager.create_job("sample.pdf")

    class _AlwaysRateLimited:
        def recognize(self, page):
            raise RateLimitError("simulated rate limit", retry_after=0.0)

    monkeypatch.setattr("bot.jobs.get_ocr_engine", lambda name=None: _AlwaysRateLimited())

    await manager.run_pipeline(job.job_id, sample_pdf_path)

    assert job.status == JobStatus.RATE_LIMITED
    assert job.error
    assert job.output_paths == {}


async def test_run_pipeline_marks_failed_on_converter_error(tmp_path, sample_pdf_path, monkeypatch):
    manager = JobManager(settings=_settings(tmp_path))
    job = await manager.create_job("sample.pdf")

    def _boom(book, output_path, font_name=None):
        raise RuntimeError("simulated converter failure")

    monkeypatch.setattr("bot.jobs.write_txt", _boom)

    await manager.run_pipeline(job.job_id, sample_pdf_path)

    assert job.status == JobStatus.FAILED
    assert "simulated converter failure" in job.error
