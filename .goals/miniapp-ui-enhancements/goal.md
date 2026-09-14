# Goal: Mini App UI Enhancements and Sample Evaluation

## User Request

Implement Milestone 2: Telegram Mini App UI enhancements and real-sample validation runner. Build interactive progress tracking, download management, and job polling into `web/`, add an offline-safe sample evaluation script for real Persian PDFs, maintain 100% test coverage (all 71+ tests pass), and complete the Git lifecycle (branch -> commit -> push -> PR -> merge -> branch cleanup -> main sync).

## Refined Goal

Modernize the lightweight vanilla Telegram Mini App with Telegram theme-aware RTL UI, explicit conversion progress, format selection, resilient polling/retry/error states, and download metadata. Add a local sample evaluation CLI that exercises a selected OCR engine without making CI depend on credentials or network access. Validate the result with the complete offline test suite and deliver it through a clean GitHub PR lifecycle.

## Acceptance Criteria

- [ ] Criterion 1: Work starts from clean synchronized `main` and is implemented on `feature/miniapp-ui-enhancements`.
- [ ] Criterion 2: `web/index.html` and `web/style.css` use Telegram theme CSS variables, native RTL/Persian typography, accessible status messaging, and a visual step indicator for Uploaded, Preprocessing, OCR, Generating Documents, and Ready states.
- [ ] Criterion 3: Mini App provides EPUB/DOCX/TXT format-selection controls and download cards with file-size indicators when output metadata is available.
- [ ] Criterion 4: `web/app.js` integrates `window.Telegram.WebApp` lifecycle (`ready`, `expand`, MainButton, haptic feedback) defensively for non-Telegram browsers.
- [ ] Criterion 5: Client-side PDF type/extension/size validation uses the configured 20 MB default, upload progress is visible, status polling handles success/failure/rate-limit/network errors, and retry UI is available.
- [ ] Criterion 6: `tools/evaluate_sample.py` provides an offline-safe CLI for a local PDF and selected engine (`dummy`, `tesseract`, `paddle`, `vision_llm`), reports runtime/page/character/output metrics, and exits cleanly with actionable messages when optional dependencies or credentials are missing.
- [ ] Criterion 7: Tests cover any backend/static-asset/API contract changes and the complete existing suite remains passing offline with no credentials or network.
- [ ] Criterion 8: `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, and `AGENTS.md` document completed Milestone 2 capabilities and evaluation-tool usage.
- [ ] Criterion 9: Feature branch is committed with the requested `[B]` marker/trailer, pushed, PR-created, squash-merged, feature branches deleted, and `main` synchronized and clean.
- [ ] Criterion 10: Final report includes changed files, synchronized-main test output, PR URL, merge SHA, blockers, and next roadmap item.

## Scope Boundaries

**In scope:**
- Vanilla HTML/CSS/JS Mini App enhancements.
- Small backend/API metadata or endpoint additions only when needed to support requested UI behavior.
- Offline-safe local sample evaluation CLI.
- Tests and continuity documentation.
- Full GitHub branch/PR/merge/cleanup lifecycle.

**Out of scope:**
- Adding a frontend framework or bundler.
- Requiring real Telegram credentials, OCR provider keys, model downloads, or network access in tests.
- Persisting jobs beyond the existing in-memory manager.
- Committing `.env`, tokens, or sample copyrighted books.

## Applicable Project Conventions

**Quality gate command:**
- `pytest tests/`

**Commit convention:**
- Builder: `feat(web): [B] enhance Telegram Mini App UI and add evaluation runner`
- Builder trailer: `Assisted-by: Claude:Sonnet-4.6`
- Inspector commits process artifacts with `[I]` and `Assisted-by: Claude:Haiku-4.5`.

**Guidelines:**
- [AGENTS.md](../../AGENTS.md)
- [.github/instructions/bot.instructions.md](../../.github/instructions/bot.instructions.md)
- [.github/instructions/ocr.instructions.md](../../.github/instructions/ocr.instructions.md)

**Rules:**
- Keep the frontend lightweight vanilla HTML/CSS/JS.
- Preserve `DummyOCREngine` as the offline default.
- Never commit `.env` or credentials.
- Preserve unrelated changes and use existing API/job contracts where possible.
