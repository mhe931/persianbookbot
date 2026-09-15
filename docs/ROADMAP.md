# Roadmap

This roadmap lists the next milestones after the verified core pipeline
scaffold (see `docs/PROJECT_STATUS.md` for what already exists and passes
its 46-test suite).

## Milestone 1 — Real OCR backend

The default `DummyOCREngine` is deterministic placeholder text.
`PaddleOCREngine` and `VisionLLMOCREngine` (Gemini/Claude) have now been
added as opt-in `OCREngine` implementations (branch
`feature/production-ocr-backends`), alongside the existing
`TesseractOCREngine`:

- Finish validating `TesseractOCREngine` (`OCR_ENGINE=tesseract`) against
  real scanned Persian book pages; document required Tesseract + `fas`
  language-data installation steps.
- `PaddleOCREngine` (`OCR_ENGINE=paddle`, `pip install .[paddle]`) is
  implemented with lazy `paddleocr` import, `PADDLE_LANG`/`PADDLE_USE_GPU`
  configuration, and automatic fallback from `fa` to Arabic-script (`ar`)
  recognition — still needs validation against real scanned Persian book
  pages and accuracy benchmarking.
- `VisionLLMOCREngine` (`OCR_ENGINE=vision_llm`, `pip install .[vision-llm]`)
  is implemented with provider-neutral HTTP calls to Gemini or Claude
  (`VISION_LLM_PROVIDER`/`VISION_LLM_API_KEY`/`VISION_LLM_MODEL`),
  structured transcription prompting, and rate-limit (`RateLimitError`)
  mapping — still needs validation against real scanned Persian book pages,
  cost/latency benchmarking, and a real provider API key to exercise
  end-to-end.
- Add accuracy/confidence benchmarking against a small real-world Persian
  scanned-book test corpus (kept out of the committed offline test suite,
  or clearly marked as an opt-in/slow test group), covering all three real
  backends (`tesseract`, `paddle`, `vision_llm`). **Tooling now exists:**
  `tools/evaluate_sample.py path/to/book.pdf --engine <name>` runs any
  backend against a local PDF and reports runtime/page/character metrics —
  the remaining work is running it against a real corpus and recording
  results, not building the tool itself.
- Keep `DummyOCREngine` as the permanent zero-credential default for CI and
  local development regardless of which real engines are added.

## Milestone 2 — Mini App UI enhancements ✅ (core UX shipped)

The `web/` frontend has been upgraded from a minimal scaffold
(`feature/miniapp-ui-enhancements`) to a Telegram theme-aware, accessible,
resilient UI, and a local sample-evaluation CLI has been added:

- ✅ Telegram theme CSS variables (`--tg-theme-*`, with light-mode
  fallbacks), native RTL/Persian typography, and an accessible five-step
  progress indicator (Uploaded / Preprocessing / OCR / Generating
  Documents / Ready) driven by `JobStatus` transitions.
- ✅ EPUB/DOCX/TXT format-selection toggles and download cards with
  file-size indicators (`ConversionJob.to_dict()["output_sizes"]`).
- ✅ Defensive `window.Telegram.WebApp` lifecycle integration (`ready`,
  `expand`, `MainButton`, haptic feedback) that degrades gracefully in a
  plain (non-Telegram) browser.
- ✅ Visible upload progress (`XMLHttpRequest` upload events), client-side
  PDF/20MB validation sourced from the new `GET /api/config` endpoint
  (rather than a hardcoded limit), and resilient status polling with
  success/failure/rate-limit/network-error handling plus a retry action.
- ✅ `tools/evaluate_sample.py` — an offline-safe local CLI to run a real
  PDF through any of the four `OCREngine` implementations
  (`dummy`/`tesseract`/`paddle`/`vision_llm`) and report
  runtime/page/character/output metrics, reusing `ocr.pipeline.process_pdf`
  and `converters.*` directly.

Still open for a follow-up Mini App iteration:

- Add a job history/list view backed by `JobManager.list_jobs()` (already
  available server-side, not yet exposed via a dedicated endpoint/UI).
- Add inline document preview before download.
- Consider a lightweight framework or design system if the vanilla
  implementation becomes hard to maintain.
- Use `tools/evaluate_sample.py` against a small corpus of real
  (non-copyrighted) scanned Persian PDFs to benchmark `tesseract`/
  `paddle`/`vision_llm` accuracy — the tool exists now; the benchmarking
  pass itself is still outstanding (see Milestone 1).

## Milestone 3 — Bot & operations hardening ✅ (CI/CD, logging, retention, health)

Delivered on branch `feature/operations-hardening`:

- ✅ `.github/workflows/ci.yml` — CI pipeline running `pytest tests/` (plus
  a lint step that only runs if a linter is already configured) on every
  push/PR targeting `main`, across an Ubuntu Python 3.10/3.11/3.12 matrix.
  No credentials required.
- ✅ Structured JSON/console logging (`src/bot/logging_config.py`) with
  `job_id`/`user_id`/`duration`/`error` context, integrated into
  `src/bot/jobs.py` job lifecycle events, with secret-shaped keys always
  scrubbed before rendering.
- ✅ `JobManager.cleanup_stale_jobs()` (`src/bot/jobs.py`) — configurable
  retention/cleanup hooks (`Settings.job_retention_seconds`) that prune
  finished jobs and their upload/output/temp files older than the TTL,
  with explicit per-path error handling so one bad file never aborts the
  rest of cleanup. In-memory architecture preserved — no database added.
- ✅ `GET /api/health` (`src/bot/api.py`) — lightweight liveness endpoint,
  covered by tests.
- ✅ Fixed a real test-isolation bug: config tests previously read a
  developer's ambient `.env` (e.g. a real `BOT_TOKEN`) instead of the
  intended safe defaults. `Settings`/`BOT_ENV_FILE` + `tests/conftest.py`
  now make the whole suite hermetic against local `.env` content.

Still open for a follow-up operations iteration:

- Live-validate the Telegram bot polling path end-to-end with a real
  `BOT_TOKEN` in a controlled environment (currently only unit-tested with
  mocks).
- Wire `JobManager.cleanup_stale_jobs()` into a periodic background task
  (e.g. an `asyncio` loop in `bot.main`) so retention happens
  automatically in a long-running process, rather than only being
  callable on demand — the hook and its tests exist now; the scheduling
  wrapper is the remaining piece.
- Consider exposing job-count/queue-depth metrics alongside `GET
  /api/health` if operational visibility needs grow beyond a liveness
  check.
- Document a font-licensing/bundling story for `PERSIAN_FONT_NAME` if a
  specific font needs to ship with deployments.
- `ConversionJob` state remains in-memory only by design (see scope
  boundaries in `AGENTS.md`); persisting it across restarts is explicitly
  out of scope unless a future milestone changes that requirement.

## Milestone 4 — Deployment ✅ (Docker/compose + periodic cleanup scheduling)

Delivered on branch `feature/containerization-deployment`:

- ✅ Multi-stage `Dockerfile` (repo root): `builder` stage installs
  `requirements.txt` into a venv (with a C toolchain available for
  source-only dependencies); `runtime` stage is a slim `python:3.11-slim`
  layer containing only that venv plus `src/`/`web/`, the runtime system
  libraries Pillow/PyMuPDF need (JPEG/PNG/JP2/TIFF codecs, font
  discovery), and optional `tesseract-ocr`/`tesseract-ocr-fas` so
  `OCR_ENGINE=tesseract` works without further setup. Runs as a fixed
  non-root user (`app`, UID/GID 1000), owns `/app/data/uploads` and
  `/app/data/output` (`chmod 750`), ships safe credential-free environment
  defaults, and declares a `HEALTHCHECK` against `GET /api/health`.
- ✅ `docker-compose.yml`: single `bot` service, port `8000` published,
  `./data:/app/data` persistent bind mount, `env_file: .env` for runtime
  secret/config injection (never baked into the image), `restart:
  unless-stopped`, matching `healthcheck:` block.
- ✅ `.dockerignore` excluding VCS files, `.venv`, caches, `tests/`, `.env`/
  `.env.*` (keeping `.env.example`), bytecode, and the runtime `data/`
  directory.
- ✅ `src/bot/main.py::periodic_cleanup_worker()` — a configurable
  `asyncio` loop (`Settings.cleanup_interval_seconds`, default 3600s/1h)
  that calls `default_job_manager.cleanup_stale_jobs()` for the lifetime
  of the process, wired into both the Telegram-polling path
  (`Application.post_init`/`post_shutdown`) and the API-only path (a
  `finally`-guarded task), with explicit cancellation on shutdown in both.
  Requires no credentials; disabled entirely when
  `cleanup_interval_seconds <= 0`.
- ✅ README/AGENTS/bot instructions/project status updated with Docker
  build/run/compose commands, volume/permission notes, healthcheck usage,
  runtime env injection, and cleanup-scheduling documentation.

Still open for a follow-up deployment iteration:

- **Build and run the image against a real Docker engine.** No Docker
  engine was available in the environment this milestone was authored in,
  so validation was static only (Dockerfile instruction parsing,
  `docker-compose.yml` YAML/schema inspection). Actually building the
  image, running `docker compose up`, and exercising the `HEALTHCHECK`/
  volume ownership end-to-end is the highest-priority remaining item.
- Consider a `.dockerignore`/build-context size audit and multi-arch
  (`linux/amd64` + `linux/arm64`) build once a real engine is available.
- ~~Define hosting/runtime requirements for `WEBHOOK_URL` (webhook mode)
  vs. polling mode behind a reverse proxy/TLS terminator~~ — delivered in
  Milestone 6 (`WEBHOOK_URL`/`WEBHOOK_SECRET`, `POST
  /api/telegram/webhook`, reverse-proxy setup in README.md).
- Consider publishing the built image to a container registry (GHCR or
  similar) via CI, once that is explicitly requested and a registry/
  credential story is defined — out of scope for this milestone by design.

## Milestone 7 — Staging infrastructure & cloud deployment playbook ✅ (offline-validated; live deployment unverified)

Delivered on branch `feature/staging-deploy-infra`:

- ✅ `deploy/docker-compose.prod.yml`: `bot` (internal-only, no
  host-published ports, `internal_net` bridge network), `nginx`
  (`nginx:1.27-alpine`, the only service publishing `80`/`443`,
  `depends_on: bot: condition: service_healthy`), and `certbot`
  (idempotent `certbot renew` loop) with persistent `./data`,
  `./certbot/conf`, and `./certbot/www` volumes, `env_file: .env` runtime
  injection, `restart: unless-stopped`, and healthchecks on every service.
- ✅ `deploy/nginx/default.conf.template`: HTTP→HTTPS redirect, ACME
  HTTP-01 challenge location, a TLS-independent `/healthz`, and HTTPS
  reverse-proxying of `/` and `/api/` to `bot:8000` with forwarded headers
  and explicit `X-Telegram-Bot-Api-Secret-Token` pass-through. Only
  `${DOMAIN}` (envsubst'd at container start) — no hardcoded real domain.
- ✅ `deploy/setup_host.sh`: idempotent Ubuntu/Debian bootstrap — Docker
  Engine/Compose-plugin check-then-install, UID/GID 1000-compatible
  `deploy/data`/`deploy/certbot` directory creation, and safe
  `deploy/.env` template generation (never overwrites an existing file,
  never writes a real secret).
- ✅ `docs/DEPLOYMENT_GUIDE.md` (new): VPS/DNS setup, the two-phase
  first-TLS-certificate bootstrap, renewal validation, webhook
  registration/verification, secret rotation, health validation, backups,
  rollback, and a troubleshooting table.
- ✅ `tests/test_deploy_configs.py` (new, 32 tests): offline YAML/template
  parsing and structural checks for every requirement above — no Docker
  engine or network access required. Full suite is **157 passing tests**.
- ✅ README/AGENTS/bot instructions/project status updated with pointers
  to the new `deploy/` bundle and its unverified-live status.

Still open / explicitly **not** validated this milestone (documented
rather than worked around):

- **No real VPS, DNS record, or Docker engine was available** — no image
  was built from `deploy/docker-compose.prod.yml`, no certificate was
  issued via `certbot certonly`, and no live Telegram webhook was
  registered through this stack. Re-run the entire
  `docs/DEPLOYMENT_GUIDE.md` walkthrough on a real host to get the first
  live result — this is now the single highest-priority remaining item
  across the whole roadmap (supersedes the Milestone 4/5 Docker
  build/run follow-up below, which this bundle also depends on).
- **Docker build/run for the base image** — unchanged from Milestone 5;
  still blocked on no `docker` CLI/daemon in this environment.
- Consider adding CI-driven `docker compose -f
  deploy/docker-compose.prod.yml config` validation (or a full build) once
  a Docker-capable CI runner is available, to catch schema regressions
  earlier than the next live deployment attempt.

## Milestone 6 — Webhook support & evaluation export ✅ (offline-validated; live delivery unverified)

Delivered on branch `feature/production-staging-webhook`:

- ✅ `Settings.webhook_secret` (new, alongside the existing `webhook_url`)
  and `.env.example` documentation for both — `webhook_url` stays fully
  optional, and polling remains the default whenever it is unset.
- ✅ `POST /api/telegram/webhook` (`src/bot/api.py`): strict
  `X-Telegram-Bot-Api-Secret-Token` validation (`401` missing, `403`
  wrong/unconfigured) before the request body is ever parsed, dispatch
  through the same `Application`/handlers polling mode uses, `400` on a
  malformed payload, `503` when no application is wired (polling/API-only
  mode) — never leaks the configured secret.
- ✅ `bot.main._run_webhook_mode()`: single event loop, `Application`
  `.initialize()`/`.start()` + `Bot.set_webhook()` instead of
  `run_polling()`, so webhook mode can never conflict with polling for the
  same bot.
- ✅ `tools/evaluate_sample.py --csv`: stable-column CSV export
  (header+one data row), mutually exclusive with `--json`, same
  clean-skip/exit-code contract for missing optional dependencies/
  credentials as the existing human/JSON modes.
- ✅ `tests/test_bot_webhook.py` (16 new tests) + 4 new `--csv` tests in
  `tests/test_tools_evaluate_sample.py` — suite is now **125 passing
  tests**, still fully offline with `DummyOCREngine`.
- ✅ README/AGENTS/bot & ocr instructions updated with reverse-proxy
  webhook setup, secret injection, polling-fallback guarantees, and
  `--csv` usage.

Still open / explicitly **not** validated this milestone (documented
rather than worked around):

- **Live webhook registration/delivery against Telegram's real servers**
  — no `BOT_TOKEN` or public HTTPS endpoint was available; only the
  route's secret-validation/parsing/dispatch logic was exercised offline
  (in-process `ASGITransport`, no network). Re-run with a real bot token
  and a reverse proxy (nginx/Caddy/Traefik terminating TLS) on a staging
  host to confirm end-to-end delivery.
- **Docker build/run** — unchanged from Milestone 5; still blocked on no
  `docker` CLI/daemon in this environment. See Milestone 5 below.
- **Real OCR engine benchmarking with `--csv`** — only exercised against
  the existing synthetic/dummy-engine fixture, per the same
  non-copyrighted-content constraint as Milestone 5; re-run
  `tools/evaluate_sample.py --engine tesseract --csv` (etc.) once a real,
  permitted sample and the relevant optional dependency are available.

## Milestone 5 — Live validation & OCR benchmark reporting ⚠️ (attempted; blocked on environment)

Attempted on branch `feature/live-validation-benchmarks`. **Blocked on
environment availability**: no Docker engine and no optional OCR
dependency/credential (`pytesseract`, `paddleocr`, `VISION_LLM_API_KEY`)
were present, so this milestone delivered a static audit + offline
benchmark harness rather than a live one. Full evidence in
`docs/BENCHMARK_RESULTS.md`.

- ⚠️ **Docker build/run smoke test** — not possible; `docker` CLI is not
  installed in this environment. Repeated the Milestone 4 static audit
  (Dockerfile instruction review, `docker-compose.yml` YAML/schema parse)
  — both still pass — but `/api/health`, log inspection, and bind-mount
  UID/GID 1000 write-permission verification remain unexercised against a
  real engine.
- ✅ **Benchmark tooling exercised end-to-end**: `tools/evaluate_sample.py
  --engine dummy --json` was run against a synthetic (non-copyrighted,
  `reportlab`-generated) 5-page PDF, reporting runtime/pages-per-second/
  character/output-size metrics plus a separately measured ~83 MiB peak
  RSS baseline (`psutil`). This confirms the CLI/reporting pipeline itself
  works; it carries no OCR-accuracy signal (the fixture has no scanned
  Persian text).
- ⚠️ **Real engine benchmarking** — `tesseract`/`paddle`/`vision_llm` each
  produced a clean, actionable, nonzero-exit skip (`pytesseract`/
  `paddleocr` not installed; `VISION_LLM_API_KEY` not set) rather than
  real recognition metrics. No dependency was installed and no credential
  was requested/read, per this milestone's scope boundaries.
- ✅ `docs/BENCHMARK_RESULTS.md` (new) — hardware/software context, exact
  commands, full JSON output for every engine attempted, observations,
  limitations, and recommended per-engine production setup/memory sizing.

Still open for a follow-up live-validation iteration:

- **Re-run this entire milestone on a host with a working Docker engine**
  (Linux host or CI runner preferred) to get the actual `/api/health`
  probe, log inspection, and bind-mount UID/GID 1000 permission result —
  this is now the single highest-priority remaining item across the whole
  roadmap.
- Install `pytesseract` + system `tesseract-ocr`/`tesseract-ocr-fas` (cheapest
  real engine) and re-run `tools/evaluate_sample.py --engine tesseract`
  against a real, licensed (non-copyrighted-content) scanned Persian PDF to
  get a first real accuracy/runtime data point.
- Only once a real scanned Persian PDF sample is legitimately available,
  benchmark `paddle`/`vision_llm` the same way and compare
  runtime/memory/cost/accuracy trade-offs (see
  `docs/BENCHMARK_RESULTS.md` recommendations for what to expect from
  each).

## Milestone 8 — Production-readiness audit ✅ (verified; live infra still unavailable)

Delivered on branch `feature/production-readiness-audit`: a full
source-anchored, read-only audit of every prior milestone below, producing
`docs/PRODUCTION_READINESS.md` and refreshing README.md/AGENTS.md/
`docs/PROJECT_STATUS.md`/this roadmap. **No application code changed.**

- ✅ Architecture, interfaces/dependencies, and security/credential-
  handling review across `src/`, `web/`, `tools/`, `deploy/`, the root
  `Dockerfile`/`docker-compose.yml`, and `.github/` — no defect found.
- ✅ Static behavioral audit of RTL/BiDi handling, converter font hooks,
  OCR error mapping, polling/webhook exclusivity, webhook secret
  validation, health/cleanup behavior, Mini App configuration/lifecycle/
  upload handling, and Docker/Compose/Nginx/bootstrap coherence — all
  confirmed correct against the current source (see
  `docs/PRODUCTION_READINESS.md` for the full per-item evidence trail).
- ✅ `pytest tests/` re-verified: **157 passed, 0 failed**, fully offline,
  zero credentials — the exact same count as Milestone 7, since no test
  was added or removed by this audit.
- ✅ Git/secret hygiene re-verified: `.env` git-ignored and untracked; no
  committed secrets, keys, certificates, PDFs, or generated runtime
  artifacts anywhere in tracked history.
- **Still not live-validated** (same environment constraints as
  Milestones 4–7, restated rather than newly discovered): no Docker
  engine, no VPS/DNS record, no TLS issuance, and no real Telegram/OCR-
  provider credential were available, so the Docker image was still never
  built/run, `deploy/docker-compose.prod.yml` was still never brought up
  against a real domain, and no live webhook/real-OCR call was made. See
  `docs/PRODUCTION_READINESS.md`'s "Known operational constraints" for the
  consolidated, prioritized follow-up list — unchanged from Milestone 7's
  own open items below, since no new infrastructure became available
  between milestones.

## Milestone 9 — Live cloud staging validation attempt ⏸️ (blocked; safe discovery only)

Delivered on branch `feature/live-staging-deployment`: a fresh,
non-destructive discovery pass for Docker/Compose, WSL, configured Docker
contexts, SSH targets, and cloud CLI tooling, producing
`docs/LIVE_STAGING_VALIDATION.md`. **No application code changed.**

- ✅ Confirmed (again, with fresh command output) that this environment
  has no Docker engine, no WSL, and no `docker-compose`/`docker` binary
  on `PATH` — `docker context ls` cannot even run.
- ✅ Discovered two pre-existing SSH host aliases (`~/.ssh/config`) and an
  authenticated Azure CLI session on this machine, but confirmed neither
  is a persianbookbot-designated deployment target and correctly left
  both untouched, per this milestone's explicit "no guessing hosts, no
  provisioning without configured access" scope boundary.
- ✅ Confirmed local `.env` presence/git-ignore status and which keys are
  set, **without reading any secret value** — `BOT_TOKEN` is set for
  local dev but `WEBHOOK_URL` is empty and no domain/TLS exists, so no
  live Telegram/webhook call was made.
- ✅ Re-confirmed UID/GID 1000 Dockerfile/`setup_host.sh` correctness by
  source read (unchanged from Milestone 5/8).
- ✅ `pytest tests/` re-verified: **157 passed, 0 failed** — identical
  count to Milestones 6–8.
- **Still blocked, same root cause as Milestones 5–8**: no Docker engine,
  no VPS/DNS/domain designated for this project, no TLS issuance, no real
  Telegram webhook delivery, and no scanned Persian PDF sample. See
  `docs/LIVE_STAGING_VALIDATION.md` for the full evidence, the
  consolidated blocker table, and exact operator unblock commands.

## Milestone 10 — Production host validation attempt ⏸️ (blocked; identical root cause)

Attempted on branch `feature/production-host-validation`, forked from
`main` at `41cbd23`: a full re-attempt of the documented production
deployment procedure (start `deploy/docker-compose.prod.yml`, probe
`/healthz`/`/api/health`, verify UID/GID 1000 bind-mount permissions,
convert a sample PDF through the live API, capture runtime metrics,
tear down cleanly). **No application code changed; no container was
started.**

- ✅ Fresh Docker/Compose/WSL/service discovery re-run on the same
  machine: still no `docker`/`docker-compose` binary, `wsl.exe` is only
  the Windows launcher stub (WSL feature not installed), and the only
  Docker-named Windows service is the unrelated `FlexeraDockerMon`
  inventory agent — none of these is a usable Docker Engine.
- ✅ Re-confirmed the same two unrelated SSH aliases and authenticated
  Azure CLI session from Milestone 9 exist but are still not designated
  persianbookbot targets, and were **not** contacted, per scope.
- ✅ `.env` key-presence re-scanned (values never read): unchanged from
  Milestone 9.
- ✅ `pytest tests/` re-verified: **157 passed, 0 failed** — identical
  count to Milestones 6–9; no test added/removed/modified.
- ✅ Tracked-secret/artifact hygiene re-checked: no `.env`/`.pem`/`.key`/
  `.pdf`/`.crt` tracked in Git; working tree clean apart from the
  untracked `.goals/` planning folder.
- **Blocked — every live acceptance item for this milestone (stack
  start/teardown, live `/healthz`/`/api/health` probe, UID/GID 1000
  runtime bind-mount check, sample-PDF conversion through a live API,
  runtime metrics capture) is explicitly marked blocked for the identical
  root cause as Milestones 5–9**: no Docker Engine or Docker-capable host
  is available in, or designated for, this authoring environment. See
  `docs/LIVE_STAGING_VALIDATION.md` ("Milestone 10 re-attempt" section)
  for full command evidence and the unchanged operator handoff.

## Milestone 11 — Delivery report and operational runbook ✅ (documentation-only finalization)

Delivered on branch `feature/delivery-report-runbook`, forked from `main`
at `a347df3`: a single, self-contained `docs/DELIVERY_REPORT.md`
consolidating all ten prior milestones for operator handoff — capability
matrix, architecture/data flow/shared contracts, local and Docker/
production deployment quickstarts, polling/webhook configuration, the
evaluation CLI, the security/secret-management model, full test
verification, and a prioritized cloud-host/OCR handoff checklist. **No
application, converter, OCR, or deployment-code logic was changed.**

- ✅ `docs/DELIVERY_REPORT.md` (new) — reconciled against current source
  and every prior milestone report; no live metric or infrastructure
  result claimed beyond what is already evidenced.
- ✅ `pytest tests/` re-verified: **157 passed, 0 failed**, fully
  offline — identical count to Milestones 6–10.
- ✅ Git/secret/artifact integrity re-checked across all local refs and
  tags (none exist): clean.
- ✅ README.md/`docs/PROJECT_STATUS.md` updated with a pointer to the
  final report and an explicit development→operations handoff statement.
- **This roadmap's remaining items are unchanged** by this milestone —
  see "Prioritization notes" below, now framed as the final operator
  handoff checklist (also restated in `docs/DELIVERY_REPORT.md` §14).

## Prioritization notes

With Milestones 3, 4, 6, 7, 8, and 11 delivered, Milestone 5
attempted-but-blocked, and Milestones 9–10 each re-attempting the same
live-infra gap with additional safe discovery (still blocked), the
highest-value next step is unchanged from before these milestones: **get
access to a real VPS/cloud host with a Docker engine, a DNS record under
your control, and a real Telegram bot token**, and run the full
`docs/DEPLOYMENT_GUIDE.md` walkthrough end-to-end — container smoke test,
TLS issuance, live webhook registration/delivery, and the UID/GID 1000/
sample-PDF/metrics checks required by Milestone 10 — all in one pass,
since they all depend on the same missing prerequisite (see Milestone 5,
Milestone 6, Milestone 7, Milestone 9, and Milestone 10 above for the
detailed follow-up lists, and `docs/LIVE_STAGING_VALIDATION.md`/
`docs/DELIVERY_REPORT.md` §14 for the consolidated, audited version of the
same list) — everything else (converters, job orchestration, delivery
surfaces including webhook mode, CI, logging, retention, containerization,
cleanup scheduling, benchmark tooling/reporting/CSV export, the
Nginx/Certbot deployment bundle, and now the final delivery
documentation) is already implemented, tested, and independently audited
end-to-end. **With this milestone, the project transitions from active
feature development to an operations/live-validation handoff** — no
further application milestones are planned in this roadmap; all
subsequent work is executing the checklist above against real
infrastructure.

