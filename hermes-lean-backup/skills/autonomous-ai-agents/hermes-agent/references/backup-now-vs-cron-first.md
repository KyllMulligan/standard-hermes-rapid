# Backup request triage: run now vs existing cron

When the user says “run the backup now”, do this sequence:

1. Check existing automation first:
   - `hermes cron list` (or `cronjob(action='list')` in-tool)
2. If a matching backup job already exists and is enabled:
   - confirm it exists and report next/last run status
   - if the user wants an immediate run, trigger the existing job (`hermes cron run <job_id>` / `cronjob(action='run', job_id=...)`) instead of re-implementing the backup manually
3. Only do manual `git add/commit/push` backup steps if:
   - no matching cron backup exists, or
   - the user explicitly asks to bypass cron

Why: avoids duplicate behavior, avoids drift from the scripted backup path, and preserves the user's established automation workflow.

Common pitfall:
- Jumping straight to manual `git push` can fail for session-local auth reasons even though the scheduled script path is already working.