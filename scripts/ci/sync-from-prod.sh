#!/usr/bin/env bash
# Copy .env and data/ from prod VPS to staging (via local temp — rsync cannot remote→remote).
#
#   KEY=~/.ssh/id_ed25519
#   GETSYNC_SOURCE_HOST=sirocco.romansegalla.online \
#   GETSYNC_TARGET_HOST=breeze.romansegalla.online \
#   ./scripts/ci/sync-from-prod.sh

set -euo pipefail

: "${GETSYNC_SOURCE_HOST:=sirocco.romansegalla.online}"
: "${GETSYNC_TARGET_HOST:=breeze.romansegalla.online}"
: "${KEY:=${HOME}/.ssh/id_ed25519}"
: "${TMPDIR:=/tmp/getsync-migrate}"

RSYNC=(rsync -avz -e "ssh -i ${KEY} -o BatchMode=yes")

echo "Source: ${GETSYNC_SOURCE_HOST}"
echo "Target: ${GETSYNC_TARGET_HOST}"
echo "Temp:   ${TMPDIR}"

mkdir -p "${TMPDIR}/data"

"${RSYNC[@]}" "root@${GETSYNC_SOURCE_HOST}:/opt/getsync/.env" "${TMPDIR}/"
"${RSYNC[@]}" "root@${GETSYNC_SOURCE_HOST}:/opt/getsync/data/" "${TMPDIR}/data/"

ssh -i "${KEY}" -o BatchMode=yes "root@${GETSYNC_TARGET_HOST}" \
  'mkdir -p /opt/getsync/data'

"${RSYNC[@]}" "${TMPDIR}/.env" "root@${GETSYNC_TARGET_HOST}:/opt/getsync/.env"
"${RSYNC[@]}" "${TMPDIR}/data/" "root@${GETSYNC_TARGET_HOST}:/opt/getsync/data/"

ssh -i "${KEY}" -o BatchMode=yes "root@${GETSYNC_TARGET_HOST}" \
  'chown -R getsync:getsync /opt/getsync && chmod 600 /opt/getsync/.env'

echo "Done. Verify:"
echo "  ssh root@${GETSYNC_TARGET_HOST} 'test -f /opt/getsync/.env && test -f /opt/getsync/data/getsync.db && echo ok'"
