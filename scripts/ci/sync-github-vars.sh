#!/usr/bin/env bash
# Set GitHub Actions repository variables for deploy (run after: gh auth login).
# Usage: ./scripts/ci/sync-github-vars.sh [owner/repo]

set -euo pipefail

REPO="${1:-segallar/getsync}"

set_var() {
  local name="$1" value="$2"
  echo "SET $name=$value"
  gh variable set "$name" --body "$value" --repo "$REPO"
}

del_var() {
  local name="$1"
  if gh variable list --repo "$REPO" --json name -q ".[] | select(.name==\"$name\") | .name" 2>/dev/null | grep -qx "$name"; then
    echo "DEL $name"
    gh variable delete "$name" --repo "$REPO"
  fi
}

set_var GETSYNC_SSH_HOST "sirocco.romansegalla.online"
set_var GETSYNC_SSH_USER "root"
set_var GETSYNC_DEPLOY_PATH "/opt/getsync"

for old in FIT_SINC_SSH_HOST FIT_SINC_SSH_USER FIT_SINC_DEPLOY_PATH; do
  del_var "$old"
done

echo "OK — variables for $REPO:"
gh variable list --repo "$REPO"
