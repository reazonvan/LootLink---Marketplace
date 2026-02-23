#!/usr/bin/env bash
#
# Trigger GitHub repository_dispatch event for post-deploy smoke checks.
#
# Required:
#   GITHUB_DISPATCH_TOKEN  - GitHub token with permission to call dispatch API
#
# Optional (env):
#   GITHUB_OWNER           - default: reazonvan
#   GITHUB_REPO            - default: LootLink---Marketplace
#   DISPATCH_EVENT_TYPE    - default: post_deploy_smoke
#   SMOKE_BASE_URL         - default: https://lootlink.ru
#   GITHUB_API_URL         - default: https://api.github.com
#
# Usage:
#   bash scripts/trigger_post_deploy_smoke.sh
#   SMOKE_BASE_URL=https://staging.lootlink.ru bash scripts/trigger_post_deploy_smoke.sh

set -euo pipefail

GITHUB_OWNER="${GITHUB_OWNER:-reazonvan}"
GITHUB_REPO="${GITHUB_REPO:-LootLink---Marketplace}"
DISPATCH_EVENT_TYPE="${DISPATCH_EVENT_TYPE:-post_deploy_smoke}"
SMOKE_BASE_URL="${SMOKE_BASE_URL:-https://lootlink.ru}"
GITHUB_API_URL="${GITHUB_API_URL:-https://api.github.com}"
DEPLOYED_SHA="${DEPLOYED_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo unknown)}"
DEPLOYED_AT="${DEPLOYED_AT:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"

if [[ -z "${GITHUB_DISPATCH_TOKEN:-}" ]]; then
    echo "[ERROR] GITHUB_DISPATCH_TOKEN is not set."
    echo "        Export token and retry, for example:"
    echo "        export GITHUB_DISPATCH_TOKEN='ghp_***'"
    exit 1
fi

dispatch_url="${GITHUB_API_URL}/repos/${GITHUB_OWNER}/${GITHUB_REPO}/dispatches"

payload=$(cat <<EOF
{"event_type":"${DISPATCH_EVENT_TYPE}","client_payload":{"base_url":"${SMOKE_BASE_URL}","deployed_sha":"${DEPLOYED_SHA}","deployed_at":"${DEPLOYED_AT}"}}
EOF
)

tmp_response="$(mktemp)"
http_code="$(curl -sS -o "${tmp_response}" -w "%{http_code}" \
    -X POST "${dispatch_url}" \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer ${GITHUB_DISPATCH_TOKEN}" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    -d "${payload}")"

if [[ "${http_code}" != "204" ]]; then
    echo "[ERROR] repository_dispatch failed (HTTP ${http_code})."
    echo "        URL: ${dispatch_url}"
    echo "        Response:"
    cat "${tmp_response}"
    rm -f "${tmp_response}"
    exit 1
fi

rm -f "${tmp_response}"
echo "[OK] repository_dispatch sent: ${DISPATCH_EVENT_TYPE}"
echo "     repo: ${GITHUB_OWNER}/${GITHUB_REPO}"
echo "     base_url: ${SMOKE_BASE_URL}"
echo "     deployed_sha: ${DEPLOYED_SHA}"
