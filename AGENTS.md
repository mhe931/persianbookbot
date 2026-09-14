# AGENTS.md — persianbookbot

Global operating rules for any human or AI agent working in this repository.
This file is the top-level entry point; subsystem-specific guidance lives in
`.github/instructions/*.instructions.md` and `docs/agents/AGENT_GUIDE.md`.

## What this project is

A Telegram bot + Mini App that converts scanned Persian PDF books into
**EPUB**, **DOCX**, and **TXT** via an async Persian OCR/RTL pipeline:

```
Scanned PDF -> render -> deskew -> OCR -> RTL assemble -> EPUB/DOCX/TXT -> Bot/API
```

See `docs/ARCHITECTURE.md` for the full breakdown, `docs/PROJECT_STATUS.md`
for current milestone status, and `docs/PRODUCTION_READINESS.md` for the
Milestone 8 production-readiness audit (architecture/security/deployment
review, static behavioral audit, test/Git-hygiene verification, and an
honest list of what still requires live infrastructure to validate).

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env   # fill in BOT_TOKEN only if running the real bot
```

## Quality gate command

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest tests/
```

(`pyproject.toml` sets `pythonpath = ["src"]` for pytest, so plain
`pytest tests/` from the repo root also works once the venv is active.)
As of this writing the suite has **157 passing tests** and requires no
network access, real Telegram token, or real OCR backend — the default
`DummyOCREngine` is fully deterministic and offline. The suite is also
**hermetic against an ambient local `.env` file**: `tests/conftest.py`
sets `BOT_ENV_FILE=""` before any test imports `bot.config`, which
disables dotenv loading entirely for the test process (see
`src/bot/config.py`), so a developer's real `BOT_TOKEN` or other local
secrets can never leak into `Settings` during `pytest tests/` even though
`.env` still loads normally for real bot/API runs.

## Continuous integration

`.github/workflows/ci.yml` runs on every push to `main` and every pull
request targeting `main`, on an Ubuntu matrix of Python 3.10/3.11/3.12: it
installs `requirements-dev.txt`, runs a lint step only if a linter is
already configured in the repo (currently none is, so it is skipped rather
than a new tool being force-added), and runs `pytest tests/` with
`BOT_ENV_FILE=""` set as defense-in-depth. CI never requires a real
`BOT_TOKEN`/OCR credential.

## Architecture summary

- `src/common/models.py` — shared dataclasses (`Book`, `PageImage`,
  `PageText`, `ConversionJob`, `JobStatus`). Every subsystem reads/writes
  only these; never introduce parallel/duplicate models.
- `src/ocr/` — PDF rendering/deskew (`preprocessing.py`), OCR engine
  abstraction (`engine.py`, `DummyOCREngine` default / optional
  `TesseractOCREngine`, `PaddleOCREngine`, `VisionLLMOCREngine`), RTL/BiDi
  text helpers (`rtl.py`), and the async orchestrator (`pipeline.py`).
- `src/converters/` — `write_txt`, `write_docx`, `write_epub` (all
  `Book -> pathlib.Path`), plus Persian font configuration (`fonts.py`).
- `src/bot/` — env-driven config (`config.py`, including `webhook_url`/
  `webhook_secret`), structured logging (`logging_config.py`), async job
  orchestration (`jobs.py`, including `JobManager.cleanup_stale_jobs()`
  retention hooks), Telegram handlers (`telegram_handlers.py`), FastAPI
  Mini App backend (`api.py`, including `GET /api/health` and the
  `POST /api/telegram/webhook` route), and the process entrypoint
  (`main.py`, including `periodic_cleanup_worker()` — a configurable
  hourly-by-default background task that calls
  `default_job_manager.cleanup_stale_jobs()` for the lifetime of the
  process, cancelled cleanly on shutdown — and the polling/webhook/
  API-only mode-selection logic described below).
- `web/` — static Telegram Mini App frontend (vanilla HTML/CSS/JS):
  Telegram theme CSS variables, RTL/Persian typography, a five-step
  progress indicator, format-selection toggles, download cards with
  file-size indicators, and defensive `window.Telegram.WebApp`
  lifecycle/MainButton/haptics integration.
- `tools/evaluate_sample.py` — offline-safe local CLI that runs a single
  PDF through the real pipeline/converters (`dummy`/`tesseract`/`paddle`/
  `vision_llm` engine selection) and reports runtime/page/character/output
  metrics as human-readable text (default), `--json`, or `--csv` (single
  header+data row, spreadsheet-friendly, mutually exclusive with `--json`);
  never required for `pytest tests/` and never requires network access
  with the default `dummy` engine.
- `tests/` — pytest suite covering pipeline, converters, bot/API, the
  Mini App static assets, the evaluation CLI, and integration, using
  generated/dummy fixtures only.
- `Dockerfile` / `docker-compose.yml` / `.dockerignore` — multi-stage,
  non-root (UID/GID 1000) container build and compose orchestration for
  deployment; see "Containerization / deployment" below.
- `deploy/` — production/staging deployment bundle (Nginx + Certbot
  compose stack, host bootstrap script, deployment guide); see
  "Production deployment bundle" below.

## Webhook mode

- **Polling is the default and remains so whenever `WEBHOOK_URL` is
  unset** — `bot.main.main()` picks between three mutually exclusive run
  paths (`_run_polling_mode`, `_run_webhook_mode`, `_run_api_only_mode`)
  based only on whether `Settings.bot_token`/`Settings.webhook_url` are
  set; never call `Application.run_polling()` and start the webhook route
  at the same time for the same bot (Telegram itself rejects concurrent
  polling + webhook with a 409 `terminated by other getUpdates request`
  error).
- `Settings.webhook_secret` (`src/bot/config.py`) must be set alongside
  `webhook_url` to actually accept webhook traffic. The route
  (`POST /api/telegram/webhook`, `src/bot/api.py`) validates the
  `X-Telegram-Bot-Api-Secret-Token` header **before** touching the request
  body: a missing header is `401`, and a present-but-wrong (or
  unconfigured) secret is `403`. The secret value is never logged, echoed
  back, or exposed by any response.
- The webhook route is registered unconditionally on the shared
  `bot.api.app` (so it is always importable/testable), but only dispatches
  updates when `app.state.telegram_application` has been set to a real,
  initialized `telegram.ext.Application` — `_run_webhook_mode` wires this
  in and calls `application.initialize()`/`.start()` before serving, and
  `.stop()`/`.shutdown()` on server exit. In polling/API-only mode this
  stays `None` and the route responds `503` instead of ever attempting to
  process an update.
- Reverse-proxy deployments (nginx/Caddy/Traefik terminating TLS in front
  of `API_HOST:API_PORT`) are the intended way to expose the webhook
  route publicly; see README.md "Webhook mode" for the setup walkthrough.
  No live Telegram webhook registration or reverse-proxy validation was
  performed for this change — no `BOT_TOKEN`, public HTTPS endpoint, or
  Docker engine was available in this environment (see
  `docs/PROJECT_STATUS.md`) — only offline secret-validation/dispatch
  behavior was exercised.

## Containerization / deployment

- `Dockerfile` is a two-stage build: a `builder` stage installs Python
  dependencies from `requirements.txt` into a venv (with a C toolchain
  available for source-only dependencies), and a slim `runtime` stage
  copies only that venv plus `src/`/`web/` — no build toolchain ships in
  the final image.
- The runtime image always runs as a non-root `app` user with fixed
  `UID=GID=1000` (never `root`), so bind-mounted `./data` directories can
  be given matching host ownership. `/app/data/uploads` and
  `/app/data/output` are created and `chown`ed to `app:app` (`chmod 750`)
  in the image; `docker-compose.yml` bind-mounts `./data:/app/data` so job
  files persist across container restarts/rebuilds.
- `GET /api/health` (see `src/bot/api.py`) is wired as both the Docker
  `HEALTHCHECK` and the compose service `healthcheck:` — keep it
  dependency-free (see the contract note in
  `.github/instructions/bot.instructions.md`) since the container/
  orchestrator liveness probe depends on it staying fast and reliable.
- Runtime configuration/secrets (`BOT_TOKEN`, `VISION_LLM_API_KEY`, ...)
  are **only** ever injected at container run time via
  `docker-compose.yml`'s `env_file: .env` (or `docker run --env-file .env`)
  — never baked into the `Dockerfile`/image. `.env` is excluded from the
  Docker build context by `.dockerignore` alongside `.git`, `.venv`,
  `.pytest_cache`, `tests/`, bytecode, and the runtime `data/` directory.
  Never commit a real `.env`; use `.env.example` as the source of truth for
  which variables exist.
- `src/bot/main.py::periodic_cleanup_worker()` runs
  `default_job_manager.cleanup_stale_jobs()` on a configurable interval
  (`Settings.cleanup_interval_seconds`, default 3600s/1h) for the lifetime
  of the process (wired into both the Telegram-polling and API-only run
  paths in `main()`), and is explicitly cancelled/awaited during shutdown
  (`post_shutdown` for the Telegram path, a `finally` block for the
  API-only path) so no cleanup sweep is left dangling. It requires no
  credentials and is disabled (returns immediately) when
  `cleanup_interval_seconds <= 0`.

## Production deployment bundle (`deploy/`)

- `deploy/docker-compose.prod.yml` composes `bot` + `nginx` + `certbot`:
  `bot` has no host-published `ports:` (only `expose: ["8000"]` on the
  shared `internal_net` network) so it is reachable only through `nginx`;
  `nginx` is the sole service publishing `80`/`443` to the host;
  `certbot` shares the `./certbot/conf` (TLS state) and `./certbot/www`
  (ACME webroot) volumes with `nginx` and runs an idempotent
  `certbot renew` loop.
- `deploy/nginx/default.conf.template` is rendered by the official
  `nginx:1.27-alpine` image's envsubst-on-templates behavior — only
  `${DOMAIN}` is substituted at container start; never hardcode a real
  domain into this file (use the `DOMAIN` compose/shell environment
  variable instead). It redirects HTTP→HTTPS, serves the ACME challenge
  and a cert-independent `/healthz` (used by the nginx `HEALTHCHECK`) over
  plain HTTP, and reverse-proxies `/` and `/api/` (including the
  `X-Telegram-Bot-Api-Secret-Token` header) to `bot:8000` over HTTPS.
- The first-ever TLS certificate for a domain requires a short two-phase
  bootstrap (start HTTP-only, obtain the cert via the webroot method,
  then enable the HTTPS server block) because nginx cannot start with a
  `ssl_certificate` directive pointing at a file that doesn't exist yet —
  see `docs/DEPLOYMENT_GUIDE.md` step 5 for the exact commands. Do not
  "fix" this by shipping a bundled/self-signed certificate in the repo.
- `deploy/setup_host.sh` is idempotent host bootstrap only — it
  checks/installs Docker, creates UID/GID 1000-compatible
  `deploy/data`/`deploy/certbot` directories, and generates
  `deploy/.env` from `.env.example` **only if it does not already
  exist**. It must never start containers, request/renew a TLS
  certificate, or write a real secret value — those are explicit,
  documented operator steps in `docs/DEPLOYMENT_GUIDE.md`.
- `tests/test_deploy_configs.py` statically validates this entire bundle
  (YAML/template parsing, service/volume/header/ACME coverage, script
  safety) with no Docker engine or network access — keep it passing for
  any change under `deploy/`.
- No command under `deploy/` has been executed against a real VPS/DNS/
  Docker engine in this repository's dev/CI environment — see
  `docs/DEPLOYMENT_GUIDE.md`'s status note and `docs/PROJECT_STATUS.md`
  before claiming otherwise.

## Git conventions

- Feature branches are named after the goal, e.g. `feature/bot-core-pipeline`.
- Commit subjects follow Conventional Commits (`type(scope): summary`,
  ≤72 characters), e.g. `docs: establish agent continuity and architecture specs`.
- Keep unrelated worktree changes untouched — inspect `git status` before
  running any Git command that stages or commits.
- Standard lifecycle: local commits -> `git push -u origin <branch>` ->
  PR via `gh pr create` -> merge (prefer squash) -> delete remote + local
  feature branch -> `git checkout main && git pull`.
- Do not open a pull request or push unless repository access/credentials
  are already configured and it is safe to do so.

## Credential invariants

- Never commit a real `BOT_TOKEN`, webhook URL, or any other secret.
  `.env` is git-ignored; `.env.example` only ever contains empty
  placeholders or safe defaults.
- All configuration is read via `pydantic-settings`
  (`src/bot/config.py::Settings`), sourced from environment variables and
  an optional local `.env` file.
- `bot_token` defaults to `None`: importing `src/bot/*`, running the test
  suite, or running the FastAPI Mini App standalone must never require a
  credential.
- The default OCR engine (`DummyOCREngine`) and all tests must run with
  zero external credentials or network access.

## Known limitation to keep in mind

The **default OCR engine is `DummyOCREngine`** — a deterministic, offline
placeholder that returns fixed Persian text per page number. It is
intentional (keeps tests/CI credential-free) but means no real text is
recognized yet; see `docs/PROJECT_STATUS.md` and `docs/ROADMAP.md` for the
plan to add a real OCR backend.

## Production-readiness audit (Milestone 8)

`docs/PRODUCTION_READINESS.md` is the canonical, source-anchored audit
report — read it before any operational-maintenance handoff or a first
live deployment attempt:

- It re-verifies (rather than changes) every invariant already documented
  in this file: credential-free defaults, `.env` git-ignore hygiene,
  webhook secret-validation ordering, polling/webhook mutual exclusivity,
  and the deployment bundle's coherence.
- It re-ran `pytest tests/` (157 passed, 0 failed, fully offline) and a
  Git/secret-hygiene sweep (no tracked secrets, keys, certificates, PDFs,
  or generated runtime artifacts) as of the audit date.
- It documents, rather than works around, the same live-infrastructure
  gap every prior milestone has recorded: no Docker engine, VPS/DNS
  record, TLS issuance, or real Telegram/OCR-provider credential was
  available, so no live `docker compose up`, TLS issuance, or real
  webhook/OCR call has ever been exercised in this environment. Do not
  claim any of those as validated without actually running them and
  updating that document.

## Live validation / benchmarking (Milestone 5)

`docs/BENCHMARK_RESULTS.md` records the Milestone 5 live-validation
attempt and is the canonical source for benchmark methodology going
forward — read it before re-running or extending this work:

- **Docker**: this environment has no `docker` CLI/daemon, so Milestone 5
  repeated the Milestone 4 static Dockerfile/`docker-compose.yml` audit
  only. `/api/health` probing, container log inspection, and bind-mount
  UID/GID 1000 write-permission verification still require a real Docker
  engine and remain the single highest-priority open item — do not claim
  a live Docker result without actually running `docker compose up` and
  observing it.
- **Benchmark usage**: `tools/evaluate_sample.py <pdf> --engine <name>
  --json` is the only sanctioned way to gather engine metrics. Always
  generate/point it at a synthetic (`tests/fixtures/pdf_factory.py`) or
  explicitly permitted PDF — never a copyrighted book — and never commit
  the PDF or any generated `data/eval*` output (`/data/` is git-ignored;
  keep it that way).
- **Runtime memory guidance**: a 5-page synthetic PDF at 200 DPI through
  `--engine dummy` peaked at **~83 MiB RSS** (measured with `psutil`
  polling the process tree). Treat this as a pipeline-overhead floor, not
  a production sizing number — `tesseract` adds its own C-library
  footprint, `paddle` adds roughly 1–2 GB for `paddlepaddle` + model
  weights, and `vision_llm` adds network/HTTP overhead instead of local
  memory. Size any container `mem_limit`/orchestrator request for the
  specific engine actually deployed, not the `dummy` baseline.
- **Missing engines/credentials must skip cleanly, never fail or leak
  secrets**: `tesseract`/`paddle`/`vision_llm` each returned a one-line
  actionable JSON error and exit code `2` when their optional dependency
  (`pytesseract`/`paddleocr`) or credential (`VISION_LLM_API_KEY`) was
  absent — reproduce that same clean-skip contract in any future benchmark
  run rather than installing heavyweight/unavailable dependencies or
  reading `.env` to hunt for a credential.
