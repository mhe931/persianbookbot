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

See [`docs/agents/AGENT_GUIDE.md`](docs/agents/AGENT_GUIDE.md) for the full
architecture, subsystem boundaries, and operational runbook.


