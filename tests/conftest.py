"""Shared pytest fixtures for the persianbookbot test suite."""
from __future__ import annotations

from pathlib import Path

import pytest

from fixtures.pdf_factory import make_sample_pdf_bytes


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """A tiny 2-page synthetic PDF, in memory."""
    return make_sample_pdf_bytes(num_pages=2)


@pytest.fixture
def sample_pdf_path(tmp_path: Path, sample_pdf_bytes: bytes) -> Path:
    """A tiny 2-page synthetic PDF written to a temp file."""
    path = tmp_path / "sample.pdf"
    path.write_bytes(sample_pdf_bytes)
    return path
