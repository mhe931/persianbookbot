# Goal: Git Lifecycle and Project Continuity Documentation

## User Request

Complete the full Git lifecycle (push -> PR -> merge -> branch cleanup -> main sync) for the verified Persian PDF bot scaffold on `feature/bot-core-pipeline`, establish standard project continuity documentation (`AGENTS.md`, `docs/PROJECT_STATUS.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`), and scaffold path-scoped instructions.

Context:
- Repo: `mhe931/persianbookbot`
- Workspace: `C:\Users\k430533\Documents\Projects\other\persianbookbot`
- Current State: Pipeline code and tests verified (46 passing tests). Commits exist on local branch `feature/bot-core-pipeline`. Remote is `origin` pointing to `mhe931/persianbookbot`. Default branch is `main`.

Rules:
- Full primary agent autonomy: discover Git/GitHub CLI status, write continuity files, push, create PR, merge, clean up branch.
- Never push raw secrets or `.env` files.
- Keep uncommitted/unrelated files intact. Inspect working tree before executing Git actions.
- Enforce clean git lifecycle: local branch -> remote push -> PR creation via `gh` -> merge to `main` -> delete remote and local feature branch -> pull latest `main`.
- Use subagents if helpful for drafting layered `.github/instructions/*.instructions.md` documents.

## Refined Goal

Finalize the verified Persian PDF bot scaffold by adding project continuity documentation and completing the repository GitHub lifecycle. The feature branch must be documented, committed, pushed, opened as a PR against `main`, merged, cleaned up locally and remotely, and synchronized back to `main`. The final repository state must be clean on `main`, with tests passing and the requested documentation present.

## Acceptance Criteria

- [ ] Criterion 1: Starting state is inspected, including `git status`, branch/remotes, GitHub CLI authentication, and absence of raw secrets or `.env` files in tracked changes.
- [ ] Criterion 2: `AGENTS.md` documents global project rules, setup, pytest command, architecture summary, Git conventions, and credential invariants.
- [ ] Criterion 3: `docs/PROJECT_STATUS.md` records the current milestone, 46 passing tests, known limitations including dummy OCR default, and operational readiness.
- [ ] Criterion 4: `docs/ARCHITECTURE.md` documents the pipeline diagram `PDF -> render -> deskew -> OCR -> RTL assemble -> EPUB/DOCX/TXT -> Bot/API` and key module responsibilities.
- [ ] Criterion 5: `docs/ROADMAP.md` lists next milestones including real PaddleOCR/Vision-LLM integration and Mini App UI enhancements.
- [ ] Criterion 6: `.github/instructions/bot.instructions.md`, `.github/instructions/ocr.instructions.md`, and `.github/instructions/converters.instructions.md` exist with path-scoped `applyTo` metadata and relevant engineering guidance.
- [ ] Criterion 7: New continuity documentation is committed on `feature/bot-core-pipeline` with message `docs: establish agent continuity and architecture specs`.
- [ ] Criterion 8: `feature/bot-core-pipeline` is pushed to `origin`, a PR is created against `main`, and the PR is merged, preferably with squash merge, deleting the remote feature branch.
- [ ] Criterion 9: Local repository is switched to `main`, synchronized with `origin/main`, local feature branch is deleted, `git status` is clean, and the active branch is `main`.
- [ ] Criterion 10: `pytest tests/` passes on synchronized `main`.
- [ ] Criterion 11: Final delivery includes PR URL, merge commit SHA, active branch confirmation, blocker status, and next milestone.

## Scope Boundaries

**In scope:**
- Documentation files requested by the user.
- Path-scoped GitHub Copilot instruction files.
- GitHub branch push, PR creation, merge, branch cleanup, and main sync.
- Local post-merge test verification.

**Out of scope:**
- Product code changes beyond documentation/instruction additions unless strictly required to fix documentation validation.
- Adding secrets, `.env`, or live credentials.
- Changing the already verified bot/OCR/converter behavior.
- Creating deployment infrastructure.

## Applicable Project Conventions

**Quality gate command:**
- `pytest tests/`

**Commit convention:**
- Existing project documentation uses conventional commits.
- The requested documentation commit must be exactly titled `docs: establish agent continuity and architecture specs`.

**Guidelines:**
- Existing guide: `docs/agents/AGENT_GUIDE.md`.

**Rules:**
- GitHub CLI is authenticated as `mhe931` with repo/workflow scopes during discovery.
- Remote `origin` points to `git@github.com:mhe931/persianbookbot.git`.
- Do not commit `.env` or raw secrets.
- Preserve unrelated worktree changes; discovery found the tree clean before this goal was created.
