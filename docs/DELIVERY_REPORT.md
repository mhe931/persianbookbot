# Delivery Report — Milestone 11 (Final Operator Handoff)

_Report date: 2026-09-15. Prepared on branch `feature/delivery-report-runbook`,
forked from `main` at commit `a347df3` (post–Milestone 10). This document is
the single, self-contained summary of everything delivered across
Milestones 1–10 plus this Milestone 11 finalization pass. It is written and
verified read-only against current source, tests, and prior milestone
reports — **no application, converter, OCR, or deployment-code logic was
changed to produce it**, and no live metric or infrastructure result is
claimed beyond what is already recorded and evidenced in
`docs/BENCHMARK_RESULTS.md`, `docs/PRODUCTION_READINESS.md`, and
`docs/LIVE_STAGING_VALIDATION.md`._

## 1. Executive summary

`persianbookbot` is a Telegram bot + Mini App that converts scanned Persian
PDF books into **EPUB**, **DOCX**, and **TXT** through an async Persian
OCR/RTL pipeline:

```
Scanned PDF -> render -> deskew -> OCR -> RTL assemble -> EPUB/DOCX/TXT -> Bot/API
```

The codebase is **functionally complete and internally consistent** across
all ten delivered milestones: core OCR/RTL pipeline, production OCR backend
options, Mini App UI, operations hardening (CI/logging/retention/health),
containerization, webhook support, a Nginx/Certbot staging deployment
bundle, a production-readiness audit, and two independent live-validation
attempts. The full offline test suite passes with **157 tests, 0
failures**, zero network access, and zero credentials (re-verified for this
report — see §8).

**The one remaining, honestly unresolved gap across every milestone is live
infrastructure validation**: this authoring environment has never had a
Docker engine, a DNS-controlled domain, a real `BOT_TOKEN`, or a real
OCR-provider credential, so the Docker image has never been built/run, the
`deploy/` Nginx+Certbot stack has never been brought up against a real
domain, and no webhook/real-OCR request has ever reached Telegram, Gemini,
or Claude servers. This report does not change that constraint; it
consolidates it into one final operator checklist (§13).

## 2. Milestone-by-milestone outcomes

| # | Milestone | Outcome | Primary evidence |
| --- | --- | --- | --- |
| 0 | Core OCR/RTL pipeline scaffold | ✅ delivered | `src/ocr/`, `src/converters/`, `src/common/models.py`; original test suite |
| 1 | Real OCR backends (`Tesseract`/`Paddle`/`VisionLLM`) | ✅ implemented; ⚠️ real-scan accuracy benchmarking still pending real corpus | `src/ocr/engine.py`, `tests/test_ocr_production_engines.py` |
| 2 | Mini App UI enhancements + evaluation CLI | ✅ delivered | `web/`, `tools/evaluate_sample.py` |
| 3 | Bot & operations hardening (CI, logging, retention, health) | ✅ delivered | `.github/workflows/ci.yml`, `src/bot/logging_config.py`, `JobManager.cleanup_stale_jobs()`, `GET /api/health` |
| 4 | Containerization + periodic cleanup scheduling | ✅ delivered (static validation only) | `Dockerfile`, `docker-compose.yml`, `periodic_cleanup_worker()` |
| 5 | Live validation & OCR benchmark reporting | ⚠️ attempted; blocked on environment | `docs/BENCHMARK_RESULTS.md` |
| 6 | Webhook support & evaluation export (`--csv`) | ✅ delivered (offline-validated; live delivery unverified) | `src/bot/api.py::telegram_webhook`, `tests/test_bot_webhook.py` |
| 7 | Staging infrastructure & cloud deployment playbook | ✅ delivered (offline-validated; live deployment unverified) | `deploy/`, `docs/DEPLOYMENT_GUIDE.md`, `tests/test_deploy_configs.py` |
| 8 | Production-readiness audit | ✅ verified; no defects found; live infra unchanged | `docs/PRODUCTION_READINESS.md` |
| 9 | Live cloud staging validation attempt | ⏸️ blocked; safe discovery only | `docs/LIVE_STAGING_VALIDATION.md` §§1–10 |
| 10 | Production host validation attempt | ⏸️ blocked; identical root cause, re-confirmed | `docs/LIVE_STAGING_VALIDATION.md` "Milestone 10 re-attempt" |
| 11 | **This report** — delivery report & operational runbook | ✅ documentation-only finalization | this file |

Nothing in Milestones 9–11 altered `src/`, `web/`, `tools/`, `deploy/`, the
root `Dockerfile`/`docker-compose.yml`, or `tests/` — each is a read-only
audit/documentation pass. The **157-test count has been stable since
Milestone 6** (webhook support); no test was added, removed, or modified by
Milestones 7–11 (Milestone 7 added the already-counted
`tests/test_deploy_configs.py`).

## 3. Capability matrix

| Capability | Status | Notes |
| --- | --- | --- |
| PDF rendering / grayscale + deskew preprocessing | ✅ | `src/ocr/preprocessing.py` (PyMuPDF rasterize, projection-profile deskew) |
| OCR engine abstraction, offline default | ✅ | `src/ocr/engine.py`: `DummyOCREngine` (default, credential-free, deterministic) |
| Real OCR backends | ✅ implemented / ⚠️ unbenchmarked on real scans | `TesseractOCREngine`, `PaddleOCREngine` (`pip install .[paddle]`), `VisionLLMOCREngine` (Gemini/Claude, `pip install .[vision-llm]`) |
| RTL/BiDi text handling | ✅ | `src/ocr/rtl.py`: `shape_rtl()` vs. `assemble_rtl_paragraph()`, Persian digit normalization |
| Async pipeline orchestration + retry/backoff | ✅ | `src/ocr/pipeline.py::process_pdf()`, `RateLimitError` handling |
| Document generation (EPUB/DOCX/TXT, explicit RTL) | ✅ | `src/converters/{txt,docx_writer,epub_writer}.py` |
| Async in-memory job orchestration | ✅ | `src/bot/jobs.py::JobManager`, shared by Telegram + Mini App |
| Telegram polling | ✅ | `bot.main._run_polling_mode` (default whenever `WEBHOOK_URL` unset) |
| Telegram webhook | ✅ implemented; ⚠️ never delivered against real Telegram servers | `bot.main._run_webhook_mode`, `POST /api/telegram/webhook`, secret-header validation |
| Mini App HTTP API | ✅ | `/api/config`, `/api/upload`, `/api/status/{id}`, `/api/download/{id}/{fmt}`, `/api/health` |
| Mini App static frontend | ✅ | `web/` — theme-aware, RTL, 5-step progress, format toggles, retry-aware polling |
| Structured logging + secret scrubbing | ✅ | `src/bot/logging_config.py` |
| Job retention / cleanup | ✅ | `JobManager.cleanup_stale_jobs()` + `periodic_cleanup_worker()` |
| CI (offline, matrix) | ✅ | `.github/workflows/ci.yml`, Python 3.10/3.11/3.12, no credentials |
| Containerization (single-host) | ✅ implemented; ⚠️ never built/run | `Dockerfile`, `docker-compose.yml` |
| Production reverse-proxy deployment (Nginx + Certbot TLS) | ✅ implemented; ⚠️ never brought up against a real domain | `deploy/docker-compose.prod.yml`, `deploy/nginx/`, `deploy/setup_host.sh` |
| Evaluation CLI | ✅ | `tools/evaluate_sample.py` — human-readable / `--json` / `--csv` |
| Offline test suite | ✅ 157/157 passing | see §8 |
| Live Docker/VPS/TLS/Telegram/OCR-provider validation | ⏸️ blocked | no Docker engine, DNS, or live credential available in any authoring environment to date (§12) |

## 4. Architecture, data flow, and shared contracts

```
Scanned PDF
   -> src/ocr/preprocessing.py   render_pdf_pages()  — rasterize pages via PyMuPDF
   -> src/ocr/preprocessing.py   preprocess_page()   — grayscale + projection-profile deskew
   -> src/ocr/engine.py          OCREngine.recognize() — DummyOCREngine (default) / Tesseract / Paddle / VisionLLM
   -> src/ocr/pipeline.py        process_pdf()       — async orchestrator, retry/backoff -> common.models.Book
   -> src/converters/{txt,docx_writer,epub_writer}.py — Book -> .txt / .docx / .epub (RTL-aware)
   -> src/bot/jobs.py            JobManager.run_pipeline() — drives the above, tracks ConversionJob
   -> src/bot/telegram_handlers.py + src/bot/api.py   — delivery: Telegram chat / Mini App HTTP API (incl. webhook route)
   -> web/                       — static Telegram Mini App frontend consumes the API
```

All data crossing subsystem boundaries flows exclusively through the shared
dataclasses in `src/common/models.py` — no subsystem defines a parallel
model:

| Type | Purpose |
| --- | --- |
| `PageImage` | A rendered page (`page_number`, `width`, `height`, `dpi`, optional raw PNG `data`). |
| `PageText` | OCR result for one page (`page_number`, `text`, `confidence`, `direction`). |
| `Book` | Fully assembled book (`title`, `pages`, `language`, `direction`, `author`), with `full_text`/`average_confidence` helpers. |
| `JobStatus` | Lifecycle enum: `pending -> preprocessing -> ocr_running -> assembling -> converting -> done` (or `failed` / `rate_limited`). |
| `ConversionJob` | End-to-end job state (`job_id`, `status`, `source_filename`, `chat_id`, `error`, `progress`, `output_paths`, timestamps, `retry_count`). |

### Interfaces and dependencies

| Surface | Entry point | Auth / gating | Notes |
| --- | --- | --- | --- |
| Telegram polling | `bot.main._run_polling_mode` | `BOT_TOKEN` set, `WEBHOOK_URL` unset | Default mode; `Application.run_polling()`. |
| Telegram webhook | `bot.main._run_webhook_mode` + `POST /api/telegram/webhook` | `BOT_TOKEN` **and** `WEBHOOK_URL` set; `X-Telegram-Bot-Api-Secret-Token` validated against `WEBHOOK_SECRET` | Mutually exclusive with polling. |
| Mini App HTTP API | `src/bot/api.py` (FastAPI) | Public; upload size-gated by `MAX_FILE_SIZE_MB` | `/api/config`, `/api/upload`, `/api/status/{id}`, `/api/download/{id}/{fmt}`, `/api/health`. |
| Static Mini App frontend | `web/` mounted at `/` | None | Mounted last so `/api/*` always wins route precedence. |
| OCR backends | `ocr.get_ocr_engine(OCR_ENGINE)` | `dummy` (none); `tesseract` (local binary); `paddle` (`pip install .[paddle]`); `vision_llm` (`VISION_LLM_API_KEY` + network) | `dummy` is the unconditional default. |
| Deployment | `Dockerfile` / `docker-compose.yml` (single host) or `deploy/docker-compose.prod.yml` (Nginx + Certbot) | Secrets via `env_file: .env` only | See §7. |
| Evaluation CLI | `tools/evaluate_sample.py` | Same as chosen `--engine` | Not part of `pytest tests/`; operator-invoked. |

## 5. Local quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env   # fill in BOT_TOKEN only if running the real bot

$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest tests\          # 157 passed, fully offline
.\.venv\Scripts\python.exe -m bot.main               # runs the API (+ bot polling if BOT_TOKEN is set)
```

No real Telegram bot token, OCR credentials, or network access are required
to run the test suite or the API/bot with the default `OCR_ENGINE=dummy` —
`DummyOCREngine` is fully deterministic and offline, and `Settings.bot_token`
defaults to `None`.

## 6. Docker and basic Compose (single host)

```powershell
docker build -t persianbookbot:latest .
Copy-Item .env.example .env          # edit before running if BOT_TOKEN etc. are needed
docker compose up -d --build
docker compose ps                    # check the /api/health healthcheck status
docker compose logs -f bot
docker compose down
```

- Runs as a fixed non-root user (`app`, UID/GID 1000); `./data` bind-mounts
  to `/app/data` (uploads + output, `chmod 750`) so job files persist across
  restarts/rebuilds.
- `GET /api/health` is the container `HEALTHCHECK` target.
- `OCR_ENGINE=dummy` (default) needs no credentials; the image also bundles
  `tesseract-ocr`/`tesseract-ocr-fas` so `OCR_ENGINE=tesseract` works
  out of the box. `paddle`/`vision_llm` need their optional extras
  installed separately.
- `periodic_cleanup_worker()` calls `JobManager.cleanup_stale_jobs()` every
  `CLEANUP_INTERVAL_SECONDS` (default 3600s); set to `0` to disable.
- **Not live-built/run in any authoring environment to date** — statically
  validated only (Dockerfile instruction parsing, compose YAML/schema
  inspection); see §12.

## 7. Production deployment: Nginx + Certbot (`deploy/`)

For an internet-facing staging/production deployment — bot container kept
internal, Nginx as the only host-exposed service (80/443), Certbot-managed
Let's Encrypt TLS with automatic renewal, and an idempotent Ubuntu/Debian
host bootstrap script:

- `deploy/docker-compose.prod.yml` — `bot` (no host-published ports, only
  `expose: ["8000"]` on a private `internal_net` bridge, reachable only
  through nginx), `nginx` (`nginx:1.27-alpine`, the only service publishing
  `80`/`443`, `depends_on: bot: condition: service_healthy`), and `certbot`
  (`certbot/certbot`, idempotent `certbot renew` loop). Persistent volumes:
  `./data` (job files), `./certbot/conf` (Let's Encrypt state),
  `./certbot/www` (ACME HTTP-01 webroot). Secrets flow only through
  `env_file: .env`; every service has `restart: unless-stopped` and a
  `healthcheck:`.
- `deploy/nginx/default.conf.template` — HTTP→HTTPS redirect, ACME
  challenge location, a TLS-independent `/healthz` (survives the
  pre-certificate bootstrap window), and HTTPS reverse-proxying of `/` and
  `/api/` to `bot:8000` with standard forwarded headers plus explicit
  `X-Telegram-Bot-Api-Secret-Token` pass-through. Only `${DOMAIN}` is
  substituted — no real domain hardcoded.
- `deploy/setup_host.sh` — idempotent Docker/Compose install-if-missing,
  UID/GID 1000-compatible `deploy/data`/`deploy/certbot` directory
  creation, and safe `deploy/.env` generation from `.env.example` (never
  overwrites an existing file, never writes a real secret, never starts
  containers or requests a certificate).
- The full VPS/DNS/TLS/webhook/secret-rotation/backup/rollback runbook is
  in `docs/DEPLOYMENT_GUIDE.md` (prerequisites → DNS → host bootstrap →
  `.env` → first-time TLS issuance → start the stack → webhook
  registration → health validation → secret rotation → backups →
  rollback → troubleshooting → uninstall).
- **Statically validated only** via `tests/test_deploy_configs.py` (32
  tests: compose structure/networking/volumes/healthchecks, nginx
  template rules, `setup_host.sh` idempotency/UID-GID/no-secrets safety) —
  never brought up against a real VPS/DNS/Docker engine; see §12.

## 8. Polling vs. webhook configuration

The bot **polls by default** (`Application.run_polling()`) whenever
`WEBHOOK_URL` is unset — no public URL, TLS, or reverse proxy required for
local development. To use webhook mode instead, set both in `.env`:

```
WEBHOOK_URL=https://bot.example.com     # public HTTPS base URL of your reverse proxy
WEBHOOK_SECRET=<random value, e.g. `openssl rand -hex 32`>
```

`bot.main.main()` then runs `_run_webhook_mode()`: it registers
`<WEBHOOK_URL>/api/telegram/webhook` with Telegram (`Bot.set_webhook`,
including the secret token) and serves the FastAPI app on
`API_HOST:API_PORT` — polling is never started in this mode, so there is no
conflict. Every request to `POST /api/telegram/webhook` must carry a
matching `X-Telegram-Bot-Api-Secret-Token` header (Telegram sends this
automatically once `set_webhook(..., secret_token=...)` has been called): a
missing header is rejected `401`, a present-but-wrong/unconfigured secret is
rejected `403` — the update body is never parsed until the secret
validates, and the secret is never logged or echoed back. This logic is
exercised offline in `tests/test_bot_webhook.py` (16 tests: secret
validation, 503 not-wired fallback, valid-update dispatch through a mocked
`Application`, malformed-payload handling, secret-leak prevention, mode
selection) — **never against Telegram's real `setWebhook`/delivery
infrastructure** (§12).

## 9. Evaluation CLI (`tools/evaluate_sample.py`)

Runs the real OCR/conversion pipeline against a single local PDF and
reports runtime/page/character/output metrics, without a Telegram bot or
FastAPI server running:

```powershell
# Human-readable report (default)
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf

# Machine-readable output — pick one (mutually exclusive)
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf --json
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf --csv > metrics.csv

# Real backends (each needs its own optional dependency/credential)
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf --engine tesseract
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf --engine paddle --paddle-lang fa
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf --engine vision_llm `
    --vision-llm-provider gemini --vision-llm-api-key $env:VISION_LLM_API_KEY
```

`--csv` prints a single header+data row (stable column set — one
`<format>_path`/`<format>_size_bytes` pair per possible output format,
blank for formats not requested) for aggregating multiple runs in a
spreadsheet. Fully offline with `--engine dummy` (the default); the other
engines report a clear, actionable error on `stderr` and exit code `2` if
their optional dependency (`pytesseract`/`paddleocr`) or credential
(`VISION_LLM_API_KEY`) is missing. `--json`/`--csv` together is a usage
error (exit `1`). Milestone 5's `docs/BENCHMARK_RESULTS.md` records the one
real run performed to date — `dummy` against a synthetic (non-copyrighted)
sample PDF — with clean, actionable skip evidence for `tesseract`/`paddle`/
`vision_llm` (missing optional dependency/credential in this environment).
No real-scan accuracy benchmark has been produced (§12).

## 10. Security and secret management

- `Settings.bot_token`, `Settings.webhook_secret`, and
  `Settings.vision_llm_api_key` all default to `None`/empty
  (`src/bot/config.py`) — nothing in `src/bot/`, `src/ocr/`, or
  `src/converters/` requires a credential to import or run with defaults.
- **Dotenv hermeticity**: `BOT_ENV_FILE` (resolved once at `bot.config`
  import time) lets `tests/conftest.py` set `BOT_ENV_FILE=""` before any
  test imports `bot.config`, disabling dotenv loading entirely for the test
  process — a developer's real `.env` can never leak into `Settings` during
  `pytest tests/`. CI sets the same variable as defense-in-depth.
  `.env` itself normally loads for real bot/API runs.
- **Webhook secret validation**: header checked and constant before the
  request body is ever parsed (§8); the secret is never logged or echoed.
- **Structured logging** (`src/bot/logging_config.py`) always scrubs a
  fixed set of secret-shaped keys (`bot_token`, `api_key`, ...) before
  rendering, in both JSON and console formats.
- **`.env` is git-ignored** (`git check-ignore -v .env` confirms) and
  untracked at HEAD; only `.env.example` (placeholder values, no real
  secret) is committed.
- **Container secrets**: injected only via `env_file: .env` at *run* time
  in both `docker-compose.yml` and `deploy/docker-compose.prod.yml` —
  never baked into the image; `Dockerfile` sets only safe, credential-free
  defaults (`OCR_ENGINE=dummy`, etc.).
- **TLS**: `deploy/` uses Certbot-issued Let's Encrypt certificates
  (`deploy/certbot/conf`, git-ignored) — no certificate or private key is
  ever committed.
- **Secret rotation and health validation** procedures are documented in
  `docs/DEPLOYMENT_GUIDE.md` §§8–9.
- See §11 for this report's own Git/secret integrity audit.

## 11. Git and secret/artifact integrity audit (this report)

Performed read-only, no secret value read or logged, across all local refs:

| Check | Command | Result |
| --- | --- | --- |
| Tags | `git tag` | none exist |
| Tracked secret-shaped files at HEAD | `git ls-files \| Select-String '\.env$\|\.pem$\|\.key$\|\.crt$\|\.pdf$\|\.p12$\|\.pfx$'` | no matches |
| Ever-added secret-shaped files (full history) | `git log --all --diff-filter=A --name-only` filtered for the same extensions | no matches |
| Token-shaped literals across all reachable commits | `git grep -I -n -E "BOT_TOKEN\s*=\s*[0-9]{6,}" $(git rev-list --all)` | no matches |
| `.env` ignore status | `git check-ignore -v .env` | ignored via `.gitignore:151` |
| `.env` tracked? | `git ls-files \| Select-String '^\.env'` | only `.env.example` tracked |
| Working tree cleanliness | `git status --porcelain` | clean except this task's own untracked `.goals/delivery-report-runbook/` artifacts |
| Tracked file count | `git ls-files \| Measure-Object` | 114 files (before this milestone's commit) |

**No real credentials, private keys, certificates, `.env` files, PDFs, or
generated runtime artifacts were found tracked in history or the working
tree.** This matches every prior milestone's own hygiene finding
(Milestones 4, 7, 8, 9, 10).

## 12. Testing

Re-run for this report exactly as documented:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest tests\ -q
```

**Result: 157 passed, 0 failed, 9 warnings (deprecation notices from
`python-telegram-bot`, not test failures), fully offline.** Identical count
to every milestone since Milestone 6 (webhook support). No test was
added, removed, or modified by this Milestone 11 documentation pass.

Suite composition (13 files under `tests/`):

| File | Covers |
| --- | --- |
| `test_ocr_pipeline.py` | Rendering, deskew, OCR abstraction, retry/backoff |
| `test_ocr_production_engines.py` | `PaddleOCREngine`/`VisionLLMOCREngine` mapping, error/rate-limit handling (mocked) |
| `test_converters.py` | TXT/DOCX/EPUB output and RTL directionality |
| `test_bot_config.py` | Settings loading/defaults, hermetic against ambient `.env` |
| `test_bot_jobs.py` | Job lifecycle/status transitions, `cleanup_stale_jobs()` |
| `test_bot_logging.py` | JSON/console log formatters, secret scrubbing |
| `test_bot_main_scheduler.py` | `periodic_cleanup_worker()` behavior |
| `test_bot_telegram_handlers.py` | Retry-on-`RetryAfter`/network error |
| `test_bot_webhook.py` | Webhook secret validation, dispatch, mode selection |
| `test_bot_api.py` | Mini App upload/status/download/config/health endpoints |
| `test_deploy_configs.py` | `deploy/` compose/nginx/bootstrap-script static structure |
| `test_tools_evaluate_sample.py` | `evaluate_sample.py` CLI (dummy success, usage errors, clean skips) |
| `test_integration.py` | End-to-end PDF-to-output flow |

No real Telegram bot token, OCR credentials, or network access are used by
any test; the default `DummyOCREngine` and mocked Telegram/HTTP/PaddleOCR
clients are used throughout.

## 13. Known live-validation constraints (honestly unresolved)

These are restated, not newly discovered — the identical root cause has
been documented since Milestone 5 and re-confirmed in Milestones 8, 9, and
10:

- **No Docker engine or Docker-capable host** in any authoring environment
  to date — the base image (`Dockerfile`/`docker-compose.yml`) and the
  production stack (`deploy/docker-compose.prod.yml`) have never been
  built or started; `HEALTHCHECK`/`/api/health`/`/healthz` have never been
  probed against a running container; UID/GID 1000 bind-mount ownership
  has never been runtime-exercised.
- **No DNS-controlled domain or VPS** — no Let's Encrypt certificate has
  ever been issued via `certbot certonly`; `docs/DEPLOYMENT_GUIDE.md` has
  never been executed end-to-end against a real host.
- **No real `BOT_TOKEN` or public HTTPS endpoint** — Telegram's real
  `setWebhook`/update-delivery path has never been exercised; only the
  webhook route's local secret-validation/parsing/dispatch logic has been
  tested (in-process, `ASGITransport`, no network).
- **No `pytesseract`/`paddleocr` install or `VISION_LLM_API_KEY`** — real
  OCR engines have only been validated by unit test with mocked
  clients/binaries; no accuracy/latency benchmark exists against a real
  scanned Persian book corpus (only a synthetic `dummy`-engine benchmark,
  see `docs/BENCHMARK_RESULTS.md`).
- **No scanned, non-copyrighted Persian PDF corpus** was available to
  exercise real-engine accuracy end-to-end.
- Two unrelated pre-existing SSH aliases and an authenticated Azure CLI
  session exist on the Milestone 9/10 authoring machine but are **not**
  persianbookbot deployment targets and were correctly left untouched,
  per the explicit "no guessing hosts" scope boundary in every milestone
  since 9.

Full reproducible command evidence for each item above is in
`docs/LIVE_STAGING_VALIDATION.md` (§§1–10 and the "Milestone 10
re-attempt" section) and `docs/BENCHMARK_RESULTS.md`.

## 14. Cloud-host / OCR handoff checklist

For the next operator/agent with real infrastructure access, in priority
order (each item's exact commands are in the referenced document):

1. **Provision a Linux VPS with a Docker engine** and a DNS A/AAAA record
   pointed at it (`docs/DEPLOYMENT_GUIDE.md` §§1–2).
2. **Run `deploy/setup_host.sh`**, fill in `deploy/.env` with a real
   `BOT_TOKEN` (and `WEBHOOK_URL`/`WEBHOOK_SECRET` for webhook mode)
   (`docs/DEPLOYMENT_GUIDE.md` §§3–4).
3. **Issue the first Let's Encrypt certificate** via the documented
   two-phase bootstrap, then start the full `deploy/docker-compose.prod.yml`
   stack (`docs/DEPLOYMENT_GUIDE.md` §§5–6).
4. **Validate health**: `curl https://<domain>/healthz` and
   `curl https://<domain>/api/health` from outside the host
   (`docs/DEPLOYMENT_GUIDE.md` §8).
5. **Register and verify the Telegram webhook** with `getWebhookInfo`, then
   send a real message to the bot and confirm dispatch
   (`docs/DEPLOYMENT_GUIDE.md` §7).
6. **Confirm UID/GID 1000 bind-mount ownership** on `./data`/`deploy/data`
   after the container has written at least one job's files.
7. **Install a real OCR backend** — `apt install tesseract-ocr
   tesseract-ocr-fas` (already in the image) and set `OCR_ENGINE=tesseract`,
   or `pip install .[paddle]`/`pip install .[vision-llm]` plus the relevant
   credential — then run `tools/evaluate_sample.py <real-scan>.pdf --engine
   <name> --json` against a real, non-copyrighted scanned Persian book and
   record the output in an update to `docs/BENCHMARK_RESULTS.md`.
8. **Re-run `pytest tests/`** on the live host as a final regression check
   before declaring the deployment production-ready, and re-verify Git/
   secret hygiene (`git status --porcelain`, `git ls-files` for secret
   extensions) on that host's checkout.
9. **Rotate `WEBHOOK_SECRET`/`BOT_TOKEN`** per `docs/DEPLOYMENT_GUIDE.md`
   §9 if any value was ever exposed during setup, and confirm backups
   (§10) are in place before considering the handoff complete.

Once these nine items have real, first-hand evidence, update
`docs/PROJECT_STATUS.md`/`docs/LIVE_STAGING_VALIDATION.md` with the actual
results — do not mark them complete here or anywhere else without direct
verification.

## 15. See also

- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — full per-module architecture breakdown
- [`docs/PROJECT_STATUS.md`](PROJECT_STATUS.md) — milestone-by-milestone status log
- [`docs/ROADMAP.md`](ROADMAP.md) — per-milestone detail and follow-up items
- [`docs/PRODUCTION_READINESS.md`](PRODUCTION_READINESS.md) — Milestone 8 audit
- [`docs/LIVE_STAGING_VALIDATION.md`](LIVE_STAGING_VALIDATION.md) — Milestones 9–10 live-validation attempts
- [`docs/BENCHMARK_RESULTS.md`](BENCHMARK_RESULTS.md) — Milestone 5 OCR benchmark run
- [`docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — VPS/DNS/TLS/webhook operator runbook
- [`docs/agents/AGENT_GUIDE.md`](agents/AGENT_GUIDE.md) — agent collaboration guide
- [`../AGENTS.md`](../AGENTS.md) — global agent operating rules
- [`../README.md`](../README.md) — project overview and quick reference
