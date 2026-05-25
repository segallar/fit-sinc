#!/usr/bin/env bash
# Tailwind → fit_sinc/web/static/app.css (before rsync deploy).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND="${ROOT}/frontend"
OUT="${ROOT}/fit_sinc/web/static/app.css"

if [[ ! -f "${FRONTEND}/package.json" ]]; then
  echo "frontend/package.json not found" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found — install Node.js or commit app.css manually" >&2
  exit 1
fi

cd "${FRONTEND}"
if [[ ! -d node_modules ]] || [[ package-lock.json -nt node_modules ]]; then
  npm ci
fi
npm run build:css
echo "OK: ${OUT}"
