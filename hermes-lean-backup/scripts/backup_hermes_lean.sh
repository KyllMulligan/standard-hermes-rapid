#!/usr/bin/env bash
set -euo pipefail

set -a
source /home/rapiduser/.hermes/.env
set +a

: "${GH_TOKEN:?GH_TOKEN is required in /home/rapiduser/.hermes/.env}"

USER_LOGIN=$(curl -fsS -H "Authorization: token $GH_TOKEN" https://api.github.com/user | python3 -c 'import sys,json; print(json.load(sys.stdin)["login"])')
REPO_NAME="${HERMES_BACKUP_REPO:-standard-hermes-rapid}"
BACKUP_DIR_IN_REPO="hermes-lean-backup"
REPO_URL="https://${GH_TOKEN}@github.com/${USER_LOGIN}/${REPO_NAME}.git"

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

STATUS=$(curl -s -o /tmp/gh_repo_status.json -w '%{http_code}' -H "Authorization: token $GH_TOKEN" "https://api.github.com/repos/${USER_LOGIN}/${REPO_NAME}")
if [ "$STATUS" != "200" ]; then
  echo "Target repo ${USER_LOGIN}/${REPO_NAME} is not accessible with this token (HTTP $STATUS)."
  cat /tmp/gh_repo_status.json
  exit 1
fi

git clone -q "$REPO_URL" "$TMP_DIR/repo"
cd "$TMP_DIR/repo"

git config user.name "Hermes Backup Bot"
git config user.email "hermes-backup@local"

mkdir -p "$BACKUP_DIR_IN_REPO"
STAGE="$TMP_DIR/stage"
mkdir -p "$STAGE"

cp -f /home/rapiduser/.hermes/config.yaml "$STAGE/" 2>/dev/null || true
cp -f /home/rapiduser/.hermes/config.lock.json "$STAGE/" 2>/dev/null || true

# Redacted .env backup (do not store raw secrets in git)
if [ -f /home/rapiduser/.hermes/.env ]; then
  python3 - <<'PY'
import re
src='/home/rapiduser/.hermes/.env'
out='/tmp/hermes_env_redacted'
with open(src,'r',encoding='utf-8',errors='ignore') as f:
    lines=f.readlines()
red=[]
for line in lines:
    if '=' in line and not line.lstrip().startswith('#'):
        k,v=line.split('=',1)
        key=k.strip()
        if re.search(r'(TOKEN|KEY|SECRET|PASSWORD|PASS|API)', key, re.I):
            red.append(f"{key}=<redacted>\n")
        else:
            red.append(line)
    else:
        red.append(line)
with open(out,'w',encoding='utf-8') as f:
    f.writelines(red)
PY
  mv /tmp/hermes_env_redacted "$STAGE/.env.redacted"
fi

# Redacted auth summary
if [ -f /home/rapiduser/.hermes/auth.json ]; then
  python3 - <<'PY'
import json
src='/home/rapiduser/.hermes/auth.json'
out='/tmp/hermes_auth_redacted.json'
try:
    d=json.load(open(src))
except Exception:
    d={'note':'unreadable auth.json'}
summary={'keys': list(d.keys()) if isinstance(d,dict) else [], 'note':'secrets removed'}
json.dump(summary, open(out,'w'), indent=2)
PY
  mv /tmp/hermes_auth_redacted.json "$STAGE/auth.redacted.json"
fi

if [ -d /home/rapiduser/.hermes/skills ]; then
  cp -a /home/rapiduser/.hermes/skills "$STAGE/"
fi
if [ -d /home/rapiduser/.hermes/profiles ]; then
  cp -a /home/rapiduser/.hermes/profiles "$STAGE/"
fi

# Local hosted website files (if present)
mkdir -p "$STAGE/website"
cp -f /tmp/fatal_site/index.html "$STAGE/website/" 2>/dev/null || true
cp -f /tmp/fatal_site/server.py "$STAGE/website/" 2>/dev/null || true

# Website persistence/service artifacts
mkdir -p "$STAGE/systemd-user"
cp -f /home/rapiduser/.config/systemd/user/fatal-site.service "$STAGE/systemd-user/" 2>/dev/null || true
cp -f /home/rapiduser/.config/systemd/user/hermes-gateway.service "$STAGE/systemd-user/" 2>/dev/null || true

# Cron/script artifacts used for ops automation
mkdir -p "$STAGE/scripts"
cp -f /home/rapiduser/.hermes/scripts/backup_hermes_lean.sh "$STAGE/scripts/" 2>/dev/null || true
cp -f /home/rapiduser/.hermes/scripts/gateway_watchdog_log.sh "$STAGE/scripts/" 2>/dev/null || true

DATE_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
printf "last_backup_utc=%s\nrepo=%s/%s\n" "$DATE_UTC" "$USER_LOGIN" "$REPO_NAME" > "$STAGE/BACKUP_METADATA.txt"

# Cron jobs snapshot
if command -v hermes >/dev/null 2>&1; then
  hermes cron list --all > "$STAGE/cron-jobs.txt" 2>&1 || {
    echo "failed to capture cron list" > "$STAGE/cron-jobs.txt"
  }
fi

rm -rf "$BACKUP_DIR_IN_REPO"/*
cp -a "$STAGE"/. "$BACKUP_DIR_IN_REPO"/

git add "$BACKUP_DIR_IN_REPO"
if git diff --cached --quiet; then
  echo "No backup changes at ${DATE_UTC}"
  exit 0
fi

git commit -q -m "Hermes lean backup ${DATE_UTC}"
git push -q origin HEAD

echo "Backup pushed to ${USER_LOGIN}/${REPO_NAME}:${BACKUP_DIR_IN_REPO} at ${DATE_UTC}"