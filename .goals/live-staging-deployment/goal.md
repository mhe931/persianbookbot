# Goal: Live cloud staging validation

## User Request

Execute Milestone 9: connect to or provision a Docker-capable Linux staging
host, deploy the production stack, validate TLS/webhook/health/permissions
and real OCR behavior, document observations, and complete the Git lifecycle.

## Refined Goal

Close the remaining live-infrastructure validation gap when suitable host,
domain, and credentials are available. If this environment lacks those
prerequisites, perform every safe offline/static preflight, document the
blockers and exact operator handoff without fabricating live probes or
committing any secret, certificate, PDF, or runtime artifact.

## Acceptance Criteria

- [ ] Docker/Compose and a reachable Linux staging target are verified, or
  their absence is explicitly recorded with reproducible evidence.
- [ ] When infrastructure is available, the production Compose stack is
  bootstrapped with UID/GID 1000 data permissions, TLS is issued/renewed,
  `/healthz` and `/api/health` return 200, and the Telegram webhook is
  verified with no reported errors. Otherwise, the report clearly marks
  these checks as blocked and provides the exact next commands.
- [ ] A permitted real Persian sample is benchmarked through the live stack
  with runtime, memory, page latency, output, and formatting observations, or
  the benchmark is explicitly blocked because no sample/engine/host exists.
- [ ] Continuity documentation records operational observations, limitations,
  and the next staging handoff without exposing credentials or artifacts.
- [ ] Existing offline tests remain green; no live secrets, certificates,
  `.env` files, copyrighted PDFs, or generated runtime data are tracked.
- [ ] Changes use a Builder commit with the required `[B]` marker and trailer,
  are pushed, opened as a PR, squash-merged, and leave synchronized clean
  `main` with the feature branch deleted.

## Scope Boundaries

**In scope:**
- Safe host/context discovery and the documented deployment procedure.
- Live validation only where authorized access and prerequisites already exist.
- Staging observations and continuity documentation.
- Offline regression tests and complete Git lifecycle.

**Out of scope:**
- Guessing cloud providers, domains, SSH hosts, tokens, or credentials.
- Reading, printing, storing, or committing secret values.
- Committing real certificates, private keys, `.env`, book PDFs, or runtime
  output.
- Rewriting application/deployment architecture merely to simulate live
  infrastructure.

## Applicable Project Conventions

**Quality gate command:**
- `$env:PYTHONPATH="$PWD\\src"; .\\.venv\\Scripts\\python.exe -m pytest tests\\`

**Commit convention:**
- Conventional commit with role marker:
  `feat(deploy): [B] complete live cloud staging and production validation`
- Required Builder trailer: `Assisted-by: Claude:Sonnet-4.6`

**Guidelines:**
- `AGENTS.md`
- `.github/instructions/bot.instructions.md`
- `.github/instructions/ocr.instructions.md`
- `.github/instructions/converters.instructions.md`
- `docs/DEPLOYMENT_GUIDE.md`

**Rules:**
- Keep the offline `DummyOCREngine` default and all tests credential-free.
- Never claim live validation without direct evidence.
- Preserve unrelated worktree changes and use existing tooling only.
