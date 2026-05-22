---
description: Pull Cam's (or Barbossa's) open tasks from the SilverBullet indexed view, using the correct done == false query
argument-hint: [assignee] [limit]
---

Pull the current open task set for an assignee. Renders a short table — page, name (truncated), priority, created date.

## Arguments

- `assignee` (optional, default: `cam`) — `cam`, `barbossa`, or any other string. Pass `*` to drop the assignee filter and see everything.
- `limit` (optional, default: `20`) — cap on results.

## Steps

1. **Verify `sb` is reachable first** — run `sb lua '"ok"'`. If it returns anything but `"ok"`, dispatch to `/sb-setup` instead of forcing the query.

2. **Build the query.** Use the **correct** filter — `done == false`, NOT `status == "open" or status == "in_progress"`. The latter is the malformed form that returns empty silently because SB tasks have no `status` field.

   ```bash
   ASSIGNEE="${1:-cam}"
   LIMIT="${2:-20}"

   if [ "$ASSIGNEE" = "*" ]; then
     FILTER='done == false and not table.includes(itags, "meta/template/slash")'
   else
     FILTER="assignee == \"$ASSIGNEE\" and done == false and not table.includes(itags, \"meta/template/slash\")"
   fi

   sb query "from index.tag \"task\" where $FILTER order by priority desc, created desc limit $LIMIT"
   ```

3. **Render the result.** The query returns a JSON list. Surface to the user as a compact markdown table:

   | Priority | Page | Task | Created |
   |----------|------|------|---------|
   | high     | Projects/X | Truncated name... | 2026-05-19 |

   Truncate task names at ~80 chars. Sort already done by the query (priority desc, created desc).

4. **Fallback to filesystem grep** if `sb query` returns `{}` AND the assignee is known to have open tasks. Don't auto-assume index lag — first verify the query syntax wasn't broken by an arg injection:

   ```bash
   grep -rEn '^\s*-\s*\[ \].*\[assignee:cam\]' ~/silverbullet/ 2>/dev/null \
     | grep -v '/Captains Log/' \
     | head -50
   ```

   If the grep returns results but `sb query` didn't, log a "real index/filesystem mismatch" note — that's worth investigating, not a routine event.

## Output expectations

- 1–20 tasks rendered in priority order
- Each task linked via wikilink to its source page
- A footer with total count and the query that ran (for debugging)

## See also

- [`task_patterns.md`](../skills/silverbullet-workflow/references/task_patterns.md) — full anatomy of a task
- [`/sb-setup`](sb-setup.md) — run if `sb query` fails
