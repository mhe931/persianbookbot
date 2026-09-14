# Project Status

_Last updated: 2026-09-14_

## Current milestone: Core pipeline scaffold verified

The Persian PDF -> EPUB/DOCX/TXT bot pipeline has been implemented and
verified end-to-end on branch `feature/bot-core-pipeline`:

- PDF rendering + grayscale/deskew preprocessing (`src/ocr/preprocessing.py`)
- Pluggable OCR engine abstraction with a deterministic offline default
  (`src/ocr/engine.py`: `DummyOCREngine`, optional `TesseractOCREngine`)
- Async pipeline orchestrator with rate-limit retry/backoff
  (`src/ocr/pipeline.py`)
- Persian RTL/BiDi text helpers (`src/ocr/rtl.py`)
- TXT/DOCX/EPUB writers with explicit RTL directionality
  (`src/converters/`)
- Async in-memory job orchestration shared by both delivery surfaces
  (`src/bot/jobs.py`)
- Telegram bot handlers with retry-on-rate-limit (`src/bot/telegram_handlers.py`)
- FastAPI Mini App backend (upload/status/download) (`src/bot/api.py`)
- Static Telegram Mini App frontend (`web/`)
- Environment-driven configuration with safe, credential-free defaults
  (`src/bot/config.py`)

## Test status

**46 tests passing**, 0 failing, across:

- `tests/test_ocr_pipeline.py` — rendering, deskew, OCR abstraction, retry/backoff
- `tests/test_converters.py` — TXT/DOCX/EPUB output and RTL directionality
- `tests/test_bot_config.py` — settings loading/defaults
- `tests/test_bot_jobs.py` — job lifecycle and status transitions
- `tests/test_bot_telegram_handlers.py` — retry-on-`RetryAfter`/network error
- `tests/test_bot_api.py` — Mini App upload/status/download endpoints
- `tests/test_integration.py` — end-to-end PDF-to-output flow

Run locally:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest tests/
```

The suite requires **no** real Telegram bot token, OCR credentials, or
network access — everything runs against the deterministic `DummyOCREngine`
and mocked Telegram/HTTP clients.

## Known limitations

- **Dummy OCR is the default engine.** `OCR_ENGINE=dummy` (the default in
  `.env.example` and `Settings`) returns fixed placeholder Persian text per
  page (`متن نمونه صفحه {page_number}`) rather than real recognized text.
  This is intentional for offline/credential-free CI and local development,
  but means the bot does **not** yet produce real OCR output out of the box.
  A real backend (`OCR_ENGINE=tesseract`, structurally implemented in
  `TesseractOCREngine`) requires `pytesseract` + the Tesseract binary with
  Persian (`fas`) language data installed, and has not been validated
  against real scanned books yet.
- No real Telegram bot token has been exercised end-to-end (the bot only
  runs in polling mode if `BOT_TOKEN` is set; this has been unit-tested
  with mocks, not live-tested against the Telegram API).
- No font binaries are bundled; `PERSIAN_FONT_NAME` is an optional hook and
  falls back to a generic font family if unset — licensing of any real
  Persian font is left to the deployer.
- No deployment/infrastructure (containers, CI workflows, hosting) has been
  set up yet; this is out of scope for the current milestone.
- The Mini App frontend (`web/`) is a minimal vanilla HTML/CSS/JS scaffold,
  not a polished UI.

## Operational readiness

- ✅ Installable and runnable locally via `requirements-dev.txt` + `.venv`.
- ✅ Fully offline test suite suitable for CI without secrets.
- ✅ FastAPI Mini App backend runs standalone (no bot token required).
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
