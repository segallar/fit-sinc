#!/usr/bin/env bash
# Deploy GetSync to sirocco via rsync + systemd restart.
# CI: set SSH_PRIVATE_KEY (file), optional GETSYNC_SSH_HOST / GETSYNC_SSH_USER / GETSYNC_DEPLOY_PATH.
# Legacy env names FIT_SINC_* are still accepted.
#
# Speed: rsync --chown (no chown -R), skip pip when pyproject.toml unchanged (editable install),
# health poll from 0s (1s between retries).

set -euo pipefail

: "${GETSYNC_SSH_HOST:=${FIT_SINC_SSH_HOST:-sirocco.romansegalla.online}}"
: "${GETSYNC_SSH_USER:=${FIT_SINC_SSH_USER:-root}}"
: "${GETSYNC_DEPLOY_PATH:=${FIT_SINC_DEPLOY_PATH:-/opt/getsync}}"
HOST="$GETSYNC_SSH_HOST"
SSH_USER="$GETSYNC_SSH_USER"
DEPLOY_PATH="$GETSYNC_DEPLOY_PATH"
SERVICE_USER=getsync
SERVICE_UNIT=getsync
DEPS_MARKER=".pyproject.sha256"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o BatchMode=yes)

log() {
  echo "[deploy +${SECONDS}s] $*"
}

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

RSYNC_OPTS=(-avz --delete --exclude-from=.rsyncignore)
if [[ "$SSH_USER" == "root" ]] && rsync --help 2>&1 | grep -q -- '--chown'; then
  RSYNC_OPTS+=(--chown="${SERVICE_USER}:${SERVICE_USER}")
fi

log "rsync → ${SSH_USER}@${HOST}:${DEPLOY_PATH}"
rsync "${RSYNC_OPTS[@]}" ./ "${SSH_USER}@${HOST}:${DEPLOY_PATH}/"

log "remote restart + health"
ssh "${SSH_OPTS[@]}" "${SSH_USER}@${HOST}" bash -s <<EOF
set -euo pipefail
DEPLOY_PATH="${DEPLOY_PATH}"
SERVICE_USER="${SERVICE_USER}"
SERVICE_UNIT="${SERVICE_UNIT}"
DEPS_MARKER="${DEPS_MARKER}"

# Права только на код (не data/, .venv/, .env) — fallback если rsync без --chown (macOS openrsync)
while IFS= read -r -d '' item; do
  chown -R "\${SERVICE_USER}:\${SERVICE_USER}" "\$item"
done < <(find "\${DEPLOY_PATH}" -mindepth 1 -maxdepth 1 \
  ! -name data ! -name .venv ! -name .env ! -name '.*' -print0 2>/dev/null)

new_hash=\$(sha256sum "\${DEPLOY_PATH}/pyproject.toml" | awk '{print \$1}')
old_hash=\$(cat "\${DEPLOY_PATH}/\${DEPS_MARKER}" 2>/dev/null || true)
if [[ "\$new_hash" != "\$old_hash" ]]; then
  echo "pyproject.toml changed — pip install -e ."
  sudo -u \${SERVICE_USER} bash -c "cd \${DEPLOY_PATH} && .venv/bin/pip install -e ."
  echo "\$new_hash" > "\${DEPLOY_PATH}/\${DEPS_MARKER}"
else
  echo "pyproject.toml unchanged — skip pip (editable install)"
fi

systemctl restart \${SERVICE_UNIT}
ok=0
for attempt in 1 2 3 4 5 6; do
  if [[ \$attempt -gt 1 ]]; then
    sleep 1
  fi
  if systemctl is-active --quiet \${SERVICE_UNIT} \
     && curl -sf http://127.0.0.1:8080/health >/dev/null; then
    ok=1
    break
  fi
  echo "waiting for \${SERVICE_UNIT} (attempt \${attempt}/6)..." >&2
done
if [[ "\$ok" != 1 ]]; then
  echo "Deploy health check failed" >&2
  systemctl status \${SERVICE_UNIT} --no-pager >&2 || true
  journalctl -u \${SERVICE_UNIT} -n 40 --no-pager >&2 || true
  exit 1
fi
curl -sf http://127.0.0.1:8080/health
echo ""
EOF

log "done — ${SSH_USER}@${HOST}:${DEPLOY_PATH}"
