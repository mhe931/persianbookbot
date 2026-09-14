# Goal: Production OCR Backends and Git Lifecycle

## User Request

Implement and integrate production OCR backend capabilities (PaddleOCR and Vision-LLM via Gemini/Claude) into `src/ocr/` behind the existing `OCREngine` abstraction, preserving `DummyOCREngine` as the offline default, maintain 100% test coverage, and execute the full Git lifecycle (branch -> push -> PR -> merge -> branch cleanup -> main sync).

## Refined Goal

Add opt-in PaddleOCR and Vision-LLM OCR engines to the existing asynchronous OCR architecture without breaking the credential-free offline default. Configuration, optional dependencies, tests, documentation, and factory registration must be complete; then the feature must be delivered through a clean GitHub PR lifecycle and verified on synchronized `main`.

## Acceptance Criteria

- [ ] Criterion 1: Repository starts clean on current `main`, and work is performed on `feature/production-ocr-backends`.
- [ ] Criterion 2: `src/ocr/engine.py` contains `PaddleOCREngine` implementing `OCREngine`, with lazy optional imports, Persian configuration/fallback behavior, usable output mapping, and actionable `OCRError` failures when unavailable.
- [ ] Criterion 3: `src/ocr/engine.py` contains `VisionLLMOCREngine` implementing `OCREngine`, with lazy provider integration for Gemini and Claude, structured raw-page transcription prompts, response parsing, rate-limit mapping to `RateLimitError`, and other provider failures mapped to `OCRError`.
- [ ] Criterion 4: `get_ocr_engine()` registers `dummy`, `tesseract`, `paddle`, and `vision_llm`; unset/unknown-safe defaults preserve `DummyOCREngine` behavior.
- [ ] Criterion 5: Settings/configuration exposes `VISION_LLM_API_KEY`, `VISION_LLM_MODEL` with a sensible default, and `PADDLE_USE_GPU=False`; `.env.example` contains safe non-secret templates.
- [ ] Criterion 6: Dependency metadata documents production OCR options without forcing heavy optional packages into the offline base install, using optional extras or equivalent references.
- [ ] Criterion 7: Tests mock PaddleOCR and Vision-LLM calls, cover factory registration, provider error/rate-limit mapping, retry/backoff behavior, and prove the full suite remains credential-free and offline.
- [ ] Criterion 8: `pytest tests/` passes with all existing and new tests.
- [ ] Criterion 9: `docs/PROJECT_STATUS.md` and `docs/ROADMAP.md` reflect the completed production-backend milestone and remaining limitations.
- [ ] Criterion 10: Feature branch is committed, pushed, PR-created, squash-merged, deleted locally/remotely, and local `main` is synchronized and clean.
- [ ] Criterion 11: Final report includes changed files, test outcome on synchronized `main`, PR URL, merge SHA, blockers, and next roadmap task.

## Scope Boundaries

**In scope:**
- OCR engine implementations and factory registration.
- Safe configuration and dependency metadata.
- Mocked unit tests and documentation updates.
- Full GitHub branch/PR/merge/cleanup lifecycle.

**Out of scope:**
- Downloading model weights or requiring GPU/network access in tests.
- Committing credentials or `.env`.
- Guaranteeing provider-specific production availability without provider credentials.
- Replacing the existing OCR pipeline or output converters.

## Applicable Project Conventions

**Quality gate command:**
- `pytest tests/`

**Commit convention:**
- Conventional Commits, with goal workflow markers: Builder uses `[B]`, Inspector uses `[I]`.
- Builder trailer: `Assisted-by: Claude:Sonnet-4.6`.
- Inspector trailer: `Assisted-by: Claude:Haiku-4.5`.

**Guidelines:**
- [AGENTS.md](../../AGENTS.md)
- [.github/instructions/ocr.instructions.md](../../.github/instructions/ocr.instructions.md)
- Existing configuration and bot guidance under `.github/instructions/`.

**Rules:**
- Keep `DummyOCREngine` as the default when `OCR_ENGINE` is unset.
- Lazy import PaddleOCR and provider SDKs inside optional engine paths.
- Never hardcode credentials; use `Settings` and `.env.example`.
- Use `asyncio.to_thread` for CPU-bound/provider sync work where needed.
- Preserve unrelated changes and do not commit `.env`.
