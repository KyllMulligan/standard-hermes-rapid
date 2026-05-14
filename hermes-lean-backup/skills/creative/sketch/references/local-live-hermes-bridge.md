# Local live HTML + Hermes bridge (single-page iterative workflow)

Use when user wants one page continuously refined (not multiple variants).

## Minimal flow

1. Create page: `index.html`
2. Start local server
3. Add `/hermes` endpoint that shells out to Hermes CLI
4. Add frontend fetch to `/hermes`
5. Add busy-state animation + cooldown reset
6. Add `/servername` endpoint + dynamic `<h1>`/`document.title`

## Backend pattern (Python stdlib)

- Base: `ThreadingHTTPServer` + `SimpleHTTPRequestHandler`
- `POST /hermes`:
  - parse JSON `{message}`
  - run: `hermes chat -q <message> -Q`
  - timeout guard (~120s)
  - return `{reply}` JSON
- `GET /servername`:
  - return `SERVER_NAME` env var if set
  - else `socket.gethostname()`

## Frontend pattern

- Root class toggle: `.app.busy`
- While busy:
  - hide/disable input area
  - show spinner
  - expand output panel height with transition
- After response:
  - render text to output log
  - keep expanded for 5s
  - collapse + restore input/focus

## Spinner text cycle (polish)

Rotate phrases every ~1.2s with short fade/translate transition:

- "Hermes is thinking..."
- "Hermes is reasoning..."
- "Hermes is writing..."

Stop interval on exit from busy state and reset phrase.

## Verification checklist

- `curl http://127.0.0.1:<port>/servername` returns JSON
- `curl -X POST /hermes` returns a real model reply JSON
- page source contains busy-state classes and spinner-cycle JS
- manual check: input hides during call, output expands, returns after 5s
