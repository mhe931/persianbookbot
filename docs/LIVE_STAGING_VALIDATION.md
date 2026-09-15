# Live Staging Validation Report — Milestone 9

_Audit date: 2026-09-15. Prepared on branch `feature/live-staging-deployment`,
forked from `main` at commit `868be4c`. This is a read-only prerequisite
inspection: no application or deployment code was changed to produce this
report, no secret value was printed or read, no arbitrary host was scanned,
and no cloud resource was provisioned._

## Executive summary

This milestone re-attempts the single open gap restated by every prior
milestone (5 through 8): **live infrastructure validation** of the
`deploy/docker-compose.prod.yml` stack — TLS issuance, `/healthz`/
`/api/health` over HTTPS, Telegram webhook delivery, UID/GID 1000
bind-mount permissions on a real filesystem, and a real-sample OCR
benchmark. The result is unchanged from Milestones 5–8: **this authoring
environment still has no Docker engine, no WSL, no reachable Linux host
designated for this project, no DNS record, and no scanned Persian PDF
sample**, so every live check below is explicitly blocked with
reproducible evidence rather than fabricated. All safe, non-destructive
local discovery checks were performed and are recorded below, together
with the exact operator commands needed to complete each blocked item on
a real host.

## Method

Every check below is either:

1. A command run directly in this session (exact command and full/trimmed
   output recorded), or
2. A static source read of `Dockerfile` / `deploy/*` / `.env.example` /
   `tests/test_deploy_configs.py` cross-checked against the claim.

No `.env` value, API token, SSH private key, or certificate content was
printed at any point. Where a local secret's **presence** (not value) was
relevant, only the key name and a `SET`/`EMPTY` marker were logged.

## 1. Docker / Compose engine

**Status: blocked — not installed.**

```
> where docker
INFO: Could not find files for the given pattern(s).
> docker version
'docker' is not recognized as an internal or external command...
> docker context ls
'docker' is not recognized as an internal or external command...
> docker compose version / docker-compose version
'docker'/'docker-compose' is not recognized...
```

No Docker Engine, Docker Desktop, or standalone `docker-compose` binary is
installed or on `PATH` in this Windows session. No Docker context is
configured (the command itself doesn't exist to list any). This is the
same constraint recorded in `docs/BENCHMARK_RESULTS.md` (Milestone 5) and
`docs/PRODUCTION_READINESS.md` (Milestone 8) — still unresolved.

## 2. WSL (potential local Linux target)

**Status: blocked — not installed.**

```
> wsl -l -v
The Windows Subsystem for Linux is not installed. You can install by
running 'wsl.exe --install'. For more information please visit
https://aka.ms/wslinstall
```

WSL is not present, so there is no local Linux subsystem available as a
Docker-capable target either.

## 3. Configured SSH remote targets

**Status: two SSH hosts are configured on this machine, but neither is a
persianbookbot deployment target — correctly out of scope, not used.**

`~/.ssh/config` contains two `Host` aliases (`aml-pulsar-shape`,
`acerserver`) with their `HostName`/`Port`/`User`/`IdentityFile` — no
passwords or key material is in the config file itself. Both are
pre-existing hosts for unrelated projects (an ML/GPU host and a personal
server) with no reference anywhere in this repository, `.env`, or
`docs/DEPLOYMENT_GUIDE.md` designating either as a persianbookbot staging
target. Per this milestone's explicit scope boundary ("do not guess or
scan arbitrary hosts"), **neither host was contacted, probed, or used**.
No SSH connection was attempted. If an operator wants to use one of these
(or any other host) for persianbookbot staging, it must be explicitly
provisioned/designated by a human first (see §8 handoff).

## 4. Cloud provider CLI tooling

**Status: `az` CLI is installed and authenticated; no persianbookbot-
specific resource is designated, so no resource was provisioned.**

```
> az account show   # exits 0, prints an existing subscription (tenant/sub IDs only, no secrets)
> aws / gcloud / doctl / flyctl / kamal   # none found on PATH
```

The Azure CLI (`C:\Users\k430533\azure-cli\bin\az.cmd`) is installed and
already logged into a personal/organizational subscription used across
this operator's other, unrelated projects. **No resource group, VM,
domain, or DNS zone in that subscription is designated for
persianbookbot**, and this milestone's scope boundary explicitly forbids
provisioning cloud resources without pre-existing, explicit configured
access for this project. No VM, IP, or DNS record was created. Standing
up a real VPS for this bot remains an explicit human decision — see §8.

## 5. Local secret/config presence (values not read)

**Status: local dev `.env` exists (git-ignored); domain/webhook
prerequisites are absent.**

```
> Test-Path .env                         # True
> git check-ignore -v .env               # .gitignore:151:.env  .env  (confirmed ignored)
> (key presence scan, values never printed)
BOT_TOKEN = <SET>            WEBHOOK_URL = <EMPTY>
API_HOST = <SET>             PERSIAN_FONT_NAME = <EMPTY>
API_PORT = <SET>
OCR_ENGINE = dummy           (only non-secret value inspected directly)
UPLOAD_DIR = <SET>
OUTPUT_DIR = <SET>
MAX_FILE_SIZE_MB = <SET>
RATE_LIMIT_MAX_RETRIES = <SET>
RATE_LIMIT_BACKOFF_SECONDS = <SET>
```

A `BOT_TOKEN` is present in the operator's local `.env` for interactive
polling-mode development, but **`WEBHOOK_URL` is empty** and no DNS/TLS
exists for it regardless. Per this milestone's rules, the token's value
was never read, and it was **not** used to make any live call (`getMe`,
`setWebhook`, etc.) — doing so was judged out of scope because (a) there
is still no public HTTPS endpoint to register as a webhook, and (b) this
credential's intended purpose (personal local testing vs. a sanctioned
staging bot) was not explicitly confirmed by the operator for this
milestone. `OCR_ENGINE=dummy` confirms the safe offline default remains
active — no real OCR credential is configured.

## 6. TLS issuance

**Status: blocked — no domain, no host, no Certbot run possible.**

`deploy/nginx/default.conf.template` and `deploy/docker-compose.prod.yml`
(`certbot` service) are statically present and validated by
`tests/test_deploy_configs.py`, but issuance requires a public DNS `A`
record resolving to a reachable host with ports 80/443 open — none
exists here. No certificate, key, or ACME account was requested.

## 7. `/healthz` / `/api/health` and webhook delivery

**Status: blocked — no running container, no public endpoint.**

Both endpoints are implemented and covered by the offline suite
(`tests/test_bot_api.py`, `tests/test_deploy_configs.py`), but reaching
them over HTTPS requires the Docker+TLS prerequisites above. No webhook
was registered with Telegram; no `getWebhookInfo` call was made.

## 8. UID/GID 1000 bind-mount permissions

**Status: statically re-confirmed — unchanged, correct, not runtime-
exercised.**

`Dockerfile` (lines re-verified this session):

```dockerfile
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app
...
RUN mkdir -p /app/data/uploads /app/data/output \
    && chown -R app:app /app/data \
    && chmod -R 750 /app/data
USER app
```

`deploy/setup_host.sh` creates `deploy/data/{uploads,output}` with
matching UID/GID 1000 ownership on the host side. This has been read and
confirmed consistent again this session; it still cannot be exercised
against a real bind mount without a Linux Docker host (see §1/§2).

## 9. Real-sample OCR benchmark

**Status: blocked — no sample, no engine credential, no host.**

```
> Get-ChildItem -Recurse -Include *.pdf   # (excluding .venv) -> no results
```

No scanned Persian PDF sample exists anywhere in the working tree. Per
`docs/BENCHMARK_RESULTS.md`, only the offline `dummy`-engine synthetic
benchmark has ever been run; `tesseract`/`paddle`/`vision_llm` remain
untested against real content. `tools/evaluate_sample.py` is unchanged
and ready to use once a licensed sample and a Docker/Linux host exist.

## 10. Offline regression suite

**Status: green — re-run this session.**

```
$env:PYTHONPATH="$PWD\src"; .\.venv\Scripts\python.exe -m pytest tests\ -q
...
157 passed, 9 warnings in 30.18s
```

157 passed, 0 failed — identical count to Milestones 6, 7, and 8. No test
was added, removed, or modified by this milestone (no application
behavior changed).

## Consolidated blockers (all restated from Milestones 5–8, still open)

| # | Blocker | Evidence | Unblock command (operator-run, on a real host) |
| - | --- | --- | --- |
| 1 | No Docker/Compose engine | §1 | Provision a Linux VM/VPS, then `deploy/setup_host.sh` (installs Docker Engine + Compose plugin) |
| 2 | No WSL / local Linux target | §2 | `wsl --install` (dev-only fallback; not a substitute for a public staging host) |
| 3 | No designated persianbookbot SSH/cloud host | §3, §4 | Operator explicitly designates (or provisions via `az vm create` / any provider) a host and shares its SSH target for this project |
| 4 | No DNS record / domain | §6 | `dig +short bot.yourdomain.com` once a domain + `A` record exist, per `docs/DEPLOYMENT_GUIDE.md` §2 |
| 5 | No TLS certificate | §6 | `docs/DEPLOYMENT_GUIDE.md` §5 (Certbot two-phase bootstrap) once §1/§4 are met |
| 6 | No live `/healthz`/`/api/health`/webhook probe | §7 | `curl -fsS https://bot.yourdomain.com/api/health`; `curl -fsS https://api.telegram.org/bot<TOKEN>/getWebhookInfo` once deployed |
| 7 | No real Persian PDF sample | §9 | Operator supplies a licensed, non-copyrighted scanned Persian PDF; then `python tools/evaluate_sample.py --engine tesseract --input <path>` |

No new blocker was discovered this milestone; all seven are exact
restatements of the same infrastructure gap tracked since Milestone 5,
re-verified with fresh command output on 2026-09-15 rather than assumed
carried-over.

## What this milestone changed vs. prior audits

- Added the discovery checks in §1–§5 that were not previously run in
  this exact form (Docker context list, WSL, SSH config, cloud CLI
  presence, `.env` key-presence-only scan) — all negative/blocked, none
  changes the substance of Milestones 5–8's conclusions.
- No code, dependency, Dockerfile, compose file, or test was modified.
- This document is the new canonical continuity report for live-staging
  status; `docs/PROJECT_STATUS.md` and `docs/ROADMAP.md` now point here
  for the Milestone 9 entry instead of duplicating the full evidence.

## Operator handoff (unchanged priority order)

1. Provision (or designate) a Docker-capable Ubuntu/Debian Linux host you
   control, with a DNS domain pointed at it.
2. Run `docs/DEPLOYMENT_GUIDE.md` end-to-end: `deploy/setup_host.sh` →
   fill in `deploy/.env` with a real `BOT_TOKEN`/`WEBHOOK_SECRET` → bring
   up `deploy/docker-compose.prod.yml` → issue TLS → verify
   `/healthz`/`/api/health` over HTTPS → register the Telegram webhook and
   confirm `getWebhookInfo` shows no `last_error_message`.
3. Supply one licensed, non-copyrighted scanned Persian PDF and run
   `tools/evaluate_sample.py` against `tesseract` (cheapest real engine)
   then optionally `paddle`/`vision_llm`, recording runtime/memory/page
   latency/output-quality observations in a follow-up update to this
   document.
4. Report results back so this document (and `docs/PROJECT_STATUS.md`/
   `docs/ROADMAP.md`) can be updated with real evidence instead of
   "blocked".
