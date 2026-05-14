# Live Status + Telemetry + Background Ticker Pattern (Local Hosted HTML)

Use this pattern when building chat-like prototype pages that should feel alive and self-monitoring.

## When to apply
- User asks for resilience signals ("did service die?", "is it connected?")
- User wants top-right status with online/offline and latency
- User wants ambient, data-driven background motion (subtle scrolling text)
- Prototype already has local backend routes (e.g., `/hermes`, `/hermes-info`, `/servername`)

## Backend contract
Expose lightweight JSON endpoints:

1. `GET /servername` → `{ "servername": "..." }`
2. `GET /hermes-info` →
   - `provider`
   - `model`
   - `calls`
   - `last_input_tokens`
   - `last_output_tokens`
   - `total_estimated_tokens`
3. `POST /hermes` → `{ "reply": "...", "meta": { ...same info... } }`

Notes:
- Token counts can be estimated (e.g., `len(text)/4`) if exact usage is unavailable.
- Keep response fields stable so UI can update without defensive branching.

## Frontend pattern

### 1) Status chip (top-right)
- Absolute positioned chip with:
  - colored dot
  - `Server: online • Nms` or `Server: offline`
- Poll every ~3s:
  - `const start = performance.now()`
  - fetch `/hermes-info` with `cache: 'no-store'`
  - latency = `performance.now() - start`
- Toggle classes:
  - `.online` = green border/dot glow
  - `.offline` = red border/dot glow

### 2) Live metadata row above output
Render model/provider/token/call stats in compact monospace panel.
- Populate on load from `/hermes-info`
- Refresh on:
  - each status poll success
  - each chat response (`data.meta`)

### 3) Ambient scrolling background text
- Add a non-interactive layer behind UI (`pointer-events:none`, low contrast)
- Two duplicated text blocks (`bg-lines`, `bg-lines-clone`) moving upward continuously for seamless loop
- Populate ticker text with dynamic values:
  - uptime since page load
  - server name
  - model/provider
  - calls/tokens
  - status string + timestamp
- Refresh ticker text every 1s; keep color dark gray to avoid legibility issues

### 4) Layering safety
- Put background layer at lower z-index
- Force foreground elements above it (`.app > :not(.bg-scroll) { z-index: 2; }`)
- Add mask gradient for cinematic fade top/bottom and reduced visual noise

## UX constraints learned from iteration
- Prefer smooth transitions over abrupt jumps (opacity/transform/height)
- While request is pending: hide/disable input and show spinner
- After response: keep expanded output briefly (e.g., 5s) then restore input area
- Keep status chip always visible, independent of busy state

## Verification checklist
- `GET /hermes-info` returns 200 and expected keys
- Status chip flips online/offline by stopping/starting server
- Latency value updates over time
- Metadata row changes after POST `/hermes`
- Background ticker scrolls continuously and remains subtle/readable
