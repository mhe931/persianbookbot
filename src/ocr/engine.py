"""OCR engine abstractions: a deterministic offline default plus an optional
Tesseract-backed engine, selected via ``get_ocr_engine``.
"""
from __future__ import annotations

import abc
import os

from common.models import PageImage, PageText

try:  # pragma: no cover - exercised only when pytesseract is installed
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]


class OCRError(Exception):
    """Base exception for OCR engine failures."""


class RateLimitError(OCRError):
    """Raised when an OCR engine/backend is rate limiting requests."""

    def __init__(self, message: str = "OCR engine rate limited", retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class OCREngine(abc.ABC):
    """Common interface implemented by all OCR engines."""

    @abc.abstractmethod
    def recognize(self, page: PageImage) -> PageText:
        """Recognize text on a single rendered page."""
        raise NotImplementedError


class DummyOCREngine(OCREngine):
    """Deterministic, offline OCR engine used as the default and in tests.

    Produces placeholder Persian text derived only from the page number, so
    it requires no network access, credentials, or external binaries.
    """

    def recognize(self, page: PageImage) -> PageText:
        text = f"متن نمونه صفحه {page.page_number}"
        return PageText(page_number=page.page_number, text=text, confidence=0.99, direction="rtl")


class TesseractOCREngine(OCREngine):
    """Real OCR engine backed by the ``pytesseract``/Tesseract binary.

    Not required in this environment - it only needs to be structurally
    correct and fail clearly when ``pytesseract`` is unavailable.
    """

    def __init__(self) -> None:
        if pytesseract is None:
            raise OCRError("pytesseract not installed; install it or use OCR_ENGINE=dummy")
        from PIL import Image  # local import: only needed by this engine

        self._Image = Image
        self._pytesseract = pytesseract

    def recognize(self, page: PageImage) -> PageText:
        import io

        if not page.data:
            return PageText(page_number=page.page_number, text="", confidence=0.0, direction="rtl")

        with self._Image.open(io.BytesIO(page.data)) as image:
            text = self._pytesseract.image_to_string(image, lang="fas")

        return PageText(page_number=page.page_number, text=text.strip(), confidence=1.0, direction="rtl")


def get_ocr_engine(name: str | None = None) -> OCREngine:
    """Factory returning an ``OCREngine`` by name (or ``OCR_ENGINE`` env var)."""
    engine_name = (name or os.environ.get("OCR_ENGINE", "dummy")).strip().lower()

    if engine_name == "dummy":
        return DummyOCREngine()
    if engine_name == "tesseract":
        return TesseractOCREngine()

    raise ValueError(f"Unknown OCR engine: '{engine_name}'")
