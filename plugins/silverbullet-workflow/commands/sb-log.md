---
description: Append an entry to today's Captain's Log
argument-hint: <task summary> [result]
---

Append an entry to today's Captain's Log (`Journals/Captains Log/YYYY-MM-DD.md`). The log is Barbossa's daily note: with `~/.config/sb-barbossa/env` sourced, `SB_DAILY_PATH` points `sb daily` at it, so logging is just `sb daily`. Format since 2026-11-18; older days were back-ported.

## Arguments

- `task` (required): one line saying what the work was. Link the page it touched: `Fix the ETag path ([[Repositories/sb-cli]])`.
- `result` (optional, default: `done`): `done` | `in progress` | `blocked` | `awaiting <thing>` (e.g. `awaiting signature`).

The body (what happened, what was found, what is left) is composed from the session, not passed as an argument.

## Entry format

Each entry is one `sb daily` item. `sb` adds the `[time:: HH:MM]` stamp; `--sign @barbossa` credits the author (it never queues a mention). The headline carries the task link and a `[result:: …]` attribute; prose paragraphs follow on stdin and stay indented inside the item:

```markdown
* [time:: 14:05] Integrate the edge server features into `sb-cli` ([[Repositories/sb-cli]]) [result:: awaiting signature]

  Prose paragraphs: what was done, what was surprising, what was verified and how.
  Name commits, paths, and counts. Link the pages touched. -- @barbossa
* [ ] [time:: 14:05] Sign the 3 commits on `feat/edge` in `~/git_local/sb-cli`, then merge @cam [author: barbossa] [created: 2026-11-18] [priority: medium] #agent -- @barbossa
```

- `result`, not `state`: `state` is a reserved field on task items. Query it: `sb query 'from index.tag "item" where page:startsWith("Journals/Captains Log/") and result == "blocked"'`.
- Autonomous worker entries also carry `[tier:: …] [model:: …]`; interactive entries don't, which is what tells them apart.
- Follow-ups for Cam are separate `--task-tag agent` entries addressed with an `@cam` mention (that puts them in his Mention Inbox; `[assignee:]` is legacy) and the full attribute set from [`task_patterns.md`](../skills/silverbullet-workflow/references/task_patterns.md). Use plain `--task` for a Barbossa-owned task.

## Steps

1. **Set up as Barbossa** (this is what routes `sb daily` to the log, not to Cam's Inbox):

   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   . ~/.config/sb-barbossa/env
   cd ~/silverbullet
   ```

2. **Pull first.** Barbossa writes here around the clock.

   ```bash
   sb --no-input sync pull 2>&1 | tail -1
   ```

3. **Append** the entry (headline + body on stdin), then any follow-up tasks. `sb daily` writes the **local** file:

   ```bash
   printf '%s\n\n%s\n' "$HEADLINE [result:: done]" "$BODY" | sb --no-input daily --sign @barbossa
   sb --no-input daily --task-tag agent --sign @barbossa "Follow-up … @cam [author: barbossa] [created: $(date +%F)] [priority: medium]"
   ```

   Missed a day? Prefix the text with `yesterday:` or `YYYY-MM-DD:`, or pass `--on YYYY-MM-DD`.

4. **Push and confirm** nothing was refused:

   ```bash
   sb --no-input sync push 2>&1 | tail -1
   ```

   Expect `Push complete: 1 uploaded, 0 conflicts, … 0 failed`. A conflict means someone wrote the log in between. Run `sb sync resolve "Journals/Captains Log/$(date +%F).md" --diff`, keep both entries, never drop Barbossa's.

5. **Surface the link:**

   ```text
   Logged to [[Journals/Captains Log/YYYY-MM-DD]].
   Open: https://bullet.coder.cam/Journals/Captains%20Log/YYYY-MM-DD
   ```

## Reading the log

`sb daily` read mode works on the log once the env is sourced: `sb daily -n 20`, `--contains zotero`, `--from 2026-11-01 --to 2026-11-07`, `--starred`, `--tags agent`.

## Style

- Prose, not bullets: the log is read later, by Cam. Lead with the outcome, then the surprise, then the evidence.
- Be concrete: commit hashes, file paths, counts, what was verified live versus in tests.
- Name what's **left**, as tasks with an owner, not as a vague "next steps" paragraph.
- A day roll-up, when asked for, is a `--star` entry starting `Day summary:`.

## See also

- [`task_patterns.md`](../skills/silverbullet-workflow/references/task_patterns.md): task anatomy and the handoff patterns
- [`/sb-inbox`](sb-inbox.md): the other half of a handoff
