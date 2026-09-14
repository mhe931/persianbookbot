# Roadmap

This roadmap lists the next milestones after the verified core pipeline
scaffold (see `docs/PROJECT_STATUS.md` for what already exists and passes
its 46-test suite).

## Milestone 1 — Real OCR backend

The default `DummyOCREngine` is deterministic placeholder text; the next
milestone is real Persian text recognition:

- Finish validating `TesseractOCREngine` (`OCR_ENGINE=tesseract`) against
  real scanned Persian book pages; document required Tesseract + `fas`
  language-data installation steps.
- Evaluate and integrate a **PaddleOCR** backend (strong multilingual/Arabic
  script support) as an additional pluggable `OCREngine` implementation.
- Evaluate a **Vision-LLM based** OCR backend (e.g. a vision-capable model
  prompted for transcription) as a higher-accuracy option for degraded
  scans, behind the same `OCREngine` interface and `OCR_ENGINE` switch.
- Add accuracy/confidence benchmarking against a small real-world Persian
  scanned-book test corpus (kept out of the committed offline test suite,
  or clearly marked as an opt-in/slow test group).
- Keep `DummyOCREngine` as the permanent zero-credential default for CI and
  local development regardless of which real engines are added.

## Milestone 2 — Mini App UI enhancements

The current `web/` frontend is a minimal vanilla HTML/CSS/JS scaffold:

- Improve upload UX: drag-and-drop, upload progress bar wired to
  `/api/status/{job_id}`, and clearer error states (oversized file,
  non-PDF, rate-limited, failed jobs).
- Add a job history/list view backed by `JobManager.list_jobs()` (already
  available server-side, not yet exposed via a dedicated endpoint/UI).
- Add format selection and inline preview before download.
- Improve RTL/Persian-language presentation of the Mini App itself (labels,
  layout direction) to match the RTL content it produces.
- Consider a lightweight framework or design system if the vanilla
  implementation becomes hard to maintain.

## Milestone 3 — Bot & operations hardening

- Add a `.github/workflows/` CI pipeline running `pytest tests/` on every
  push/PR (none exists yet — currently run manually).
- Add structured logging/observability for job failures and rate-limit
  events across `src/bot/jobs.py` and the OCR pipeline.
- Live-validate the Telegram bot polling path end-to-end with a real
  `BOT_TOKEN` in a controlled environment (currently only unit-tested with
  mocks).
- Persist `ConversionJob` state (currently in-memory only) if multi-process
  or restart-safe operation becomes a requirement.
- Document a font-licensing/bundling story for `PERSIAN_FONT_NAME` if a
  specific font needs to ship with deployments.

## Milestone 4 — Deployment

- Containerize the API/bot process (`src/bot/main.py`) for reproducible
  deployment.
- Define hosting/runtime requirements (persistent `UPLOAD_DIR`/`OUTPUT_DIR`,
  webhook vs. polling mode via `WEBHOOK_URL`).
- Out of scope for the current documentation-and-lifecycle milestone; see
  `AGENTS.md` scope boundaries.

## Prioritization notes

Milestone 1 (real OCR) is the highest-value next step since it is the only
gap between "pipeline scaffold" and "usable product" — everything else
(converters, job orchestration, delivery surfaces) is already implemented
and tested end-to-end against the pluggable `OCREngine` interface.
