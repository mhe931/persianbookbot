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
