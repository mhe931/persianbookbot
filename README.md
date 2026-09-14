# persianbookbot

Telegram bot and Mini App that converts scanned Persian PDF books into
**EPUB**, **DOCX**, and **TXT** via an async Persian OCR/RTL pipeline.

## Pipeline

```
Scanned PDF -> page preprocessing/deskew -> Persian OCR -> RTL/BiDi text
assembly -> EPUB/DOCX/TXT output -> Telegram bot / Mini App delivery
```

## Project layout

- `src/common/` — shared data models (`Book`, `PageText`, `ConversionJob`, ...)
- `src/ocr/` — PDF rendering/preprocessing, OCR engine abstraction
  (deterministic offline `DummyOCREngine` by default), and RTL text helpers
- `src/converters/` — TXT/DOCX/EPUB generation with explicit RTL formatting
- `src/bot/` — configuration, async job orchestration, Telegram handlers,
  and the FastAPI Mini App backend
- `web/` — static Telegram Mini App frontend (vanilla HTML/CSS/JS)
- `deploy/` — production/staging deployment bundle (Nginx + Certbot
  compose stack, host bootstrap script); see "Production/staging
  deployment" below
- `docs/agents/` — agent collaboration guide and operational runbook
- `tests/` — pytest suite covering the pipeline, converters, and bot/API

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env   # fill in BOT_TOKEN only if running the real bot

$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest tests/          # run tests
.\.venv\Scripts\python.exe -m bot.main               # run the API (+ bot if BOT_TOKEN is set)
```

No real Telegram bot token, OCR credentials, or network access are required
to run the test suite: the default `DummyOCREngine` is fully deterministic
and offline.

## Webhook mode

The bot **polls by default** (`Application.run_polling()`) whenever
`WEBHOOK_URL` is unset — no public URL, TLS, or reverse proxy is required
for local development. To run behind a reverse proxy instead (e.g. on a
staging/production host), set both:

```powershell
# .env
WEBHOOK_URL=https://bot.example.com     # public HTTPS base URL of your reverse proxy
WEBHOOK_SECRET=<random value, e.g. `openssl rand -hex 32`>
```

`bot.main.main()` then runs `_run_webhook_mode()` instead of polling: it
registers `<WEBHOOK_URL>/api/telegram/webhook` with Telegram
(`Bot.set_webhook`, including the secret token) and serves the FastAPI app
(with the webhook route already mounted) on `API_HOST:API_PORT` — polling
is never started in this mode, so there is no conflict with the webhook.

A minimal nginx reverse-proxy snippet, terminating TLS and forwarding to
the container/process on port 8000:

```nginx
server {
    listen 443 ssl;
    server_name bot.example.com;
    ssl_certificate     /etc/letsencrypt/live/bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Every request to `POST /api/telegram/webhook` must carry a matching
`X-Telegram-Bot-Api-Secret-Token` header — Telegram sends this
automatically once `set_webhook(..., secret_token=...)` has been called
with it, so nothing else needs to set the header. A request with a
missing header is rejected `401`; a present-but-wrong (or unconfigured)
secret is rejected `403` — the update body is never parsed until the
secret validates, and the secret itself is never logged or echoed back.

**Never commit `WEBHOOK_SECRET` or `WEBHOOK_URL` values** — inject them at
runtime via `.env` (local) or your platform's secret store (staging/
production), exactly like `BOT_TOKEN`.

**Staging limitation**: this repository's dev/CI environment has no
`BOT_TOKEN`, public HTTPS endpoint, or Docker engine, so webhook
registration/reverse-proxy delivery could only be validated offline
(secret-header validation, update parsing, and dispatch through the
Telegram `Application`, all exercised in `tests/test_bot_webhook.py`) —
not against Telegram's real servers. Live validation is the next step on
a host that has those prerequisites (see `docs/PROJECT_STATUS.md`).

For a ready-made production reverse-proxy stack (Nginx + Certbot-managed
TLS, non-root bot container) instead of the snippet above, see
[`deploy/`](deploy/) and
[`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md).

## Sample evaluation CLI

`tools/evaluate_sample.py` runs the real OCR/conversion pipeline against a
single local PDF and reports runtime/page/character/output metrics,
without ever requiring a Telegram bot or the FastAPI server to be running:

```powershell
# Human-readable report (default)
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf

# Machine-readable output - pick one (mutually exclusive)
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf --json
.\.venv\Scripts\python.exe tools\evaluate_sample.py path\to\book.pdf --csv > metrics.csv
```

`--csv` prints a single header+data row (one column per metric, plus a
`<format>_path`/`<format>_size_bytes` column pair for every possible output
format so the header stays stable regardless of `--formats`) — handy for
appending results from multiple runs/engines into one spreadsheet. It is
fully offline with the default `--engine dummy`; `--engine
tesseract/paddle/vision_llm` each report a clear, actionable error (exit
code `2`) on `stderr` if their optional dependency (`pytesseract`/
`paddleocr`) or credential (`VISION_LLM_API_KEY`) is missing — see
`docs/PROJECT_STATUS.md` for what real-engine setup requires.

## Docker / deployment

The bot ships with a production-ready, non-root, multi-stage `Dockerfile`
and a `docker-compose.yml` for local/self-hosted deployment. See
[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the full deployment
write-up; quick reference:

```powershell
# Build the image (multi-stage: build deps -> minimal runtime layer).
docker build -t persianbookbot:latest .

# Runtime environment (BOT_TOKEN, etc.) is injected via .env at *run* time,
# never baked into the image - copy and edit it first if you haven't already.
Copy-Item .env.example .env

# Run directly with docker: -v mounts persistent uploads/output, matching
# the image's non-root UID/GID 1000 so host-written files stay accessible.
docker run -d --name persianbookbot -p 8000:8000 `
  -v ${PWD}/data:/app/data --env-file .env --restart unless-stopped `
  persianbookbot:latest

# ...or via docker compose (recommended - also wires the healthcheck):
docker compose up -d --build
docker compose ps                 # check the /api/health healthcheck status
docker compose logs -f bot
docker compose down
```

Notes:

- The container runs as a fixed non-root user (`app`, UID/GID 1000).
  `./data` is bind-mounted to `/app/data` (uploads + output subfolders,
  `chmod 750`, owned by `app`) so job files persist across container
  restarts/rebuilds.
- `GET /api/health` is used as the container `HEALTHCHECK` (also usable by
  an external load balancer/orchestrator).
- The default `OCR_ENGINE=dummy` requires no credentials; the image also
  includes `tesseract-ocr`/`tesseract-ocr-fas` so `OCR_ENGINE=tesseract`
  works without further setup. `paddle`/`vision_llm` still need their
  optional Python extras installed separately (see `requirements.txt`).
- A periodic cleanup worker (`bot.main.periodic_cleanup_worker`, wired into
  `bot.main.main()`) calls `default_job_manager.cleanup_stale_jobs()` every
  `CLEANUP_INTERVAL_SECONDS` (default 3600s/1h) for the lifetime of the
  process, and is cancelled cleanly on shutdown. Set it to `0` to disable
  the periodic sweep (cleanup stays callable on demand).

## Production/staging deployment (Nginx + TLS)

For an internet-facing staging/production deployment — bot container
kept internal, Nginx as the only host-exposed service (ports 80/443),
Certbot-managed Let's Encrypt TLS with automatic renewal, and an
idempotent Ubuntu/Debian host bootstrap script — see:

- [`deploy/docker-compose.prod.yml`](deploy/docker-compose.prod.yml) —
  `bot` + `nginx` + `certbot` services.
- [`deploy/nginx/default.conf.template`](deploy/nginx/default.conf.template) —
  HTTP→HTTPS redirect, ACME challenge, and reverse-proxy rules.
- [`deploy/setup_host.sh`](deploy/setup_host.sh) — Docker install,
  UID/GID 1000-compatible directories, safe `.env` template generation.
- [`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md) — the full
  VPS/DNS/TLS/webhook/secret-rotation/backup/rollback runbook.

This bundle is statically validated (`tests/test_deploy_configs.py`) but
**not** exercised against a real VPS/DNS/Docker engine in this repository
— see the guide's status note and `docs/PROJECT_STATUS.md` for exactly
what remains unverified.

## Production readiness

[`docs/PRODUCTION_READINESS.md`](docs/PRODUCTION_READINESS.md) is the
authoritative Milestone 8 audit report: architecture, interfaces/
dependencies, a security/credential-handling review, a static behavioral
audit (RTL/BiDi, OCR error mapping, webhook exclusivity/secret validation,
health/cleanup, Mini App upload handling, Docker/Compose/Nginx coherence),
full test/Git-hygiene verification, a deployment pre-flight checklist, and
an honest list of what still requires live infrastructure (Docker engine,
VPS/DNS, TLS, and real Telegram/OCR-provider credentials) to validate.
Read it before a first production deployment attempt or any operational
maintenance handoff.

See [`docs/agents/AGENT_GUIDE.md`](docs/agents/AGENT_GUIDE.md) for the full
architecture, subsystem boundaries, and operational runbook.


