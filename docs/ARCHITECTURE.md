# Architecture

## Pipeline overview

```
Scanned PDF -> render -> deskew -> OCR -> RTL assemble -> EPUB/DOCX/TXT -> Bot/API
```

Expanded, with the module that owns each stage:

```
Scanned PDF
   -> src/ocr/preprocessing.py   render_pdf_pages()  — rasterize pages via PyMuPDF
   -> src/ocr/preprocessing.py   preprocess_page()   — grayscale + projection-profile deskew
   -> src/ocr/engine.py          OCREngine.recognize() — DummyOCREngine (default) / TesseractOCREngine
   -> src/ocr/pipeline.py        process_pdf()       — async orchestrator, retry/backoff, -> common.models.Book
   -> src/converters/{txt,docx_writer,epub_writer}.py — Book -> .txt / .docx / .epub (RTL-aware)
   -> src/bot/jobs.py            JobManager.run_pipeline() — drives the above, tracks ConversionJob
   -> src/bot/telegram_handlers.py + src/bot/api.py   — delivery: Telegram chat / Mini App HTTP API
   -> web/                       — static Telegram Mini App frontend consumes the API
```

All data crossing subsystem boundaries flows through the shared dataclasses
in `src/common/models.py` — no subsystem defines a parallel model.

## Shared data contracts (`src/common/models.py`)

| Type | Purpose |
| --- | --- |
| `PageImage` | A single rendered page (`page_number`, `width`, `height`, `dpi`, optional raw PNG `data`). |
| `PageText` | OCR result for one page (`page_number`, `text`, `confidence`, `direction`). |
| `Book` | Fully assembled book (`title`, `pages: list[PageText]`, `language`, `direction`, `author`), with `full_text`/`average_confidence` helpers. |
| `JobStatus` | Enum lifecycle for a conversion job: `pending -> preprocessing -> ocr_running -> assembling -> converting -> done` (or `failed` / `rate_limited`). |
| `ConversionJob` | End-to-end job state (`job_id`, `status`, `source_filename`, `chat_id`, `error`, `progress`, `output_paths`, timestamps, `retry_count`), with `mark()`/`touch()`/`to_dict()`. |

## Module responsibilities

### `src/ocr/` — OCR / pipeline
- `preprocessing.py`: `render_pdf_pages()` rasterizes each PDF page to PNG
  bytes via PyMuPDF (`fitz`) at a configurable DPI; `preprocess_page()`
  grayscales the image and estimates/corrects skew using a horizontal
  row-sum projection-profile search over a small angle range.
- `engine.py`: `OCREngine` ABC with `recognize(page) -> PageText`.
  `DummyOCREngine` (default, `OCR_ENGINE=dummy`) is deterministic and
  offline — it returns fixed placeholder Persian text keyed only by page
  number, requiring zero credentials or network access. `TesseractOCREngine`
  (`OCR_ENGINE=tesseract`) wraps `pytesseract` and fails clearly with a
  clear `OCRError` if `pytesseract`/Tesseract isn't installed. `PaddleOCREngine`
  (`OCR_ENGINE=paddle`) lazily wraps the optional `paddleocr` package
  (`pip install .[paddle]`), with `PADDLE_LANG`/`PADDLE_USE_GPU` config and
  automatic `fa` -> `ar` fallback. `VisionLLMOCREngine` (`OCR_ENGINE=vision_llm`)
  prompts Gemini or Claude over provider-neutral HTTP (lazily imported
  `httpx`, `pip install .[vision-llm]`) using `VISION_LLM_PROVIDER`/
  `VISION_LLM_API_KEY`/`VISION_LLM_MODEL`. `RateLimitError` signals a
  backend is throttling (mapped from provider HTTP 429 responses for
  `VisionLLMOCREngine`). `get_ocr_engine(name)` is the factory, driven by
  the `OCR_ENGINE` env var by default.
- `rtl.py`: Two distinct RTL concerns — `shape_rtl()` (visual reshape +
  bidi-reorder, for contexts with no bidi engine of their own, e.g. image
  rendering) vs. `assemble_rtl_paragraph()` (logical/reading order preserved,
  for EPUB/DOCX which have their own bidi engines). Also
  `normalize_persian_digits()` and `is_rtl_text()` heuristics.
- `pipeline.py`: `process_pdf()` is the async orchestrator — renders pages
  in a thread, preprocesses each, calls the engine with retry/exponential
  backoff on `RateLimitError` (`_recognize_with_retry`), reports progress via
  an optional callback, and returns a `Book`.

### `src/converters/` — document generation
- `txt.py`: plain-text writer.
- `docx_writer.py`: builds a DOCX via `python-docx`, manipulating raw OXML
  elements directly (`w:bidi`, `w:rtl`, complex-script `w:rFonts`) because
  `python-docx` has no high-level bidi API — sets both paragraph- and
  document-level RTL plus the configured Persian font.
- `epub_writer.py`: builds an EPUB via `EbookLib`, setting `EpubHtml(direction="rtl")`
  per chapter (ebooklib regenerates the `<html>`/`<body>` wrapper, so a
  `dir="rtl"` attribute embedded directly in body HTML would be discarded)
  plus an RTL CSS stylesheet (`direction: rtl; text-align: right;`).
- `fonts.py`: resolves the configured/default Persian font name; no font
  binaries are bundled — licensing is the deployer's responsibility.
- Contract: every `write_*(book, output_path, ...) -> pathlib.Path`.

### `src/bot/` — Telegram bot & Mini App
- `config.py`: `Settings` (pydantic-settings) — all configuration from env
  vars / `.env`; `bot_token` defaults to `None` so nothing here requires a
  credential to import or run standalone.
- `jobs.py`: `JobManager` — async in-memory `ConversionJob` store; `default_job_manager`
  singleton shared by both the Telegram handlers and the FastAPI API so a
  job started on either surface can be polled/downloaded from both.
  `run_pipeline()` drives `process_pdf()` + the three converters, mapping
  exceptions to `JobStatus.FAILED`/`RATE_LIMITED` rather than crashing.
- `telegram_handlers.py`: Telegram chat handlers; `_send_with_retry` retries
  on `RetryAfter`/`TimedOut`/`NetworkError` with backoff.
- `api.py`: FastAPI app exposing `/api/config`, `/api/upload`,
  `/api/status/{job_id}`, `/api/download/{job_id}/{fmt}`, and mounting the
  static `web/` frontend at `/`. Rejects oversized uploads by declared size
  before buffering the full file.
- `main.py`: process entrypoint — runs the API (and Telegram polling in a
  background thread if `BOT_TOKEN` is set).

### `web/` — Mini App frontend
Static vanilla HTML/CSS/JS (`index.html`, `app.js`, `style.css`) that talks
to the `/api/*` endpoints above; served directly by the FastAPI app.
Telegram theme-aware (`--tg-theme-*` CSS variables), RTL/Persian, with a
five-step progress indicator, format-selection toggles, download cards with
file-size indicators, defensive `window.Telegram.WebApp` lifecycle/
`MainButton`/haptics integration, and resilient upload/polling with retry.

### `tools/` — operator CLIs
`evaluate_sample.py`: offline-safe local CLI that runs a single PDF through
the real `ocr.pipeline.process_pdf` + `converters.*` (engine selectable via
`--engine dummy|tesseract|paddle|vision_llm`) and reports runtime/page/
character/output metrics. Never required for `pytest tests/`; the default
`dummy` engine needs no network/credentials, and other engines fail with an
actionable message/nonzero exit if their optional dependency or credential
is missing.

### `tests/`
Pytest suite (83 tests) covering rendering/deskew, the OCR abstraction and
retry/backoff, `PaddleOCREngine`/`VisionLLMOCREngine` mapping and
error/rate-limit handling (mocked), converters' RTL output, bot config, job
lifecycle, Telegram handler retry behavior, the Mini App API (including
`/api/config` and static-asset delivery), the `tools/evaluate_sample.py`
CLI, and a full integration flow — all against generated/dummy fixtures, no
real PDFs/tokens/network.

## Design principles

1. **Single shared contract** — all cross-subsystem data flows through
   `src/common/models.py`.
2. **Offline-first default** — `DummyOCREngine` and `bot_token=None` mean
   the entire pipeline and test suite run with zero external credentials.
3. **Explicit RTL, not visual hacks** — document formats get real bidi
   flags (`w:bidi`/`dir="rtl"`), not pre-reordered characters.
4. **Resilience at the boundary** — rate limits and transient network
   errors are retried with backoff at the point of external interaction
   (OCR engine, Telegram API), and job-level failures are contained rather
   than propagated to crash the process.
