# Benchmark Results — Milestone 5 (Production Build/Run Smoke Test & Real Corpus Benchmarking)

_Recorded: 2026-09-14_

This document records the live-validation attempt for Milestone 5
(`docs/ROADMAP.md`): building/running the Docker container against a real
engine, verifying bind-mount permissions, and benchmarking the OCR engines
(`tesseract`, `paddle`, `vision_llm`) against a sample PDF via
`tools/evaluate_sample.py`. **No Docker engine and no optional OCR
dependency/credential were available in this environment**, so this run
produced a static audit + a fully offline `dummy`-engine benchmark, with
clean, actionable skip reasons for every other engine — no results are
fabricated or estimated.

## Environment / hardware / software context

| Item | Value |
| --- | --- |
| OS | Microsoft Windows 11 Enterprise 64-bit, Build 26200 |
| CPU | AMD Ryzen 3 7335U with Radeon Graphics — 4 cores / 8 logical processors |
| RAM | ~14.8 GiB total (15134 MiB) |
| Python | 3.11.15 |
| PyMuPDF (`pymupdf`) | 1.28.2 |
| Pillow | 12.3.0 |
| reportlab | 5.0.0 |
| Docker CLI | **Not installed** (`docker` not found on `PATH`) |

## Docker / compose validation

**Status: static audit only — no Docker engine available.**

`docker --version` / `docker info` both fail with
`CommandNotFoundException` — the `docker` CLI is not installed in this
environment, so no image build, `docker compose up`, `/api/health` probe,
log inspection, or bind-mount permission check could be executed live.
This mirrors the same limitation recorded for Milestone 4
(`docs/PROJECT_STATUS.md`) — it has not yet been resolved because no
environment with a working Docker daemon has been available for either
milestone's authoring session.

Static checks performed instead (all pass):

- **`Dockerfile`** — instruction-by-instruction review: valid two-stage
  build (`builder` → `runtime`), non-root `app` user created with fixed
  `--uid 1000 --gid 1000`, `/app/data/{uploads,output}` created and
  `chown app:app` + `chmod 750` **before** `USER app` is set, `HEALTHCHECK`
  targets `GET /api/health` via `curl`, and no `BOT_TOKEN`/
  `VISION_LLM_API_KEY` values are baked into image layers (defaults mirror
  `bot.config.Settings`, both left unset).
- **`docker-compose.yml`** — parsed with `yaml.safe_load()`: single `bot`
  service with `build.context/dockerfile`, `ports: ["8000:8000"]`,
  `volumes: ["./data:/app/data"]`, `env_file: [".env"]` (runtime-only
  secret injection, never committed), `restart: unless-stopped`, and a
  `healthcheck` block matching the Dockerfile's `HEALTHCHECK`. All
  required keys present and well-formed.
- **Bind-mount UID/GID 1000 write permissions** — could not be verified
  live (requires an actual container process writing to a host-mounted
  `./data`). Static review confirms the *intent* is correct (image runs as
  UID/GID 1000 and pre-creates/owns `/app/data/*` with `chmod 750` before
  dropping root), but the actual host-side permission behavior — especially
  relevant on this Windows host, where Docker Desktop's WSL2/Hyper-V VM
  backend translates bind-mount ownership differently than a native Linux
  Docker host — remains unverified. **This is the single highest-priority
  remaining follow-up** (see Recommendations below and `docs/ROADMAP.md`).

No image was built, no container was started, and no logs were produced —
there is nothing to "shut down."

## OCR engine benchmark (`tools/evaluate_sample.py`)

A synthetic, non-copyrighted 5-page PDF was generated in-memory with the
existing test fixture helper (`tests/fixtures/pdf_factory.py::make_sample_pdf_bytes`,
already used by `tests/test_tools_evaluate_sample.py`) and written to the
git-ignored `data/` directory (never staged/committed). No real book
content, no licensed material, and no Persian-language raster text is in
this fixture — it only exercises pipeline/CLI plumbing, so no accuracy
claim is made for `dummy`, and no engine invocation may claim real
recognition without the fixture actually containing scanned Persian text.

Command:

```powershell
$env:PYTHONPATH = "$PWD\src"
python tools\evaluate_sample.py data\eval_input\synthetic_sample.pdf --engine dummy --output-dir data\eval_output\dummy --json
```

### `dummy` (fully offline, zero credentials) — ✅ ran successfully

```json
{
  "pdf_path": "data\\eval_input\\synthetic_sample.pdf",
  "engine": "dummy",
  "dpi": 200,
  "runtime_seconds": 1.074,
  "page_count": 5,
  "pages_per_second": 4.654,
  "total_characters": 80,
  "average_characters_per_page": 16.0,
  "average_confidence": 0.99,
  "output_sizes": { "txt": 221, "docx": 36795, "epub": 4188 }
}
```

- Peak process RSS during this run (parent + child, measured with
  `psutil`, polled every 20 ms): **~83.4 MiB** for a 5-page PDF rendered at
  200 DPI. This is a `dummy`-engine, small-fixture baseline for pipeline
  overhead (PDF rendering + `python-docx`/`ebooklib` writers); real OCR
  engines (`tesseract`/`paddle`/`vision_llm`) will add their own model/
  runtime memory on top of this baseline (see Recommendations).
- Exit code `0`; no network access; no credentials read or required.

### `tesseract` — ⏭️ cleanly skipped (missing optional dependency)

```json
{
  "error": "OCR engine 'tesseract' unavailable: pytesseract not installed; install it or use OCR_ENGINE=dummy",
  "engine": "tesseract"
}
```

Exit code `2` (`EXIT_ENGINE_UNAVAILABLE`). `pytesseract` is not installed
in this environment (`pip show pytesseract` reports nothing found) and no
attempt was made to install it (out of scope — see Scope Boundaries).

### `paddle` — ⏭️ cleanly skipped (missing optional dependency)

```json
{
  "error": "OCR engine 'paddle' unavailable: paddleocr not installed; install the 'paddle' extra (pip install persianbookbot[paddle]) or use OCR_ENGINE=dummy",
  "engine": "paddle"
}
```

Exit code `2`. `paddleocr` is not installed (`pip show paddleocr` reports
nothing found); it is a heavyweight dependency (pulls in `paddlepaddle`)
and was intentionally not installed per the goal's scope boundaries.

### `vision_llm` — ⏭️ cleanly skipped (missing credential)

```json
{
  "error": "OCR engine 'vision_llm' unavailable: VISION_LLM_API_KEY not set; configure it in .env or use OCR_ENGINE=dummy",
  "engine": "vision_llm"
}
```

Exit code `2`. `httpx` (the only runtime dependency `VisionLLMOCREngine`
needs) **is** installed, but `VISION_LLM_API_KEY` is not set in the
process environment. Consistent with the credential-safety rule, this
check only inspected `os.environ` — the local `.env` file was never read,
opened, or inspected by this workflow, so any real key a developer may
have configured there was never touched or exposed.

## Observations

- The CLI's exit-code contract (`0` success, `1` usage, `2` engine
  unavailable, `3` pipeline failure) behaved exactly as documented in
  `tools/evaluate_sample.py`'s module docstring and
  `.github/instructions/ocr.instructions.md` for all four engines.
- No stack traces, secrets, or partial credentials were ever printed —
  every unavailable-engine case produced a single-line, actionable JSON
  `error` message.
- The synthetic fixture is intentionally non-representative of real
  scanned Persian book pages (it is vector text drawn by `reportlab`, not
  a raster scan), so `dummy`'s ~80-character/5-page output and the
  unexercised real engines carry **no accuracy signal** — this run
  validates the *tooling/reporting pipeline*, not OCR quality.

## Limitations

1. **No Docker engine available** — image build, `docker compose up`,
   `/api/health` liveness probe, log inspection, and live bind-mount
   permission verification could not be performed. Static Dockerfile/
   compose audit only (see above).
2. **No `pytesseract`/`paddleocr` installed** — `tesseract`/`paddle`
   engines could only be exercised for their clean-failure path, not real
   recognition. Installing them (plus, for `paddle`, the multi-hundred-MB
   `paddlepaddle` wheel) was out of scope for this validation pass.
3. **No `VISION_LLM_API_KEY` configured** — `vision_llm` could only be
   exercised for its clean-failure path. No key was requested, generated,
   or read from `.env`.
4. **No licensed/real scanned Persian PDF available** — only the
   synthetic, non-copyrighted `reportlab`-generated fixture was used, so
   no character-accuracy/WER-style metric could be computed for any
   engine, dummy included.
5. This machine is Windows, not the Linux target the production Docker
   image runs on — even once Docker is available, first validation should
   still happen on (or via a VM/CI runner matching) a Linux Docker host to
   avoid WSL2/Hyper-V-specific bind-mount permission quirks masking a real
   issue (or a Windows-only workaround masking a real Linux-host bug).

## Recommendations for production engine setup

- **Docker**: run the existing static-audit-passed `Dockerfile`/
  `docker-compose.yml` through one real `docker compose up --build` pass
  on a Linux Docker host (or Linux CI runner) before any production
  rollout; confirm `GET /api/health` returns `200` and that a test file
  written by the container to `./data/uploads` is owned by host UID/GID
  1000 (or readable by the deploying operator) as designed.
- **`tesseract`**: cheapest real engine to validate first — only needs
  the `tesseract-ocr`/`tesseract-ocr-fas` system packages (already in the
  Docker image) and `pip install pytesseract`; no credentials, no GPU.
  Good default for a self-hosted deployment with no LLM budget.
- **`paddle`**: budget \~1–2 GB of additional resident memory (model
  weights + `paddlepaddle` runtime) on top of the ~83 MiB `dummy` baseline
  measured above, plus first-run model-download time/bandwidth; validate
  on the target CPU architecture (`PADDLE_USE_GPU=false` unless a GPU is
  actually provisioned) before committing to it for production Persian
  OCR.
- **`vision_llm`**: needs a `VISION_LLM_PROVIDER`
  (`gemini`/`claude`)/`VISION_LLM_API_KEY` pair injected via `.env`/secrets
  manager only, never committed; expect materially higher per-page
  latency and a per-page cost — benchmark against a real, licensed
  Persian scanned-book sample (never the synthetic fixture used here)
  before choosing it as the production default, and set
  `--max-retries`/`--backoff-seconds` (or the equivalent pipeline
  defaults) to tolerate provider rate limits.
- **Memory sizing**: the ~83 MiB peak RSS measured here is a `dummy`-only,
  5-page/200-DPI floor. Size any production container's memory limit for
  the *real* engine chosen (see per-engine notes above) plus headroom for
  concurrent jobs, since `bot.jobs.JobManager` processes jobs
  independently and does not currently cap in-flight concurrency.
