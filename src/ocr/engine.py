"""OCR engine abstractions: a deterministic offline default plus optional
Tesseract, PaddleOCR, and Vision-LLM (Gemini/Claude) backed engines, all
selected via ``get_ocr_engine``.
"""
from __future__ import annotations

import abc
import base64
import io
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


class PaddleOCREngine(OCREngine):
    """Real OCR engine backed by the optional ``paddleocr`` package.

    PaddleOCR runs a local model (no network access, no API key), but is a
    heavy optional dependency (``paddleocr`` + ``paddlepaddle``) - it is
    never required to import ``ocr.engine`` and only needs to be
    structurally correct and fail with a clear ``OCRError`` when the
    package is unavailable or recognition fails.
    """

    # PaddleOCR does not ship a dedicated "fa" (Persian) model in every
    # build; Arabic-script ("ar") recognition shares most glyphs with
    # Persian, so it is used as an automatic fallback rather than failing
    # outright when the requested language is unavailable.
    _FALLBACK_LANG = "ar"

    def __init__(self, lang: str = "fa", use_gpu: bool = False) -> None:
        try:
            from paddleocr import PaddleOCR  # type: ignore[import-not-found]
        except ImportError as exc:
            raise OCRError(
                "paddleocr not installed; install the 'paddle' extra "
                "(pip install persianbookbot[paddle]) or use OCR_ENGINE=dummy"
            ) from exc

        self._lang = lang
        try:
            self._ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu, show_log=False)
        except Exception:
            try:
                self._lang = self._FALLBACK_LANG
                self._ocr = PaddleOCR(
                    use_angle_cls=True, lang=self._FALLBACK_LANG, use_gpu=use_gpu, show_log=False
                )
            except Exception as exc:  # pragma: no cover - defensive, both langs failing is unusual
                raise OCRError(f"failed to initialize PaddleOCR: {exc}") from exc

    def recognize(self, page: PageImage) -> PageText:
        if not page.data:
            return PageText(page_number=page.page_number, text="", confidence=0.0, direction="rtl")

        try:
            import numpy as np
            from PIL import Image

            with Image.open(io.BytesIO(page.data)) as image:
                array = np.array(image.convert("RGB"))
            result = self._ocr.ocr(array, cls=True)
        except Exception as exc:
            raise OCRError(f"PaddleOCR recognition failed: {exc}") from exc

        lines: list[str] = []
        confidences: list[float] = []
        for block in result or []:
            for entry in block or []:
                _box, (text, confidence) = entry
                if text:
                    lines.append(text)
                    confidences.append(confidence)

        combined_text = "\n".join(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return PageText(
            page_number=page.page_number, text=combined_text, confidence=avg_confidence, direction="rtl"
        )


class VisionLLMOCREngine(OCREngine):
    """OCR engine that prompts a vision-capable LLM (Gemini or Claude) to
    transcribe a raw scanned page image.

    Uses provider-neutral HTTP calls (via a lazily imported ``httpx``)
    rather than a heavy provider SDK, so no SDK is ever required to import
    ``ocr.engine`` or to run the offline test suite. Provider throttling
    (HTTP 429) is mapped to ``RateLimitError``; any other provider failure
    (network error, non-2xx status, unparseable response) is mapped to
    ``OCRError``.
    """

    _GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    _CLAUDE_ENDPOINT = "https://api.anthropic.com/v1/messages"
    _DEFAULT_PROMPT = (
        "Transcribe every visible character of text on this scanned book "
        "page exactly as written (the text is most likely Persian/Farsi), "
        "preserving line breaks and reading order. Return only the "
        "transcribed text with no commentary, translation, or formatting."
    )
    _PROVIDERS = ("gemini", "claude")
    _DEFAULT_MODELS = {"gemini": "gemini-1.5-flash", "claude": "claude-3-5-sonnet-20241022"}

    def __init__(
        self,
        provider: str = "gemini",
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        provider = (provider or "gemini").strip().lower()
        if provider not in self._PROVIDERS:
            raise OCRError(
                f"Unknown vision-llm provider: '{provider}' (expected one of {self._PROVIDERS})"
            )
        if not api_key:
            raise OCRError(
                "VISION_LLM_API_KEY not set; configure it in .env or use OCR_ENGINE=dummy"
            )

        self._provider = provider
        self._api_key = api_key
        self._model = model or self._DEFAULT_MODELS[provider]
        self._timeout = timeout

    def recognize(self, page: PageImage) -> PageText:
        if not page.data:
            return PageText(page_number=page.page_number, text="", confidence=0.0, direction="rtl")

        try:
            import httpx
        except ImportError as exc:
            raise OCRError(
                "httpx not installed; install the 'vision-llm' extra "
                "(pip install persianbookbot[vision-llm]) or use OCR_ENGINE=dummy"
            ) from exc

        if self._provider == "gemini":
            text = self._recognize_gemini(httpx, page)
        else:
            text = self._recognize_claude(httpx, page)

        return PageText(page_number=page.page_number, text=text.strip(), confidence=0.9, direction="rtl")

    def _recognize_gemini(self, httpx_module, page: PageImage) -> str:
        url = self._GEMINI_ENDPOINT.format(model=self._model)
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": self._DEFAULT_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(page.data).decode("ascii"),
                            }
                        },
                    ]
                }
            ]
        }

        try:
            response = httpx_module.post(
                url, params={"key": self._api_key}, json=payload, timeout=self._timeout
            )
        except Exception as exc:
            raise OCRError(f"Vision-LLM (gemini) request failed: {exc}") from exc

        self._raise_for_provider_status(response)
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OCRError(f"Unexpected Gemini response shape: {data!r}") from exc

    def _recognize_claude(self, httpx_module, page: PageImage) -> str:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._DEFAULT_PROMPT},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64.b64encode(page.data).decode("ascii"),
                            },
                        },
                    ],
                }
            ],
        }

        try:
            response = httpx_module.post(
                self._CLAUDE_ENDPOINT, headers=headers, json=payload, timeout=self._timeout
            )
        except Exception as exc:
            raise OCRError(f"Vision-LLM (claude) request failed: {exc}") from exc

        self._raise_for_provider_status(response)
        data = response.json()
        try:
            return "".join(block.get("text", "") for block in data["content"])
        except (KeyError, TypeError) as exc:
            raise OCRError(f"Unexpected Claude response shape: {data!r}") from exc

    @staticmethod
    def _raise_for_provider_status(response) -> None:
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            raise RateLimitError(
                "Vision-LLM provider rate limited the request",
                retry_after=float(retry_after) if retry_after else None,
            )
        if response.status_code >= 400:
            raise OCRError(
                f"Vision-LLM provider returned HTTP {response.status_code}: {response.text}"
            )


def get_ocr_engine(name: str | None = None) -> OCREngine:
    """Factory returning an ``OCREngine`` by name (or ``OCR_ENGINE`` env var)."""
    engine_name = (name or os.environ.get("OCR_ENGINE", "dummy")).strip().lower()

    if engine_name == "dummy":
        return DummyOCREngine()
    if engine_name == "tesseract":
        return TesseractOCREngine()
    if engine_name == "paddle":
        use_gpu = os.environ.get("PADDLE_USE_GPU", "false").strip().lower() in ("1", "true", "yes")
        lang = os.environ.get("PADDLE_LANG", "fa")
        return PaddleOCREngine(lang=lang, use_gpu=use_gpu)
    if engine_name == "vision_llm":
        provider = os.environ.get("VISION_LLM_PROVIDER", "gemini")
        api_key = os.environ.get("VISION_LLM_API_KEY")
        model = os.environ.get("VISION_LLM_MODEL") or None
        return VisionLLMOCREngine(provider=provider, api_key=api_key, model=model)

    raise ValueError(f"Unknown OCR engine: '{engine_name}'")
