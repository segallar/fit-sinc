#!/usr/bin/env bash
# Deploy GetSync to sirocco via rsync + systemd restart.
# CI: set SSH_PRIVATE_KEY (file), optional GETSYNC_SSH_HOST / GETSYNC_SSH_USER / GETSYNC_DEPLOY_PATH.
# Legacy env names FIT_SINC_* are still accepted.

set -euo pipefail

: "${GETSYNC_SSH_HOST:=${FIT_SINC_SSH_HOST:-sirocco.romansegalla.online}}"
: "${GETSYNC_SSH_USER:=${FIT_SINC_SSH_USER:-root}}"
: "${GETSYNC_DEPLOY_PATH:=${FIT_SINC_DEPLOY_PATH:-/opt/getsync}}"
HOST="$GETSYNC_SSH_HOST"
SSH_USER="$GETSYNC_SSH_USER"
DEPLOY_PATH="$GETSYNC_DEPLOY_PATH"
SERVICE_USER=getsync
SERVICE_UNIT=getsync
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

COMMIT="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || true)"
DEPLOY_NUMBER="${GETSYNC_DEPLOY_NUMBER:-${GITHUB_RUN_NUMBER:-}}"
DEPLOYED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 - "$COMMIT" "$DEPLOY_NUMBER" "$DEPLOYED_AT" <<'PY'
import json
import sys
from pathlib import Path

commit, number, deployed_at = sys.argv[1:4]
meta: dict[str, object] = {"deployed_at": deployed_at}
if commit:
    meta["commit"] = commit
if number:
    try:
        meta["deploy_number"] = int(number)
    except ValueError:
        meta["deploy_number"] = number
Path("getsync/_build_meta.json").write_text(
    json.dumps(meta, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
PY

rsync -avz --delete --exclude-from=.rsyncignore \
  ./ "${SSH_USER}@${HOST}:${DEPLOY_PATH}/"

ssh "${SSH_OPTS[@]}" "${SSH_USER}@${HOST}" bash -s <<EOF
set -euo pipefail
chown -R ${SERVICE_USER}:${SERVICE_USER} ${DEPLOY_PATH}
sudo -u ${SERVICE_USER} bash -c 'cd ${DEPLOY_PATH} && .venv/bin/pip install -e .'
systemctl restart ${SERVICE_UNIT}
ok=0
for attempt in 1 2 3 4 5 6; do
  sleep 2
  if systemctl is-active --quiet ${SERVICE_UNIT} \
     && curl -sf http://127.0.0.1:8080/health >/dev/null; then
    ok=1
    break
  fi
  echo "waiting for ${SERVICE_UNIT} (attempt \${attempt}/6)..." >&2
done
if [[ "\$ok" != 1 ]]; then
  echo "Deploy health check failed" >&2
  systemctl status ${SERVICE_UNIT} --no-pager >&2 || true
  journalctl -u ${SERVICE_UNIT} -n 40 --no-pager >&2 || true
  exit 1
fi
curl -sf http://127.0.0.1:8080/health
echo ""
EOF

echo "Deploy OK: ${SSH_USER}@${HOST}:${DEPLOY_PATH}"
