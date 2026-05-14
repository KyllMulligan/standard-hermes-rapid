# Local-hosted chat prototype pattern (HTML + `/hermes` route)

Use when user asks for:
- a single-page dark/brand-themed site,
- centered input + bottom output panel,
- and a local "receive calls" behavior.

## Proven flow
1. Build `index.html` with three vertical zones:
   - top header/title,
   - center input form,
   - bottom scrollable output console.
2. JS submit handler:
   - append user line to output,
   - `fetch('/hermes', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message}) })`,
   - render `data.reply` or error line.
3. Host with custom Python server (not static-only `http.server`) that supports `POST /hermes` and returns JSON.
4. Verify both:
   - `GET /` returns expected HTML markers,
   - `POST /hermes` returns valid JSON.

## Minimal response contract
```json
{ "reply": "..." }
```

## Common pitfall
- Serving with `python -m http.server` and expecting `/hermes` to work. It won't; endpoint must be implemented explicitly.
