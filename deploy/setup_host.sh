#!/usr/bin/env bash
# deploy/setup_host.sh - idempotent Ubuntu/Debian host bootstrap for the
# persianbookbot production deployment (deploy/docker-compose.prod.yml).
#
# What it does (safe to re-run any number of times):
#   1. Checks for Docker Engine + the Compose plugin; installs them via
#      Docker's official apt repository only if missing.
#   2. Creates deploy/data, deploy/certbot/conf, deploy/certbot/www with
#      UID/GID 1000-compatible ownership/permissions (matching the
#      non-root `app` user baked into ../Dockerfile).
#   3. Generates deploy/.env from ../.env.example if it does not already
#      exist - never overwrites an existing .env, and never writes a real
#      secret; every value is left blank/placeholder for the operator to
#      fill in by hand.
#
# It does NOT: install/reload nginx configuration, request or renew any
# TLS certificate, start any container, or read/print any secret value.
# See docs/DEPLOYMENT_GUIDE.md for those steps.
#
# Usage:
#   cd deploy && ./setup_host.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Fixed non-root UID/GID baked into ../Dockerfile's `app` user - keep data
# directories writable by the container without relaxing permissions to
# world-writable or running the container as root.
APP_UID=1000
APP_GID=1000

log() {
    printf '[setup_host] %s\n' "$1"
}

require_linux_apt() {
    if ! command -v apt-get >/dev/null 2>&1; then
        log "ERROR: this script targets Ubuntu/Debian hosts with apt-get; none found. Aborting."
        exit 1
    fi
}

# --- 1. Docker Engine + Compose plugin -------------------------------------
install_docker_if_missing() {
    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        log "Docker Engine + Compose plugin already installed ($(docker --version)); skipping install."
        return 0
    fi

    require_linux_apt
    log "Docker Engine/Compose plugin not found - installing from Docker's official apt repository."

    # Official convenience script path (docs.docker.com/engine/install/ubuntu
    # and .../debian): add Docker's apt repo + GPG key, then install the
    # engine + compose plugin packages. Idempotent - re-running apt-get
    # install on already-installed packages is a no-op.
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg

    sudo install -m 0755 -d /etc/apt/keyrings
    if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
        . /etc/os-release
        curl -fsSL "https://download.docker.com/linux/${ID}/gpg" \
            | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
    fi

    if [ ! -f /etc/apt/sources.list.d/docker.list ]; then
        . /etc/os-release
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" \
            | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
    fi

    sudo apt-get update -y
    sudo apt-get install -y \
        docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin

    log "Docker Engine + Compose plugin installed."
    log "NOTE: add your user to the 'docker' group (sudo usermod -aG docker \$USER) and re-login to run docker without sudo."
}

# --- 2. Persistent data/TLS/ACME directories -------------------------------
setup_directories() {
    log "Creating persistent data/TLS/ACME directories under ${SCRIPT_DIR} (idempotent)."

    mkdir -p "${SCRIPT_DIR}/data/uploads" "${SCRIPT_DIR}/data/output"
    mkdir -p "${SCRIPT_DIR}/certbot/conf" "${SCRIPT_DIR}/certbot/www"

    # UID/GID 1000-compatible ownership so the non-root container user can
    # read/write ./data without the container running as root or the host
    # directory being world-writable. Falls back to a permission-only
    # change (no chown) when not run with sudo/root - `docker compose up`
    # still works as long as the *effective* host UID/GID already matches
    # 1000:1000 (the common case for a freshly created deploy user).
    if [ "$(id -u)" = "0" ] || command -v sudo >/dev/null 2>&1; then
        sudo chown -R "${APP_UID}:${APP_GID}" "${SCRIPT_DIR}/data" 2>/dev/null \
            || log "WARNING: could not chown ./data to ${APP_UID}:${APP_GID} - ensure the container's non-root UID/GID can write it."
    fi
    chmod -R 750 "${SCRIPT_DIR}/data"

    # certbot/conf and certbot/www are managed by the certbot/nginx
    # containers themselves (root-owned Let's Encrypt state is standard);
    # only ensure they exist and are not world-writable.
    chmod 755 "${SCRIPT_DIR}/certbot" "${SCRIPT_DIR}/certbot/conf" "${SCRIPT_DIR}/certbot/www"

    log "Directories ready: ${SCRIPT_DIR}/data, ${SCRIPT_DIR}/certbot/{conf,www}."
}

# --- 3. Safe .env template generation --------------------------------------
generate_env_template() {
    local env_file="${SCRIPT_DIR}/.env"
    local example_file="${REPO_ROOT}/.env.example"

    if [ -f "${env_file}" ]; then
        log "${env_file} already exists - leaving it untouched (never overwritten by this script)."
        return 0
    fi

    if [ ! -f "${example_file}" ]; then
        log "WARNING: ${example_file} not found - skipping .env template generation."
        return 0
    fi

    cp "${example_file}" "${env_file}"
    chmod 600 "${env_file}"
    log "Created ${env_file} from .env.example (all secrets blank). Fill in BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET, etc. before starting the stack - never commit this file."
}

main() {
    log "Starting idempotent host bootstrap for persianbookbot production deployment."
    install_docker_if_missing
    setup_directories
    generate_env_template
    log "Host bootstrap complete. Next: fill in ${SCRIPT_DIR}/.env, then follow docs/DEPLOYMENT_GUIDE.md for DNS/TLS issuance and 'docker compose -f docker-compose.prod.yml up -d'."
}

main "$@"
