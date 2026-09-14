# Goal: Production Staging Webhook and Evaluation Export

## User Request

Transition from local development to production staging on a Docker-capable host. Execute live container validation, benchmark a permitted Persian sample using installed OCR engines, wire Telegram webhook support as an alternative to polling for reverse-proxy deployments, update documentation, and complete the full Git lifecycle.

## Refined Goal

Add secure Telegram webhook support while preserving polling as the default when `WEBHOOK_URL` is unset, extend the sample evaluator with CSV output, and validate/document staging behavior honestly. The implementation must remain credential-safe and offline-testable; available live Docker/OCR capabilities should be exercised, while unavailable host dependencies or credentials must produce explicit, non-secret limitations.

## Acceptance Criteria

- [ ] Criterion 1: Work starts from clean synchronized `main` and uses `feature/production-staging-webhook`; `.env`, tokens, API keys, PDFs, and generated outputs remain untracked.
- [ ] Criterion 2: Settings exposes `webhook_url` and `webhook_secret` safely; `.env.example` documents runtime webhook configuration without values.
- [ ] Criterion 3: FastAPI exposes a webhook route that validates `X-Telegram-Bot-API-Secret-Token`, rejects invalid/missing secrets with 401/403, parses Telegram updates, and dispatches them through the existing application/handler path without exposing tokens.
- [ ] Criterion 4: Polling remains the default when `WEBHOOK_URL` is unset; webhook mode avoids conflicting polling and is compatible with reverse-proxy/container deployment.
- [ ] Criterion 5: `tools/evaluate_sample.py` supports `--csv` output alongside JSON/human output, with clear handling for optional fonts/image libraries and unavailable engines.
- [ ] Criterion 6: Tests cover webhook configuration, secret validation/dispatch, polling fallback, CSV output, and preserve 108+ offline tests with `DummyOCREngine`.
- [ ] Criterion 7: Documentation updates explain webhook reverse-proxy setup, secret injection, polling fallback, evaluator CSV usage, and staging limitations.
- [ ] Criterion 8: Feature branch is committed with requested `[B]` marker/trailer, pushed, PR-created, squash-merged, feature branches deleted/pruned, and `main` synchronized and clean.
- [ ] Criterion 9: Final report includes tests, webhook behavior, CSV/benchmark results or skip reasons, Docker/engine blockers, PR URL, merge SHA, and next deployment step.

## Scope Boundaries

**In scope:**
- Webhook config, secure FastAPI route, Telegram lifecycle integration.
- CSV evaluation export and tests.
- Documentation and staging validation.
- Full GitHub lifecycle.

**Out of scope:**
- Committing or exposing credentials.
- Acquiring copyrighted PDFs or installing heavyweight OCR dependencies without need.
- Replacing polling as the default.
- Rewriting the Telegram handler architecture or unrelated product code.

## Applicable Project Conventions

**Quality gate command:**
- `pytest tests/`

**Commit convention:**
- Builder: `feat(bot): [B] add webhook support and evaluation export capabilities`
- Builder trailer: `Assisted-by: Claude:Sonnet-4.6`
- Inspector commits process artifacts with `[I]` and `Assisted-by: Claude:Haiku-4.5`.

**Guidelines:**
- [AGENTS.md](../../AGENTS.md)
- [.github/instructions/bot.instructions.md](../../.github/instructions/bot.instructions.md)
- [.github/instructions/ocr.instructions.md](../../.github/instructions/ocr.instructions.md)

**Rules:**
- Never log or commit secrets; webhook secret must be header-validated and runtime-injected.
- Keep polling fallback if `WEBHOOK_URL` is unset.
- Preserve offline tests and `DummyOCREngine`.
- Preserve unrelated changes and do not modify the user's `.env`.
