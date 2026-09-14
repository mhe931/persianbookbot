# Agent Guide: persianbookbot

This document defines how specialist agents (human or AI) collaborate on the
`persianbookbot` codebase: a Telegram bot + Mini App that converts scanned
Persian PDF books into EPUB, DOCX, and TXT via an async Persian OCR/RTL
pipeline.

## Architecture at a glance

```
Scanned PDF
   -> src/ocr/preprocessing.py   (render pages, grayscale + deskew)
   -> src/ocr/engine.py          (OCR abstraction: DummyOCREngine / TesseractOCREngine)
   -> src/ocr/pipeline.py        (async orchestrator -> common.models.Book)
   -> src/converters/{txt,docx_writer,epub_writer}.py (Book -> .txt/.docx/.epub, RTL-aware)
   -> src/bot/jobs.py            (JobManager drives the pipeline, tracks ConversionJob)
   -> src/bot/telegram_handlers.py + src/bot/api.py (delivery: Telegram chat / Mini App HTTP API)
   -> web/                       (static Telegram Mini App frontend)
```

Shared contracts live in `src/common/models.py` (`Book`, `PageImage`, `PageText`,
`ConversionJob`, `JobStatus`). Every subsystem below reads/writes only these
shared dataclasses — do not introduce parallel/duplicate models.

## Specialist agent boundaries

### 1. OCR / Pipeline agent — `src/ocr/`
- Owns: PDF page rendering (`preprocessing.py`), OCR engine abstraction and
  deterministic fallback (`engine.py`), Persian RTL/BiDi text helpers
  (`rtl.py`), and the async orchestration (`pipeline.py`).
- Contract: `process_pdf(pdf_path, engine=None, ...) -> Book`. Must work fully
  offline via `DummyOCREngine` (the default) with zero credentials, so tests
  and CI never need a real OCR service. Real engines (e.g. Tesseract) are
  optional, pluggable via `OCR_ENGINE` env var, and must fail with a clear
  error only when actually invoked without their runtime dependency present.
- Rate limits/retries: `RateLimitError` from an engine must be retried with
  exponential backoff inside `process_pdf` (`max_retries`, `backoff_seconds`),
  not swallowed silently and not left to crash the caller.

### 2. Document Generation agent — `src/converters/`
- Owns: `write_txt`, `write_docx`, `write_epub`, and `fonts.py` (Persian font
  name/path configuration hooks — no font binaries are ever bundled/shipped;
  licensing is the deployer's responsibility).
- Contract: each `write_*` function takes a `Book` and an output path and
  returns a `pathlib.Path`. DOCX/EPUB must set explicit RTL directionality
  (OXML `w:bidi`/`w:rtl` for DOCX; `dir="rtl"` + CSS `direction:rtl` for EPUB)
  rather than relying on visual character reshaping — logical text order is
  preserved and readers handle bidi reordering themselves.

### 3. Telegram Bot & Mini App agent — `src/bot/`, `web/`
- Owns: environment-driven configuration (`config.py`), the in-memory async
  job orchestrator (`jobs.py`), Telegram chat handlers (`telegram_handlers.py`),
  the FastAPI Mini App backend (`api.py`), the process entrypoint (`main.py`),
  and the static Mini App frontend (`web/`).
- Contract: `Settings.bot_token` defaults to `None`; nothing in this package
  may require a real token to import or to run the API standalone. All
  Telegram/network calls that can hit rate limits (`RetryAfter`) or transient
  errors (`TimedOut`, `NetworkError`) must retry with backoff
  (`_send_with_retry`). Large uploads are rejected by declared size *before*
  download. The Telegram bot and the Mini App API share one `JobManager`
  (`bot.jobs.default_job_manager`) so a job started from either surface can be
  polled/downloaded from both.

### 4. Verification / QA agent — `tests/`
- Owns: automated tests for pipeline artifacts, RTL/layout correctness,
  configuration loading, large-file/rate-limit fallback behavior, and mocked
  file-transfer flows (bot handlers, Mini App API), using generated/dummy
  fixtures only — no real PDFs, tokens, or network calls.
- Contract: `pytest tests/` must pass locally with `PYTHONPATH=src` (already
  configured via `pyproject.toml`'s `[tool.pytest.ini_options]`). Tests must
  not depend on external services (Telegram, real OCR APIs) or on execution
  order.

## Task handoff protocol

1. Read `src/common/models.py` before touching any other module — it is the
   single source of truth for data shapes crossing subsystem boundaries.
2. Do not edit another subsystem's owned files. If integration reveals a bug
   in another subsystem, report it precisely (file, function, expected vs.
   actual) rather than silently patching around it, unless you are the
   integrator responsible for final wiring.
3. Every new module must be importable with `PYTHONPATH` pointed at `src/`
   without requiring any environment variable, network access, or credential.
4. Validate your own subsystem in isolation (unit-level smoke checks) before
   handing off; the integrator/QA agent is responsible for cross-subsystem
   end-to-end verification.

## Operational runbook

**Setup**
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env   # then fill in BOT_TOKEN only if running the real bot
```

**Run the Mini App API only (no bot token needed)**
```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m bot.main
```

**Run the full bot + API** — set `BOT_TOKEN` in `.env`, then run the same
command; `bot.main` will start Telegram polling on the main thread and the
FastAPI app in a background thread.

**Run tests**
```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest tests/
```
(or simply `pytest tests/` from repo root — `pyproject.toml` sets
`pythonpath = ["src"]` for pytest automatically.)

## Credentials policy

- Never commit a real `BOT_TOKEN`, webhook URL, or any secret. `.env` is
  git-ignored; `.env.example` only ever contains empty placeholders or safe
  defaults.
- All configuration is read via `pydantic-settings` (`src/bot/config.py`),
  which loads from environment variables and an optional local `.env` file.
- The OCR pipeline's default engine (`DummyOCREngine`) and all tests must
  operate with zero external credentials.

## Git workflow

- Work happens on feature branches named after the goal, e.g.
  `feature/bot-core-pipeline`.
- Builder commits are tagged `[B]` in the subject and include the trailer
  `Assisted-by: Claude:Sonnet-4.6`; Inspector/QA review commits are tagged
  `[I]` with `Assisted-by: Claude:Haiku-4.5`.
- Commit subjects follow Conventional Commits (`type(scope): [marker] summary`,
  ≤72 characters), e.g. `feat(bot): [B] implement Persian PDF pipeline`.
- Keep unrelated worktree changes untouched — scaffold/implementation work
  must not clobber pre-existing files outside the task's scope.
- Do not open a pull request unless repository access/credentials are already
  configured and it is safe to do so; this scaffold is validated locally via
  `pytest tests/` first.
