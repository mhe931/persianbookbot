# Goal: Telegram Persian PDF Bot Core Pipeline

## User Request

Implement an end-to-end Telegram Bot and Mini App that ingests scanned Persian PDF books, processes Persian OCR/layout extraction, and converts them to EPUB, DOCX, and TXT. Orchestrate multi-agent subtasks, initialize full repository scaffolding, manage Git lifecycle, and provide clear agent documentation.

Context:
- Repo: mhe931/persianbookbot
- Local Path: C:\Users\k430533\Documents\Projects\other\persianbookbot
- Core Workflow: Scanned Persian PDF -> Page Preprocessing/Deskew -> Persian OCR/Text Recognition -> RTL/BiDi Text Layout Assembly -> Output Formatter (EPUB, DOCX, TXT) -> Telegram Bot / Mini App delivery.

Rules:
- Full primary agent ownership: inspect, plan, scaffold, implement, verify, commit.
- Use specialist subagents for parallel execution:
  - Subagent 1 (OCR/Pipeline): Persian text handling, RTL shaping, page-to-text extraction.
  - Subagent 2 (Document Generation): EPUB, DOCX, and TXT builders ensuring proper RTL rendering and embedded Persian fonts.
  - Subagent 3 (Telegram Bot & Mini App): Bot polling/webhook interface, Mini App frontend/API bridge, and user upload/download handlers.
  - Subagent 4 (Verification/QA): Automated tests for pipeline artifacts, layout integrity, and mock file transfers.
- Async Python: Prioritize simplicity over unnecessary complexity; use explicit error handling for rate limits, retries, and concurrent jobs.
- Do not expose credentials or hardcode bot tokens. Use `.env.example` and standard configuration loaders.
- Keep uncommitted/unrelated files intact.

## Refined Goal

Build a complete initial Python scaffold for `persianbookbot` on branch `feature/bot-core-pipeline`. The repository must provide a modular async pipeline for scanned Persian PDF ingestion, page preprocessing/OCR abstraction, RTL/BiDi text assembly, EPUB/DOCX/TXT conversion, Telegram bot delivery, and a lightweight Telegram Mini App API/static client. The implementation must be credential-safe, documented for agent handoffs, covered by tests using generated/dummy fixtures, and committed with logically grouped atomic commits.

## Acceptance Criteria

- [ ] Criterion 1: Repository is on branch `feature/bot-core-pipeline` and contains a Python project scaffold with dependency metadata for Telegram bot, PDF handling, OCR integration, EPUB/DOCX generation, Persian RTL shaping, web API, and tests.
- [ ] Criterion 2: `src/ocr/` implements PDF page extraction/preprocessing interfaces and Persian OCR/text layout assembly with deterministic fallback behavior suitable for tests without requiring live OCR credentials.
- [ ] Criterion 3: `src/converters/` generates TXT, DOCX, and EPUB outputs from Persian/RTL book content and includes explicit RTL/BiDi handling and Persian font configuration hooks.
- [ ] Criterion 4: `src/bot/` implements configuration loading from environment, Telegram file receipt/progress/download handlers, explicit large-file/rate-limit error handling, and Mini App API routes for upload/status/download workflows.
- [ ] Criterion 5: `web/` provides a lightweight Telegram Mini App client that can upload PDFs, poll job status, and download generated artifacts through the local API.
- [ ] Criterion 6: `docs/agents/AGENT_GUIDE.md` documents specialist subagent boundaries, task handoffs, operational runbooks, verification steps, credentials policy, and Git workflow.
- [ ] Criterion 7: `tests/` verifies dummy PDF processing to EPUB/DOCX/TXT, RTL text orientation/formatting artifacts, environment loading, large-file handling, rate-limit fallback behavior, and mocked file transfer flows.
- [ ] Criterion 8: `pytest tests/` passes locally.
- [ ] Criterion 9: Work is committed in logically grouped atomic commits and the final report includes status, changed files, validation, git/PR state, blockers, and next operational step.

## Scope Boundaries

**In scope:**
- Initial production-oriented repository scaffold.
- Python source under `src/bot/`, `src/ocr/`, and `src/converters/`.
- Lightweight Mini App frontend under `web/`.
- Agent documentation under `docs/agents/`.
- Unit/integration tests under `tests/` using mocks or generated fixtures.
- Safe configuration via `.env.example`.
- Local validation with `pytest tests/`.
- Git branch and commits.

**Out of scope:**
- Deploying infrastructure or hosting the bot/API.
- Creating a GitHub pull request unless credentials and repository access are already configured and it is safe to do so.
- Real Telegram bot token provisioning or live Telegram API calls.
- Guaranteeing full OCR accuracy for arbitrary scanned books; this scaffold must expose OCR integration points and deterministic test fallbacks.
- Shipping copyrighted Persian book content or embedding proprietary fonts.

## Applicable Project Conventions

**Quality gate command:**
- `pytest tests/`

**Commit convention:**
- No repository-specific convention discovered.
- Use conventional commits by default.
- Builder commits must include `[B]` marker and `Assisted-by: Claude:Sonnet-4.6`.
- Inspector commits must include `[I]` marker and `Assisted-by: Claude:Haiku-4.5`.
- Session-level final squash command should use `feat(bot): implement Persian PDF bot pipeline`.

**Guidelines:**
- No `AGENTS.md`, `CONSTITUTION.md`, `.agents/guidelines/`, or `.github/guidelines/` files were present during discovery.

**Rules:**
- Preserve unrelated worktree changes. Discovery found the initial worktree clean.
- Do not hardcode credentials or expose bot tokens.
- Use `.env.example` and standard configuration loaders.
- Prioritize simple async Python with explicit handling for rate limits, retries, concurrent jobs, and large uploads.
