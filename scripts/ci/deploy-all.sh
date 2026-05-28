#!/usr/bin/env bash
# Deploy to several VPS (comma-separated GETSYNC_SSH_HOSTS).
# Example:
#   SSH_PRIVATE_KEY="$(cat ~/.ssh/id_ed25519)" \
#   GETSYNC_SSH_HOSTS=breeze.romansegalla.online ./scripts/ci/deploy-all.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
: "${GETSYNC_SSH_HOSTS:=breeze.romansegalla.online}"

IFS=',' read -r -a _hosts <<< "${GETSYNC_SSH_HOSTS}"
if [[ "${#_hosts[@]}" -eq 0 ]]; then
  echo "GETSYNC_SSH_HOSTS is empty" >&2
  exit 1
fi

for _raw in "${_hosts[@]}"; do
  _host="${_raw#"${_raw%%[![:space:]]*}"}"
  _host="${_host%"${_host##*[![:space:]]}"}"
  [[ -z "${_host}" ]] && continue
  echo ""
  echo "========== ${_host} =========="
  GETSYNC_SSH_HOST="${_host}" "${ROOT}/scripts/ci/deploy.sh"
done

echo ""
echo "All hosts done: ${GETSYNC_SSH_HOSTS}"
