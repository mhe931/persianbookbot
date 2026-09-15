# Project Status

_Last updated: 2026-09-15 (Milestone 11 delivery report and operational runbook)_

## Current milestone: Milestone 11 — Delivery report and operational runbook ✅ (documentation-only finalization)

Delivered on branch `feature/delivery-report-runbook`, forked from `main`
at `a347df3` (post–Milestone 10): a single, self-contained
`docs/DELIVERY_REPORT.md` consolidating all ten prior milestones —
capability matrix, architecture/data flow/shared contracts, local and
Docker/production deployment quickstarts, polling/webhook configuration,
the evaluation CLI, the security/secret-management model, full test
verification, and a prioritized cloud-host/OCR handoff checklist. **No
application, converter, OCR, or deployment-code logic was changed.**

- ✅ `docs/DELIVERY_REPORT.md` (new): reconciled against current source,
  `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, `docs/PRODUCTION_READINESS.md`,
  `docs/LIVE_STAGING_VALIDATION.md`, and `docs/BENCHMARK_RESULTS.md` — no
  live metric or infrastructure result is claimed beyond what those
  reports already evidence.
- ✅ `pytest tests/` re-verified: **157 passed, 0 failed**, fully offline —
  identical count to Milestones 6–10.
- ✅ Git/secret/artifact integrity re-checked across all local refs and
  tags (none exist): no tracked `.env`/`.pem`/`.key`/`.crt`/`.pdf`, no
  such file ever added in history, no token-shaped literal in any
  reachable commit, `.env` confirmed git-ignored and untracked.
- ✅ README.md/`docs/ROADMAP.md` updated with a pointer to the final
  report and an explicit statement that the project transitions from
  active feature development to an operations/live-validation handoff —
  no further application milestones are planned; remaining work is the
  cloud-host/OCR checklist in `docs/DELIVERY_REPORT.md` §14.
- **Not live-validated** (unchanged from every prior milestone): this is a
  documentation-only pass, so the Docker/VPS/TLS/Telegram/OCR-provider
  constraints restated in `docs/DELIVERY_REPORT.md` §13 remain exactly as
  they were after Milestone 10.

## Previous milestone: Milestone 10 — Production host validation attempt ⏸️ (blocked; no Docker host available)

Attempted on branch `feature/production-host-validation`, forked from
`main` at `41cbd23`: a full re-attempt of Milestone 9's live
Docker/Compose deployment, health-probe, UID/GID 1000, sample-PDF
conversion, and metrics-capture procedure. **No application code
changed; no container was run.**

- ✅ Re-verified (fresh command output, same machine): no Docker Engine,
  no Docker Compose CLI, no usable WSL Linux distribution (`wsl.exe` is
  only the launcher stub; the feature itself is not installed), and the
  only Docker-named Windows service is an unrelated Flexera inventory
  monitor — none of these is a Docker-capable host.
- ✅ Re-confirmed the two pre-existing SSH aliases and the authenticated
  Azure CLI session are unrelated to persianbookbot and were **not**
  contacted or used, per the explicit "no guessing hosts" scope
  boundary — identical finding to Milestone 9.
- ✅ `.env` key-presence (not value) re-scanned: unchanged from Milestone
  9 (`WEBHOOK_URL` still empty, `OCR_ENGINE` still the credential-free
  `dummy` default).
- ✅ `pytest tests/` re-verified: **157 passed, 0 failed**, fully offline
  — identical count to Milestones 6–9.
- ✅ Tracked-secret/artifact hygiene re-checked: `git ls-files` has no
  `.env`/`.pem`/`.key`/`.pdf`/`.crt`; `git status --porcelain` shows only
  the untracked `.goals/` planning folder.
- **Blocked — same root cause as Milestones 5, 6, 7, 8, 9**: no Docker
  Engine or Docker-capable host is available in this authoring
  environment, so the production Compose stack was not started, `/healthz`
  and `/api/health` were not probed live, UID/GID 1000 bind-mount
  behavior was not runtime-exercised, no sample PDF was converted through
  a live API, and no runtime metrics were captured. See
  `docs/LIVE_STAGING_VALIDATION.md` ("Milestone 10 re-attempt" section)
  for the full reproducible evidence and unchanged operator handoff.

## Previous milestone: Milestone 9 — Live cloud staging validation attempt ⏸️ (blocked; safe discovery only)

Delivered on branch `feature/live-staging-deployment`: a fresh,
non-destructive discovery pass over Docker/Compose, WSL, configured
Docker contexts, SSH targets, and cloud CLI tooling, producing the new
`docs/LIVE_STAGING_VALIDATION.md`. **No application code changed.**

- ✅ New `docs/LIVE_STAGING_VALIDATION.md`: the canonical Milestone 9
  continuity report — exact commands and output for Docker/Compose/WSL/
  SSH/cloud-CLI discovery, a key-presence-only `.env` scan (no secret
  value read or used), a restated TLS/webhook/health-endpoint blocker
  list with unblock commands, and re-confirmed UID/GID 1000 Dockerfile
  evidence.
- ✅ `pytest tests/` re-verified: **157 passed, 0 failed**, fully offline
  — identical count to Milestones 6–8, since no test was added/removed.
- **Still blocked, same root cause as Milestones 5–8**: this environment
  has no Docker engine, no WSL, no persianbookbot-designated Linux host
  or domain, and no scanned Persian PDF sample. Two unrelated SSH hosts
  and an authenticated Azure CLI session exist on this machine but are
  **not** persianbookbot deployment targets and were correctly left
  untouched per this milestone's scope (no guessing hosts, no
  provisioning without explicit configured access). See
  `docs/LIVE_STAGING_VALIDATION.md` for the full, reproducible evidence
  and the exact operator handoff commands.

## Previous milestone: Milestone 8 — Production-readiness audit ✅ (verified; live infra unchanged)

Delivered on branch `feature/production-readiness-audit`: a full
source-anchored, read-only audit of all seven prior milestones (core
pipeline, production OCR backends, Mini App UI, operations hardening,
containerization, webhook support, and the staging deployment bundle),
producing the new `docs/PRODUCTION_READINESS.md` and refreshing this
continuity documentation set. **No application code changed** — this
milestone is verification/documentation only.

- ✅ `docs/PRODUCTION_READINESS.md` (new): authoritative production-
  readiness report — architecture, interfaces/dependencies, a security/
  credential-handling audit, a per-acceptance-criterion static behavioral
  audit (RTL/BiDi, converter font hooks, OCR error mapping, polling/
  webhook exclusivity, webhook secret validation, health/cleanup behavior,
  Mini App configuration/lifecycle/upload handling, Docker/Compose/Nginx/
  bootstrap coherence), full test verification, Git/secret-hygiene
  verification, a deployment pre-flight checklist, and an honest,
  consolidated statement of what remains live-unvalidated.
- ✅ **No defects found**: every static-audit item above was verified
  against the current source and passed; no regression, secret exposure,
  or coherence gap was identified in `src/`, `web/`, `tools/`, `deploy/`,
  the root `Dockerfile`/`docker-compose.yml`, or `.github/`.
- ✅ **Test suite re-verified**: `pytest tests/` — **157 passed, 0
  failed**, fully offline, zero credentials, matching every prior
  milestone's own count exactly (no test added or removed by this audit).
- ✅ **Git/secret hygiene re-verified**: `.env` confirmed git-ignored and
  untracked; no committed secrets, private keys, certificates, PDFs, or
  generated runtime artifacts found anywhere in tracked history
  (`git ls-files`, `git log --all --diff-filter=A`, and `git grep` for
  token-shaped patterns all came back clean).
- ✅ README.md/AGENTS.md/`docs/ROADMAP.md` updated with this milestone's
  findings and a pointer to `docs/PRODUCTION_READINESS.md` for the
  operational-maintenance handoff.
- **Not live-validated** (restated, not newly discovered — same
  environment constraints as every prior milestone): no Docker engine, no
  VPS/DNS record, no TLS issuance, and no real Telegram/OCR-provider
  credential were available in this environment, so this audit could not
  build/run the Docker image, bring up `deploy/docker-compose.prod.yml`
  against a real domain, or exercise a live Telegram webhook/real OCR
  call. See `docs/PRODUCTION_READINESS.md`'s "Known operational
  constraints" section for the full, prioritized list — it is unchanged
  from Milestone 7's own open items, since no new infrastructure became
  available between milestones.

## Previous milestone: Staging infrastructure and cloud deployment playbook

Delivered on branch `feature/staging-deploy-infra`: a production-oriented
deployment bundle under `deploy/` that composes the bot behind Nginx with
Certbot-managed Let's Encrypt TLS, plus `docs/DEPLOYMENT_GUIDE.md`, on top
of the webhook-support milestone below.

- **`deploy/docker-compose.prod.yml`** — three services: `bot` (no
  host-published ports, only `expose: ["8000"]` on a private
  `internal_net` bridge network — reachable exclusively through nginx),
  `nginx` (`nginx:1.27-alpine`, the *only* service publishing `80`/`443`
  to the host, `depends_on: bot: condition: service_healthy`), and
  `certbot` (`certbot/certbot`, an idempotent `certbot renew` loop sharing
  TLS/ACME volumes with nginx). Persistent volumes: `./data` (bot job
  files), `./certbot/conf` (Let's Encrypt state), `./certbot/www` (ACME
  HTTP-01 webroot). Runtime secrets flow only through `env_file: .env`;
  every service has `restart: unless-stopped` and a `healthcheck:`.
- **`deploy/nginx/default.conf.template`** — rendered by the official
  nginx image's envsubst-on-templates mechanism (only `${DOMAIN}` is
  substituted). Provides an HTTP→HTTPS redirect, the ACME challenge
  location, a TLS-independent `/healthz` (so the Docker healthcheck
  survives the pre-certificate bootstrap window), and HTTPS
  reverse-proxying of `/` and `/api/` to `bot:8000` with standard
  forwarded headers (`X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`,
  `X-Forwarded-Host`) and explicit `X-Telegram-Bot-Api-Secret-Token`
  pass-through for the webhook route. No real domain is hardcoded
  anywhere in the file.
- **`deploy/setup_host.sh`** — idempotent Ubuntu/Debian bootstrap:
  detects an existing Docker Engine/Compose plugin and only installs from
  Docker's official apt repository if missing; creates
  `deploy/data`/`deploy/certbot` with UID/GID 1000-compatible ownership
  (matching the `app` user baked into `../Dockerfile`); generates
  `deploy/.env` from `.env.example` only if it does not already exist.
  Never starts containers, never requests/renews a certificate, never
  writes a real secret.
- **`docs/DEPLOYMENT_GUIDE.md`** (new) — end-to-end VPS/DNS/TLS runbook:
  host bootstrap, the two-phase first-TLS-certificate bootstrap (nginx
  cannot start with a `443 ssl` block pointing at a certificate that
  doesn't exist yet), webhook registration/verification via
  `getWebhookInfo`, secret rotation, `/api/health`/`/healthz` validation,
  backup/rollback, and a troubleshooting table.
- **Tests**: `tests/test_deploy_configs.py` (new, 32 tests) statically
  validates the entire bundle — compose YAML structure/services/
  networking/volumes/env-injection/restart/healthchecks, nginx template
  redirect/ACME/proxy/header/domain-placeholder rules, and
  `setup_host.sh` idempotency/UID-GID/no-secrets/no-container-start
  safety — with no Docker engine or network access required. The full
  suite is **157 passing tests**, still fully offline with
  `DummyOCREngine` and zero credentials.
- **Not live-validated** (documented rather than worked around, same as
  every prior milestone in this environment): no Docker engine, no public
  DNS record, and no cloud VPS/account were available, so no command in
  `docs/DEPLOYMENT_GUIDE.md` was actually executed — no image was built
  from `deploy/docker-compose.prod.yml`, no certificate was issued, and
  no live Telegram webhook was registered through this stack. The
  configuration is reviewed and statically verified only.
- README.md/AGENTS.md/`.github/instructions/bot.instructions.md` updated
  with pointers to the new `deploy/` bundle and its unverified-live status.

## Previous milestone: Production staging webhook support and evaluation export

Delivered on branch `feature/production-staging-webhook`: secure Telegram
webhook support (as an opt-in alternative to polling), a CSV export mode
for `tools/evaluate_sample.py`, and honest documentation of what could/
could not be live-validated in this environment, on top of the Milestone 5
work below.

- **`Settings.webhook_secret`** (`src/bot/config.py`, new field alongside
  the existing `webhook_url`) — the shared secret Telegram must echo back
  via `X-Telegram-Bot-Api-Secret-Token` on every webhook request.
  `.env.example` documents both as empty placeholders; `webhook_url`
  remains fully optional (polling stays the default whenever it is unset).
- **`POST /api/telegram/webhook`** (`src/bot/api.py`) — validates the
  secret header before ever parsing the request body (missing header:
  `401`; wrong or unconfigured secret: `403`), then parses the JSON body
  into a `telegram.Update` and dispatches it through the *same*
  `telegram.ext.Application`/handlers polling mode uses
  (`app.state.telegram_application`, wired in by webhook mode only). A
  malformed payload is rejected `400` rather than crashing; the configured
  secret is never logged, echoed, or otherwise exposed.
- **`bot.main`** now has three mutually exclusive run paths —
  `_run_polling_mode()` (default, unchanged behavior), `_run_webhook_mode()`
  (new: single event loop, `Application.initialize()`/`.start()` +
  `Bot.set_webhook()` instead of `run_polling()`, so there is no
  conflicting-polling situation), and `_run_api_only_mode()` (unchanged) —
  selected purely from whether `bot_token`/`webhook_url` are configured.
- **`tools/evaluate_sample.py --csv`** — a new output mode alongside the
  existing human-readable/`--json` reports: a single CSV header+data row
  (stable column set — one `<format>_path`/`<format>_size_bytes` pair per
  possible output format, blank for formats not requested via
  `--formats`), for aggregating multiple evaluation runs in a
  spreadsheet. `--json`/`--csv` together is a usage error (exit `1`);
  missing optional dependencies/credentials (`pytesseract`, `paddleocr`,
  `VISION_LLM_API_KEY`) still produce the same clear, actionable `stderr`
  message and exit code `2` in every output mode, and errors never leak a
  partial JSON/CSV payload onto `stdout`.
- **Tests**: `tests/test_bot_webhook.py` (new, 16 tests) covers secret
  validation, the 503 "not wired" fallback, valid-update dispatch through
  a mocked `Application` (using a real, network-free `telegram.Bot(...)`
  object so `Update.de_json` can build nested objects correctly),
  malformed-payload handling, secret-leak prevention, `Settings` field
  coverage, and `bot.main.main()`'s polling/webhook/API-only mode
  selection. `tests/test_tools_evaluate_sample.py` gained 4 new `--csv`
  tests. The full suite is **125 passing tests**, still fully offline
  with `DummyOCREngine` and zero credentials.
- **Staging/live-validation limitations** (same environment constraints as
  Milestone 5, restated honestly rather than worked around): no
  `BOT_TOKEN`, no public HTTPS endpoint/reverse proxy, and no Docker
  engine were available, so:
  - Webhook registration against Telegram's real `setWebhook` API and
    delivery through an actual reverse proxy were **not** exercised —
    only the route's secret-validation/parsing/dispatch logic was tested
    offline (`ASGITransport`, in-process, no network).
  - No new Docker/container validation was attempted this milestone; the
    Milestone 4/5 static audit findings (Dockerfile/`docker-compose.yml`
    parse-only checks) still stand unchanged — see Milestone 5 below.
  - No OCR benchmark corpus run was repeated this milestone (CSV export
    was validated with the existing synthetic/dummy-engine fixture only,
    per the same non-copyrighted-content constraint as Milestone 5).
- README.md/AGENTS.md/`.github/instructions/bot.instructions.md`/
  `.github/instructions/ocr.instructions.md`/`docs/ROADMAP.md` updated
  with webhook reverse-proxy setup, secret injection, polling-fallback
  guarantees, and `--csv` usage.

## Previous milestone: Live validation and OCR benchmark reporting

Milestone 5 (`docs/ROADMAP.md`) was attempted on branch
`feature/live-validation-benchmarks`: a live Docker build/run smoke test
and real-corpus OCR engine benchmarking were both attempted, on top of the
Milestone 4 containerization work below. **No Docker engine and no
optional OCR dependency/credential (`pytesseract`, `paddleocr`,
`VISION_LLM_API_KEY`) were available in this environment**, so this
milestone produced a static Docker/compose audit, a fully offline `dummy`
engine benchmark against a synthetic (non-copyrighted) sample PDF, and
clean/actionable skip evidence for `tesseract`/`paddle`/`vision_llm` —
recorded in full in `docs/BENCHMARK_RESULTS.md`:

- **Docker**: `docker` CLI is not installed in this environment (`docker
  --version`/`docker info` both fail with `CommandNotFoundException`).
  Static audit repeated the Milestone 4 checks (Dockerfile instruction
  review, `docker-compose.yml` YAML/schema parse) — both still pass — but
  no image was built, no container ran, `/api/health` was not probed, and
  bind-mount UID/GID 1000 write permissions were not exercised live. This
  remains the top open follow-up (see `docs/ROADMAP.md`).
- **`tools/evaluate_sample.py --engine dummy --json`**: ran successfully
  against an in-memory-generated synthetic 5-page PDF (reused
  `tests/fixtures/pdf_factory.py::make_sample_pdf_bytes`, never staged/
  committed — written only to the git-ignored `/data/` directory and
  deleted afterward). Reported ~1.07s runtime, 4.65 pages/s, and (measured
  separately with `psutil`) ~83 MiB peak RSS for the whole process tree —
  a `dummy`-engine/small-fixture memory floor, not a real-OCR benchmark.
- **`tesseract`/`paddle`/`vision_llm`**: each cleanly failed with exit code
  `2` and an actionable one-line JSON error (`pytesseract`/`paddleocr` not
  installed; `VISION_LLM_API_KEY` not set) — no stack traces, no partial
  credentials, and the local `.env` file was never opened/read to check
  for a real key (only `os.environ` was inspected).
- Full findings, exact commands, JSON output, environment/hardware
  context, limitations, and recommended production engine setup are in
  the new `docs/BENCHMARK_RESULTS.md`.

## Previous milestone: Containerization, deployment readiness, and periodic cleanup scheduling

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

See `docs/BENCHMARK_RESULTS.md` for a recorded Milestone 5 run of this tool
(synthetic PDF, `dummy` engine metrics + peak-RSS measurement, and clean
skip evidence for `tesseract`/`paddle`/`vision_llm` when their optional
dependency/credential is absent) plus recommended per-engine memory/setup
guidance for production use.

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
  no Docker installation was available for Milestone 4, the Milestone 5
  live-validation attempt, or the Milestone 7 staging-deployment bundle,
  so the `Dockerfile`/`docker-compose.yml`/`deploy/docker-compose.prod.yml`
  remain validated statically only (see above and
  `docs/BENCHMARK_RESULTS.md`/`docs/DEPLOYMENT_GUIDE.md`). Building and
  running the images (and exercising the `HEALTHCHECK`/bind-mount volume
  ownership, TLS issuance, and live webhook delivery end-to-end) against a
  real engine/VPS/DNS record is the key open follow-up.
- **No real scanned Persian PDF or OCR engine dependency/credential was
  available to benchmark** — `tools/evaluate_sample.py` was exercised with
  a synthetic (non-copyrighted) fixture and the `dummy` engine only;
  `tesseract`/`paddle`/`vision_llm` produced clean, actionable skip errors
  (missing `pytesseract`/`paddleocr`/`VISION_LLM_API_KEY`) rather than real
  recognition results. See `docs/BENCHMARK_RESULTS.md` for full details and
  recommended per-engine memory/setup guidance once each dependency is
  available.
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
- ✅ Production/staging reverse-proxy bundle (`deploy/`): Nginx +
  Certbot-managed Let's Encrypt TLS in front of the bot container, an
  idempotent `setup_host.sh` bootstrap script, and
  `docs/DEPLOYMENT_GUIDE.md`; validated statically via
  `tests/test_deploy_configs.py` only (no VPS/DNS/Docker engine available
  — see "Known limitations").
- ✅ Periodic in-process cleanup: `bot.main.periodic_cleanup_worker()`
  invokes `default_job_manager.cleanup_stale_jobs()` hourly by default
  (`Settings.cleanup_interval_seconds`), with clean cancellation on
  shutdown.
- ⚠️ Real Persian OCR output requires switching `OCR_ENGINE` to a real
  backend and validating it against real scans (tracked in
  `docs/ROADMAP.md`).
- ⚠️ Neither the base container image nor the `deploy/` production stack
  has been built/run — build/run validation against a real Docker
  engine, DNS record, and VPS is the key remaining deployment follow-up.

## Links

- **Final delivery report (Milestone 11): [`docs/DELIVERY_REPORT.md`](DELIVERY_REPORT.md)**
- Architecture: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Production readiness (Milestone 8): [`docs/PRODUCTION_READINESS.md`](PRODUCTION_READINESS.md)
- Live staging validation (Milestones 9–10): [`docs/LIVE_STAGING_VALIDATION.md`](LIVE_STAGING_VALIDATION.md)
- Benchmark results (Milestone 5): [`docs/BENCHMARK_RESULTS.md`](BENCHMARK_RESULTS.md)
- Deployment guide (Milestone 7): [`docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md)
- Roadmap: [`docs/ROADMAP.md`](ROADMAP.md)
- Agent collaboration guide: [`docs/agents/AGENT_GUIDE.md`](agents/AGENT_GUIDE.md)
- Global agent rules: [`../AGENTS.md`](../AGENTS.md)

