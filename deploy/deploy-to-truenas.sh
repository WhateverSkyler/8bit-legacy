#!/usr/bin/env bash
# Build + deploy the 8bit-pipeline container to TrueNAS from a machine WITHOUT Docker
# (works from Mac, work laptop, etc). Source is tarballed, SCP'd to TrueNAS, and built
# there via the TrueNAS REST API cronjob pattern. Same approach as Navi's deploy.
#
# Prereq (one-time, see DEPLOY.md):
#   /mnt/pool/apps/8bit-pipeline/
#   ├── docker-compose.yml    (from deploy/docker-compose.yml)
#   ├── .env                  (ANTHROPIC_API_KEY, ZERNIO_API_KEY, …)
#   ├── config/oauth2client.json  (Google OAuth Desktop client)
#   └── data/                 (container writes intermediate artifacts here)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TRUENAS_IP="${TRUENAS_IP:-192.168.4.2}"
TRUENAS_API_KEY="${TRUENAS_API_KEY:?set TRUENAS_API_KEY in config/.env or the shell}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
REMOTE_APP_DIR="/mnt/pool/apps/8bit-pipeline"
REMOTE_SRC="/tmp/8bit-pipeline-src.tar.gz"
REMOTE_BUILD="/tmp/8bit-pipeline-build"
LOCAL_SRC="/tmp/8bit-pipeline-src.tar.gz"

echo "==> Tarballing repo (scripts/ + deploy/ + assets/{fonts,brand}/ — dashboard, data, .venv excluded)"
cd "$REPO_ROOT"
tar czf "$LOCAL_SRC" \
  --exclude='.venv' \
  --exclude='.git' \
  --exclude='dashboard' \
  --exclude='node_modules' \
  --exclude='data' \
  --exclude='docs' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='*.tar.gz' \
  scripts/ \
  deploy/ \
  assets/fonts/ \
  assets/brand/ \
  CLAUDE.md

echo "==> SCP to TrueNAS ($TRUENAS_IP)"
scp -i "$SSH_KEY" "$LOCAL_SRC" "truenas_admin@${TRUENAS_IP}:${REMOTE_SRC}"
scp -i "$SSH_KEY" deploy/docker-compose.yml "truenas_admin@${TRUENAS_IP}:${REMOTE_APP_DIR}/docker-compose.yml"

echo "==> Triggering build + deploy via TrueNAS cronjob API"
BUILD_CMD="rm -rf ${REMOTE_BUILD}; mkdir -p ${REMOTE_BUILD} && tar xzf ${REMOTE_SRC} -C ${REMOTE_BUILD} && cd ${REMOTE_BUILD} && DOCKER_BUILDKIT=0 docker build --no-cache -f deploy/Dockerfile -t 8bit-pipeline:latest . > /tmp/8bit-pipeline-build.log 2>&1 && docker stop 8bit-pipeline 2>/dev/null; docker rm 8bit-pipeline 2>/dev/null; cd ${REMOTE_APP_DIR} && docker compose up -d >> /tmp/8bit-pipeline-build.log 2>&1 && echo DEPLOY_SUCCESS >> /tmp/8bit-pipeline-build.log || echo DEPLOY_FAILED >> /tmp/8bit-pipeline-build.log"

# JSON-encode the command so embedded quotes survive
CMD_JSON=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$BUILD_CMD")

RESPONSE=$(curl -s -X POST "http://${TRUENAS_IP}/api/v2.0/cronjob" \
  -H "Authorization: Bearer ${TRUENAS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"user\":\"root\",\"command\":${CMD_JSON},\"description\":\"Deploy 8bit-pipeline\",\"schedule\":{\"minute\":\"0\",\"hour\":\"0\",\"dom\":\"1\",\"month\":\"1\",\"dow\":\"0\"},\"enabled\":false}")

CRONJOB_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")

if [[ -z "$CRONJOB_ID" ]]; then
  echo "FAILED to create deploy cronjob. Response:"
  echo "$RESPONSE"
  exit 1
fi

echo "==> Running cronjob $CRONJOB_ID (builds image + recreates container)"
curl -s -X POST "http://${TRUENAS_IP}/api/v2.0/cronjob/run" \
  -H "Authorization: Bearer ${TRUENAS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"id\": $CRONJOB_ID}" > /dev/null

echo "==> Polling build log (up to 4 min)…"
for i in $(seq 1 48); do
  sleep 5
  STATUS=$(ssh -i "$SSH_KEY" "truenas_admin@${TRUENAS_IP}" "tail -1 /tmp/8bit-pipeline-build.log 2>/dev/null" || true)
  echo "    [${i}x5s] ${STATUS}"
  if [[ "$STATUS" == *DEPLOY_SUCCESS* ]] || [[ "$STATUS" == *DEPLOY_FAILED* ]]; then
    break
  fi
done

echo "==> Cleaning up cronjob"
curl -s -X DELETE "http://${TRUENAS_IP}/api/v2.0/cronjob/id/${CRONJOB_ID}" \
  -H "Authorization: Bearer ${TRUENAS_API_KEY}" > /dev/null

echo ""
echo "==> Container status:"
ssh -i "$SSH_KEY" "truenas_admin@${TRUENAS_IP}" "docker ps --filter name=8bit-pipeline --format 'table {{.Names}}\t{{.Status}}'"

echo ""
echo "==> Last 20 log lines:"
ssh -i "$SSH_KEY" "truenas_admin@${TRUENAS_IP}" "docker logs --tail 20 8bit-pipeline 2>&1" || true

echo ""
echo "==> If anything broke, full build log: ssh truenas_admin@${TRUENAS_IP} 'cat /tmp/8bit-pipeline-build.log'"
