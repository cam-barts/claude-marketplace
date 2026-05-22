---
documentation_type: reference
---

# Task patterns in Cam's space

How Cam structures tasks in SilverBullet, what the query looks like, and what NOT to track as a task.

## Anatomy of a task

A task is a Markdown checklist bullet with attributes inline:

```markdown
- [ ] Fix the headless-Chrome bridge wedge investigation [assignee:cam] [priority:medium] [created:2026-05-19]
- [/] Audit Windmill variables integrity [assignee:barbossa] [priority:high] [wip_by:local_9402e31d] [wip_at:2026-05-20T14:00:00Z]
- [x] Phase 6: hybrid embedding layer via Ollama [assignee:barbossa] [completed:2026-05-21]
```

States:

- `- [ ]` — open
- `- [/]` — in progress (claimed by an agent fire)
- `- [x]` — done
- `- [~]` — abandoned / cancelled

Attributes (in `[key:value]` inline-bracket form, all optional):

- `[assignee:cam]` or `[assignee:barbossa]` — owner. No assignee = nobody owns it.
- `[priority:high|medium|low]` — sort key
- `[created:YYYY-MM-DD]` — when the task was filed
- `[completed:YYYY-MM-DD]` — when it closed
- `[wip_by:<session_id>]` `[wip_at:<ISO8601>]` — claim metadata while in progress

## The correct query

SilverBullet indexes tasks as `index.tag "task"` objects with fields including `done: bool`, `state: " "/"x"/"~"`, `assignee`, `priority`, `created`, `name`, `page`, `pos`. **There is no `status` field.**

The right way to pull open tasks assigned to barbossa:

```bash
sb query 'from index.tag "task" where assignee == "barbossa" and done == false and not table.includes(itags, "meta/template/slash") order by priority desc, created desc'
```

The `not table.includes(itags, "meta/template/slash")` exclusion filters out template scaffolding so example tasks inside slash-command templates don't show up in real work pulls.

Substitute `assignee == "cam"` for Cam's tasks, or drop the assignee filter to see everything.

### The query that DOES NOT work

```bash
# WRONG — there is no `status` field. Returns {} silently.
sb query '... where status == "open" or status == "in_progress" ...'
```

An earlier version of this skill used the `status ==` form and was the source of multiple days of false "SB index lag" reports. Two days of Barbossa fires fell through to filesystem-grep mode because the query returned empty — not from index lag, from a non-existent field. Cleaned up 2026-05-22.

## Pulling from the filesystem

When you don't want to depend on the SB server (or want a sanity-check against the index):

```bash
grep -rEn '^\s*-\s*\[ \].*\[assignee:cam\]' ~/silverbullet/ 2>/dev/null \
  | grep -v '/Captains Log/' \
  | head -50
```

This catches `- [ ]` bullets with the `[assignee:cam]` marker, excluding journal entries. Replace `cam` with `barbossa` for Barbossa's set.

## Tasks vs bullets

A task implies **action** and an **owner**. A bullet is anything that doesn't satisfy both.

- ✅ Task: `- [ ] Confirm Meilisearch data dir is in borgmatic [assignee:cam]` — there is a specific action and someone owns it
- ❌ Not a task: `- Consider mxbai-embed-large after a week of use` — this is a consideration, not committed work; if it stays a bullet it's clearer
- ✅ Task: `- [ ] Bisect remaining plugs for headless-Chrome readiness [assignee:barbossa]` — specific action, owned
- ❌ Not a task: `- The bridge wedge might be silversearch` — observation, not action

Don't promote considerations to tasks just because they're written down. Bullets are fine for thinking; tasks are commitments.

## Captain's Log + tasks

When Barbossa completes a task in a fire, the Captain's Log entry references it:

```markdown
**Task picked:** [[Projects/SilverBullet Fast Search]] — confirm Meilisearch data dir in backup. Found two redundant paths (gastown rsnapshot + warrig borgmatic); restore procedure documented. Marked `[x]` on the task line.
```

This makes the audit trail across the log + project doc consistent.

## See also

- The companion `silverbullet` plugin's SKILL.md — covers the `sb query` syntax in more depth
- `/sb-tasks` slash command — runs the corrected query and renders the result
- `[[Projects/SilverBullet Chrome Runtime Issue]]` in Cam's space — the wedge investigation that was over-reported because of the malformed query
