# Local Hermes Web UI Bridge Pattern (Durable + Observable)

Use this when building a lightweight local webpage that calls Hermes via a local HTTP endpoint.

## Backend shape (simple + effective)

- Serve static UI + API endpoints from one Python process (`ThreadingHTTPServer`).
- Keep `/hermes` as a POST endpoint that shells out to:
  - `hermes chat -q "<message>" -Q`
- Return JSON with both response text and lightweight metadata:
  - `reply`
  - `meta.model`, `meta.provider`
  - `meta.calls`, `meta.last_input_tokens`, `meta.last_output_tokens`, `meta.total_estimated_tokens`
- Add two read-only endpoints for UI hydration:
  - `/servername` (hostname or env override)
  - `/hermes-info` (current model/provider + counters)

## UI layout pattern (from iterative user feedback)

1. **Keep top indicators separate**
   - Machine/server name: absolute **top-center**.
   - Server status + latency chip: absolute **top-right**.
   - Do not merge these into a single full-width top row.

2. **Status chip should be compact**
   - Keep it narrow (`~10vw`, with sane clamps like `clamp(150px, 10vw, 220px)`).
   - Truncate text with ellipsis instead of expanding across the page.

3. **Background telemetry should focus on the visitor**
   - Prefer client/visitor signals only (UA, locale, TZ, device/network hints, referrer, arrival time).
   - Remove page/self-descriptive lines (URL/origin/path/model/provider/token counters) if the user asks for accessor-only telemetry.

4. **Ticker readability tuning**
   - Slower scroll speed improves legibility.
   - If overlap occurs, increase line-height/padding first.
   - If user prefers no wrapping, use `white-space: pre` and adjust spacing to avoid collisions.

## Reliability UX pattern

1. **Top-right status chip**
   - Poll `/hermes-info` every ~3s.
   - Show `online/offline` + measured latency ms.
2. **Busy-state lock during request**
   - Hide/disable input while a request is in-flight.
   - Show spinner with rotating phrases.
   - Expand output panel while waiting; collapse after cooldown.
3. **Background telemetry ticker (optional)**
   - Subtle dark scrolling text using client-observable signals only.

## Pitfall

Background processes launched ad-hoc can disappear after service restarts/session changes.

## Durable run recommendation

Prefer a supervisor for local demos you care about:

- `systemd --user` (recommended on Linux)
- `pm2` / `supervisord` (alternative)

At minimum, expose a health endpoint and include in-page connection state so outages are immediately visible.

## Notes

- Token counts in this pattern are lightweight estimates unless your backend emits true usage counters.
- Keep all telemetry local if you promise no third-party analytics.
