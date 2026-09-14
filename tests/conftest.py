"""Shared pytest fixtures for the persianbookbot test suite.

Test isolation: ``BOT_ENV_FILE`` is set to the empty string *before*
anything imports ``bot.config`` (conftest modules are loaded ahead of test
collection), which tells ``Settings`` to skip dotenv loading entirely - see
``bot.config``. This makes the whole suite hermetic against an ambient
local ``.env`` file (e.g. containing a real ``BOT_TOKEN``): tests only ever
see environment variables set explicitly via ``monkeypatch``/``Settings(...)``
kwargs, never values silently read from disk.
"""
from __future__ import annotations

import os

os.environ.setdefault("BOT_ENV_FILE", "")

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from fixtures.pdf_factory import make_sample_pdf_bytes  # noqa: E402

from bot.config import reset_settings_cache  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_settings_cache_around_each_test():
    """Ensure ``get_settings()`` never leaks a cached instance between tests.

    Runs before *and* after every test so a previous test's monkeypatched
    environment (or the ambient real environment) can never bleed into the
    next test's ``Settings`` instance.
    """
    reset_settings_cache()
    yield
    reset_settings_cache()


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
