# Project Status

_Last updated: 2026-09-14 (containerization & deployment milestone)_

## Current milestone: Containerization, deployment readiness, and periodic cleanup scheduling

Milestone 4 (`docs/ROADMAP.md`) has been delivered on branch
`feature/containerization-deployment`: a production-ready multi-stage
`Dockerfile`, `docker-compose.yml` orchestration, a `.dockerignore`, and a
configurable periodic cleanup scheduler wired into `bot.main`, on top of
the previously delivered Milestone 3 operations hardening (CI, structured
logging, retention hooks, `GET /api/health`):

- **`Dockerfile`** (repo root): two-stage build (`builder` installs
  `requirements.txt` into a venv with a C toolchain available;
  `runtime` is a slim `python:3.11-slim` layer with only the venv, app
  source, and the runtime system libraries actually needed — JPEG/PNG/
  JP2/TIFF codecs and font discovery for Pillow/PyMuPDF, plus optional
  `tesseract-ocr`/`tesseract-ocr-fas` so `OCR_ENGINE=tesseract` works out
  of the box). Runs as a fixed non-root user (`app`, UID/GID 1000),
  creates/owns `/app/data/uploads` and `/app/data/output`
  (`chown app:app`, `chmod 750`), sets safe credential-free environment
  defaults (mirroring `Settings` defaults; `BOT_TOKEN`/
  `VISION_LLM_API_KEY` are never set in the image), and declares a
  `HEALTHCHECK` against `GET /api/health`.
- **`docker-compose.yml`**: single `bot` service, port `8000` published,
  `./data:/app/data` persistent bind mount, `env_file: .env` for runtime
  secret/config injection (never baked into the image or committed),
  `restart: unless-stopped`, and a matching `healthcheck:` block.
- **`.dockerignore`**: excludes `.git`, `.venv`, `.pytest_cache`, `tests/`,
  `.env`/`.env.*` (keeping `.env.example`), bytecode caches, and the
  runtime `data/` directory from the build context.
- **Periodic cleanup scheduler** (`src/bot/main.py::periodic_cleanup_worker`):
  an `asyncio` loop that calls `default_job_manager.cleanup_stale_jobs()`
  every `Settings.cleanup_interval_seconds` (new setting, default 3600s/1h)
  for the lifetime of the process. Wired into both `main()` run paths —
  the Telegram-polling path via `Application.post_init`/`post_shutdown`
  hooks, and the API-only path via a `finally`-guarded task cancellation —
  so the worker is always cancelled/awaited cleanly on shutdown. Requires
  no credentials and is disabled (returns immediately, no cleanup ever
  runs) when `cleanup_interval_seconds <= 0`.
- **Docker/compose validation**: no Docker engine was available in the
  build/verification environment for this milestone, so validation was
  static: the `Dockerfile` was parsed instruction-by-instruction (stage
  names, valid instruction keywords, line-continuation handling) and
  `docker-compose.yml` was parsed with `yaml.safe_load` and inspected for
  the expected `services.bot.{build,ports,volumes,env_file,restart,
  healthcheck}` keys — both passed. **No image has been built or run**;
  build/run validation against a real Docker engine remains an open
  follow-up (see `docs/ROADMAP.md`).

Milestone 3 (`docs/ROADMAP.md`) was delivered on branch
`feature/operations-hardening`: a GitHub Actions CI workflow, structured
logging, configurable `JobManager` retention/cleanup hooks, a `GET
/api/health` liveness endpoint, and a fix making the test suite hermetic
against an ambient local `.env` file — alongside the previously verified
core pipeline, production OCR backends, and Mini App UI:

- **CI**: `.github/workflows/ci.yml` runs on every push/PR targeting
  `main`, on an Ubuntu Python 3.10/3.11/3.12 matrix, installing
  `requirements-dev.txt` and running `pytest tests/` with no credentials
  required. A lint step runs only if a linter is already configured in the
  repo (currently none is, so it is skipped rather than forcing a new tool
  in).
- **Hermetic test isolation fix**: `Settings` (`src/bot/config.py`) now
  resolves its dotenv path from `BOT_ENV_FILE` at import time (unset =
  `.env` as before, `""` = dotenv loading disabled entirely).
  `tests/conftest.py` sets `BOT_ENV_FILE=""` before any test imports
  `bot.config`, so `pytest tests/` no longer silently reads a real
  developer's `BOT_TOKEN`/other secrets from a local `.env` — this was a
  real, previously-unnoticed bug (`test_settings_default_bot_token_is_none_and_safe`
  and `test_settings_can_be_constructed_directly_without_env` would fail
  whenever a workspace had a non-empty `BOT_TOKEN` in `.env`).
- **Structured logging** (`src/bot/logging_config.py`): a JSON formatter
  (one object per line, for log aggregation) and a human-readable console
  formatter, both attaching `job_id`/`user_id`/`duration`/`error` context
  via `log_event()`/`log_duration()`, with a small set of secret-shaped
  keys (`bot_token`, `api_key`, ...) always scrubbed before rendering.
  Configured once at startup via `configure_logging()` (`bot.main`), driven
  by the new `Settings.log_format`/`Settings.log_level` fields. Integrated
  into `JobManager.create_job()`/`run_pipeline()`/`cleanup_stale_jobs()`.
- **Job retention/cleanup hooks** (`src/bot/jobs.py`):
  `JobManager.cleanup_stale_jobs()` prunes finished jobs (`done`/`failed`/
  `rate_limited`) and their associated upload/output files once older than
  the configurable `Settings.job_retention_seconds` TTL (default 24h).
  In-flight jobs are never touched; every file-removal failure is caught
  and recorded in the returned `CleanupResult.errors` list instead of
  raising, so cleanup never crashes on one bad path. The in-memory
  architecture is unchanged — no database was introduced.
- **`GET /api/health`** (`src/bot/api.py`): a dependency-free liveness
  probe returning `{"status": "ok", "uptime_seconds": ...}` — no
  configuration/secret exposure, suitable for uptime checks/load
  balancers.

Alongside the previously verified core pipeline, production OCR backends,
and Mini App:

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
  (bytes) once a job is `done`, for Mini App download cards, and pruning
  finished jobs/files past `Settings.job_retention_seconds` via
  `cleanup_stale_jobs()`
- Telegram bot handlers with retry-on-rate-limit (`src/bot/telegram_handlers.py`)
- FastAPI Mini App backend (upload/status/download, plus a new
  `GET /api/config` endpoint exposing `max_file_size_mb`/`formats` so the
  frontend never hardcodes limits separately from `Settings`, and
  `GET /api/health` for liveness checks)
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

**108 tests passing**, 0 failing, across:

- `tests/test_bot_main_scheduler.py` — **new**: `periodic_cleanup_worker()`
  behavior (disabled when `cleanup_interval_seconds <= 0`, runs
  `cleanup_stale_jobs()` on each tick, stops cleanly via a stop event,
  survives per-sweep errors without dying, and is cleanly cancellable) plus
  `Settings.cleanup_interval_seconds` default/env-override coverage — all
  using a fake in-memory job manager and short/zero intervals, no network
  or Docker dependency

- `tests/test_ocr_pipeline.py` — rendering, deskew, OCR abstraction, retry/backoff
- `tests/test_ocr_production_engines.py` — `PaddleOCREngine`/`VisionLLMOCREngine`
  factory registration, response mapping, provider error/rate-limit
  mapping, and retry/backoff, all with `paddleocr`/`httpx` mocked at the
  module boundary
- `tests/test_converters.py` — TXT/DOCX/EPUB output and RTL directionality
- `tests/test_bot_config.py` — settings loading/defaults, hermetic against
  an ambient local `.env`
- `tests/test_bot_jobs.py` — job lifecycle/status transitions and
  `cleanup_stale_jobs()` retention behavior (finished-job pruning,
  in-flight jobs untouched, file-removal error containment)
- `tests/test_bot_logging.py` — JSON/console structured logging
  formatters, `log_event`/`log_duration` context + secret scrubbing
- `tests/test_bot_telegram_handlers.py` — retry-on-`RetryAfter`/network error
- `tests/test_bot_api.py` — Mini App upload/status/download/config/health
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
- **Docker image has not been built/run against a real Docker engine** —
  the environment used to author Milestone 4 had no Docker installed, so
  the `Dockerfile`/`docker-compose.yml` were validated statically (see
  above) only. Building and running the image (and exercising the
  `HEALTHCHECK`/volume ownership end-to-end) against a real engine is the
  key open follow-up.
- `JobManager` remains **in-memory only** — `cleanup_stale_jobs()` prunes
  stale entries/files but does not persist state across process restarts;
  a durable/multi-process job store remains out of scope by design (see
  scope boundaries in `AGENTS.md`).
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
- ✅ CI (`.github/workflows/ci.yml`) runs `pytest tests/` on every push/PR
  targeting `main` across a Python 3.10/3.11/3.12 matrix, no credentials
  required.
- ✅ Containerized deployment: multi-stage `Dockerfile` (non-root UID/GID
  1000, `/api/health` `HEALTHCHECK`) + `docker-compose.yml` (persistent
  `./data` volume, `env_file: .env` runtime injection, `restart:
  unless-stopped`) + `.dockerignore`; validated statically (no Docker
  engine available in this environment — see "Known limitations").
- ✅ Periodic in-process cleanup: `bot.main.periodic_cleanup_worker()`
  invokes `default_job_manager.cleanup_stale_jobs()` hourly by default
  (`Settings.cleanup_interval_seconds`), with clean cancellation on
  shutdown.
- ⚠️ Real Persian OCR output requires switching `OCR_ENGINE` to a real
  backend and validating it against real scans (tracked in
  `docs/ROADMAP.md`).
- ⚠️ The container image itself has not been built/run — build/run
  validation against a real Docker engine is the key remaining deployment
  follow-up.

## Links

- Architecture: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Roadmap: [`docs/ROADMAP.md`](ROADMAP.md)
- Agent collaboration guide: [`docs/agents/AGENT_GUIDE.md`](agents/AGENT_GUIDE.md)
- Global agent rules: [`../AGENTS.md`](../AGENTS.md)

