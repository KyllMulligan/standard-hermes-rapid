# Loading-state choreography for local HTML chat prototypes

Use this pattern when a user wants a dramatic but controlled request/response interaction in a one-page chat-style prototype.

## Goal

During a pending request:
1. hide/disable the input area,
2. show an explicit loading indicator,
3. smoothly expand the output panel upward,
4. after response arrives, hold expanded state briefly,
5. then collapse back and restore input.

## Recommended implementation

### 1) Drive state with one root class

Toggle a single class (e.g. `.app.busy`) on the app container. Let CSS derive all visual states.

- `.app.busy .input-wrap` → fade out + collapse height + disable pointer events
- `.app.busy .spinner` → visible with opacity/translate transition
- `.app.busy .output` → larger height

This prevents JS/CSS drift from setting many per-element styles manually.

### 2) Keep transitions smooth and coordinated

Use transitions on:
- `opacity`
- `transform` (small `translateY`)
- `max-height` for hide/show wrappers
- `height` for output expansion

Good defaults for this pattern:
- input fade/slide: ~300–450ms
- output expansion: ~550–700ms with eased cubic-bezier (e.g. `.2,.8,.2,1`)
- spinner pulse loop: ~900–1200ms

### 3) Request lifecycle

In submit handler:
- ignore submit if already busy,
- set busy immediately after logging user message,
- issue `fetch('/hermes', ...)`,
- append response or error to output,
- in `finally`, wait cooldown (e.g. 5000ms), then clear busy and refocus input.

### 4) Cooldown behavior

A short post-response hold (3–5s) improves perceived polish when the user requested cinematic motion.

Use one timeout handle (`pendingCooldown`) and clear it before starting a new request to avoid race conditions.

### 5) Accessibility baseline

- disable input during busy state to prevent duplicate submissions,
- optionally mark form `aria-hidden="true"` while hidden,
- set spinner text in an `aria-live="polite"` region,
- restore focus to the input when ready.

## Pitfalls

- Using `display: none` directly on animated elements (kills transitions). Prefer opacity/max-height/transform choreography.
- Expanding output without guarding re-submits (creates overlapping requests and UI flicker).
- Forgetting to restore focus after re-enable.
- Applying independent inline style toggles instead of one container state class.
