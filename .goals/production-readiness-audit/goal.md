# Goal: Production readiness audit

## User Request

Execute Milestone 8 for `mhe931/persianbookbot`: audit the completed
milestones, verify architectural coherence and security hygiene, run the
offline test suite, create `docs/PRODUCTION_READINESS.md`, update continuity
documentation, and complete the feature-branch pull-request lifecycle.

## Refined Goal

Produce an authoritative, source-anchored production-readiness report for the
Telegram bot, Persian OCR/conversion pipeline, Mini App, and deployment bundle.
The audit must preserve the credential-free offline development contract,
document live-validation constraints honestly, and leave `main` synchronized
with the merged result after the feature branch is removed.

## Acceptance Criteria

- [ ] A comprehensive `docs/PRODUCTION_READINESS.md` covers architecture,
  interfaces/dependencies, security and credential handling, deployment
  pre-flight checks, and known operational constraints.
- [ ] Static audit verifies RTL/BiDi handling, converter font hooks, OCR error
  mapping, polling/webhook exclusivity, webhook secret validation, health and
  cleanup behavior, Mini App configuration/lifecycle/upload handling, and
  Docker/Compose/Nginx/bootstrap coherence.
- [ ] `pytest tests/` passes with at least the existing 157 tests, offline and
  without credentials; no tracked secrets, keys, certificates, PDFs, or
  generated runtime artifacts are introduced.
- [ ] `README.md`, `AGENTS.md`, `docs/PROJECT_STATUS.md`, and
  `docs/ROADMAP.md` reflect the audit and operational-maintenance handoff.
- [ ] Changes are committed using the required conventional `[B]` marker and
  `Assisted-by: Claude:Sonnet-4.6` trailer, pushed, opened as a pull request,
  squash-merged, and synchronized to a clean `main` with the feature branch
  deleted.

## Scope Boundaries

**In scope:**
- Read-only verification of all completed application and deployment layers.
- Production-readiness documentation and continuity-documentation updates.
- Offline tests and Git/secret-hygiene checks.
- The requested feature branch, pull request, merge, cleanup, and main sync.

**Out of scope:**
- Architectural rewrites or new runtime capabilities unrelated to audit
  findings.
- Live Docker/VPS/TLS/Telegram/OCR-provider execution where required host,
  network, domain, or credentials are unavailable.
- Committing credentials, certificates, private keys, copyrighted book
  material, or runtime data.

## Applicable Project Conventions

**Quality gate command:**
- `$env:PYTHONPATH="$PWD\\src"; .\\.venv\\Scripts\\python.exe -m pytest tests\\`
- Use existing repository tooling only; do not add test or lint dependencies.

**Commit convention:**
- Conventional commits with a role marker: `type(scope): [B] description`,
  title no longer than 72 characters.
- Required trailer: `Assisted-by: Claude:Sonnet-4.6`

**Guidelines:**
- `AGENTS.md`
- `.github/instructions/bot.instructions.md`
- `.github/instructions/ocr.instructions.md`
- `.github/instructions/converters.instructions.md`
- `docs/agents/AGENT_GUIDE.md`

**Rules:**
- Keep `DummyOCREngine` as the deterministic, credential-free default.
- Never expose or commit secrets; `.env` remains runtime-only and ignored.
- Preserve existing behavior and unrelated worktree changes.
- Document unavailable live infrastructure rather than claiming it was tested.
