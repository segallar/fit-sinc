#!/usr/bin/env bash
# Smoke: HTTPS /health on prod and staging.
#
#   ./scripts/ci/verify-hosts.sh

set -euo pipefail

check() {
  local name="$1" url="$2"
  printf '%-8s %s … ' "$name" "$url"
  if body="$(curl -sf --max-time 12 "$url")"; then
  if echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('status')=='ok'" 2>/dev/null; then
      commit="$(echo "$body" | python3 -c "import json,sys; print(json.load(sys.stdin).get('commit','?'))" 2>/dev/null || echo '?')"
      num="$(echo "$body" | python3 -c "import json,sys; print(json.load(sys.stdin).get('deploy_number','?'))" 2>/dev/null || echo '?')"
      echo "ok commit=${commit} deploy#${num}"
      return 0
    fi
    echo "bad json"
    return 1
  else
    echo "FAIL"
    return 1
  fi
}

failed=0
check prod "https://app.getsync.me/health" || failed=1
check staging "https://breeze.romansegalla.online/health" || failed=1

if [[ "$failed" != 0 ]]; then
  exit 1
fi
echo "All hosts OK"
