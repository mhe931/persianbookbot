"""Persian font configuration hooks.

This module does NOT bundle or ship any font binary (font licensing is out
of scope for this project). It only centralizes the *name* of the Persian
font family that generated documents should reference, plus an optional
hook for a locally-supplied font file path that a deployer may configure
via environment variables. Consumers must gracefully fall back to
font-name-only substitution when no font file is configured.
"""
from __future__ import annotations

import os

DEFAULT_PERSIAN_FONT = "Vazirmatn"


def get_persian_font_name(override: str | None = None) -> str:
    """Return the Persian font family name to use in generated documents.

    Priority: explicit ``override`` argument, then the ``PERSIAN_FONT_NAME``
    environment variable, then :data:`DEFAULT_PERSIAN_FONT`.
    """
    if override:
        return override
    return os.environ.get("PERSIAN_FONT_NAME", DEFAULT_PERSIAN_FONT)


def get_font_file_path(override: str | None = None) -> str | None:
    """Return an optional path to a locally-supplied font file.

    Priority: explicit ``override`` argument, then the ``PERSIAN_FONT_PATH``
    environment variable. Returns ``None`` if not configured; callers must
    handle that by relying on font-name substitution only (no font is
    bundled with this project).
    """
    if override:
        return override
    return os.environ.get("PERSIAN_FONT_PATH")
