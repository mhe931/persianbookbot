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
As of this writing the suite has **71 passing tests** and requires no
network access, real Telegram token, or real OCR backend — the default
`DummyOCREngine` is fully deterministic and offline.

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
- `src/bot/` — env-driven config (`config.py`), async job orchestration
  (`jobs.py`), Telegram handlers (`telegram_handlers.py`), FastAPI Mini App
  backend (`api.py`), and the process entrypoint (`main.py`).
- `web/` — static Telegram Mini App frontend (vanilla HTML/CSS/JS).
- `tests/` — pytest suite covering pipeline, converters, bot/API, and
  integration, using generated/dummy fixtures only.

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
