"""Tests for the OCR/pipeline subsystem: rendering, preprocessing, engines,
RTL helpers, and the async orchestrator - all using the deterministic
``DummyOCREngine`` so no network access or credentials are ever required.
"""
from __future__ import annotations

import pytest

from common.models import PageImage
from ocr.engine import (
    DummyOCREngine,
    OCRError,
    RateLimitError,
    get_ocr_engine,
)
from ocr.pipeline import process_pdf
from ocr.preprocessing import preprocess_page, render_pdf_pages
from ocr.rtl import assemble_rtl_paragraph, is_rtl_text, normalize_persian_digits, shape_rtl


def test_render_pdf_pages_returns_one_entry_per_page(sample_pdf_path):
    pages = render_pdf_pages(sample_pdf_path, dpi=100)

    assert len(pages) == 2
    assert [p.page_number for p in pages] == [1, 2]
    assert all(p.data for p in pages)
    assert all(p.width > 0 and p.height > 0 for p in pages)


def test_preprocess_page_grayscales_and_preserves_page_number(sample_pdf_path):
    pages = render_pdf_pages(sample_pdf_path, dpi=100)
    processed = preprocess_page(pages[0])

    assert processed.page_number == pages[0].page_number
    assert processed.data
    assert processed.width > 0 and processed.height > 0


def test_preprocess_page_passthrough_when_no_data():
    page = PageImage(page_number=1, width=10, height=10, data=None)
    result = preprocess_page(page)
    assert result is page


def test_dummy_ocr_engine_is_deterministic_and_offline():
    engine = DummyOCREngine()
    page = PageImage(page_number=3, width=10, height=10, data=None)

    result_a = engine.recognize(page)
    result_b = engine.recognize(page)

    assert result_a.text == result_b.text
    assert "3" in result_a.text
    assert result_a.direction == "rtl"
    assert result_a.confidence > 0


def test_get_ocr_engine_defaults_to_dummy():
    assert isinstance(get_ocr_engine(), DummyOCREngine)
    assert isinstance(get_ocr_engine("dummy"), DummyOCREngine)


def test_get_ocr_engine_rejects_unknown_name():
    with pytest.raises(ValueError):
        get_ocr_engine("not-a-real-engine")


def test_get_ocr_engine_tesseract_fails_clearly_without_pytesseract():
    # pytesseract is not installed in this environment; constructing the
    # engine must fail with a clear, actionable OCRError rather than an
    # opaque ImportError deep inside recognize().
    try:
        import pytesseract  # noqa: F401

        pytest.skip("pytesseract is installed in this environment")
    except ImportError:
        pass

    with pytest.raises(OCRError):
        get_ocr_engine("tesseract")


def test_shape_rtl_returns_nonempty_string_for_persian_text():
    shaped = shape_rtl("سلام دنیا")
    assert isinstance(shaped, str)
    assert len(shaped) > 0


def test_normalize_persian_digits_converts_western_digits():
    assert normalize_persian_digits("Page 123") == "Page ۱۲۳"


def test_is_rtl_text_detects_persian_and_rejects_english():
    assert is_rtl_text("این یک متن فارسی است") is True
    assert is_rtl_text("This is English text") is False
    assert is_rtl_text("") is False


def test_assemble_rtl_paragraph_preserves_logical_order():
    text = "سلام دنیا"
    assert assemble_rtl_paragraph(text) == text


async def test_process_pdf_end_to_end_with_dummy_engine(sample_pdf_path):
    book = await process_pdf(sample_pdf_path, engine=DummyOCREngine())

    assert book.title == sample_pdf_path.stem
    assert book.language == "fa"
    assert book.direction == "rtl"
    assert len(book.pages) == 2
    assert [p.page_number for p in book.pages] == [1, 2]
    assert all(p.text for p in book.pages)


async def test_process_pdf_reports_progress(sample_pdf_path):
    progress_values: list[float] = []

    await process_pdf(
        sample_pdf_path,
        engine=DummyOCREngine(),
        progress_callback=progress_values.append,
    )

    assert progress_values == [0.5, 1.0]


class _FlakyEngine:
    """Fails a fixed number of times with ``RateLimitError`` before succeeding."""

    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.calls = 0

    def recognize(self, page):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RateLimitError("simulated rate limit")
        from common.models import PageText

        return PageText(page_number=page.page_number, text="ok", confidence=1.0)


async def test_process_pdf_retries_on_rate_limit_then_succeeds(sample_pdf_path):
    engine = _FlakyEngine(fail_times=1)

    book = await process_pdf(
        sample_pdf_path,
        engine=engine,
        max_retries=3,
        backoff_seconds=0.0,
    )

    assert len(book.pages) == 2
    # first page needed one retry, second page succeeded first try
    assert engine.calls == 3


async def test_process_pdf_raises_after_exhausting_retries(sample_pdf_path):
    engine = _FlakyEngine(fail_times=99)

    with pytest.raises(RateLimitError):
        await process_pdf(
            sample_pdf_path,
            engine=engine,
            max_retries=2,
            backoff_seconds=0.0,
        )
