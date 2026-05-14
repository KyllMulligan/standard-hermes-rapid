# Gateway watchdog logging via cron (script-only)

Use this when you want a low-noise health trail for Hermes gateway state without auto-remediation.

## Goal
Create a recurring check that logs:
- systemd gateway active/sub state
- MainPID + process state + runtime seconds
- quick `hermes gateway status` responsiveness
- a conservative "hung suspected" heuristic flag

## Script
Create `~/.hermes/scripts/gateway_watchdog_log.sh`:

```bash
#!/usr/bin/env bash
set -u

LOG_FILE="$HOME/.hermes/logs/gateway-watchdog.log"
mkdir -p "$(dirname "$LOG_FILE")"

ts="$(date -Is)"
host="$(hostname)"

active_state="unknown"
sub_state="unknown"
main_pid="0"
pid_state="na"
pid_elapsed="na"
hung_suspected="no"
reason=""

if command -v systemctl >/dev/null 2>&1; then
  active_state="$(systemctl --user show hermes-gateway.service -p ActiveState --value 2>/dev/null || echo unknown)"
  sub_state="$(systemctl --user show hermes-gateway.service -p SubState --value 2>/dev/null || echo unknown)"
  main_pid="$(systemctl --user show hermes-gateway.service -p MainPID --value 2>/dev/null || echo 0)"
fi

if [[ "$main_pid" =~ ^[0-9]+$ ]] && [[ "$main_pid" -gt 0 ]] && ps -p "$main_pid" >/dev/null 2>&1; then
  pid_state="$(ps -o stat= -p "$main_pid" 2>/dev/null | awk '{print $1}' || echo na)"
  pid_elapsed="$(ps -o etimes= -p "$main_pid" 2>/dev/null | tr -d ' ' || echo na)"
fi

# Hung heuristic:
# 1) service stuck activating/deactivating > 300s
# 2) main pid in uninterruptible sleep (D)
if [[ "$sub_state" == "activating" || "$sub_state" == "deactivating" ]]; then
  if [[ "$pid_elapsed" =~ ^[0-9]+$ ]] && [[ "$pid_elapsed" -gt 300 ]]; then
    hung_suspected="yes"
    reason="sub_state_${sub_state}_gt300s"
  fi
fi

if [[ "$pid_state" == D* ]]; then
  hung_suspected="yes"
  reason="pid_state_D"
fi

status_timeout="ok"
if ! timeout 20s hermes gateway status >/dev/null 2>&1; then
  status_timeout="timeout_or_error"
  if [[ "$hung_suspected" == "no" ]]; then
    hung_suspected="maybe"
    reason="status_timeout_or_error"
  fi
fi

printf "%s host=%s active=%s sub=%s pid=%s pid_state=%s pid_elapsed_s=%s status_check=%s hung=%s reason=%s\n" \
  "$ts" "$host" "$active_state" "$sub_state" "$main_pid" "$pid_state" "$pid_elapsed" "$status_timeout" "$hung_suspected" "$reason" \
  >> "$LOG_FILE"

# Keep stdout empty for no_agent cron silent mode.
exit 0
```

Then:

```bash
chmod +x ~/.hermes/scripts/gateway_watchdog_log.sh
~/.hermes/scripts/gateway_watchdog_log.sh
tail -n 3 ~/.hermes/logs/gateway-watchdog.log
```

## Cron job (preferred)
Use script-only cron so it is deterministic and quiet:

- `name`: `gateway-watchdog-log`
- `schedule`: `every 15m` (adjust as needed)
- `script`: `gateway_watchdog_log.sh` (relative to `~/.hermes/scripts/`)
- `no_agent`: `true`
- `deliver`: `local`

Rationale:
- no LLM tokens used
- no chat spam
- leaves a durable audit trail in `~/.hermes/logs/gateway-watchdog.log`

## Reading the log
Quick filters:

```bash
tail -n 50 ~/.hermes/logs/gateway-watchdog.log
grep 'hung=yes\|hung=maybe' ~/.hermes/logs/gateway-watchdog.log | tail -n 20
```

## Notes
- This is monitoring-only; no restart/kill actions are taken.
- For autoremediation, create a separate script and gate it with strict safeguards.