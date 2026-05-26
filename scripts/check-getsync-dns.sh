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
VERBOSE=0
for arg in "$@"; do
  case "$arg" in
    --test-smtp) TEST_SMTP=1 ;;
    -v|--verbose) VERBOSE=1 ;;
    -h|--help)
      echo "Usage: $0 [--test-smtp] [-v|--verbose]" >&2
      exit 0
      ;;
    *)
      echo "Usage: $0 [--test-smtp] [-v|--verbose]" >&2
      exit 1
      ;;
  esac
done

log() {
  [[ "$VERBOSE" -eq 1 ]] && echo "$*" >&2
}

ENV_FILE="${GETSYNC_DNS_ENV_FILE:-$HOME/.config/getsync/dns-notify.env}"

# Load KEY=VALUE safely (passwords with spaces must be quoted in the env file).
load_env_file() {
  local file="$1" line key val
  [[ -f "$file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ ! "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      echo "Skip invalid line in $file: $line" >&2
      continue
    fi
    key="${BASH_REMATCH[1]}"
    val="${BASH_REMATCH[2]}"
    if [[ "$val" =~ ^\'(.*)\'$ ]]; then
      val="${BASH_REMATCH[1]}"
    elif [[ "$val" =~ ^\"(.*)\"$ ]]; then
      val="${BASH_REMATCH[1]}"
    fi
    export "$key=$val"
  done <"$file"
}

if [[ -f "$ENV_FILE" ]]; then
  load_env_file "$ENV_FILE"
  log "Loaded $ENV_FILE"
else
  log "No env file: $ENV_FILE"
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
try:
    with smtp:
        if use_tls:
            smtp.starttls()
        smtp.login(user, password)
        refused = smtp.send_message(msg)
        if refused:
            print(f"SMTP refused recipients: {refused}", file=sys.stderr)
            sys.exit(1)
        print(f"SMTP accept from={from_addr} to={to} subject={subject!r}", file=sys.stderr)
except smtplib.SMTPAuthenticationError as e:
    hint = ""
    if "Application-specific password" in str(e) or e.smtp_code == 534:
        hint = (
            "\nGmail: use an App Password, not your normal password.\n"
            "  https://myaccount.google.com/apppasswords\n"
            "  (2-Step Verification must be enabled on the Google account.)\n"
            "Put the 16-character password in GETSYNC_DNS_SMTP_PASS in dns-notify.env"
        )
    print(f"SMTP login failed: {e}{hint}", file=sys.stderr)
    sys.exit(1)
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
  log "SMTP user=$GETSYNC_DNS_SMTP_USER host=$GETSYNC_DNS_SMTP_HOST port=${GETSYNC_DNS_SMTP_PORT:-587} → $TO"
  send_smtp "$subject" "$body"
  echo "Test email accepted by Gmail for: $TO"
  echo "  • Inbox/Spam at $TO (not necessarily the Gmail login inbox)"
  echo "  • Sent folder of ${GETSYNC_DNS_SMTP_FROM:-$GETSYNC_DNS_SMTP_USER}"
  exit 0
fi

if [[ -f "$STATE" ]]; then
  log "Already notified ($STATE), exit"
  exit 0
fi

resolve() {
  dig +short "$1" A 2>/dev/null | grep -E '^[0-9.]+$' | head -1 | tr -d '\r'
}

root_ip="$(resolve "$DOMAIN")"
app_ip="$(resolve "$APP_DOMAIN")"

if [[ -z "$root_ip" && -z "$app_ip" ]]; then
  log "No public DNS yet for $DOMAIN / $APP_DOMAIN (dig empty), no email"
  exit 0
fi

log "DNS live: $DOMAIN=$root_ip $APP_DOMAIN=$app_ip"

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
