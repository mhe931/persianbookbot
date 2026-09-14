---
applyTo: "src/bot/**,web/**"
---

# Bot & Mini App instructions

Scope: `src/bot/` (Telegram bot, job orchestration, FastAPI Mini App
backend) and `web/` (static Mini App frontend). See `docs/ARCHITECTURE.md`
for the full pipeline context and `AGENTS.md` for repo-wide rules.

## Contract

- `Settings.bot_token` (`src/bot/config.py`) **must always default to
  `None`**. Nothing in this package may require a real Telegram bot token,
  OCR credential, or network access to import, to run the FastAPI app
  standalone, or to pass its tests.
- Configuration is read exclusively via `pydantic-settings`
  (`Settings`/`get_settings()`), sourced from environment variables and an
  optional local `.env` file. Do not read `os.environ` directly elsewhere
  in this package — add new fields to `Settings` instead.
- Dotenv loading is controlled by `BOT_ENV_FILE` (resolved once at
  `bot.config` import time): unset loads `.env` as usual, an explicit path
  loads that file instead, and `""` (empty) disables dotenv loading
  entirely. `tests/conftest.py` sets `BOT_ENV_FILE=""` before any test
  imports `bot.config`, so `Settings()`/`get_settings()` in tests never
  read a real local `.env` — do not remove that guard, and do not add new
  test code that reads `.env` directly.
- `bot.jobs.default_job_manager` is a shared singleton `JobManager` used by
  **both** the Telegram handlers and the FastAPI API, so a job started from
  either surface can be polled/downloaded from both. Do not create a second
  independent `JobManager` instance for a new delivery surface without a
  deliberate reason.
- `JobManager.run_pipeline()` is the top-level entry point for a background
  task: it must catch all exceptions internally and translate them into a
  terminal `JobStatus` (`FAILED` or `RATE_LIMITED`) rather than letting them
  propagate and crash the caller's task/event loop.
- `JobManager.cleanup_stale_jobs()` prunes finished jobs (`DONE`/`FAILED`/
  `RATE_LIMITED`) and their upload/output files once older than
  `settings.job_retention_seconds` (default 24h). It never touches
  in-flight jobs, and every file-removal failure is caught and recorded in
  the returned `CleanupResult.errors` list rather than raised — do not let
  a single bad path abort cleanup of the remaining jobs.

## Logging

- `src/bot/logging_config.py` provides `configure_logging()` (call once at
  process startup — see `bot.main`), `log_event()`, and `log_duration()`
  for structured logging with `job_id`/`user_id`/`duration`/`error`
  context. Prefer these helpers over ad-hoc `logger.info(f"...")` string
  interpolation when logging job/request lifecycle events.
- Never pass a `Settings` object, `bot_token`, API key, or any other
  credential into a logging call — `log_event`/the formatters drop a
  well-known set of secret-shaped keys as defense in depth, but that is not
  a substitute for not passing secrets in the first place.
- `LOG_FORMAT` (`"console"` default or `"json"`) and `LOG_LEVEL` are read
  from `Settings`; do not hardcode a different logging setup elsewhere in
  this package.

## Retry / resilience

- All outbound Telegram calls that can hit `RetryAfter` (rate limit),
  `TimedOut`, or `NetworkError` must go through the existing
  `_send_with_retry` helper (`telegram_handlers.py`) with backoff — do not
  add a raw unguarded Telegram API call.
- OCR-side rate limits (`ocr.engine.RateLimitError`) are handled inside
  `ocr.pipeline.process_pdf` / surfaced as `JobStatus.RATE_LIMITED` by
  `run_pipeline` — do not duplicate retry logic in the bot layer for that
  path.

## Uploads (`src/bot/api.py`)

- Enforce `settings.max_file_size_mb` by rejecting an oversized upload
  **before** it is fully buffered/written to disk (read in bounded chunks,
  as the existing `upload_pdf` endpoint does) — never load an unbounded
  upload into memory first.
- Only accept PDF uploads (`content_type == "application/pdf"` or a
  `.pdf` filename suffix); reject everything else with a 4xx.
- `/api/download/{job_id}/{fmt}` must only serve a file once the job's
  `JobStatus` is `DONE` and the output path actually exists on disk.
- `GET /api/config` exposes `settings.max_file_size_mb` and the valid
  format set so the Mini App frontend can validate uploads client-side
  without hardcoding a limit separately from `Settings` — add new
  frontend-facing config fields here rather than duplicating them in
  `web/app.js`.
- `GET /api/health` is a lightweight liveness probe: no I/O, no
  configuration/credential exposure, just `{"status": "ok",
  "uptime_seconds": ...}`. Keep it dependency-free — do not add DB/OCR
  engine checks to it without a deliberate reason, since its only job is
  to answer quickly for uptime checks/load balancers.
- `ConversionJob.to_dict()` (`src/common/models.py`) includes a
  best-effort `output_sizes` dict (bytes per format, once available) for
  Mini App download-card metadata — keep computing this from the actual
  files on disk (never trust a stale/cached size) and keep it optional
  (skip a format whose file is missing/unreadable) rather than raising.

## Static frontend (`web/`)

- `src/bot/api.py` mounts `web/` as a catch-all static route **last**, so
  `/api/...` routes always take precedence. Do not reorder route
  registration such that a new API route ends up after the static mount.
- Keep the frontend framework-free (vanilla HTML/CSS/JS) unless a roadmap
  milestone (see `docs/ROADMAP.md`) explicitly calls for a framework
  migration.
- Milestone 2 (`docs/ROADMAP.md`) added Telegram theme CSS variables
  (`--tg-theme-*`, with light-mode fallbacks), a five-step progress
  indicator driven by `JobStatus`, format-selection toggles, download
  cards with file-size indicators, and defensive
  `window.Telegram.WebApp` (`ready`/`expand`/`MainButton`/haptics)
  integration in `web/app.js`. Any Telegram WebApp API call must stay
  wrapped so a plain (non-Telegram) browser never throws.
- `web/app.js` fetches `GET /api/config` for `max_file_size_mb` but must
  keep a safe hardcoded fallback (20MB) if that request fails, so the
  Mini App stays usable even when the backend/network is unavailable.

## Tests

- New bot/API behavior must be covered with mocked Telegram objects / an
  in-process FastAPI test client — never a real bot token, live Telegram
  API call, or real network request. Run `pytest tests/` (101 tests as of
  this writing) before committing.
- Tests must stay hermetic against an ambient local `.env` (see the
  `BOT_ENV_FILE` contract note above) — don't add a test that relies on
  real dotenv content, and prefer `Settings(...)` kwargs or
  `monkeypatch.setenv(...)` + `config.reset_settings_cache()` for
  test-specific configuration.
