#!/usr/bin/env bash
# Patch romansegalla server block in nginx default (sirocco).
set -euo pipefail

DEFAULT="${1:-/etc/nginx/sites-available/default}"
ENABLED="${2:-/etc/nginx/sites-enabled/romansegalla.online}"

rm -f "$ENABLED"

python3 - "$DEFAULT" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text()
proxy = """
\tlocation /webhooks/ {
\t\tproxy_pass http://127.0.0.1:8080;
\t\tproxy_http_version 1.1;
\t\tproxy_set_header Host $host;
\t\tproxy_set_header X-Real-IP $remote_addr;
\t\tproxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
\t\tproxy_set_header X-Forwarded-Proto $scheme;
\t}

\tlocation /static/ {
\t\tproxy_pass http://127.0.0.1:8080;
\t\tproxy_set_header Host $host;
\t}

\tlocation /favicon.ico {
\t\tproxy_pass http://127.0.0.1:8080;
\t\tproxy_set_header Host $host;
\t}

\tlocation / {
\t\tproxy_pass http://127.0.0.1:8080;
\t\tproxy_http_version 1.1;
\t\tproxy_set_header Host $host;
\t\tproxy_set_header X-Real-IP $remote_addr;
\t\tproxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
\t\tproxy_set_header X-Forwarded-Proto $scheme;
\t}
"""
pattern = re.compile(
    r"(server_name romansegalla\.online www\.romansegalla\.online;.*?)"
    r"\tlocation /health \{[^}]+\}\n\n"
    r"\tlocation / \{[^}]+\}\n",
    re.DOTALL,
)
new_text, n = pattern.subn(r"\1" + proxy + "\n", text, count=1)
if n != 1:
    raise SystemExit(f"romansegalla block not patched (matches={n})")
path.write_text(new_text)
print(f"Patched {path}")
PY

nginx -t
systemctl reload nginx
echo "nginx OK"
