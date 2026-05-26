#!/usr/bin/env bash
# One-time VPS migration: fit_sinc → getsync (user, /opt path, systemd unit).
# Run on sirocco as root: bash deploy/scripts/migrate-fit-sinc-to-getsync.sh

set -euo pipefail

OLD_USER=fit_sinc
NEW_USER=getsync
OLD_DIR=/opt/fit_sinc
NEW_DIR=/opt/getsync
OLD_UNIT=fit-sinc
NEW_UNIT=getsync

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi

if [[ -d "$NEW_DIR" && ! -d "$OLD_DIR" ]]; then
  echo "Already migrated: $NEW_DIR exists, $OLD_DIR missing"
  exit 0
fi

if [[ ! -d "$OLD_DIR" ]]; then
  echo "Missing $OLD_DIR — nothing to migrate" >&2
  exit 1
fi

echo "Stopping $OLD_UNIT..."
systemctl stop "$OLD_UNIT" 2>/dev/null || true

if ! id "$NEW_USER" &>/dev/null; then
  echo "Creating user $NEW_USER..."
  useradd -r -d "$NEW_DIR" -s /usr/sbin/nologin "$NEW_USER"
fi

if [[ ! -d "$NEW_DIR" ]]; then
  echo "Moving $OLD_DIR → $NEW_DIR..."
  mv "$OLD_DIR" "$NEW_DIR"
fi

echo "Fixing ownership..."
chown -R "$NEW_USER:$NEW_USER" "$NEW_DIR"

if [[ -d "$NEW_DIR/.venv" ]]; then
  echo "Recreating venv (paths break after directory move)..."
  rm -rf "$NEW_DIR/.venv"
  sudo -u "$NEW_USER" python3.12 -m venv "$NEW_DIR/.venv"
  sudo -u "$NEW_USER" "$NEW_DIR/.venv/bin/pip" install -q -e "$NEW_DIR"
fi

data_dir="$NEW_DIR/data"
if [[ -f "$data_dir/fit_sinc.db" && ! -e "$data_dir/getsync.db" ]]; then
  echo "Renaming fit_sinc.db → getsync.db..."
  mv "$data_dir/fit_sinc.db" "$data_dir/getsync.db"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
svc_src="${GETSYNC_SERVICE_FILE:-$SCRIPT_DIR/../getsync.service}"
if [[ ! -f "$svc_src" && -f /tmp/getsync.service ]]; then
  svc_src=/tmp/getsync.service
fi
if [[ ! -f "$svc_src" ]]; then
  echo "Missing getsync.service (set GETSYNC_SERVICE_FILE)" >&2
  exit 1
fi
cp "$svc_src" "/etc/systemd/system/${NEW_UNIT}.service"

systemctl daemon-reload
systemctl enable "$NEW_UNIT"
systemctl start "$NEW_UNIT"
systemctl disable "$OLD_UNIT" 2>/dev/null || true

sleep 2
systemctl is-active --quiet "$NEW_UNIT"
curl -sf http://127.0.0.1:8080/health >/dev/null

echo "OK: $NEW_UNIT active, data at $NEW_DIR"
echo "Optional cleanup: userdel $OLD_USER (if unused)"
