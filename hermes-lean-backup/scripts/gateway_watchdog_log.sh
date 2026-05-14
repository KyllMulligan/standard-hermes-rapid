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

# Extra signal: hermes gateway status command responsiveness
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

# Stay silent in no_agent mode (stdout empty) unless script crashes.
exit 0
