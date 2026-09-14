# Deployment Guide: Staging/Production VPS Bootstrap

This guide walks through deploying `persianbookbot` to a Ubuntu/Debian
VPS (or any cloud VM with a public IPv4/IPv6 address) behind Nginx with
Let's Encrypt (Certbot) TLS, using `deploy/docker-compose.prod.yml`.

> **Status of this document**: every command below was authored and statically validated (YAML/template parsing, shell syntax, offline tests in `tests/test_deploy_configs.py`) in an environment with no Docker engine, no public DNS record, and no cloud account. No command in this guide has been executed against a real VPS, and no live TLS/webhook delivery is claimed anywhere in this repository. Treat every step as reviewed-but-unexecuted until you run it yourself and record the result (see `docs/PROJECT_STATUS.md` / `docs/ROADMAP.md`).

## 1. Prerequisites

- A Ubuntu 22.04+/Debian 12+ VPS or cloud VM (1 vCPU / 1 GiB RAM is
  sufficient for the `dummy`/`tesseract` OCR engines; budget more for
  `paddle`).
- A domain name you control, with the ability to create DNS `A`/`AAAA`
  records pointing at the VPS's public IP.
- SSH access with a sudo-capable user.
- A real Telegram bot token from [@BotFather](https://t.me/BotFather) (not
  required to deploy the API-only Mini App, but required for webhook
  mode).

## 2. DNS setup

1. Note the VPS's public IPv4 (and IPv6, if available) address.
2. In your DNS provider, create:
   - `A    bot.yourdomain.com  ->  <VPS public IPv4>`
   - `AAAA bot.yourdomain.com  ->  <VPS public IPv6>` (optional)
3. Wait for propagation and confirm resolution before requesting a
   certificate (Let's Encrypt's HTTP-01 challenge requires the domain to
   already resolve to this host):
   ```bash
   dig +short bot.yourdomain.com
   ```

Replace every `bot.yourdomain.com` / `bot.example.com` in this guide and
in `deploy/nginx/default.conf.template` (via the `DOMAIN` environment
variable) with your **real** domain. Never commit a real domain into the
repository itself — it stays in the untracked `deploy/.env`.

## 3. Host bootstrap

```bash
git clone <this repository> persianbookbot
cd persianbookbot/deploy
chmod +x setup_host.sh   # if the executable bit was lost in transfer
./setup_host.sh
```

`setup_host.sh` is idempotent — safe to re-run after any interruption. It:

- Installs Docker Engine + the Compose plugin from Docker's official apt
  repository, only if not already present.
- Creates `deploy/data/{uploads,output}` and
  `deploy/certbot/{conf,www}` with UID/GID 1000-compatible ownership,
  matching the non-root `app` user baked into `../Dockerfile`.
- Copies `../.env.example` to `deploy/.env` **only if `deploy/.env` does
  not already exist** — every value starts blank/placeholder; it never
  writes or overwrites a real secret.

After it completes, add your user to the `docker` group if prompted
(`sudo usermod -aG docker $USER`) and start a new shell/session.

## 4. Fill in `deploy/.env`

Edit `deploy/.env` (git-ignored, never commit it) and set at minimum:

```
BOT_TOKEN=<real token from @BotFather>
WEBHOOK_URL=https://bot.yourdomain.com
WEBHOOK_SECRET=<random value, e.g. `openssl rand -hex 32`>
```

Leave `OCR_ENGINE=dummy` (the default) unless you have already validated
a real engine's optional dependency/credential — see
`docs/PROJECT_STATUS.md` and `docs/BENCHMARK_RESULTS.md`. Set
`DOMAIN=bot.yourdomain.com` as a **shell/compose environment variable**
(not inside `.env`, since it configures nginx, not the bot) before
running `docker compose`, e.g.:

```bash
export DOMAIN=bot.yourdomain.com
```

## 5. First-time TLS certificate issuance (chicken-and-egg bootstrap)

`deploy/nginx/default.conf.template` renders a `443 ssl` server block that
references `/etc/letsencrypt/live/${DOMAIN}/{fullchain,privkey}.pem`.
Nginx will refuse to start if those files don't exist yet, so the very
first issuance needs a short two-phase bootstrap:

1. **Temporarily comment out (or remove) the entire `server { listen 443
   ssl; ... }` block** in `deploy/nginx/default.conf.template`, keeping
   only the port-80 server block (HTTP redirect + ACME challenge +
   `/healthz`). Start just nginx:
   ```bash
   docker compose -f docker-compose.prod.yml up -d bot nginx
   ```
2. Request the certificate via the webroot method (shares the
   `./certbot/www` volume nginx is already serving
   `/.well-known/acme-challenge/` from):
   ```bash
   docker compose -f docker-compose.prod.yml run --rm certbot \
     certbot certonly --webroot -w /var/www/certbot \
     -d "$DOMAIN" --email you@yourdomain.com --agree-tos --no-eff-email
   ```
3. **Restore** the `443 ssl` server block in
   `deploy/nginx/default.conf.template` (undo step 1), then start the
   full stack:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```
   Nginx now finds the certificate issued in step 2 and starts cleanly.

From this point on, the `certbot` service's built-in renewal loop
(`certbot renew --webroot ... ; sleep 12h`) keeps the certificate current
without any further manual steps — `certbot renew` is a no-op until a
certificate is within its renewal window (~30 days before expiry), so it
is safe to leave running indefinitely.

### Renewal validation / manual renewal

```bash
# Dry-run (no real renewal, no rate-limit consumption) - always safe to
# run for a health check of the renewal path itself.
docker compose -f docker-compose.prod.yml run --rm certbot \
  certbot renew --dry-run

# Force an immediate real renewal attempt (normally unnecessary - the
# background loop already does this every 12h and only acts within the
# renewal window).
docker compose -f docker-compose.prod.yml exec certbot certbot renew
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## 6. Start the stack

```bash
cd deploy
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

All three services (`bot`, `nginx`, `certbot`) should show `Up`/`healthy`.

## 7. Webhook registration

Webhook registration is automatic: `bot.main._run_webhook_mode()` calls
`Bot.set_webhook()` on startup whenever `WEBHOOK_URL` and `BOT_TOKEN` are
both set in `deploy/.env` (see README.md "Webhook mode"). To confirm
registration succeeded against Telegram's real servers:

```bash
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo" | python3 -m json.tool
```

Expect `"url": "https://bot.yourdomain.com/api/telegram/webhook"` and
`"last_error_message"` absent/empty. If Telegram reports a TLS or
connectivity error, re-check DNS, the certificate (step 5), and that port
443 is reachable from the public internet (cloud firewall/security group
rules, not just the host's own `ufw`/`iptables`).

**Never paste `BOT_TOKEN` into shell history you don't control** — prefer
`read -s BOT_TOKEN` or a secrets manager in real operational use.

## 8. Health validation

```bash
# From the host itself:
curl -f http://localhost/healthz            # nginx liveness (no cert needed)
curl -f https://bot.yourdomain.com/api/health  # end-to-end through nginx -> bot

# Container-level:
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f bot
```

`GET /api/health` (see `src/bot/api.py`) is dependency-free by design —
a failure here means the bot process itself is unhealthy, not an
upstream OCR/Telegram outage.

## 9. Secret rotation

To rotate `BOT_TOKEN`, `WEBHOOK_SECRET`, or `VISION_LLM_API_KEY`:

1. Generate the new value out-of-band (e.g. re-issue the bot token via
   @BotFather's `/revoke`, or `openssl rand -hex 32` for
   `WEBHOOK_SECRET`).
2. Edit `deploy/.env` with the new value — never log it, never commit it.
3. Recreate only the `bot` service so the new environment is picked up
   (nginx/certbot are unaffected by bot secrets):
   ```bash
   docker compose -f docker-compose.prod.yml up -d --force-recreate bot
   ```
4. If `WEBHOOK_SECRET` changed, `_run_webhook_mode()` re-registers the
   webhook with the new secret automatically on the next `bot` start
   (`Bot.set_webhook(..., secret_token=...)` runs on every startup) — no
   manual `setWebhook` call is required.
5. Confirm with `getWebhookInfo` (step 7) and a fresh `/api/health` check
   (step 8).

## 10. Backups

The only durable state outside the Docker images is:

- `deploy/data/` — uploaded PDFs and generated EPUB/DOCX/TXT output.
  These are transient by design (`JOB_RETENTION_SECONDS`,
  `CLEANUP_INTERVAL_SECONDS` in `.env.example` prune them automatically),
  so back this up only if you need audit/compliance retention beyond the
  bot's own cleanup window.
- `deploy/certbot/conf/` — Let's Encrypt account key + issued
  certificates. Losing this just means re-issuing a new certificate (rate
  limits permitting); it is not a hard requirement to back up, but doing
  so avoids a Let's Encrypt rate-limit wait during recovery.
- `deploy/.env` — **never back this up to an unencrypted location**; if
  you must, use an encrypted secrets store, not a plain file copy.

```bash
tar czf persianbookbot-backup-$(date +%Y%m%d).tar.gz \
  deploy/data deploy/certbot/conf
```

## 11. Rollback

```bash
# Roll back to a previous image tag/commit:
git -C /path/to/persianbookbot checkout <previous-tag-or-commit>
docker compose -f docker-compose.prod.yml up -d --build

# Or, if only configuration (nginx template/.env) changed:
docker compose -f docker-compose.prod.yml up -d --force-recreate nginx bot
```

Because `deploy/data` is a bind mount (not a named volume tied to a
container), rolling back the application image never touches persisted
job data. If a bad deploy corrupted `deploy/data` itself, restore it from
the most recent backup (step 10).

## 12. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `nginx` container exits immediately on first start | TLS cert files referenced in `default.conf.template` don't exist yet | Follow the two-phase bootstrap in step 5 |
| `certbot certonly` fails with a challenge/connection error | DNS not yet propagated, or port 80 blocked by a cloud firewall | Re-check `dig +short $DOMAIN`; open port 80/443 in the cloud security group, not just `ufw` |
| `getWebhookInfo` shows a TLS error | Certificate not yet issued/renewed, or `DOMAIN` mismatched between `.env`/nginx template and the actual DNS name | Re-run step 5; confirm `DOMAIN` matches the DNS record exactly (no trailing dot/scheme) |
| `bot` container marked unhealthy | `/api/health` unreachable — check `docker compose logs bot` for a startup exception (e.g. missing `BOT_TOKEN` when webhook mode is expected) | Fix the underlying config/env issue, then `docker compose up -d --force-recreate bot` |
| Uploaded files not persisting across restarts | `deploy/data` not bind-mounted correctly, or `setup_host.sh` wasn't run to fix ownership | Re-run `./setup_host.sh`; confirm `docker compose config` shows the `./data:/app/data` volume |
| `403`/`401` on `POST /api/telegram/webhook` | `WEBHOOK_SECRET` mismatch between `.env` and what Telegram is echoing back (usually a stale registration) | Restart `bot` to force re-registration (step 9), or verify no proxy in front of nginx is stripping `X-Telegram-Bot-Api-Secret-Token` |
| `502 Bad Gateway` from nginx | `bot` container not yet healthy/started, or crashed | `docker compose ps`; `docker compose logs bot`; nginx's `depends_on: condition: service_healthy` should prevent most races, but check anyway |

## 13. Uninstall / teardown

```bash
docker compose -f docker-compose.prod.yml down
# Add -v only if you intentionally want to discard the named `internal_net`
# network definition; deploy/data and deploy/certbot are bind mounts and
# are never removed by `docker compose down` regardless of -v.
```

## See also

- `README.md` — "Webhook mode" and "Docker / deployment" sections (local/
  single-container development usage).
- `AGENTS.md` — "Containerization / deployment" and "Webhook mode"
  sections (implementation-level contracts).
- `docs/PROJECT_STATUS.md` / `docs/ROADMAP.md` — what has and has not
  been live-validated in this repository's own CI/dev environment.
- `tests/test_deploy_configs.py` — the offline static checks this guide's
  configuration is validated against.
