# Goal: Operations Hardening, CI, and Hermetic Tests

## User Request

Implement Milestone 3 (Operations Hardening & CI/CD) and fix test suite `.env` isolation. Deliver a GitHub Actions CI workflow, isolate config unit tests from ambient `.env` files, add structured JSON/console logging, implement clean job persistence/cleanup hooks, update continuity docs, and complete the full Git lifecycle (branch -> commit -> push -> PR -> merge -> branch cleanup -> main sync).

## Refined Goal

Harden the bot operations layer without breaking its simple async architecture: make configuration tests hermetic against ambient dotenv files, add a Python-version matrix CI workflow, provide structured contextual logging, add explicit job retention/temporary-file cleanup hooks, and expose a health endpoint. Update continuity documentation, verify the full offline suite in both the dirty workspace and clean CI-like checkout, and deliver through a complete GitHub PR lifecycle.

## Acceptance Criteria

- [ ] Criterion 1: Work starts from clean synchronized `main` and is implemented on `feature/operations-hardening`; ignored local `.env` is preserved and never staged.
- [ ] Criterion 2: Config tests and/or shared fixtures explicitly disable dotenv loading or isolate environment state so `pytest tests/` passes regardless of an ambient `.env`.
- [ ] Criterion 3: `.github/workflows/ci.yml` triggers on pushes to `main` and PRs targeting `main`, tests Python 3.10/3.11/3.12 on Ubuntu, installs dependencies, runs available linting, and runs `pytest tests/` without credentials.
- [ ] Criterion 4: `src/bot/logging_config.py` provides structured JSON or structured console logging with job_id, user_id, duration, and error context, and is safely configurable without leaking secrets.
- [ ] Criterion 5: `JobManager` has explicit retention/cleanup hooks that prune stale jobs and associated temporary/upload/output files older than a configurable TTL, with safe error handling and tests.
- [ ] Criterion 6: `GET /api/health` exposes a lightweight liveness response and is covered by tests.
- [ ] Criterion 7: Existing behavior remains intact, `DummyOCREngine` remains the default, and the full suite passes offline with no credentials.
- [ ] Criterion 8: `AGENTS.md`, bot instructions, `docs/PROJECT_STATUS.md`, and `docs/ROADMAP.md` document CI, logging, persistence/cleanup, and test-isolation rules.
- [ ] Criterion 9: Feature branch is committed with the requested `[B]` marker/trailer, pushed, PR-created, squash-merged, feature branches deleted, and `main` synchronized and clean.
- [ ] Criterion 10: Final report includes changed files, clean-main test output, PR URL, merge SHA, blockers, and next roadmap item.

## Scope Boundaries

**In scope:**
- CI workflow and existing Python test/lint commands.
- Configuration test isolation and fixtures.
- Structured logging module and integration into bot/job operations.
- Job retention/cleanup hooks and health endpoint.
- Tests and continuity documentation.
- Full GitHub branch/PR/merge/cleanup lifecycle.

**Out of scope:**
- Deleting or modifying the user's local `.env`.
- Adding secrets, external services, databases, or deployment infrastructure.
- Replacing the in-memory job manager with a distributed database.
- Requiring network/API credentials for tests.
- Unrelated OCR, converter, or Mini App feature changes.

## Applicable Project Conventions

**Quality gate command:**
- `pytest tests/`

**Commit convention:**
- Builder: `feat(ops): [B] harden operations, add CI/CD and isolate test config`
- Builder trailer: `Assisted-by: Claude:Sonnet-4.6`
- Inspector commits process artifacts with `[I]` and `Assisted-by: Claude:Haiku-4.5`.

**Guidelines:**
- [AGENTS.md](../../AGENTS.md)
- [.github/instructions/bot.instructions.md](../../.github/instructions/bot.instructions.md)

**Rules:**
- Preserve `DummyOCREngine` and offline behavior.
- Never commit `.env` or credentials.
- Keep async complexity minimal and exceptions explicit.
- Preserve unrelated worktree changes.
