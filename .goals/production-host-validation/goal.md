# Goal: Production host validation

## User Request

Execute Milestone 10: deploy the production Compose bundle on an active
Docker-capable staging host, verify live health endpoints, UID/GID 1000
volume permissions, a sample PDF conversion, runtime metrics, and complete
the Git lifecycle.

## Refined Goal

Run the production-host validation procedure only against an authorized,
available Docker host. Capture reproducible container, probe, volume, and
conversion evidence. If no such host is available, perform safe local
preflight and document the exact blocker and operator handoff rather than
fabricating live results.

## Acceptance Criteria

- [ ] Docker Engine/Compose and a designated staging host are verified, or
  their absence is explicitly documented with command evidence.
- [ ] When available, the production stack is started and torn down cleanly,
  `/healthz` and `/api/health` are probed, UID/GID 1000 bind-mount behavior is
  verified, and a permitted synthetic/sample PDF completes through the live
  API with runtime metrics. Otherwise each live check is marked blocked.
- [ ] `docs/LIVE_STAGING_VALIDATION.md`, `docs/PROJECT_STATUS.md`, and
  `docs/ROADMAP.md` record the dated execution attempt, metrics, and exact
  next handoff; no result is claimed without evidence.
- [ ] The offline suite remains green with at least 157 passing tests and no
  staging secrets, certificates, `.env`, PDFs, or generated outputs tracked.
- [ ] Changes use the requested Builder commit/trailer, are pushed and
  squash-merged through a PR, and leave clean synchronized `main` with the
  feature branch deleted.

## Scope Boundaries

**In scope:**
- Safe local/authorized-host runtime checks and production-stack validation.
- Documentation of live evidence or precise blockers.
- Offline regression tests, artifact hygiene, and Git lifecycle.

**Out of scope:**
- Guessing or scanning arbitrary SSH hosts, cloud resources, domains, or
  credentials.
- Reading, logging, or committing secret values.
- Committing certificates, private keys, `.env`, copyrighted PDFs, or runtime
  output.
- Application architecture rewrites unrelated to observed runtime failures.

## Applicable Project Conventions

**Quality gate command:**
- `$env:PYTHONPATH="$PWD\\src"; .\\.venv\\Scripts\\python.exe -m pytest tests\\`

**Commit convention:**
- `feat(deploy): [B] verify production container runtime and live endpoints`
- Required trailer: `Assisted-by: Claude:Sonnet-4.6`

**Guidelines:**
- `AGENTS.md`
- `.github/instructions/bot.instructions.md`
- `.github/instructions/ocr.instructions.md`
- `.github/instructions/converters.instructions.md`
- `docs/DEPLOYMENT_GUIDE.md`

**Rules:**
- Preserve the credential-free `DummyOCREngine` offline default.
- Never claim live validation without direct command evidence.
- Keep secrets and runtime artifacts outside Git.
