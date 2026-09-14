"""Offline static validation for the production deployment bundle.

Covers ``deploy/docker-compose.prod.yml``, ``deploy/nginx/default.conf.template``,
and ``deploy/setup_host.sh``. Every check here is pure file/text/YAML
parsing - no Docker engine, no network access, and no real secret is ever
read or required, matching the rest of this offline-only test suite.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_DIR = REPO_ROOT / "deploy"
COMPOSE_PATH = DEPLOY_DIR / "docker-compose.prod.yml"
NGINX_TEMPLATE_PATH = DEPLOY_DIR / "nginx" / "default.conf.template"
SETUP_HOST_PATH = DEPLOY_DIR / "setup_host.sh"
DEPLOYMENT_GUIDE_PATH = REPO_ROOT / "docs" / "DEPLOYMENT_GUIDE.md"

# Real-looking domains/TLDs that must never appear in committed deployment
# configuration - only the documentation-safe placeholders below are
# allowed as the "domain" portion of any hostname literal.
ALLOWED_PLACEHOLDER_DOMAINS = {"example.com", "yourdomain.com"}

# File-extension-like suffixes that can trip the "looks like a domain"
# regex when it matches a filename reference (e.g. "default.conf") inside
# a comment - not an actual hostname, so they're excluded from the check.
_NON_DOMAIN_SUFFIXES = ("conf", "template", "md", "yml", "yaml", "sh", "txt", "pem", "prod", "py")


def _is_allowed_placeholder(domain: str) -> bool:
    if domain in ALLOWED_PLACEHOLDER_DOMAINS:
        return True
    if any(domain == d or domain.endswith("." + d) for d in ALLOWED_PLACEHOLDER_DOMAINS):
        return True
    if domain.rsplit(".", 1)[-1] in _NON_DOMAIN_SUFFIXES:
        return True
    return False


def _load_compose() -> dict:
    with COMPOSE_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _nginx_template_text() -> str:
    return NGINX_TEMPLATE_PATH.read_text(encoding="utf-8")


def _setup_host_text() -> str:
    return SETUP_HOST_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File presence
# ---------------------------------------------------------------------------


def test_deploy_bundle_files_exist():
    assert COMPOSE_PATH.is_file()
    assert NGINX_TEMPLATE_PATH.is_file()
    assert SETUP_HOST_PATH.is_file()
    assert DEPLOYMENT_GUIDE_PATH.is_file()


# ---------------------------------------------------------------------------
# docker-compose.prod.yml
# ---------------------------------------------------------------------------


def test_compose_file_is_valid_yaml():
    compose = _load_compose()
    assert isinstance(compose, dict)
    assert "services" in compose


def test_compose_defines_bot_nginx_certbot_services():
    compose = _load_compose()
    services = compose["services"]
    assert set(services.keys()) == {"bot", "nginx", "certbot"}


def test_compose_bot_has_no_host_exposed_ports():
    """The bot must only be reachable through nginx, never directly."""
    bot = _load_compose()["services"]["bot"]
    assert "ports" not in bot
    # `expose` (container-to-container only) is fine and expected.
    assert bot.get("expose") == ["8000"]


def test_compose_nginx_exposes_only_80_and_443():
    nginx = _load_compose()["services"]["nginx"]
    ports = nginx.get("ports", [])
    assert len(ports) == 2
    normalized = {str(p).split(":")[0] for p in ports}
    assert normalized == {"80", "443"}


def test_compose_certbot_has_no_host_ports():
    certbot = _load_compose()["services"]["certbot"]
    assert "ports" not in certbot


def test_compose_bot_and_nginx_share_internal_network():
    compose = _load_compose()
    assert "internal_net" in compose.get("networks", {})
    for name in ("bot", "nginx", "certbot"):
        service = compose["services"][name]
        assert "internal_net" in service.get("networks", []), name


def test_compose_defines_persistent_data_and_tls_acme_volumes():
    compose = _load_compose()

    bot_volumes = compose["services"]["bot"]["volumes"]
    assert any(v.startswith("./data:") for v in bot_volumes), (
        "bot service must bind-mount a persistent ./data volume"
    )

    nginx_volumes = compose["services"]["nginx"]["volumes"]
    assert any("/etc/letsencrypt" in v for v in nginx_volumes), (
        "nginx must mount the Let's Encrypt (TLS) volume"
    )
    assert any("/var/www/certbot" in v for v in nginx_volumes), (
        "nginx must mount the ACME challenge webroot volume"
    )

    certbot_volumes = compose["services"]["certbot"]["volumes"]
    assert any("/etc/letsencrypt" in v for v in certbot_volumes)
    assert any("/var/www/certbot" in v for v in certbot_volumes)


def test_compose_bot_uses_env_file_for_runtime_injection():
    bot = _load_compose()["services"]["bot"]
    assert bot.get("env_file") == [".env"]
    # No inline `environment:` secrets - runtime config only via env_file.
    assert "environment" not in bot


def test_compose_services_have_restart_policy():
    compose = _load_compose()
    for name in ("bot", "nginx", "certbot"):
        assert compose["services"][name].get("restart") == "unless-stopped", name


def test_compose_bot_and_nginx_have_healthchecks():
    compose = _load_compose()
    for name in ("bot", "nginx"):
        healthcheck = compose["services"][name].get("healthcheck")
        assert healthcheck is not None, name
        assert healthcheck["test"][0] == "CMD"


def test_compose_nginx_depends_on_bot_health():
    nginx = _load_compose()["services"]["nginx"]
    depends_on = nginx.get("depends_on", {})
    assert "bot" in depends_on
    assert depends_on["bot"].get("condition") == "service_healthy"


def test_compose_has_no_committed_secrets_or_real_domains():
    raw_text = COMPOSE_PATH.read_text(encoding="utf-8")

    forbidden_patterns = [
        r"BOT_TOKEN\s*=\s*[0-9]{6,}:",  # a real-looking Telegram bot token
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"WEBHOOK_SECRET\s*=\s*[A-Za-z0-9]{16,}",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, raw_text), f"found forbidden secret-like pattern: {pattern}"

    # Only the documented placeholder default domain may appear.
    for match in re.finditer(r"DOMAIN:-([A-Za-z0-9.\-]+)", raw_text):
        domain = match.group(1)
        assert _is_allowed_placeholder(domain), domain


def test_compose_build_context_points_at_repo_root_dockerfile():
    bot = _load_compose()["services"]["bot"]
    build = bot["build"]
    assert build["context"] == ".."
    assert build["dockerfile"] == "Dockerfile"


# ---------------------------------------------------------------------------
# nginx/default.conf.template
# ---------------------------------------------------------------------------


def test_nginx_template_has_http_to_https_redirect():
    text = _nginx_template_text()
    assert "listen 80;" in text
    assert re.search(r"return 301 https://\$host\$request_uri;", text)


def test_nginx_template_has_acme_challenge_location():
    text = _nginx_template_text()
    assert "location /.well-known/acme-challenge/" in text
    assert "/var/www/certbot" in text


def test_nginx_template_has_https_server_block():
    text = _nginx_template_text()
    assert "listen 443 ssl;" in text
    assert "ssl_certificate " in text
    assert "ssl_certificate_key " in text


def test_nginx_template_proxies_root_and_api_to_bot():
    text = _nginx_template_text()
    assert re.search(r"location\s*/\s*\{[^}]*proxy_pass http://bot:8000;", text, re.S)
    assert re.search(r"location /api/\s*\{[^}]*proxy_pass http://bot:8000/api/;", text, re.S)


def test_nginx_template_sets_forwarded_headers():
    text = _nginx_template_text()
    for header in (
        "X-Real-IP",
        "X-Forwarded-For",
        "X-Forwarded-Proto",
        "X-Forwarded-Host",
    ):
        assert header in text, header


def test_nginx_template_passes_through_webhook_secret_header():
    text = _nginx_template_text()
    assert "X-Telegram-Bot-Api-Secret-Token" in text
    assert "proxy_pass_request_headers on;" in text


def test_nginx_template_uses_domain_placeholder_only():
    text = _nginx_template_text()
    # ${DOMAIN} must be the only hostname mechanism - substituted at
    # container start by nginx's envsubst-on-templates behavior.
    assert "${DOMAIN}" in text
    assert "server_name ${DOMAIN};" in text

    # The nginx directives that actually carry a hostname/path must use
    # ${DOMAIN}, never a hardcoded value - checked directly on the
    # directive lines rather than scanning the whole file (which also
    # contains dotted filenames like ".env.example" in prose comments
    # that are not hostnames).
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("server_name ", "ssl_certificate ", "ssl_certificate_key ")):
            assert "${DOMAIN}" in stripped, stripped
            for domain in ALLOWED_PLACEHOLDER_DOMAINS:
                assert domain not in stripped, stripped


def test_nginx_template_has_no_hardcoded_secrets():
    text = _nginx_template_text()
    assert not re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
    assert "BOT_TOKEN" not in text
    assert "WEBHOOK_SECRET=" not in text


def test_nginx_template_defines_healthz_endpoint_without_tls_dependency():
    """The Docker healthcheck must not require a cert to already exist."""
    text = _nginx_template_text()
    assert "location = /healthz" in text
    # The /healthz block must live in the port-80 (no TLS) server block,
    # i.e. it must appear before the first "listen 443" directive.
    healthz_index = text.index("location = /healthz")
    https_index = text.index("listen 443")
    assert healthz_index < https_index


# ---------------------------------------------------------------------------
# setup_host.sh
# ---------------------------------------------------------------------------


def test_setup_host_has_bash_shebang_and_strict_mode():
    text = _setup_host_text()
    assert text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text


def test_setup_host_is_idempotent_for_docker_install():
    text = _setup_host_text()
    # Must check for an existing installation before attempting to install.
    assert "command -v docker" in text
    assert re.search(r"if\s+command -v docker.*docker compose version", text, re.S)


def test_setup_host_never_overwrites_existing_env():
    text = _setup_host_text()
    assert re.search(r'if \[ -f "\$\{env_file\}" \]; then', text)
    # The early-return must come before the `cp` that generates the template.
    guard_index = text.index('if [ -f "${env_file}" ]; then')
    copy_index = text.index('cp "${example_file}" "${env_file}"')
    assert guard_index < copy_index


def test_setup_host_creates_uid_gid_1000_compatible_directories():
    text = _setup_host_text()
    assert "APP_UID=1000" in text
    assert "APP_GID=1000" in text
    assert "chown" in text
    assert "chmod" in text


def test_setup_host_never_contains_secret_values():
    text = _setup_host_text()
    assert not re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
    assert not re.search(r"BOT_TOKEN\s*=\s*[0-9]{6,}:", text)
    # It may *reference* the env var names but never assign a real value.
    assert not re.search(r"WEBHOOK_SECRET\s*=\s*[A-Za-z0-9]{16,}", text)


def test_setup_host_does_not_start_containers_or_request_certificates():
    """setup_host.sh is host-bootstrap only; it must not itself execute a
    Docker Compose or Certbot command, per the deployment guide's
    separation of concerns (docs/DEPLOYMENT_GUIDE.md steps 3 vs. 5/6). It
    may only *mention* the follow-up command in a log/echo string for the
    operator, which is why this checks for the command at the start of a
    (whitespace-trimmed) line rather than anywhere in the file."""
    text = _setup_host_text()
    for line in text.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("docker compose"), line
        assert not stripped.startswith("certbot certonly"), line
        assert not stripped.startswith("certbot renew"), line


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available to syntax-check the script")
def test_setup_host_has_valid_bash_syntax():
    result = subprocess.run(
        ["bash", "-n", str(SETUP_HOST_PATH)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# Cross-cutting: no credentials anywhere in the deployment bundle
# ---------------------------------------------------------------------------


def test_no_env_files_committed_in_deploy_bundle():
    """deploy/.env must never exist as a tracked/generated artifact next
    to the templates in this repository checkout."""
    assert not (DEPLOY_DIR / ".env").exists()


def test_deployment_guide_documents_no_live_validation_claim():
    text = DEPLOYMENT_GUIDE_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "no docker engine" in lowered or "no live" in lowered or "not been executed" in lowered
    assert "never executed" in lowered or "no command in this guide has been executed" in lowered
