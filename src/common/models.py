"""Shared data models used across the OCR pipeline, converters, and bot layers.

Keeping these models in one place lets the OCR/pipeline, document-generation,
and Telegram bot subsystems agree on a single contract without importing each
other's internals.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class JobStatus(str, Enum):
    """Lifecycle states for a single book-conversion job."""

    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    OCR_RUNNING = "ocr_running"
    ASSEMBLING = "assembling"
    CONVERTING = "converting"
    DONE = "done"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"

    @property
    def is_terminal(self) -> bool:
        return self in (JobStatus.DONE, JobStatus.FAILED)


@dataclass
class PageImage:
    """A single rendered page ready for OCR."""

    page_number: int
    width: int
    height: int
    dpi: int = 300
    # Raw image bytes (e.g. PNG) - kept optional so lightweight pipelines /
    # tests can operate on metadata only without holding large buffers.
    data: bytes | None = None


@dataclass
class PageText:
    """OCR result for a single page."""

    page_number: int
    text: str
    confidence: float = 1.0
    direction: str = "rtl"


@dataclass
class Book:
    """Fully assembled book content, ready for format conversion."""

    title: str
    pages: list[PageText] = field(default_factory=list)
    language: str = "fa"
    direction: str = "rtl"
    author: str | None = None

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in sorted(self.pages, key=lambda p: p.page_number))

    @property
    def average_confidence(self) -> float:
        if not self.pages:
            return 0.0
        return sum(p.confidence for p in self.pages) / len(self.pages)


def new_job_id() -> str:
    return uuid.uuid4().hex


@dataclass
class ConversionJob:
    """Tracks the end-to-end state of one PDF -> {epub,docx,txt} conversion."""

    job_id: str = field(default_factory=new_job_id)
    status: JobStatus = JobStatus.PENDING
    source_filename: str | None = None
    chat_id: int | None = None
    error: str | None = None
    progress: float = 0.0
    output_paths: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    retry_count: int = 0

    def touch(self) -> None:
        self.updated_at = time.time()

    def mark(self, status: JobStatus, *, progress: float | None = None, error: str | None = None) -> None:
        self.status = status
        if progress is not None:
            self.progress = progress
        if error is not None:
            self.error = error
        self.touch()

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "source_filename": self.source_filename,
            "error": self.error,
            "progress": self.progress,
            "output_paths": self.output_paths,
            "output_sizes": self._output_sizes(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "retry_count": self.retry_count,
        }

    def _output_sizes(self) -> dict[str, int]:
        """Best-effort file size (bytes) per output format, for Mini App
        download cards. Skips formats whose file is missing/unreadable
        rather than raising - this is presentational metadata only.
        """
        sizes: dict[str, int] = {}
        for fmt, path_str in self.output_paths.items():
            try:
                sizes[fmt] = Path(path_str).stat().st_size
            except OSError:
                continue
        return sizes
