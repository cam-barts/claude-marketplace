---
description: Append an entry to today's Captain's Log
argument-hint: <task summary> [state] [author]
---

Append a timestamped entry to today's Captain's Log (`Journals/Captains Log/YYYY-MM-DD.md`), in the format the log has used since June 2026. Creates the day's file if it doesn't exist.

## Arguments

- `task` (required) — one line: what the work was. Link the page it touched: `Fix the ETag path ([[Repositories/sb-cli]])`.
- `state` (optional, default: `done`) — `done` | `in progress` | `blocked` | `awaiting <thing>` (e.g. `awaiting signature`).
- `author` (optional) — who's writing. Defaults to `claude (interactive session with Cam)` in an interactive session. Autonomous runs use their own name (`barbossa-worker`, `claude-code`).

The body — what happened, what was found, what's left — is composed from the session, not passed as an argument.

## Entry format

```markdown
## 14:05 — claude-code
**Task:** Integrate the edge server features into `sb-cli` ([[Repositories/sb-cli]])
**State:** awaiting signature

Prose paragraphs: what was done, what was surprising, what was verified and how.
Name commits, paths, and counts. Link the pages touched.

- [ ] Follow-up that needs Cam #agent [assignee: cam] [author: claude-code] [created: 2026-09-04] [priority: medium]
```

- Heading: `## HH:MM — author` (local 24h time). Interactive sessions use a hyphen and a parenthetical: `## 03:40 - claude (interactive session with Cam)`.
- `**Tier:**` appears only on Barbossa's autonomous entries (`opus → claude-opus-5`); leave it out otherwise.
- Follow-ups for Cam are **tasks** at the end of the entry, with the full attribute set — see [`task_patterns.md`](../skills/silverbullet-workflow/references/task_patterns.md). This is how work gets handed back; it's what `/sb-tasks` pulls.
- Don't `--sign` log entries: the heading already names the author.

## Steps

1. **Resolve the page and time** in the local timezone:

   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   TODAY=$(date +%Y-%m-%d)
   NOW=$(date +%H:%M)
   PAGE="Journals/Captains Log/${TODAY}"
   ```

2. **Pull first** so you append to the server's latest copy, not a stale one — Barbossa writes here around the clock:

   ```bash
   cd ~/silverbullet && sb --no-input sync pull 2>&1 | tail -1
   ```

3. **Compose the entry** into `$ENTRY` (heading, `**Task:**`, `**State:**`, blank line, body, optional tasks). If the day's file doesn't exist yet, prefix the page heading:

   ```bash
   test -f ~/silverbullet/"${PAGE}.md" || ENTRY="# Captain's Log — ${TODAY}
   ${ENTRY}"
   ```

4. **Append.** `sb page append` handles the leading newline and creates the file if needed. It writes the **local** file:

   ```bash
   sb --no-input page append "$PAGE" --content "$ENTRY"
   ```

5. **Push and confirm** nothing was refused:

   ```bash
   sb --no-input sync push 2>&1 | tail -1
   ```

   Expect `Push complete: 1 uploaded, 0 conflicts, … 0 failed`. A conflict means someone wrote the log in between — `sb sync resolve "${PAGE}.md" --diff`, keep both entries, never drop Barbossa's.

6. **Surface the link:**

   ```text
   Logged to [[Journals/Captains Log/YYYY-MM-DD]].
   Open: https://bullet.coder.cam/Journals/Captains%20Log/YYYY-MM-DD
   ```

## Style

- Prose, not bullets — the log is read later, by Cam. Lead with the outcome, then the surprise, then the evidence.
- Be concrete: commit hashes, file paths, counts, what was verified live versus in tests.
- Name what's **left**, as tasks with an owner, not as a vague "next steps" paragraph.
- A day roll-up, when asked for, goes at the bottom under `## Day summary`.

## See also

- [`task_patterns.md`](../skills/silverbullet-workflow/references/task_patterns.md) — task anatomy and the handoff patterns
- [`/sb-inbox`](sb-inbox.md) — the other half of a handoff
