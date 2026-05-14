# Kanban dashboard quickstart (validated)

Use when a user asks to "set up Kanban in UI" or "get the dashboard up" quickly.

## Sequence

```bash
# 1) Initialize board (idempotent)
hermes kanban init

# 2) Confirm board + counts
hermes kanban boards list
hermes kanban stats

# 3) Start dashboard on localhost
hermes dashboard --host 127.0.0.1 --port 9119 --no-open

# 4) Verify health
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:9119
# expect: 200
```

## Notes

- `hermes kanban daemon` may still appear in help output but is deprecated in current builds.
  Dispatcher behavior is hosted by gateway; ensure `hermes gateway status` is active.
- If user is remote over SSH, tunnel dashboard:

```bash
ssh -L 9119:127.0.0.1:9119 <host>
```

Then open `http://127.0.0.1:9119` locally.
