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

See [`docs/agents/AGENT_GUIDE.md`](docs/agents/AGENT_GUIDE.md) for the full
architecture, subsystem boundaries, and operational runbook.

