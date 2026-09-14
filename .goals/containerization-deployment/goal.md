# Goal: Containerization, Deployment Readiness, and Scheduled Cleanup

## User Request

Implement Milestone 4 (Containerization & Deployment Readiness). Deliver production Docker configurations, docker-compose orchestration, volume mounts, permission handling for runtime data directories, a periodic background cleanup scheduler in `bot.main`, update documentation, and complete the full Git lifecycle (branch -> commit -> push -> PR -> merge -> branch cleanup -> main sync).

## Refined Goal

Package the Persian PDF bot for repeatable non-root container deployment with a multi-stage Docker build, compose orchestration, persistent upload/output volumes, health checks, and runtime environment injection. Wire the existing stale-job cleanup into a configurable periodic lifecycle worker, document operations and deployment usage, validate the Docker configuration and full offline tests, then deliver through a complete GitHub PR lifecycle.

## Acceptance Criteria

- [ ] Criterion 1: Work starts from clean synchronized `main` and is implemented on `feature/containerization-deployment`; `.env` and secrets remain untracked and untouched.
- [ ] Criterion 2: `Dockerfile` is a valid multi-stage Python 3.11-slim build with required runtime libraries, non-root user, correct ownership/permissions for `/app/data/uploads` and `/app/data/output`, safe environment defaults, and `/api/health` healthcheck.
- [ ] Criterion 3: `docker-compose.yml` defines the bot service, port 8000, persistent `./data` volume, runtime `.env` injection without committing `.env`, restart policy, and healthcheck.
- [ ] Criterion 4: `.dockerignore` excludes VCS files, virtual environments, caches, tests, `.env`, bytecode, and runtime data.
- [ ] Criterion 5: `src/bot/main.py` starts a configurable periodic cleanup worker invoking `default_job_manager.cleanup_stale_jobs()` hourly by default, with explicit cancellation/shutdown handling and no credential requirement.
- [ ] Criterion 6: Tests cover scheduler behavior or runtime settings, the full existing suite remains offline and green, and `DummyOCREngine` remains the default.
- [ ] Criterion 7: README, AGENTS, project status, roadmap, and relevant instructions document Docker build/run/compose usage, volume permissions, environment injection, health checks, and cleanup scheduling.
- [ ] Criterion 8: Feature branch is committed with the requested `[B]` marker/trailer, pushed, PR-created, squash-merged, deleted/pruned, and `main` synchronized and clean.
- [ ] Criterion 9: Final report includes changed files, synchronized-main pytest output, Docker/compose validation, PR URL, merge SHA, blockers, and next roadmap task.

## Scope Boundaries

**In scope:**
- Dockerfile, docker-compose.yml, .dockerignore.
- Periodic cleanup scheduler in `src/bot/main.py`.
- Runtime settings/tests needed for deployment.
- Deployment documentation and continuity updates.
- Full GitHub branch/PR/merge/cleanup lifecycle.

**Out of scope:**
- Committing `.env`, tokens, API keys, or model weights.
- Building/pushing container images to a registry unless explicitly configured and safe.
- Replacing the in-memory job manager or adding external databases.
- Requiring credentials or network access for tests.
- Unrelated OCR, converter, or Mini App changes.

## Applicable Project Conventions

**Quality gate command:**
- `pytest tests/`

**Commit convention:**
- Builder: `feat(deploy): [B] add Dockerfile, compose, and periodic cleanup scheduler`
- Builder trailer: `Assisted-by: Claude:Sonnet-4.6`
- Inspector commits process artifacts with `[I]` and `Assisted-by: Claude:Haiku-4.5`.

**Guidelines:**
- [AGENTS.md](../../AGENTS.md)
- [.github/instructions/bot.instructions.md](../../.github/instructions/bot.instructions.md)

**Rules:**
- Use non-root container execution and explicit data-directory ownership.
- Keep `DummyOCREngine` and credential-free offline tests.
- Use runtime environment injection; never bake secrets into images.
- Preserve unrelated changes and do not modify the user's local `.env`.
