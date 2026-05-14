# Model/Provider Switcher (Allowlist) for Local Hermes Web Bridges

Use this pattern when a local web UI should let users switch between a small, pre-approved set of model/provider pairs.

## Why allowlist
- Prevent arbitrary provider/model writes from the browser.
- Keep UX simple: users choose named presets, not raw config fields.
- Makes error handling predictable when a provider is missing credentials.

## Backend contract

### 1) Define presets

```python
MODEL_OPTIONS = [
  {"id":"codex-main","label":"GPT-5.3 Codex (openai-codex)","provider":"openai-codex","model":"gpt-5.3-codex"},
  {"id":"sonnet4","label":"Claude Sonnet 4 (openrouter)","provider":"openrouter","model":"anthropic/claude-sonnet-4"},
  {"id":"gpt5","label":"GPT-5 (openrouter)","provider":"openrouter","model":"openai/gpt-5"},
]
```

### 2) Expose read endpoint
`GET /model-options` returns:

```json
{
  "options": [...],
  "current": {"provider":"...","model":"..."}
}
```

Use `current` for frontend preselect.

### 3) Expose apply endpoint
`POST /set-model` accepts:

```json
{"option_id":"sonnet4"}
```

Server behavior:
1. Validate `option_id` exists in `MODEL_OPTIONS`.
2. Run both commands (same resolved Hermes binary):
   - `hermes config set model.provider <provider>`
   - `hermes config set model.default <model>`
3. Refresh live state metadata.
4. Return `{ok,message,meta}`.

## Frontend contract
- On page load, fetch `/model-options`, populate `<select>`, preselect current pair.
- On Apply click, POST `/set-model`.
- On success: refresh model/provider display immediately.
- On failure: show returned error text inline (don’t fail silently).

## Verification checklist
1. `GET /model-options` returns options + current pair.
2. `POST /set-model` with each valid option returns `ok:true`.
3. `GET /hermes-info` reflects changed provider/model.
4. Next `/hermes` response metadata matches selected provider/model.

## Common pitfalls
- PATH drift in daemonized server process causes `hermes` not found.
  - Fix with resolved binary fallback (`shutil.which("hermes") or "/home/<user>/.local/bin/hermes"`).
- Using different binaries for chat vs config detection causes mismatch/stale `unknown` metadata.
- OpenRouter presets fail without configured key/access; surface actionable message to user.
