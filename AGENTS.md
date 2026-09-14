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

See `docs/ARCHITECTURE.md` for the full breakdown and `docs/PROJECT_STATUS.md`
for current milestone status.

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
As of this writing the suite has **108 passing tests** and requires no
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
- `src/bot/` — env-driven config (`config.py`), structured logging
  (`logging_config.py`), async job orchestration (`jobs.py`, including
  `JobManager.cleanup_stale_jobs()` retention hooks), Telegram handlers
  (`telegram_handlers.py`), FastAPI Mini App backend (`api.py`, including
  `GET /api/health`), and the process entrypoint (`main.py`, including
  `periodic_cleanup_worker()` — a configurable hourly-by-default background
  task that calls `default_job_manager.cleanup_stale_jobs()` for the
  lifetime of the process, cancelled cleanly on shutdown).
- `web/` — static Telegram Mini App frontend (vanilla HTML/CSS/JS):
  Telegram theme CSS variables, RTL/Persian typography, a five-step
  progress indicator, format-selection toggles, download cards with
  file-size indicators, and defensive `window.Telegram.WebApp`
  lifecycle/MainButton/haptics integration.
- `tools/evaluate_sample.py` — offline-safe local CLI that runs a single
  PDF through the real pipeline/converters (`dummy`/`tesseract`/`paddle`/
  `vision_llm` engine selection) and reports runtime/page/character/output
  metrics; never required for `pytest tests/` and never requires network
  access with the default `dummy` engine.
- `tests/` — pytest suite covering pipeline, converters, bot/API, the
  Mini App static assets, the evaluation CLI, and integration, using
  generated/dummy fixtures only.
- `Dockerfile` / `docker-compose.yml` / `.dockerignore` — multi-stage,
  non-root (UID/GID 1000) container build and compose orchestration for
  deployment; see "Containerization / deployment" below.

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
