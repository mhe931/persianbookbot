# Goal: Staging Infrastructure and Cloud Deployment Playbook

## User Request

Execute Milestone 7 (Staging Infrastructure & Cloud Deployment Playbook). Deliver infrastructure-as-code deployment scripts, automated Nginx reverse-proxy configurations with Let's Encrypt TLS automation, a remote deployment validation runbook, update project documentation, and complete the full Git lifecycle.

## Refined Goal

Add a production-oriented deployment bundle that composes the bot behind Nginx with Certbot-managed TLS, persists runtime data, supports non-root UID/GID 1000 permissions, and provides an idempotent Ubuntu/Debian host bootstrap script. Document DNS, deployment, webhook registration, renewal, secret rotation, rollback, and remote validation steps. Verify the configuration statically and through the offline test suite, then deliver it via a complete GitHub PR lifecycle.

## Acceptance Criteria

- [ ] Criterion 1: Work starts from clean synchronized `main` and uses `feature/staging-deploy-infra`; no credentials, private keys, certificates, `.env`, or real domains are committed.
- [ ] Criterion 2: `deploy/docker-compose.prod.yml` defines bot, nginx, and certbot services, internal bot networking, port 80/443 exposure only through nginx, persistent `./data` and TLS/ACME volumes, runtime env injection, and restart/health behavior.
- [ ] Criterion 3: `deploy/nginx/default.conf.template` provides HTTP-to-HTTPS redirect, ACME challenge location, HTTPS proxying for `/` and `/api/` to bot, forwarded headers, and webhook request/header pass-through without hardcoded secrets.
- [ ] Criterion 4: `deploy/setup_host.sh` is idempotent for Ubuntu/Debian hosts, checks/installs Docker appropriately, creates data/config directories with UID/GID 1000-compatible permissions, and generates only safe environment templates.
- [ ] Criterion 5: `docs/DEPLOYMENT_GUIDE.md` gives reproducible VPS/cloud setup, DNS/TLS/Certbot flow, webhook registration, secret rotation, validation, backup, rollback, and troubleshooting steps.
- [ ] Criterion 6: Deployment config tests validate YAML/template integrity, service/environment/volume coverage, proxy headers, ACME handling, and setup-script safety without requiring Docker or network.
- [ ] Criterion 7: README, AGENTS, PROJECT_STATUS, ROADMAP, and relevant instructions reference the deployment bundle and operational limitations.
- [ ] Criterion 8: `pytest tests/` passes offline with 125+ tests, `DummyOCREngine` remains default, and no credentials/artifacts enter Git.
- [ ] Criterion 9: Feature branch is committed with requested `[B]` marker/trailer, pushed, PR-created, squash-merged, feature branches deleted/pruned, and `main` synchronized and clean.
- [ ] Criterion 10: Final report includes changed files, validation, PR URL, merge SHA, blockers, and next operational step.

## Scope Boundaries

**In scope:**
- Production Compose, Nginx template, Certbot service/renewal configuration, host bootstrap script.
- Deployment guide and continuity updates.
- Static configuration tests and existing offline test suite.
- Full GitHub lifecycle.

**Out of scope:**
- Running cloud commands against a real VPS or DNS provider.
- Committing secrets, certificates, private keys, `.env`, or real domain names.
- Replacing the existing application architecture or adding a database/HA system.
- Claiming live TLS/webhook validation without a configured host.

## Applicable Project Conventions

**Quality gate command:**
- `pytest tests/`

**Commit convention:**
- Builder: `feat(deploy): [B] add production compose, nginx reverse proxy, and deployment guide`
- Builder trailer: `Assisted-by: Claude:Sonnet-4.6`
- Inspector commits process artifacts with `[I]` and `Assisted-by: Claude:Haiku-4.5`.

**Guidelines:**
- [AGENTS.md](../../AGENTS.md)
- [.github/instructions/bot.instructions.md](../../.github/instructions/bot.instructions.md)

**Rules:**
- Never commit credentials or real deployment secrets.
- Keep offline tests and `DummyOCREngine`.
- Prefer explicit, idempotent scripts and standard Docker Compose.
- Preserve unrelated changes and do not modify the user's `.env`.
