# Session cleanup by pattern (keep matching, delete rest)

Use this when you need to preserve only sessions matching a text marker in the `hermes sessions list` table (for example, keep entries whose preview contains `[Fatal7x]`).

## Why this exists
`hermes sessions delete <ID>` prompts for confirmation. In non-interactive loops this often results in silent cancellation unless you pass `--yes`.

## Safe workflow
1. Preview current sessions:

```bash
hermes sessions list --limit 1000
```

2. Build target IDs (keep matches, delete everything else), then delete with non-interactive confirmation:

```bash
python3 - <<'PY'
import subprocess, re

KEEP_MARKER = "[Fatal7x]"

res = subprocess.run(["hermes", "sessions", "list", "--limit", "1000"], capture_output=True, text=True)
lines = res.stdout.splitlines()
id_re = re.compile(r'(\d{8}_\d{6}_[0-9a-f]+)$')

delete_ids = []
keep_ids = []
for line in lines:
    m = id_re.search(line.strip())
    if not m:
        continue
    sid = m.group(1)
    if KEEP_MARKER in line:
        keep_ids.append(sid)
    else:
        delete_ids.append(sid)

print(f"Keeping {len(keep_ids)}; deleting {len(delete_ids)}")
for sid in delete_ids:
    subprocess.run(["hermes", "sessions", "delete", "--yes", sid], check=False)

print("\nRemaining:")
print(subprocess.run(["hermes", "sessions", "list", "--limit", "1000"], capture_output=True, text=True).stdout)
PY
```

3. Manually confirm remaining sessions match intent.

## Pitfalls
- Do not omit `--yes` in scripted deletions.
- Match only table rows ending with valid session IDs to avoid parsing header/separator lines.
- Use a high enough `--limit` or you'll only clean the visible subset.