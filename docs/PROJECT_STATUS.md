# Project Status

_Last updated: 2026-09-14_

## Current milestone: Mini App UI enhancements + sample evaluation CLI

The Telegram Mini App frontend (`web/`) has been upgraded from a minimal
scaffold to a theme-aware, accessible, resilient UI on branch
`feature/miniapp-ui-enhancements`, and a new offline-safe sample evaluation
CLI (`tools/evaluate_sample.py`) has been added, alongside the previously
verified core pipeline and production OCR backends:

- PDF rendering + grayscale/deskew preprocessing (`src/ocr/preprocessing.py`)
- Pluggable OCR engine abstraction with a deterministic offline default
  (`src/ocr/engine.py`: `DummyOCREngine`, optional `TesseractOCREngine`,
  `PaddleOCREngine`, `VisionLLMOCREngine`)
- Async pipeline orchestrator with rate-limit retry/backoff
  (`src/ocr/pipeline.py`)
- Persian RTL/BiDi text helpers (`src/ocr/rtl.py`)
- TXT/DOCX/EPUB writers with explicit RTL directionality
  (`src/converters/`)
- Async in-memory job orchestration shared by both delivery surfaces
  (`src/bot/jobs.py`), now also reporting per-format `output_sizes`
  (bytes) once a job is `done`, for Mini App download cards
- Telegram bot handlers with retry-on-rate-limit (`src/bot/telegram_handlers.py`)
- FastAPI Mini App backend (upload/status/download, plus a new
  `GET /api/config` endpoint exposing `max_file_size_mb`/`formats` so the
  frontend never hardcodes limits separately from `Settings`)
  (`src/bot/api.py`)
- **Enhanced static Telegram Mini App frontend (`web/`)**: Telegram
  theme-aware CSS variables (`--tg-theme-*`) with light-mode fallbacks,
  native RTL/Persian typography, an accessible five-step progress
  indicator (Uploaded / Preprocessing / OCR / Generating Documents /
  Ready), EPUB/DOCX/TXT format-selection toggles, download cards with
  file-size indicators, defensive `window.Telegram.WebApp` lifecycle
  integration (`ready`, `expand`, `MainButton`, haptic feedback), visible
  upload progress (via `XMLHttpRequest` upload events), client-side
  PDF/20MB validation sourced from `/api/config`, and resilient status
  polling with success/failure/rate-limit/network-error handling plus a
  retry action - still plain vanilla HTML/CSS/JS, no build step
- **New: `tools/evaluate_sample.py`** - an offline-safe local CLI that
  runs a single PDF through the real pipeline/converters (`dummy`,
  `tesseract`, `paddle`, or `vision_llm` engine) and reports
  runtime/page/character/output metrics; see "Evaluation tool" below
- Environment-driven configuration with safe, credential-free defaults
  (`src/bot/config.py`)

## Test status

**83 tests passing**, 0 failing, across:

- `tests/test_ocr_pipeline.py` — rendering, deskew, OCR abstraction, retry/backoff
- `tests/test_ocr_production_engines.py` — `PaddleOCREngine`/`VisionLLMOCREngine`
  factory registration, response mapping, provider error/rate-limit
  mapping, and retry/backoff, all with `paddleocr`/`httpx` mocked at the
  module boundary
- `tests/test_converters.py` — TXT/DOCX/EPUB output and RTL directionality
- `tests/test_bot_config.py` — settings loading/defaults
- `tests/test_bot_jobs.py` — job lifecycle and status transitions
- `tests/test_bot_telegram_handlers.py` — retry-on-`RetryAfter`/network error
- `tests/test_bot_api.py` — Mini App upload/status/download/config
  endpoints, `output_sizes` metadata, and static-asset delivery
  (`index.html`/`app.js`/`style.css`)
- `tests/test_integration.py` — end-to-end PDF-to-output flow
- `tests/test_tools_evaluate_sample.py` — `tools/evaluate_sample.py` CLI:
  successful offline `dummy`-engine run + metrics/output validation, usage
  errors (missing/non-PDF file, unknown format), and clean nonzero exits
  for `tesseract`/`paddle`/`vision_llm` when their optional
  dependency/credential is absent (never installs/requires them)

Run locally:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest tests/
```

The suite requires **no** real Telegram bot token, OCR credentials, or
network access — everything runs against the deterministic `DummyOCREngine`
and mocked Telegram/HTTP/PaddleOCR clients.

## Evaluation tool: `tools/evaluate_sample.py`

A local CLI for validating the OCR pipeline against a real (or synthetic)
Persian PDF without touching CI or requiring credentials by default:

```powershell
# Fully offline, zero-credential smoke test (default engine):
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf

# Real backends (each needs its own optional dependency/credential):
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf --engine tesseract
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf --engine paddle --paddle-lang fa
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf --engine vision_llm `
    --vision-llm-provider gemini --vision-llm-api-key $env:VISION_LLM_API_KEY
```

It reuses `ocr.engine.get_ocr_engine`, `ocr.pipeline.process_pdf`, and
`converters.*` directly (no duplicated OCR/rendering/conversion logic),
reports runtime/page-count/character-count/output-size metrics
(human-readable or `--json`), and exits with an actionable nonzero status
(`1` usage error, `2` missing optional dependency/credential or exhausted
rate-limit retries, `3` pipeline failure) instead of a raw traceback. Never
requires network access or real books to be committed - no sample PDFs are
checked into the repository.

## Known limitations

- **Dummy OCR is the default engine.** `OCR_ENGINE=dummy` (the default in
  `.env.example` and `Settings`) returns fixed placeholder Persian text per
  page (`متن نمونه صفحه {page_number}`) rather than real recognized text.
  This is intentional for offline/credential-free CI and local development,
  but means the bot does **not** yet produce real OCR output out of the box.
  Three real backends exist behind the same `OCREngine` interface:
  - `OCR_ENGINE=tesseract` (`TesseractOCREngine`) requires `pytesseract` +
    the Tesseract binary with Persian (`fas`) language data installed.
  - `OCR_ENGINE=paddle` (`PaddleOCREngine`) requires the optional `paddle`
    extra (`pip install .[paddle]`, i.e. `paddleocr` + `paddlepaddle`);
    falls back from `PADDLE_LANG=fa` to Arabic-script (`ar`) recognition if
    the requested language model is unavailable.
  - `OCR_ENGINE=vision_llm` (`VisionLLMOCREngine`) prompts a vision-capable
    LLM (Gemini or Claude, selected via `VISION_LLM_PROVIDER`) to transcribe
    each page image over HTTP; requires the optional `vision-llm` extra
    (`pip install .[vision-llm]`, i.e. `httpx`) and a real `VISION_LLM_API_KEY`.
  None of these three has been validated against real scanned books yet;
  `tools/evaluate_sample.py` is the new local tool for doing so (structural
  correctness is still unit-tested with mocks only in `tests/`).
- No real Telegram bot token has been exercised end-to-end (the bot only
  runs in polling mode if `BOT_TOKEN` is set; this has been unit-tested
  with mocks, not live-tested against the Telegram API).
- No font binaries are bundled; `PERSIAN_FONT_NAME` is an optional hook and
  falls back to a generic font family if unset — licensing of any real
  Persian font is left to the deployer.
- No deployment/infrastructure (containers, CI workflows, hosting) has been
  set up yet; this is out of scope for the current milestone.
- The Mini App frontend (`web/`) is now theme-aware/accessible/resilient
  but still has no job-history/list view and no inline document preview
  before download (tracked as remaining Milestone 2 follow-ups in
  `docs/ROADMAP.md`).

## Operational readiness

- ✅ Installable and runnable locally via `requirements-dev.txt` + `.venv`.
- ✅ Fully offline test suite suitable for CI without secrets.
- ✅ FastAPI Mini App backend runs standalone (no bot token required).
- ✅ Local sample-evaluation CLI (`tools/evaluate_sample.py`) available for
  manually validating any of the four OCR engines against a real PDF,
  without requiring network/credentials for the default `dummy` engine.
- ⚠️ Real Persian OCR output requires switching `OCR_ENGINE` to a real
  backend and validating it against real scans (tracked in
  `docs/ROADMAP.md`).
- ⚠️ No CI workflow file exists yet in `.github/workflows/`; `pytest tests/`
  must currently be run manually before merging.

## Links

- Architecture: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Roadmap: [`docs/ROADMAP.md`](ROADMAP.md)
- Agent collaboration guide: [`docs/agents/AGENT_GUIDE.md`](agents/AGENT_GUIDE.md)
- Global agent rules: [`../AGENTS.md`](../AGENTS.md)

