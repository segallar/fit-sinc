#!/usr/bin/env bash
# One-time GetSync host bootstrap (Ubuntu 22.04+).
# Usage:
#   ssh root@breeze.romansegalla.online 'bash -s' < scripts/ci/bootstrap-host.sh
# Or from repo root after deploy path exists:
#   GETSYNC_SSH_HOST=breeze.romansegalla.online ./scripts/ci/bootstrap-host.sh

set -euo pipefail

if [[ -n "${GETSYNC_SSH_HOST:-}" ]] && [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  exec ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
    "root@${GETSYNC_SSH_HOST}" 'bash -s' < "${BASH_SOURCE[0]}"
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  python3 python3-pip python3-venv \
  python3.11 python3.11-venv \
  nginx certbot python3-certbot-nginx \
  rsync git curl ufw

useradd -r -d /opt/getsync -s /usr/sbin/nologin getsync 2>/dev/null || true
mkdir -p /opt/getsync/data/logs /opt/getsync/.cache
chown -R getsync:getsync /opt/getsync

if [[ -f /opt/getsync/deploy/getsync.service ]]; then
  cp /opt/getsync/deploy/getsync.service /etc/systemd/system/getsync.service
  systemctl daemon-reload
  systemctl enable getsync
fi

systemctl enable nginx
systemctl start nginx 2>/dev/null || true

echo "Bootstrap done. Next:"
echo "  1. sync .env + data: ./scripts/ci/sync-from-prod.sh (from Mac)"
echo "  2. nginx: scp deploy/nginx/breeze.conf → /etc/nginx/conf.d/ && certbot"
echo "  3. deploy: GETSYNC_SSH_HOST=<host> ./scripts/ci/deploy.sh"
