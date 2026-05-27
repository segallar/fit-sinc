#!/usr/bin/env bash
# Deploy GetSync to sirocco via rsync + systemd restart.
# CI: set SSH_PRIVATE_KEY (file), optional GETSYNC_SSH_HOST / GETSYNC_SSH_USER / GETSYNC_DEPLOY_PATH.
# Speed: rsync --chown (no chown -R), skip pip when pyproject.toml unchanged (editable install),
# health poll from 0s (1s between retries).

set -euo pipefail

: "${GETSYNC_SSH_HOST:=sirocco.romansegalla.online}"
: "${GETSYNC_SSH_USER:=root}"
: "${GETSYNC_DEPLOY_PATH:=/opt/getsync}"
HOST="$GETSYNC_SSH_HOST"
SSH_USER="$GETSYNC_SSH_USER"
DEPLOY_PATH="$GETSYNC_DEPLOY_PATH"
SERVICE_USER=getsync
SERVICE_UNIT=getsync
DEPS_MARKER=".pyproject.sha256"
PLAYWRIGHT_MARKER=".playwright-chromium.ok"
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
if [[ -z "${DEPLOY_NUMBER}" ]]; then
  last="$(
    ssh "${SSH_OPTS[@]}" "${SSH_USER}@${HOST}" \
      "python3 -c \"import json; from pathlib import Path; p=Path('${DEPLOY_PATH}/getsync/_build_meta.json');
print(int(json.loads(p.read_text()).get('deploy_number') or 0)) if p.is_file() else 0\"" \
      2>/dev/null || echo "0"
  )"
  if [[ "${last}" == "0" ]]; then
    : "${GETSYNC_PUBLIC_HEALTH_URL:=https://romansegalla.online/health}"
    last="$(
      curl -sf --max-time 8 "${GETSYNC_PUBLIC_HEALTH_URL}" 2>/dev/null \
        | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(d.get('deploy_number') or 0))" 2>/dev/null \
        || echo "0"
    )"
  fi
  DEPLOY_NUMBER=$((last + 1))
  log "manual deploy #${DEPLOY_NUMBER} (previous: ${last})"
fi
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
PLAYWRIGHT_MARKER="${PLAYWRIGHT_MARKER}"

mkdir -p "\${DEPLOY_PATH}/data/logs"
chown "\${SERVICE_USER}:\${SERVICE_USER}" "\${DEPLOY_PATH}/data/logs" 2>/dev/null || true

# Права только на код (не data/, .venv/, .env) — fallback если rsync без --chown (macOS openrsync)
while IFS= read -r -d '' item; do
  chown -R "\${SERVICE_USER}:\${SERVICE_USER}" "\$item"
done < <(find "\${DEPLOY_PATH}" -mindepth 1 -maxdepth 1 \
  ! -name data ! -name .venv ! -name .env ! -name '.*' -print0 2>/dev/null)

new_hash=\$(sha256sum "\${DEPLOY_PATH}/pyproject.toml" | awk '{print \$1}')
old_hash=\$(cat "\${DEPLOY_PATH}/\${DEPS_MARKER}" 2>/dev/null || true)
pip_changed=0
if [[ "\$new_hash" != "\$old_hash" ]]; then
  echo "pyproject.toml changed — pip install -e ."
  sudo -u \${SERVICE_USER} bash -c "cd \${DEPLOY_PATH} && .venv/bin/pip install -e ."
  echo "\$new_hash" > "\${DEPLOY_PATH}/\${DEPS_MARKER}"
  pip_changed=1
else
  echo "pyproject.toml unchanged — skip pip (editable install)"
fi
sudo -u \${SERVICE_USER} bash -c "cd \${DEPLOY_PATH} && .venv/bin/python -c \"
import cryptography
from getsync.credentials.store import CredentialStore
from getsync.web.app import app
print('import_ok', app.version)
\""

playwright_ok=0
if [[ -f "\${DEPLOY_PATH}/\${PLAYWRIGHT_MARKER}" ]]; then
  playwright_ok=1
fi
if [[ "\$pip_changed" == "1" ]] || [[ "\$playwright_ok" != "1" ]]; then
  echo "Playwright — install Chromium to \${DEPLOY_PATH}/.cache/ms-playwright"
  mkdir -p "\${DEPLOY_PATH}/.cache"
  chown "\${SERVICE_USER}:\${SERVICE_USER}" "\${DEPLOY_PATH}/.cache"
  if ! sudo -u \${SERVICE_USER} env \
      HOME="\${DEPLOY_PATH}" \
      PLAYWRIGHT_BROWSERS_PATH="\${DEPLOY_PATH}/.cache/ms-playwright" \
      bash -c "cd '\${DEPLOY_PATH}' && .venv/bin/playwright install chromium"; then
    echo "playwright install chromium failed — trying install-deps (needs apt libraries)" >&2
    "\${DEPLOY_PATH}/.venv/bin/playwright" install-deps chromium || true
    sudo -u \${SERVICE_USER} env \
      HOME="\${DEPLOY_PATH}" \
      PLAYWRIGHT_BROWSERS_PATH="\${DEPLOY_PATH}/.cache/ms-playwright" \
      bash -c "cd '\${DEPLOY_PATH}' && .venv/bin/playwright install chromium"
  fi
  chown -R "\${SERVICE_USER}:\${SERVICE_USER}" "\${DEPLOY_PATH}/.cache"
  pw_ver=\$(sudo -u \${SERVICE_USER} "\${DEPLOY_PATH}/.venv/bin/python" -c "import playwright; print(playwright.__version__)" 2>/dev/null || echo "unknown")
  echo "playwright=\${pw_ver} chromium_ok" > "\${DEPLOY_PATH}/\${PLAYWRIGHT_MARKER}"
  chown "\${SERVICE_USER}:\${SERVICE_USER}" "\${DEPLOY_PATH}/\${PLAYWRIGHT_MARKER}"
else
  echo "Playwright Chromium already installed — skip"
fi

systemctl restart \${SERVICE_UNIT}
ok=0
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if [[ \$attempt -gt 1 ]]; then
    sleep 2
  fi
  if systemctl is-active --quiet \${SERVICE_UNIT} \
     && curl -sf http://127.0.0.1:8080/health >/dev/null; then
    ok=1
    break
  fi
  echo "waiting for \${SERVICE_UNIT} (attempt \${attempt}/10)..." >&2
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
