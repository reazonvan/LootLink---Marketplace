#!/usr/bin/env bash
#
# Production deployment helper with optional post-deploy smoke trigger.
#
# Supported modes:
#   docker  - deploy via docker compose (default)
#   systemd - deploy via systemd service + nginx
#
# Optional env:
#   DEPLOY_MODE=docker|systemd
#   DEPLOY_BRANCH=main
#   DEPLOY_REMOTE=origin
#   HEALTHCHECK_URL=https://lootlink.ru/health/
#   RUN_DISPATCH_AFTER_DEPLOY=true|false
#   STRICT_DISPATCH=true|false
#   DEPLOY_SKIP_SETUP_SMOKE_DATA=true|false
#
# For setup_smoke_data (optional), provide:
#   SMOKE_SELLER_USERNAME / SMOKE_SELLER_PASSWORD / SMOKE_SELLER_EMAIL
#   SMOKE_BUYER_USERNAME  / SMOKE_BUYER_PASSWORD  / SMOKE_BUYER_EMAIL
#
# For repository_dispatch trigger:
#   GITHUB_DISPATCH_TOKEN (required if RUN_DISPATCH_AFTER_DEPLOY=true)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

DEPLOY_MODE="${DEPLOY_MODE:-docker}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
DEPLOY_REMOTE="${DEPLOY_REMOTE:-origin}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-https://lootlink.ru/health/}"
RUN_DISPATCH_AFTER_DEPLOY="${RUN_DISPATCH_AFTER_DEPLOY:-true}"
STRICT_DISPATCH="${STRICT_DISPATCH:-false}"
DEPLOY_SKIP_SETUP_SMOKE_DATA="${DEPLOY_SKIP_SETUP_SMOKE_DATA:-false}"

log() {
    echo "[INFO] $1"
}

warn() {
    echo "[WARN] $1"
}

error() {
    echo "[ERROR] $1" >&2
}

require_command() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        error "Required command not found: ${cmd}"
        exit 1
    fi
}

resolve_compose_cmd() {
    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        echo "docker compose"
        return
    fi
    if command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
        return
    fi
    error "Docker Compose is not available (docker compose or docker-compose)."
    exit 1
}

run_setup_smoke_data_docker() {
    local compose_cmd="$1"
    if [[ "${DEPLOY_SKIP_SETUP_SMOKE_DATA}" == "true" ]]; then
        log "Skipping setup_smoke_data (DEPLOY_SKIP_SETUP_SMOKE_DATA=true)."
        return
    fi

    if [[ -z "${SMOKE_SELLER_USERNAME:-}" || -z "${SMOKE_SELLER_PASSWORD:-}" || -z "${SMOKE_BUYER_USERNAME:-}" || -z "${SMOKE_BUYER_PASSWORD:-}" ]]; then
        warn "SMOKE_* credentials are not fully set; skipping setup_smoke_data."
        return
    fi

    local seller_email="${SMOKE_SELLER_EMAIL:-${SMOKE_SELLER_USERNAME}@lootlink.local}"
    local buyer_email="${SMOKE_BUYER_EMAIL:-${SMOKE_BUYER_USERNAME}@lootlink.local}"

    log "Running setup_smoke_data in web container..."
    ${compose_cmd} exec -T web python manage.py setup_smoke_data \
        --seller-username "${SMOKE_SELLER_USERNAME}" \
        --seller-email "${seller_email}" \
        --seller-password "${SMOKE_SELLER_PASSWORD}" \
        --buyer-username "${SMOKE_BUYER_USERNAME}" \
        --buyer-email "${buyer_email}" \
        --buyer-password "${SMOKE_BUYER_PASSWORD}"
}

run_setup_smoke_data_systemd() {
    if [[ "${DEPLOY_SKIP_SETUP_SMOKE_DATA}" == "true" ]]; then
        log "Skipping setup_smoke_data (DEPLOY_SKIP_SETUP_SMOKE_DATA=true)."
        return
    fi

    if [[ -z "${SMOKE_SELLER_USERNAME:-}" || -z "${SMOKE_SELLER_PASSWORD:-}" || -z "${SMOKE_BUYER_USERNAME:-}" || -z "${SMOKE_BUYER_PASSWORD:-}" ]]; then
        warn "SMOKE_* credentials are not fully set; skipping setup_smoke_data."
        return
    fi

    local seller_email="${SMOKE_SELLER_EMAIL:-${SMOKE_SELLER_USERNAME}@lootlink.local}"
    local buyer_email="${SMOKE_BUYER_EMAIL:-${SMOKE_BUYER_USERNAME}@lootlink.local}"

    if [[ -d "${PROJECT_DIR}/venv" ]]; then
        # shellcheck disable=SC1091
        source "${PROJECT_DIR}/venv/bin/activate"
    else
        warn "venv not found in ${PROJECT_DIR}/venv, using system python."
    fi

    log "Running setup_smoke_data in systemd mode..."
    python manage.py setup_smoke_data \
        --seller-username "${SMOKE_SELLER_USERNAME}" \
        --seller-email "${seller_email}" \
        --seller-password "${SMOKE_SELLER_PASSWORD}" \
        --buyer-username "${SMOKE_BUYER_USERNAME}" \
        --buyer-email "${buyer_email}" \
        --buyer-password "${SMOKE_BUYER_PASSWORD}"
}

check_health() {
    local max_attempts=36
    local sleep_seconds=5

    require_command curl

    log "Waiting for health endpoint: ${HEALTHCHECK_URL}"
    for ((i = 1; i <= max_attempts; i++)); do
        code="$(curl -k -sS -o /dev/null -w "%{http_code}" "${HEALTHCHECK_URL}" || true)"
        if [[ "${code}" == "200" ]]; then
            log "Health check passed (HTTP 200)."
            return 0
        fi
        log "Health check attempt ${i}/${max_attempts}: HTTP ${code:-n/a}"
        sleep "${sleep_seconds}"
    done

    error "Health check failed after ${max_attempts} attempts."
    return 1
}

run_dispatch_trigger() {
    if [[ "${RUN_DISPATCH_AFTER_DEPLOY}" != "true" ]]; then
        log "Skipping repository_dispatch (RUN_DISPATCH_AFTER_DEPLOY=${RUN_DISPATCH_AFTER_DEPLOY})."
        return 0
    fi

    local deployed_sha
    deployed_sha="$(git rev-parse --short HEAD)"
    log "Triggering post-deploy smoke workflow (sha=${deployed_sha})..."

    if DEPLOYED_SHA="${deployed_sha}" "${SCRIPT_DIR}/trigger_post_deploy_smoke.sh"; then
        log "repository_dispatch sent successfully."
        return 0
    fi

    if [[ "${STRICT_DISPATCH}" == "true" ]]; then
        error "repository_dispatch failed and STRICT_DISPATCH=true."
        return 1
    fi

    warn "repository_dispatch failed, but deployment remains successful (STRICT_DISPATCH=false)."
    return 0
}

deploy_git_update() {
    require_command git

    log "Fetching latest ${DEPLOY_BRANCH} from ${DEPLOY_REMOTE}..."
    git fetch "${DEPLOY_REMOTE}" "${DEPLOY_BRANCH}"
    git checkout "${DEPLOY_BRANCH}"
    git pull --ff-only "${DEPLOY_REMOTE}" "${DEPLOY_BRANCH}"
}

deploy_docker() {
    local compose_cmd
    compose_cmd="$(resolve_compose_cmd)"

    log "Deploy mode: docker"
    log "Using compose command: ${compose_cmd}"

    ${compose_cmd} up -d --build web celery_worker celery_beat caddy
    run_setup_smoke_data_docker "${compose_cmd}"
}

deploy_systemd() {
    require_command systemctl
    require_command python

    log "Deploy mode: systemd"
    sudo systemctl stop lootlink || true

    if [[ -d "${PROJECT_DIR}/venv" ]]; then
        # shellcheck disable=SC1091
        source "${PROJECT_DIR}/venv/bin/activate"
    fi

    pip install -r requirements.txt --upgrade
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    run_setup_smoke_data_systemd

    sudo systemctl start lootlink
    sudo systemctl restart nginx || true
}

main() {
    log "Starting deployment in ${PROJECT_DIR}"
    deploy_git_update

    case "${DEPLOY_MODE}" in
        docker)
            deploy_docker
            ;;
        systemd)
            deploy_systemd
            ;;
        *)
            error "Unsupported DEPLOY_MODE: ${DEPLOY_MODE}. Use docker or systemd."
            exit 1
            ;;
    esac

    check_health
    run_dispatch_trigger
    log "Deployment finished."
}

main "$@"
