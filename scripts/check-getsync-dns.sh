#!/usr/bin/env bash
# Email via external SMTP when getsync.me resolves in public DNS.
#
# Config: ~/.config/getsync/dns-notify.env (see scripts/dns-notify.env.example)
#
# Test SMTP only (no DNS check, no state file):
#   ./scripts/check-getsync-dns.sh --test-smtp
#
# Cron:
#   */15 * * * * /Users/roman/getsync/scripts/check-getsync-dns.sh >>/tmp/getsync-dns-check.log 2>&1

set -euo pipefail

TEST_SMTP=0
if [[ "${1:-}" == "--test-smtp" ]]; then
  TEST_SMTP=1
elif [[ -n "${1:-}" ]]; then
  echo "Usage: $0 [--test-smtp]" >&2
  exit 1
fi

ENV_FILE="${GETSYNC_DNS_ENV_FILE:-$HOME/.config/getsync/dns-notify.env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a && source "$ENV_FILE" && set +a
fi

DOMAIN="${GETSYNC_DNS_DOMAIN:-getsync.me}"
APP_DOMAIN="${GETSYNC_DNS_APP_DOMAIN:-app.getsync.me}"
EXPECTED="${GETSYNC_DNS_EXPECTED_IP:-134.209.133.187}"
TO="${GETSYNC_DNS_NOTIFY_TO:-}"
STATE="${GETSYNC_DNS_STATE_FILE:-$HOME/.getsync-dns-notified}"
HOST_LABEL="$(hostname -s 2>/dev/null || hostname)"

require() {
  local name="$1" val="$2"
  if [[ -z "$val" ]]; then
    echo "Missing $name — set in $ENV_FILE" >&2
    exit 1
  fi
}

require GETSYNC_DNS_NOTIFY_TO "$TO"
require GETSYNC_DNS_SMTP_HOST "${GETSYNC_DNS_SMTP_HOST:-}"
require GETSYNC_DNS_SMTP_USER "${GETSYNC_DNS_SMTP_USER:-}"
require GETSYNC_DNS_SMTP_PASS "${GETSYNC_DNS_SMTP_PASS:-}"

send_smtp() {
  local subject="$1" body="$2"
  export GETSYNC_DNS_MAIL_TO="$TO" GETSYNC_DNS_MAIL_SUBJECT="$subject"
  printf '%s' "$body" | python3 <<'PY'
import os
import smtplib
import sys
from email.message import EmailMessage

body = sys.stdin.read()
to = os.environ["GETSYNC_DNS_MAIL_TO"]
subject = os.environ["GETSYNC_DNS_MAIL_SUBJECT"]
host = os.environ["GETSYNC_DNS_SMTP_HOST"]
port = int(os.environ.get("GETSYNC_DNS_SMTP_PORT", "587"))
user = os.environ["GETSYNC_DNS_SMTP_USER"]
password = os.environ["GETSYNC_DNS_SMTP_PASS"]
from_addr = os.environ.get("GETSYNC_DNS_SMTP_FROM", user)
use_ssl = os.environ.get("GETSYNC_DNS_SMTP_SSL", "0") == "1"
use_tls = os.environ.get("GETSYNC_DNS_SMTP_TLS", "1" if not use_ssl else "0") == "1"

msg = EmailMessage()
msg["Subject"] = subject
msg["From"] = from_addr
msg["To"] = to
msg.set_content(body)

if use_ssl:
    smtp = smtplib.SMTP_SSL(host, port, timeout=30)
else:
    smtp = smtplib.SMTP(host, port, timeout=30)
with smtp:
    if use_tls:
        smtp.starttls()
    smtp.login(user, password)
    smtp.send_message(msg)
PY
}

if [[ "$TEST_SMTP" -eq 1 ]]; then
  subject="GetSync DNS notify — SMTP test"
  body=$(cat <<EOF
Test message from check-getsync-dns.sh on $HOST_LABEL.

SMTP: ${GETSYNC_DNS_SMTP_HOST}:${GETSYNC_DNS_SMTP_PORT:-587}
If you received this, Gmail SMTP is configured correctly.

Current DNS (for info):
  $DOMAIN     $(dig +short "$DOMAIN" A 2>/dev/null | head -1 || echo '<empty>')
  $APP_DOMAIN $(dig +short "$APP_DOMAIN" A 2>/dev/null | head -1 || echo '<empty>')
EOF
  )
  send_smtp "$subject" "$body"
  echo "Test email sent to $TO"
  exit 0
fi

if [[ -f "$STATE" ]]; then
  exit 0
fi

resolve() {
  dig +short "$1" A 2>/dev/null | grep -E '^[0-9.]+$' | head -1 | tr -d '\r'
}

root_ip="$(resolve "$DOMAIN")"
app_ip="$(resolve "$APP_DOMAIN")"

if [[ -z "$root_ip" && -z "$app_ip" ]]; then
  exit 0
fi

warn=""
if [[ -n "$EXPECTED" ]]; then
  if [[ -n "$root_ip" && "$root_ip" != "$EXPECTED" ]]; then
    warn+=" $DOMAIN -> $root_ip (expected $EXPECTED);"
  fi
  if [[ -n "$app_ip" && "$app_ip" != "$EXPECTED" ]]; then
    warn+=" $APP_DOMAIN -> $app_ip (expected $EXPECTED);"
  fi
fi

subject="GetSync DNS live: $DOMAIN"
body=$(cat <<EOF
Public DNS now resolves GetSync domains (checked from $HOST_LABEL).

  $DOMAIN     A  ${root_ip:-<none>}
  $APP_DOMAIN A  ${app_ip:-<none>}
  expected IP:   $EXPECTED

Verify:
  dig +short $DOMAIN
  dig +short $APP_DOMAIN

Next on sirocco:
  certbot certonly --webroot -w /var/www/html -d getsync.me -d app.getsync.me --non-interactive --agree-tos
${warn:+
Warning:$warn}
EOF
)

send_smtp "$subject" "$body"

mkdir -p "$(dirname "$STATE")"
{
  echo "notified_at=$(date -Iseconds 2>/dev/null || date)"
  echo "domain=$DOMAIN root=$root_ip app=$app_ip"
} >"$STATE"
echo "Sent notification to $TO via ${GETSYNC_DNS_SMTP_HOST}"
