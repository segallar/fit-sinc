#!/usr/bin/env bash
# Deploy fit_sinc to sirocco via rsync + systemd restart.
# CI: set SSH_PRIVATE_KEY (file), optional FIT_SINC_SSH_HOST / FIT_SINC_SSH_USER / FIT_SINC_DEPLOY_PATH.

set -euo pipefail

: "${FIT_SINC_SSH_HOST:=sirocco.romansegalla.online}"
: "${FIT_SINC_SSH_USER:=root}"
: "${FIT_SINC_DEPLOY_PATH:=/opt/fit_sinc}"
HOST="$FIT_SINC_SSH_HOST"
USER="$FIT_SINC_SSH_USER"
DEPLOY_PATH="$FIT_SINC_DEPLOY_PATH"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o BatchMode=yes)

if [[ -z "${SSH_PRIVATE_KEY:-}" ]]; then
  echo "SSH_PRIVATE_KEY is not set" >&2
  exit 1
fi

eval "$(ssh-agent -s)"
trap 'ssh-agent -k >/dev/null 2>&1 || true' EXIT
printf '%s\n' "$SSH_PRIVATE_KEY" | tr -d '\r' | ssh-add -

mkdir -p ~/.ssh
ssh-keyscan -H "$HOST" >> ~/.ssh/known_hosts 2>/dev/null || true

RSYNC_SSH="ssh ${SSH_OPTS[*]}"
export RSYNC_RSH="$RSYNC_SSH"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

rsync -avz --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.git' \
  --exclude 'data' \
  --exclude '.env' \
  --exclude '.DS_Store' \
  --exclude 'dist' \
  --exclude '*.egg-info' \
  ./ "${USER}@${HOST}:${DEPLOY_PATH}/"

ssh "${SSH_OPTS[@]}" "${USER}@${HOST}" bash -s <<EOF
set -euo pipefail
chown -R fit_sinc:fit_sinc ${DEPLOY_PATH}
sudo -u fit_sinc bash -c 'cd ${DEPLOY_PATH} && .venv/bin/pip install -e .'
systemctl restart fit-sinc
sleep 2
systemctl is-active fit-sinc
curl -sf http://127.0.0.1:8080/health
EOF

echo "Deploy OK: ${USER}@${HOST}:${DEPLOY_PATH}"
