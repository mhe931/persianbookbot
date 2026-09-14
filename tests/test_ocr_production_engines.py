"""Tests for optional production OCR backends: ``PaddleOCREngine`` and
``VisionLLMOCREngine`` (Gemini/Claude). Every provider/SDK dependency is
mocked at the module boundary (``sys.modules`` / monkeypatched classes) so
this file - like the rest of the suite - never requires network access,
real credentials, or heavy optional packages (``paddleocr``, ``httpx``) to
actually be installed.
"""
from __future__ import annotations

import sys
import types

import pytest

from common.models import PageImage
from ocr.engine import (
    OCRError,
    PaddleOCREngine,
    RateLimitError,
    VisionLLMOCREngine,
    get_ocr_engine,
)
from ocr.pipeline import process_pdf


def _page(data: bytes | None = b"fake-image-bytes") -> PageImage:
    return PageImage(page_number=1, width=10, height=10, data=data)


def _real_png_bytes() -> bytes:
    """A tiny real PNG, needed by tests that exercise ``PIL.Image.open``
    (``PaddleOCREngine.recognize`` decodes the page image bytes); the
    Vision-LLM engine only base64-encodes bytes as-is so it can use opaque
    fake bytes instead.
    """
    import io as _io

    from PIL import Image

    buffer = _io.BytesIO()
    Image.new("RGB", (4, 4), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Factory registration
# ---------------------------------------------------------------------------


def test_get_ocr_engine_rejects_unknown_name_still_works():
    with pytest.raises(ValueError):
        get_ocr_engine("not-a-real-engine")


def test_get_ocr_engine_paddle_fails_clearly_without_paddleocr(monkeypatch):
    monkeypatch.setitem(sys.modules, "paddleocr", None)
    with pytest.raises(OCRError, match="paddleocr"):
        get_ocr_engine("paddle")


def test_get_ocr_engine_vision_llm_fails_clearly_without_api_key(monkeypatch):
    monkeypatch.delenv("VISION_LLM_API_KEY", raising=False)
    with pytest.raises(OCRError, match="VISION_LLM_API_KEY"):
        get_ocr_engine("vision_llm")


def test_get_ocr_engine_vision_llm_reads_env_config(monkeypatch):
    monkeypatch.setenv("VISION_LLM_API_KEY", "fake-key")
    monkeypatch.setenv("VISION_LLM_PROVIDER", "claude")
    monkeypatch.setenv("VISION_LLM_MODEL", "claude-test-model")

    engine = get_ocr_engine("vision_llm")

    assert isinstance(engine, VisionLLMOCREngine)
    assert engine._provider == "claude"
    assert engine._model == "claude-test-model"
    assert engine._api_key == "fake-key"


def test_get_ocr_engine_paddle_reads_env_config(monkeypatch):
    fake_paddleocr = _make_fake_paddleocr_module(ocr_result=[])
    monkeypatch.setitem(sys.modules, "paddleocr", fake_paddleocr)
    monkeypatch.setenv("PADDLE_USE_GPU", "true")
    monkeypatch.setenv("PADDLE_LANG", "ar")

    engine = get_ocr_engine("paddle")

    assert isinstance(engine, PaddleOCREngine)
    assert engine._lang == "ar"


# ---------------------------------------------------------------------------
# PaddleOCREngine
# ---------------------------------------------------------------------------


class _FakePaddleOCR:
    """Stand-in for ``paddleocr.PaddleOCR`` returning canned results."""

    last_init_kwargs: dict | None = None

    def __init__(self, result=None, fail_langs: tuple[str, ...] = (), **kwargs):
        _FakePaddleOCR.last_init_kwargs = kwargs
        if kwargs.get("lang") in fail_langs:
            raise RuntimeError(f"unsupported lang: {kwargs.get('lang')}")
        self._result = result if result is not None else []

    def ocr(self, array, cls=True):
        return self._result


def _make_fake_paddleocr_module(ocr_result=None, fail_langs=()):
    module = types.ModuleType("paddleocr")

    def _factory(*args, **kwargs):
        return _FakePaddleOCR(result=ocr_result, fail_langs=fail_langs, **kwargs)

    module.PaddleOCR = _factory
    return module


def test_paddle_engine_raises_ocr_error_without_paddleocr_installed(monkeypatch):
    monkeypatch.setitem(sys.modules, "paddleocr", None)
    with pytest.raises(OCRError, match="paddleocr not installed"):
        PaddleOCREngine()


def test_paddle_engine_maps_recognition_result_to_page_text(monkeypatch):
    result = [
        [
            [[0, 0, 0, 0], ("سلام", 0.95)],
            [[0, 0, 0, 0], ("دنیا", 0.85)],
        ]
    ]
    fake_module = _make_fake_paddleocr_module(ocr_result=result)
    monkeypatch.setitem(sys.modules, "paddleocr", fake_module)

    engine = PaddleOCREngine(lang="fa", use_gpu=False)
    page_text = engine.recognize(_page(data=_real_png_bytes()))

    assert page_text.page_number == 1
    assert page_text.text == "سلام\nدنیا"
    assert page_text.confidence == pytest.approx(0.9)
    assert page_text.direction == "rtl"


def test_paddle_engine_returns_empty_page_text_when_no_image_data(monkeypatch):
    fake_module = _make_fake_paddleocr_module(ocr_result=[])
    monkeypatch.setitem(sys.modules, "paddleocr", fake_module)

    engine = PaddleOCREngine()
    page_text = engine.recognize(_page(data=None))

    assert page_text.text == ""
    assert page_text.confidence == 0.0


def test_paddle_engine_falls_back_to_arabic_when_persian_unsupported(monkeypatch):
    fake_module = _make_fake_paddleocr_module(ocr_result=[], fail_langs=("fa",))
    monkeypatch.setitem(sys.modules, "paddleocr", fake_module)

    engine = PaddleOCREngine(lang="fa")

    assert engine._lang == "ar"


def test_paddle_engine_raises_ocr_error_when_both_langs_fail(monkeypatch):
    fake_module = _make_fake_paddleocr_module(ocr_result=[], fail_langs=("fa", "ar"))
    monkeypatch.setitem(sys.modules, "paddleocr", fake_module)

    with pytest.raises(OCRError, match="failed to initialize PaddleOCR"):
        PaddleOCREngine(lang="fa")


def test_paddle_engine_wraps_recognition_failures_in_ocr_error(monkeypatch):
    class _BoomOCR(_FakePaddleOCR):
        def ocr(self, array, cls=True):
            raise RuntimeError("boom")

    fake_module = types.ModuleType("paddleocr")
    fake_module.PaddleOCR = lambda *a, **k: _BoomOCR(**k)
    monkeypatch.setitem(sys.modules, "paddleocr", fake_module)

    engine = PaddleOCREngine()
    with pytest.raises(OCRError, match="PaddleOCR recognition failed"):
        engine.recognize(_page(data=_real_png_bytes()))


# ---------------------------------------------------------------------------
# VisionLLMOCREngine
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self._json_data


def _install_fake_httpx(monkeypatch, post_impl):
    fake_httpx = types.ModuleType("httpx")
    fake_httpx.post = post_impl
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    return fake_httpx


def test_vision_llm_engine_rejects_unknown_provider():
    with pytest.raises(OCRError, match="Unknown vision-llm provider"):
        VisionLLMOCREngine(provider="not-a-provider", api_key="fake-key")


def test_vision_llm_engine_requires_api_key():
    with pytest.raises(OCRError, match="VISION_LLM_API_KEY"):
        VisionLLMOCREngine(provider="gemini", api_key=None)


def test_vision_llm_engine_returns_empty_page_text_when_no_image_data():
    engine = VisionLLMOCREngine(provider="gemini", api_key="fake-key")
    page_text = engine.recognize(_page(data=None))
    assert page_text.text == ""
    assert page_text.confidence == 0.0


def test_vision_llm_engine_gemini_success(monkeypatch):
    def _post(url, params=None, json=None, timeout=None):
        assert "gemini-1.5-flash" in url
        assert params == {"key": "fake-key"}
        return _FakeResponse(
            status_code=200,
            json_data={"candidates": [{"content": {"parts": [{"text": "سلام دنیا"}]}}]},
        )

    _install_fake_httpx(monkeypatch, _post)

    engine = VisionLLMOCREngine(provider="gemini", api_key="fake-key")
    page_text = engine.recognize(_page())

    assert page_text.text == "سلام دنیا"
    assert page_text.confidence == pytest.approx(0.9)
    assert page_text.direction == "rtl"


def test_vision_llm_engine_claude_success(monkeypatch):
    def _post(url, headers=None, json=None, timeout=None):
        assert headers["x-api-key"] == "fake-key"
        assert json["model"] == "claude-test-model"
        return _FakeResponse(status_code=200, json_data={"content": [{"text": "سلام دنیا"}]})

    _install_fake_httpx(monkeypatch, _post)

    engine = VisionLLMOCREngine(provider="claude", api_key="fake-key", model="claude-test-model")
    page_text = engine.recognize(_page())

    assert page_text.text == "سلام دنیا"


def test_vision_llm_engine_maps_http_429_to_rate_limit_error(monkeypatch):
    def _post(*args, **kwargs):
        return _FakeResponse(status_code=429, headers={"retry-after": "3"})

    _install_fake_httpx(monkeypatch, _post)

    engine = VisionLLMOCREngine(provider="gemini", api_key="fake-key")
    with pytest.raises(RateLimitError) as exc_info:
        engine.recognize(_page())

    assert exc_info.value.retry_after == 3.0


def test_vision_llm_engine_maps_http_429_without_retry_after_header(monkeypatch):
    def _post(*args, **kwargs):
        return _FakeResponse(status_code=429)

    _install_fake_httpx(monkeypatch, _post)

    engine = VisionLLMOCREngine(provider="claude", api_key="fake-key")
    with pytest.raises(RateLimitError) as exc_info:
        engine.recognize(_page())

    assert exc_info.value.retry_after is None


def test_vision_llm_engine_maps_other_http_errors_to_ocr_error(monkeypatch):
    def _post(*args, **kwargs):
        return _FakeResponse(status_code=500, text="internal server error")

    _install_fake_httpx(monkeypatch, _post)

    engine = VisionLLMOCREngine(provider="gemini", api_key="fake-key")
    with pytest.raises(OCRError, match="HTTP 500"):
        engine.recognize(_page())


def test_vision_llm_engine_maps_transport_errors_to_ocr_error(monkeypatch):
    def _post(*args, **kwargs):
        raise ConnectionError("network unreachable")

    _install_fake_httpx(monkeypatch, _post)

    engine = VisionLLMOCREngine(provider="gemini", api_key="fake-key")
    with pytest.raises(OCRError, match="request failed"):
        engine.recognize(_page())


def test_vision_llm_engine_maps_malformed_gemini_response_to_ocr_error(monkeypatch):
    def _post(*args, **kwargs):
        return _FakeResponse(status_code=200, json_data={"unexpected": "shape"})

    _install_fake_httpx(monkeypatch, _post)

    engine = VisionLLMOCREngine(provider="gemini", api_key="fake-key")
    with pytest.raises(OCRError, match="Unexpected Gemini response shape"):
        engine.recognize(_page())


def test_vision_llm_engine_maps_malformed_claude_response_to_ocr_error(monkeypatch):
    def _post(*args, **kwargs):
        return _FakeResponse(status_code=200, json_data={"unexpected": "shape"})

    _install_fake_httpx(monkeypatch, _post)

    engine = VisionLLMOCREngine(provider="claude", api_key="fake-key")
    with pytest.raises(OCRError, match="Unexpected Claude response shape"):
        engine.recognize(_page())


def test_vision_llm_engine_raises_ocr_error_without_httpx_installed(monkeypatch):
    monkeypatch.setitem(sys.modules, "httpx", None)
    engine = VisionLLMOCREngine(provider="gemini", api_key="fake-key")
    with pytest.raises(OCRError, match="httpx not installed"):
        engine.recognize(_page())


# ---------------------------------------------------------------------------
# Retry/backoff integration through the pipeline (rate-limit mapping)
# ---------------------------------------------------------------------------


async def test_process_pdf_retries_vision_llm_rate_limit_then_succeeds(monkeypatch, sample_pdf_path):
    calls = {"count": 0}

    def _post(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] <= 2:
            return _FakeResponse(status_code=429, headers={"retry-after": "0"})
        return _FakeResponse(
            status_code=200,
            json_data={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
        )

    _install_fake_httpx(monkeypatch, _post)

    engine = VisionLLMOCREngine(provider="gemini", api_key="fake-key")
    book = await process_pdf(sample_pdf_path, engine=engine, max_retries=5, backoff_seconds=0.0)

    assert len(book.pages) == 2
    assert all(p.text == "ok" for p in book.pages)
    # first page needed two retries (3 calls), second page succeeded first try
    assert calls["count"] == 4


async def test_process_pdf_raises_after_exhausting_vision_llm_retries(monkeypatch, sample_pdf_path):
    def _post(*args, **kwargs):
        return _FakeResponse(status_code=429)

    _install_fake_httpx(monkeypatch, _post)

    engine = VisionLLMOCREngine(provider="gemini", api_key="fake-key")
    with pytest.raises(RateLimitError):
        await process_pdf(sample_pdf_path, engine=engine, max_retries=1, backoff_seconds=0.0)
