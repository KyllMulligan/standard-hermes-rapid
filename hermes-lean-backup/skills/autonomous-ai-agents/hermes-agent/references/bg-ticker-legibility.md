# Background ticker legibility for local web UIs

Use this when a local Hermes web bridge includes animated telemetry text in the background.

## Symptoms
- Text appears crowded or overlapping during vertical scroll.
- Rapid motion makes status text hard to parse.
- Wrapping causes jagged column breaks and visual noise.

## Stable tuning sequence
1. Slow scroll first.
   - Increase animation duration (e.g., `30s -> 80–120s`) before changing layout.
2. Control wrapping behavior intentionally.
   - Prefer `white-space: pre` for fixed-line telemetry blocks.
   - If overlap appears with `pre`, keep `pre` and increase spacing/padding before re-enabling wrapping.
3. Increase vertical rhythm.
   - Raise `line-height` (e.g., toward `1.7–1.9`).
   - Increase block padding (e.g., `16px 24px` or more).
4. Then adjust density/contrast.
   - Optionally lower background layer opacity if still noisy.

## Suggested baseline CSS
```css
.bg-lines {
  white-space: pre;
  word-break: normal;
  overflow-wrap: normal;
  line-height: 1.8;
  padding: 16px 24px;
  animation: bgUp 85s linear infinite;
}
```

## Safety check after edits
- Re-open the edited CSS block and verify brace balance (`{}`) before finishing.
- If concurrent edits are possible, re-read the file before a second patch.
