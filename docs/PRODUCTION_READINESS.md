# Production Readiness Report

_Milestone 8 — audit date: 2026-09-14. Prepared as a static, source-anchored
review of the repository at commit `de23ca4` (branch
`feature/production-readiness-audit`, forked from `main`). No code behavior
was changed to produce this report._

## Executive summary

`persianbookbot` (Telegram bot + Mini App converting scanned Persian PDF
books into EPUB/DOCX/TXT) is **functionally complete and internally
consistent** across all seven prior delivered milestones: core OCR/RTL
pipeline, production OCR backend options, Mini App UI, operations
hardening (CI/logging/retention/health), containerization, webhook support,
and a Nginx/Certbot staging deployment bundle. The full offline test suite
(**157 tests**) passes with zero failures, zero network access, and zero
credentials. Git history and the current worktree are clean of secrets,
private keys, certificates, and generated runtime artifacts.

**The single, previously-and-still-open gap is live infrastructure
validation**: no Docker engine, VPS/DNS, TLS issuance, or real Telegram/
OCR-provider credential is available in this audit environment, so the
Docker image has never been built and run, the `deploy/` Nginx+Certbot
stack has never been brought up against a real domain, and no webhook or
real-OCR call has ever reached Telegram/Gemini/Claude servers. This matches
every prior milestone's own documented status — this audit does not change
that constraint, it re-confirms it and consolidates the evidence in one
place (see "Known operational constraints" below).

**Recommendation**: the codebase, tests, and documentation are ready for a
first live deployment attempt. The highest-priority next action for any
operator/agent with real infrastructure access is to execute
`docs/DEPLOYMENT_GUIDE.md` end-to-end on a real VPS with a DNS record and a
real `BOT_TOKEN`, and report back the first live `/api/health`,
`docker compose up`, and Telegram webhook-delivery results.

## Scope and method

This audit is **read-only verification**: every source file under `src/`,
`web/`, `tools/`, `deploy/`, the root `Dockerfile`/`docker-compose.yml`, the
`.github/` CI workflow and instruction files, and `tests/` was inspected
against the claims already recorded in `docs/PROJECT_STATUS.md` and
`docs/ROADMAP.md`. No application code was modified. The offline pytest
suite was executed exactly as documented (`$env:PYTHONPATH="$PWD\src";
.\.venv\Scripts\python.exe -m pytest tests\`). Only this report and the
four continuity documents listed in the acceptance criteria were updated.

## Architecture overview

```
Scanned PDF
  -> src/ocr/preprocessing.py   render_pdf_pages() / preprocess_page()  (PyMuPDF rasterize, grayscale + projection-profile deskew)
  -> src/ocr/engine.py          OCREngine.recognize()  (DummyOCREngine default; Tesseract / Paddle / VisionLLM optional)
  -> src/ocr/pipeline.py        process_pdf()          (async orchestrator, retry/backoff -> common.models.Book)
  -> src/converters/{txt,docx_writer,epub_writer}.py    (Book -> .txt / .docx / .epub, explicit RTL)
  -> src/bot/jobs.py            JobManager.run_pipeline()  (drives the above, tracks ConversionJob, retention cleanup)
  -> src/bot/telegram_handlers.py + src/bot/api.py      (delivery: Telegram chat / Mini App HTTP API, incl. webhook route)
  -> web/                       (static Telegram Mini App frontend, consumes the API)
```

All cross-subsystem data flows through the shared dataclasses in
`src/common/models.py` (`PageImage`, `PageText`, `Book`, `JobStatus`,
`ConversionJob`) — verified no subsystem defines a parallel/shadow model.
See `docs/ARCHITECTURE.md` for the full per-module breakdown; this report
does not duplicate it, only cross-checks it against the current source.

## Interfaces and dependencies

| Surface | Entry point | Auth / gating | Notes |
| --- | --- | --- | --- |
| Telegram polling | `bot.main._run_polling_mode` | `BOT_TOKEN` set, `WEBHOOK_URL` unset | Default mode; `Application.run_polling()`. |
| Telegram webhook | `bot.main._run_webhook_mode` + `POST /api/telegram/webhook` | `BOT_TOKEN` **and** `WEBHOOK_URL` set; `X-Telegram-Bot-Api-Secret-Token` validated against `WEBHOOK_SECRET` | Mutually exclusive with polling — see "Polling/webhook exclusivity" below. |
| Mini App HTTP API | `src/bot/api.py` (`FastAPI`) | None (public endpoints); upload size-gated | `/api/config`, `/api/upload`, `/api/status/{id}`, `/api/download/{id}/{fmt}`, `/api/health`. |
| Static Mini App frontend | `web/` mounted at `/` | None | Mounted last so `/api/*` always wins route precedence. |
| OCR backends | `ocr.get_ocr_engine(OCR_ENGINE)` | `dummy` (none); `tesseract` (local binary); `paddle` (local model, `pip install .[paddle]`); `vision_llm` (`VISION_LLM_API_KEY` + network to Gemini/Claude) | `dummy` is the unconditional default; all others fail closed with `OCRError` only when actually constructed/invoked. |
| Deployment | `Dockerfile` / `docker-compose.yml` (single-host) or `deploy/docker-compose.prod.yml` (Nginx + Certbot) | Secrets via `env_file: .env` only | See "Deployment pre-flight checks". |
| Evaluation CLI | `tools/evaluate_sample.py` | Same as chosen `--engine` | Not part of `pytest tests/`; operator-invoked only. |

External runtime dependencies (from `requirements.txt`): `python-telegram-bot`,
`fastapi`/`uvicorn`, `pydantic`/`pydantic-settings`, `pypdf`/`PyMuPDF`/`Pillow`/
`numpy`, `python-bidi`/`arabic-reshaper`, `python-docx`/`EbookLib`. Optional
extras (`paddleocr`+`paddlepaddle`, `httpx`) are declared in
`pyproject.toml[project.optional-dependencies]` and are never required to
import `ocr.engine` or run the default test suite — confirmed by reading
every lazy-import site in `src/ocr/engine.py`.

## Security and credential handling audit

- **`Settings.bot_token`, `webhook_secret`, `vision_llm_api_key` all default
  to `None`** (`src/bot/config.py`) — confirmed by reading the field
  declarations; nothing in `src/bot/`, `src/ocr/`, or `src/converters/`
  requires a credential to import.
- **Dotenv hermeticity**: `BOT_ENV_FILE` (resolved once at
  `bot.config` import time) lets `tests/conftest.py` set `BOT_ENV_FILE=""`
  before any test imports `bot.config`, disabling dotenv loading entirely
  for the test process — confirmed present in both `conftest.py` and
  `.github/workflows/ci.yml` (set as defense-in-depth even though CI never
  has a `.env` file in a fresh checkout).
- **Webhook secret validation ordering** (`src/bot/api.py::telegram_webhook`):
  the `X-Telegram-Bot-Api-Secret-Token` header is checked (`401` missing,
  `403` wrong/unconfigured) **before** `await request.json()` is ever
  called — confirmed by reading the function body; the secret value is
  never included in any log call or response payload anywhere in the file.
- **`.env` is git-ignored and untracked**: `git check-ignore -v .env`
  confirms the root `.gitignore` line matches; `git status --porcelain
  --ignored` shows `.env` only under the ignored section, never staged.
  `deploy/.env`, `deploy/data/`, and `deploy/certbot/` are separately
  ignored (`.gitignore` lines for the production bundle's runtime state).
- **No secrets, keys, or certificates in tracked history**: `git ls-files`
  and `git log --all --diff-filter=A --name-only` were searched for
  `.pem`/`.key`/`.crt`/`.p12` and returned no matches; `git grep` across
  tracked content for `BOT_TOKEN=<digits>`-shaped assignments and
  Gemini/OpenAI-style API-key patterns (`AIza...`, `sk-...`) returned no
  matches.
- **No copyrighted book material or generated runtime artifacts tracked**:
  `git ls-files` contains no `.pdf`/`.epub`/`.docx` files; `/data/`,
  `deploy/data/`, and `deploy/certbot/` are all git-ignored.
- **Dockerfile/compose never bake in a credential**: `Dockerfile`'s `ENV`
  block sets only non-secret defaults (`OCR_ENGINE=dummy`, ports, log
  config); `BOT_TOKEN`/`VISION_LLM_API_KEY` are absent from the image and
  only reach the container via `env_file: .env` in both
  `docker-compose.yml` and `deploy/docker-compose.prod.yml` — confirmed by
  reading both compose files end-to-end.
- **Structured logging never leaks secrets**: `src/bot/logging_config.py`
  scrubs a fixed set of secret-shaped keys before rendering either
  formatter; `log_event` call sites reviewed in `jobs.py`/`main.py` never
  pass a `Settings` object or raw credential as a logged value.

No credential-handling regression or exposure was found. This confirms
(rather than newly discovers) the invariant already stated in `AGENTS.md`.

## Static behavioral audit (per acceptance criteria)

- **RTL/BiDi handling** (`src/ocr/rtl.py`): `shape_rtl()` (visual
  reshape+reorder, for non-bidi-aware rendering contexts only) and
  `assemble_rtl_paragraph()` (logical order preserved, for EPUB/DOCX) are
  kept as two distinct, correctly-scoped helpers — confirmed no converter
  calls `shape_rtl()` on text destined for DOCX/EPUB (`grep` across
  `src/converters/` for `shape_rtl` returned no matches).
- **Converter font hooks** (`src/converters/fonts.py`): no font binary is
  bundled; `get_persian_font_name()`/`get_font_file_path()` only resolve a
  name/path from an explicit override or `PERSIAN_FONT_NAME`/
  `PERSIAN_FONT_PATH` env vars, falling back to `"Vazirmatn"` — confirmed
  the module contains no embedded font bytes and no network font fetch.
- **OCR error mapping** (`src/ocr/engine.py`): every optional engine
  (`Tesseract`/`Paddle`/`VisionLLM`) raises `OCRError` (or the
  `RateLimitError` subclass for HTTP 429 from `VisionLLMOCREngine`) only at
  construction/invocation time when its dependency/credential is missing —
  never at module import time; `pipeline._recognize_with_retry` (via
  `ocr/pipeline.py`, exercised by `tests/test_ocr_pipeline.py`) retries
  `RateLimitError` with exponential backoff up to `rate_limit_max_retries`
  before re-raising.
- **Polling/webhook exclusivity** (`src/bot/main.py::main`): exactly one of
  `_run_polling_mode` / `_run_webhook_mode` / `_run_api_only_mode` runs,
  selected purely from `bot_token`/`webhook_url` presence — confirmed
  `_run_webhook_mode` never calls `Application.run_polling()` and
  `_run_polling_mode` never touches `app.state.telegram_application`,
  which is exactly what prevents Telegram's `409 terminated by other
  getUpdates request` conflict.
- **Webhook secret validation** (`src/bot/api.py::telegram_webhook`): see
  "Security and credential handling audit" above — header checked before
  body parse, `401`/`403` distinguished correctly, no secret leakage.
- **Health and cleanup behavior**: `GET /api/health` (`src/bot/api.py`) is
  confirmed dependency-free (no I/O, no settings/credential exposure, just
  `{"status": "ok", "uptime_seconds": ...}`); `periodic_cleanup_worker`
  (`src/bot/main.py`) is wired into all three run paths with explicit
  cancellation on shutdown (`post_shutdown` for polling,
  `finally`-guarded task cancellation for webhook/API-only), and is a
  no-op when `cleanup_interval_seconds <= 0`; `JobManager.cleanup_stale_jobs()`
  (`src/bot/jobs.py`) only prunes `DONE`/`FAILED`/`RATE_LIMITED` jobs past
  the TTL, never touches in-flight jobs, and isolates every file-removal
  error into `CleanupResult.errors` rather than raising.
- **Mini App configuration/lifecycle/upload handling**: `GET /api/config`
  exposes `max_file_size_mb`/`formats` so `web/app.js` never hardcodes
  limits separately from `Settings` (confirmed a safe 20MB client-side
  fallback exists if that fetch fails); `POST /api/upload` reads in bounded
  1MB chunks and rejects an oversized file (`413`) before the whole
  payload is buffered — confirmed by reading the `while True` chunk loop
  in `upload_pdf`; `GET /api/download/{job_id}/{fmt}` only serves a file
  once `JobStatus.DONE` and the on-disk path still exists.
- **Docker/Compose/Nginx/bootstrap coherence**:
  - `Dockerfile` — two-stage build, fixed non-root UID/GID 1000, safe
    credential-free `ENV` defaults, `HEALTHCHECK` against `GET
    /api/health`; confirmed `COPY --chown=app:app` and
    `chown -R app:app /app/data` keep the runtime user's write access
    consistent with `docker-compose.yml`'s `./data:/app/data` bind mount.
  - `docker-compose.yml` — single `bot` service, `env_file: .env`,
    matching `healthcheck:`/`restart: unless-stopped`; parses cleanly with
    `yaml.safe_load` per `tests/test_deploy_configs.py`'s pattern (root
    `docker-compose.yml` itself is not re-validated by that suite, but its
    structure mirrors `deploy/docker-compose.prod.yml`'s `bot` service,
    which is).
  - `deploy/docker-compose.prod.yml` — `bot` has **no** host-published
    `ports:` (only `expose: ["8000"]` on `internal_net`); `nginx` is the
    sole service publishing `80`/`443` and has `depends_on: bot:
    condition: service_healthy`; `certbot` shares `./certbot/{conf,www}`
    and runs an idempotent `certbot renew` loop — confirmed no
    unconditional `certbot certonly`/issuance call exists anywhere in the
    compose file (first issuance is a documented manual step).
  - `deploy/nginx/default.conf.template` — HTTP→HTTPS redirect, a
    TLS-independent `/healthz`, ACME challenge location served over plain
    HTTP, and HTTPS reverse-proxying of `/` and `/api/` to `bot:8000` with
    `X-Telegram-Bot-Api-Secret-Token` explicitly forwarded via
    `proxy_pass_request_headers on` — confirmed only `${DOMAIN}` is
    substituted (envsubst-on-templates) and no real domain is hardcoded
    anywhere in the file (only the documentation-comment placeholder
    `bot.example.com`).
  - `deploy/setup_host.sh` — confirmed idempotent (checks-before-install
    Docker, `mkdir -p` for directories, `.env` generated only if absent)
    and confirmed it never starts a container, never calls
    `certbot certonly`/`renew`, and never writes a non-placeholder secret
    value (copies `.env.example`, which is all blanks).
  - `tests/test_deploy_configs.py` (32 tests) statically validates all of
    the above — YAML/template parsing, service/network/volume/header/ACME
    coverage, and script safety — with no Docker engine or network access.

No coherence gap or safety regression was found across this bundle.

## Test verification

Command run (as documented in `AGENTS.md`/`README.md`):

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest tests\
```

Result: **157 passed, 0 failed, 9 warnings** (all warnings are a single
upstream `python-telegram-bot` `PTBDeprecationWarning` about a future
`retry_after` type change — not a defect in this repository). Breakdown by
file (`--collect-only`):

| File | Tests |
| --- | --- |
| `test_bot_api.py` | 10 |
| `test_bot_config.py` | 5 |
| `test_bot_jobs.py` | 14 |
| `test_bot_logging.py` | 10 |
| `test_bot_main_scheduler.py` | 7 |
| `test_bot_telegram_handlers.py` | 7 |
| `test_bot_webhook.py` | 13 |
| `test_converters.py` | 5 |
| `test_deploy_configs.py` | 32 |
| `test_integration.py` | 1 |
| `test_ocr_pipeline.py` | 15 |
| `test_ocr_production_engines.py` | 25 |
| `test_tools_evaluate_sample.py` | 13 |
| **Total** | **157** |

No network access, real `BOT_TOKEN`, or real OCR credential was used or
required. This meets and matches the acceptance criterion of "at least the
existing 157 tests" exactly (no test was added or removed by this audit).

## Git and secret hygiene verification

- `git check-ignore -v .env` → matched by `.gitignore`; `.env` is present
  on disk (local runtime file) but untracked.
- `git status --porcelain=v1 --ignored` → `.env` appears only under the
  ignored (`!!`) section, never staged or tracked.
- `git ls-files | Select-String -Pattern "\.env$|\.pem$|\.key$|\.crt$|\.pdf$"`
  → no matches (no committed secrets, keys, certificates, or PDFs).
- `git grep` across tracked files for hardcoded-token-shaped patterns
  (`BOT_TOKEN=<digits>`, `AIza...`, `sk-...`) → no matches.
- `git log --all --diff-filter=A --name-only` filtered for
  `.pem`/`.key`/`.crt`/`.p12` → no matches (nothing of that shape was ever
  added and later removed, either).
- Only this audit's own untracked `.goals/production-readiness-audit/`
  artifact and the intended documentation edits are present in `git
  status` at audit time — no other worktree changes were touched or lost.

## Deployment pre-flight checklist

Use this checklist on a real host before/while running
`docs/DEPLOYMENT_GUIDE.md`; every item below was statically verified in
this audit but **not** exercised live (see "Known operational
constraints"):

- [ ] Docker Engine + Compose plugin installed (or run `deploy/setup_host.sh`
  on Ubuntu/Debian).
- [ ] DNS `A`/`AAAA` record for the target domain resolves to the host.
- [ ] `deploy/.env` created from `.env.example` with a real `BOT_TOKEN`,
  a random `WEBHOOK_SECRET` (e.g. `openssl rand -hex 32`), and
  `WEBHOOK_URL=https://<domain>` — never commit this file.
- [ ] First-issuance two-phase Certbot bootstrap followed exactly as
  written in `docs/DEPLOYMENT_GUIDE.md` step 5 (HTTP-only start, obtain
  cert via webroot, then enable the HTTPS server block).
- [ ] `docker compose -f deploy/docker-compose.prod.yml up -d` brought up
  cleanly; `docker compose ps` shows `bot`/`nginx`/`certbot` all healthy.
- [ ] `curl https://<domain>/healthz` and `curl https://<domain>/api/health`
  both return `200`.
- [ ] `getWebhookInfo` (Telegram Bot API) confirms the registered webhook
  URL matches and `pending_update_count` stays near zero after a test
  message.
- [ ] A real end-to-end PDF upload (Telegram chat or Mini App) produces a
  downloadable EPUB/DOCX/TXT set.
- [ ] `docker compose logs -f bot` shows no unexpected error-level events
  during the above.

## Known operational constraints (honestly unresolved — not worked around)

Consistent with every prior milestone's own status notes
(`docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`), this audit environment has:

- **No Docker engine/daemon** — the `Dockerfile` and both compose files
  have only ever been statically parsed/reviewed, never built or run. No
  `HEALTHCHECK`, bind-mount UID/GID 1000 permission, or container log has
  ever been observed live.
- **No VPS, public DNS record, or TLS certificate** — the
  `deploy/docker-compose.prod.yml` + `deploy/nginx/` + `deploy/setup_host.sh`
  bundle and `docs/DEPLOYMENT_GUIDE.md` have never been executed against a
  real host; no Let's Encrypt certificate has ever been issued through
  this stack.
- **No real `BOT_TOKEN` or public HTTPS endpoint** — `POST
  /api/telegram/webhook` has only ever been exercised in-process
  (`ASGITransport`, no network) via `tests/test_bot_webhook.py`; Telegram's
  real `setWebhook`/delivery path is unverified.
- **No `pytesseract`/`paddleocr` installation or `VISION_LLM_API_KEY`** —
  `TesseractOCREngine`/`PaddleOCREngine`/`VisionLLMOCREngine` are
  structurally correct and unit-tested with mocks
  (`tests/test_ocr_production_engines.py`), but have never recognized a
  real scanned Persian page; `docs/BENCHMARK_RESULTS.md` records only a
  `DummyOCREngine` runtime/memory baseline against a synthetic PDF.

None of these gaps were "worked around" by this audit (e.g. no fake
Docker run was staged, no credential was requested or synthesized). They
are the same environment limitations documented since Milestone 4/5/6/7,
restated here as the single consolidated list a future live-validation
pass should close, in priority order:

1. Real Docker build/run + `deploy/` stack bring-up on an actual VPS with
   DNS — the single highest-leverage remaining action, since it unblocks
   both the container smoke test and TLS/webhook validation in one pass.
2. A real `BOT_TOKEN` + the above, to confirm live webhook
   registration/delivery end-to-end.
3. `pytesseract`/system Tesseract + a real (non-copyrighted, licensed)
   scanned Persian PDF, to get the first real OCR accuracy data point
   (cheapest real engine to validate first, per `docs/ROADMAP.md`).

## Milestone 8 sign-off

- [x] Comprehensive `docs/PRODUCTION_READINESS.md` covering architecture,
  interfaces/dependencies, security/credential handling, deployment
  pre-flight checks, and known operational constraints (this document).
- [x] Static audit of RTL/BiDi handling, converter font hooks, OCR error
  mapping, polling/webhook exclusivity, webhook secret validation, health/
  cleanup behavior, Mini App configuration/lifecycle/upload handling, and
  Docker/Compose/Nginx/bootstrap coherence — see "Static behavioral audit"
  above; no defect found.
- [x] `pytest tests/` passes all **157** tests offline, without
  credentials; no tracked secrets, keys, certificates, PDFs, or generated
  runtime artifacts were found or introduced.
- [x] `README.md`, `AGENTS.md`, `docs/PROJECT_STATUS.md`, and
  `docs/ROADMAP.md` updated to reflect this audit and the operational-
  maintenance handoff (see each file's Milestone 8 section).
- [ ] Feature branch pushed, PR opened, squash-merged, and `main`
  synchronized with the branch deleted — **out of scope for this Builder
  turn**; the orchestrator handles push/PR/merge/cleanup lifecycle for
  this goal. This report and the doc updates are staged in a single
  Builder commit only.
