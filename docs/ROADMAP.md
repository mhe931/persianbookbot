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
- Define hosting/runtime requirements for `WEBHOOK_URL` (webhook mode)
  vs. polling mode behind a reverse proxy/TLS terminator, if a specific
  hosting target is chosen.
- Consider publishing the built image to a container registry (GHCR or
  similar) via CI, once that is explicitly requested and a registry/
  credential story is defined — out of scope for this milestone by design.

## Prioritization notes

With Milestones 3 and 4 delivered, the highest-value next steps are: (1)
building/running the container image against a real Docker engine and
exercising the healthcheck/volume behavior end-to-end (the remaining open
item from Milestone 4), and (2) live-validating the real OCR backends and
Telegram bot polling path against real data/credentials in a controlled
environment (the remaining open item from Milestones 1 and 3) — everything
else (converters, job orchestration, delivery surfaces, CI, logging,
retention, containerization, cleanup scheduling) is already implemented
and tested end-to-end.
