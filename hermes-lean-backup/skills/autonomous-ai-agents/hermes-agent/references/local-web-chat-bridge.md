# Local website ↔ Hermes bridge (simple HTTP server pattern)

Use this when a user asks to host a lightweight webpage and wire a text box to Hermes responses.

## Pattern

- Serve static `index.html` with Python `http.server` subclass.
- Add `POST /hermes` endpoint in the same handler.
- In `POST /hermes`, call:

```bash
hermes chat -q "<message>" -Q
```

- Return JSON to frontend:

```json
{"reply":"...","meta":{...}}
```

## Recommended companion endpoints

- `GET /servername` → returns `SERVER_NAME` env var fallback to `socket.gethostname()`.
- `GET /hermes-info` → returns UI metadata:
  - `model`
  - `provider`
  - `calls`
  - `last_input_tokens`
  - `last_output_tokens`
  - `total_estimated_tokens`

## Model/provider detection detail

`hermes config` output is formatted text and often includes:

```text
Model: {'default': '...', 'provider': '...'}
```

Robust parse approach:
1. regex extract dict after `Model:`
2. parse with `ast.literal_eval`
3. fallback to line-based parsing for `provider:` / `default:`

## Token display note

If exact usage is not exposed from command output, use explicit "estimated" labels. A lightweight estimate is `round(len(text)/4)`.

## Frontend UX behavior that worked well

- While waiting for `/hermes` response:
  - hide/disable input
  - show spinner text cycle (thinking/reasoning/writing)
  - expand output panel with smooth transition
- After response:
  - keep expanded for 5 seconds
  - collapse and re-enable input

## Ops checklist

- Run server in Hermes-managed background process (not shell `&`).
- Verify:
  - `curl /servername`
  - `curl /hermes-info`
  - `curl -X POST /hermes ...`
- If server code changes, restart process and re-check endpoints.
