"""Persian/Arabic RTL text helpers.

Two distinct concerns are handled here:

* **Visual** reordering (``shape_rtl``) - joins Arabic/Persian letterforms and
  reorders the string into left-to-right visual order, for contexts (e.g.
  fixed-width terminal/image rendering) that have no bidi engine of their own.
* **Logical** order (``assemble_rtl_paragraph``) - for rich document formats
  (EPUB/DOCX) that have their own bidi engines, text should stay in logical
  (reading) order and RTL-ness should be expressed via a ``dir="rtl"``/bidi
  flag on the container element instead of visually reordering characters.
"""
from __future__ import annotations

import arabic_reshaper
from bidi.algorithm import get_display

_WESTERN_TO_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_ARABIC_RANGES = (
    (0x0600, 0x06FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)


def shape_rtl(text: str) -> str:
    """Reshape and bidi-reorder ``text`` into visual RTL display order.

    Use this only for rendering contexts without their own bidi engine
    (e.g. drawing text onto an image). Do not use it for EPUB/DOCX content.
    """
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def normalize_persian_digits(text: str) -> str:
    """Convert Western (0-9) digits in ``text`` to Persian digits (۰-۹)."""
    return text.translate(_WESTERN_TO_PERSIAN_DIGITS)


def _is_arabic_letter(char: str) -> bool:
    code_point = ord(char)
    return any(start <= code_point <= end for start, end in _ARABIC_RANGES)


def is_rtl_text(text: str) -> bool:
    """Heuristic: True if most alphabetic characters in ``text`` are Arabic/Persian."""
    alphabetic = [ch for ch in text if ch.isalpha()]
    if not alphabetic:
        return False
    arabic_count = sum(1 for ch in alphabetic if _is_arabic_letter(ch))
    return arabic_count / len(alphabetic) > 0.5


def assemble_rtl_paragraph(text: str) -> str:
    """Return ``text`` unchanged, preserving logical (reading) order.

    Document formats like EPUB and DOCX have their own bidi algorithms and
    expect text in logical order plus a ``dir="rtl"``/bidi flag on the
    container - not visually pre-reordered text like ``shape_rtl`` produces.
    This wrapper exists so callers can be explicit about that intent.
    """
    return text
