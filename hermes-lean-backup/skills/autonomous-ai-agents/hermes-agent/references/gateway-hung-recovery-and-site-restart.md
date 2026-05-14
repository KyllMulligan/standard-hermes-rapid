# Gateway hung recovery + local site restart verification

Use this when the user says the gateway is hung and also expects a local companion website to come back.

## Fast recovery runbook

1) Clear failed unit state and restart gateway service:

```bash
systemctl --user reset-failed hermes-gateway || true
hermes gateway start || true
hermes gateway status
```

2) If a local web bridge/demo site is expected, verify endpoint first (don't assume it survived restarts):

```bash
curl -fsS http://127.0.0.1:8080/hermes-info
```

3) If endpoint is down, relaunch directly from known project path (example):

```bash
python3 /tmp/fatal_site/server.py
```

4) Re-verify availability with a short retry loop:

```bash
for i in 1 2 3 4 5; do
  curl -fsS http://127.0.0.1:8080/hermes-info && break
  sleep 1
done
```

## Why this is durable

- `reset-failed` prevents a stale failed state from blocking restart attempts.
- Local ad-hoc website processes are often ephemeral; always health-check after gateway recovery.
- Final confirmation should include both service status (gateway) and endpoint response (site).
