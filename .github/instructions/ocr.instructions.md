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
- Real/optional engines (e.g. `TesseractOCREngine`) are selected via the
  `OCR_ENGINE` env var / `get_ocr_engine(name)` factory, and must fail with
  a clear `OCRError` only when actually invoked without their runtime
  dependency present (e.g. `pytesseract` not installed) — never at import
  time of `ocr.engine`.
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
  does with `pytesseract`), never at module import time, so importing
  `ocr.engine` never requires that dependency to be installed.

## Tests

- New OCR/pipeline behavior must be testable without real PDFs, real OCR
  credentials, or network access — use generated fixtures. Run
  `pytest tests/` (46 tests as of this writing) before committing.
