---
applyTo: "src/ocr/**"
---

# OCR / pipeline instructions

Scope: `src/ocr/` — PDF rendering/preprocessing (`preprocessing.py`), the
OCR engine abstraction (`engine.py`), Persian RTL/BiDi helpers (`rtl.py`),
and the async orchestrator (`pipeline.py`). See `docs/ARCHITECTURE.md` for
the full pipeline context and `AGENTS.md` for repo-wide rules.

## Contract

- `process_pdf(pdf_path, engine=None, ...) -> Book` is the module's public
  entry point; keep this signature/return type stable, extending via new
  optional keyword arguments rather than breaking changes.
- **Must work fully offline via `DummyOCREngine` (the default)** with zero
  credentials, so tests and CI never need a real OCR service. Any new
  default behavior must preserve this.
- Real/optional engines (e.g. `TesseractOCREngine`, `PaddleOCREngine`,
  `VisionLLMOCREngine`) are selected via the `OCR_ENGINE` env var /
  `get_ocr_engine(name)` factory, and must fail with a clear `OCRError`
  only when actually invoked/constructed without their runtime dependency
  present (e.g. `pytesseract`/`paddleocr`/`httpx` not installed, or
  `VISION_LLM_API_KEY` unset) — never at import time of `ocr.engine`.
- `DummyOCREngine` is the **known/intentional default limitation**: it
  returns deterministic placeholder Persian text keyed only by page number
  (`متن نمونه صفحه {page_number}`), not real recognized text. Do not change
  its output format casually — tests and downstream converter fixtures may
  depend on its exact shape.

## Rate limits / retries

- An engine signals throttling by raising `ocr.engine.RateLimitError` from
  `recognize()`. `process_pdf`'s internal `_recognize_with_retry` must
  retry with exponential backoff (`backoff_seconds * 2**attempt`) up to
  `max_retries`, then re-raise — do not swallow a `RateLimitError` silently
  and do not let it crash the caller uncaught before retries are exhausted.
- CPU-bound work (`render_pdf_pages`, `preprocess_page`, `engine.recognize`)
  must run via `asyncio.to_thread` inside the async orchestrator, not
  directly on the event loop, to avoid blocking concurrent jobs.

## RTL text handling

- Use `rtl.shape_rtl()` only for rendering contexts with no bidi engine of
  their own (e.g. drawing text onto an image) — never for content destined
  for EPUB/DOCX.
- Use `rtl.assemble_rtl_paragraph()` (logical/reading order, unchanged
  text) for any text that will end up in EPUB/DOCX — those formats have
  their own bidi engines and expect a `dir="rtl"`/bidi flag on the
  container, not pre-reordered characters. Do not conflate the two helpers.

## New OCR engines

- Implement the `OCREngine` ABC (`recognize(page: PageImage) -> PageText`).
- Register the new engine in `get_ocr_engine()` behind a new `OCR_ENGINE`
  value; keep `"dummy"` as the unconditional default.
- Any heavy/optional dependency (a new SDK, model weights, GPU runtime)
  must be imported lazily inside the engine class (as `TesseractOCREngine`
  does with `pytesseract`, `PaddleOCREngine` does with `paddleocr`, and
  `VisionLLMOCREngine` does with `httpx`), never at module import time, so
  importing `ocr.engine` never requires that dependency to be installed.
- Provider-backed engines (e.g. `VisionLLMOCREngine`'s Gemini/Claude HTTP
  calls) must map throttling/HTTP 429 responses to `RateLimitError` and any
  other provider failure (network error, non-2xx status, unparseable
  response) to `OCRError`, so `pipeline._recognize_with_retry` can retry
  correctly. Never require a provider SDK — use provider-neutral HTTP (a
  lazily imported `httpx`) instead.
- Prefer running provider/CPU-bound work synchronously inside `recognize()`
  itself: `pipeline.process_pdf` already invokes `engine.recognize` via
  `asyncio.to_thread`, so a blocking implementation here is correct and
  does not block the event loop.

## Tests

- New OCR/pipeline behavior must be testable without real PDFs, real OCR
  credentials, or network access — use generated fixtures. Provider/SDK
  dependencies (`paddleocr`, `httpx`) must be mocked at the module boundary
  (e.g. `monkeypatch.setitem(sys.modules, ...)`), never actually installed
  or called. Run `pytest tests/` (157 tests as of this writing) before
  committing.
- `tools/evaluate_sample.py` is a separate local CLI (not part of
  `pytest tests/`) for manually validating any `OCREngine` against a real
  local PDF; it must keep reusing `get_ocr_engine`/`process_pdf`/
  `converters.*` rather than duplicating pipeline logic, and must keep
  failing cleanly (actionable message, nonzero exit) rather than crashing
  when an optional dependency or credential is missing — see
  `tests/test_tools_evaluate_sample.py` for the expected exit-code
  contract (`1` usage, `2` missing dependency/credential/rate-limit,
  `3` pipeline failure). It supports three mutually-exclusive-ish output
  modes: human-readable (default), `--json`, and `--csv` (single
  header+data row with one column pair per possible output format,
  padded blank for formats not requested via `--formats`); passing both
  `--json` and `--csv` is a usage error (exit `1`). Errors always print to
  `stderr`, never as a partial JSON/CSV payload on `stdout`, in every
  output mode.
