# Lean backup: include website/gateway service persistence artifacts

Use this when a user asks to ensure backups contain everything needed to recover local Hermes web integrations after restart/logout.

## Goal
Back up not just app code, but also persistence/control-plane artifacts that make services survive reboot/session changes.

## Required artifact classes
1) Website app files (if user-hosted locally)
- `website/index.html`
- `website/server.py`

2) User systemd unit files
- `systemd-user/fatal-site.service` (or whichever site unit is used)
- `systemd-user/hermes-gateway.service` (if present)

3) Operational scripts
- `scripts/backup_hermes_lean.sh`
- `scripts/gateway_watchdog_log.sh` (or equivalent watchdog script)

4) Scheduler inventory
- `cron-jobs.txt` from `hermes cron list --all`

## Patch pattern for backup script
Inside the staging section of `~/.hermes/scripts/backup_hermes_lean.sh`, add guarded copies:

- `mkdir -p "$STAGE/systemd-user"` then `cp ... || true`
- `mkdir -p "$STAGE/scripts"` then `cp ... || true`

Keep copies non-fatal (`|| true`) so optional files don't break the backup.

## Verification pattern (important)
After pushing backup, verify by cloning/pulling target repo and checking expected paths exist.
Do not assume inclusion from script edits alone.

Minimum verify list:
- `hermes-lean-backup/systemd-user/fatal-site.service`
- `hermes-lean-backup/scripts/backup_hermes_lean.sh`
- `hermes-lean-backup/scripts/gateway_watchdog_log.sh`
- `hermes-lean-backup/cron-jobs.txt`
- `hermes-lean-backup/website/server.py`

## Notes
- If website lives under `/tmp`, include a note that those files are ephemeral and may be absent later.
- Prefer promoting production website files to a persistent path, then backing up that persistent location.
