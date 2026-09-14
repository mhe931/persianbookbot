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
- `bot.jobs.default_job_manager` is a shared singleton `JobManager` used by
  **both** the Telegram handlers and the FastAPI API, so a job started from
  either surface can be polled/downloaded from both. Do not create a second
  independent `JobManager` instance for a new delivery surface without a
  deliberate reason.
- `JobManager.run_pipeline()` is the top-level entry point for a background
  task: it must catch all exceptions internally and translate them into a
  terminal `JobStatus` (`FAILED` or `RATE_LIMITED`) rather than letting them
  propagate and crash the caller's task/event loop.

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

## Static frontend (`web/`)

- `src/bot/api.py` mounts `web/` as a catch-all static route **last**, so
  `/api/...` routes always take precedence. Do not reorder route
  registration such that a new API route ends up after the static mount.
- Keep the frontend framework-free (vanilla HTML/CSS/JS) unless a roadmap
  milestone (see `docs/ROADMAP.md`) explicitly calls for a framework
  migration.

## Tests

- New bot/API behavior must be covered with mocked Telegram objects / an
  in-process FastAPI test client — never a real bot token, live Telegram
  API call, or real network request. Run `pytest tests/` (46 tests as of
  this writing) before committing.
