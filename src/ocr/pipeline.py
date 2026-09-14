"""Async orchestrator that turns a PDF into a fully OCR'd ``Book``."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

from common.models import Book, PageImage, PageText

from ocr.engine import OCREngine, RateLimitError, get_ocr_engine
from ocr.preprocessing import preprocess_page, render_pdf_pages


async def process_pdf(
    pdf_path: str | Path,
    engine: OCREngine | None = None,
    dpi: int = 200,
    title: str | None = None,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
    progress_callback: Callable[[float], None] | None = None,
) -> Book:
    """Render, preprocess, and OCR every page of ``pdf_path`` into a ``Book``."""
    engine = engine or get_ocr_engine()

    pages = await asyncio.to_thread(render_pdf_pages, pdf_path, dpi)
    total_pages = len(pages)

    page_texts: list[PageText] = []
    for index, page in enumerate(pages):
        processed = await asyncio.to_thread(preprocess_page, page)
        page_text = await _recognize_with_retry(engine, processed, max_retries, backoff_seconds)
        page_texts.append(page_text)

        if progress_callback is not None:
            try:
                progress_callback((index + 1) / total_pages)
            except Exception:  # noqa: BLE001 - progress reporting must never break the pipeline
                pass

    return Book(
        title=title or Path(pdf_path).stem,
        pages=page_texts,
        language="fa",
        direction="rtl",
    )


async def _recognize_with_retry(
    engine: OCREngine,
    page: PageImage,
    max_retries: int,
    backoff_seconds: float,
) -> PageText:
    """Run ``engine.recognize`` in a thread, retrying with backoff on rate limits."""
    attempt = 0
    while True:
        try:
            return await asyncio.to_thread(engine.recognize, page)
        except RateLimitError:
            if attempt >= max_retries:
                raise
            await asyncio.sleep(backoff_seconds * 2**attempt)
            attempt += 1
