# Goal: Live Validation and OCR Benchmark Reporting

## User Request

Execute Milestone 5 (Production Build/Run Smoke Test & Real Corpus Benchmarking). Build and validate the Docker container on a real Docker host, verify `/api/health` and bind-mount file permissions, benchmark the OCR engines (`tesseract`, `paddle`, `vision_llm`) against a sample Persian scanned PDF using `tools/evaluate_sample.py`, record metrics in `docs/BENCHMARK_RESULTS.md`, and complete the full Git lifecycle.

## Refined Goal

Run the available live container and OCR validations safely, record reproducible benchmark outcomes and environment limitations, and deliver the report through a complete GitHub PR lifecycle. When Docker, OCR binaries/models, licensed sample PDFs, or provider credentials are unavailable, the workflow must skip gracefully, document the exact limitation, and preserve the credential-free offline test gate.

## Acceptance Criteria

- [ ] Criterion 1: Work starts from clean synchronized `main` and uses `feature/live-validation-benchmarks`; no `.env`, credentials, or copyrighted PDFs are staged.
- [ ] Criterion 2: Docker availability is checked. If available, image build/compose startup, `/api/health`, logs, bind-mount write permissions, and compose shutdown are executed; if unavailable, static Docker/Compose audit and an explicit limitation record are produced.
- [ ] Criterion 3: A permitted local/synthetic PDF is evaluated through `tools/evaluate_sample.py` with `dummy`, and available `tesseract`, `paddle`, and `vision_llm` engines are attempted or cleanly skipped with actionable reasons.
- [ ] Criterion 4: `docs/BENCHMARK_RESULTS.md` records hardware/software context, engine availability, runtime/page, character/output metrics, observations, limitations, and recommended production engine setup without embedding secrets or sample PDFs.
- [ ] Criterion 5: `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, and `AGENTS.md` reflect Milestone 5 validation status, benchmark usage, runtime memory guidance, and remaining follow-ups.
- [ ] Criterion 6: `pytest tests/` passes offline with 108+ tests and `DummyOCREngine` default; no benchmark artifacts or credentials enter the repository.
- [ ] Criterion 7: Feature branch is committed with requested `[B]` marker/trailer, pushed, PR-created, squash-merged, feature branches deleted/pruned, and `main` synchronized and clean.
- [ ] Criterion 8: Final report includes Docker status, benchmark metrics/skip reasons, tests, changed files, PR URL, merge SHA, blockers, and next roadmap item.

## Scope Boundaries

**In scope:**
- Live Docker smoke test where the host supports Docker.
- Safe static Docker audit when Docker is unavailable.
- Local/synthetic/permitted sample evaluation with existing CLI.
- Benchmark report and continuity documentation.
- Full GitHub lifecycle.

**Out of scope:**
- Installing Docker, downloading OCR model weights, or acquiring copyrighted books.
- Committing sample PDFs, generated outputs, API keys, bot tokens, or `.env`.
- Claiming provider accuracy when dependencies/credentials are unavailable.
- Product-code rewrites unrelated to validation/reporting.

## Applicable Project Conventions

**Quality gate command:**
- `pytest tests/`

**Commit convention:**
- Builder: `feat(eval): [B] add benchmark results and runtime verification`
- Builder trailer: `Assisted-by: Claude:Sonnet-4.6`
- Inspector commits process artifacts with `[I]` and `Assisted-by: Claude:Haiku-4.5`.

**Guidelines:**
- [AGENTS.md](../../AGENTS.md)
- [.github/instructions/ocr.instructions.md](../../.github/instructions/ocr.instructions.md)

**Rules:**
- Never expose or modify local credentials.
- Keep tests offline and `DummyOCREngine` as default.
- Use only synthetic or explicitly permitted sample material.
- Preserve unrelated worktree changes.
