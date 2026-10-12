---
documentation_type: reference
---

# Task patterns in Cam's space

How Cam structures tasks in SilverBullet, what the query looks like, and what NOT to track as a task.

## Ownership: mentions, not assignee metadata

**Since 2026-10-11 ownership is expressed as an `@name` mention in the task line.**
`[assignee: cam]` is legacy: still read, still present on older tasks, but no longer the
thing to write. A mention lands in Cam's Mention Inbox, which he reads; `[assignee:]` only
surfaces if someone runs a query.

```markdown
- [ ] Confirm Meilisearch data dir is in borgmatic @cam #agent [author: barbossa] [created: 2026-10-11] [priority: medium]
```

Put `@cam` after the task text and **before** the `#tags` and `[attributes]`.

### A task is only a work item if it carries an inline hashtag

This is the rule that matters most, and getting it wrong is how an agent spams Cam's inbox.

`space/CONFIG.md` deliberately sets `config.set("index.task.all", false)` (see its
"Task Indexer Scope" section; decision logged 2026-05-12 in
`AI Generated/Barbossa/SilverBullet Tasks Workflow` § 3.5). With that flag off, the
indexer keeps only tasks with at least one **inline** hashtag:

```js
i || (a = a.filter(u => u.tag !== "task" || u.tags?.length))
```

So the space has two distinct kinds of checkbox:

| Shape | Meaning |
|---|---|
| `- [ ] … #agent` / `#shared` / `#review` | a real work item: indexed, queryable, belongs in the inbox |
| `- [ ] …` with no hashtag | a **document-semantic** checkbox — a step in a plan, a rubric row. NOT work. |

Measured 2026-10-11: 604 tagged tasks are indexed, 1396 untagged ones are not, with zero
mismatches either way. New agent tasks get a channel tag automatically from the slash
templates in `Library/Personal/Slash Templates/`.

**Therefore: only ever address a mention to a task that carries a channel tag.** Adding
`@cam` to an untagged checkbox misrepresents a document step as assigned work. This
mistake was made and reverted on 2026-10-11: 166 mentions were added off `[assignee: cam]`
alone, and 75 had to be stripped again because their tasks were untagged.

Note that `tags` on a task object is the **inline** hashtags only; `itags` additionally
carries tags inherited from the page frontmatter. The indexer filters on `tags`, so a page
tagged `project` does nothing for its untagged tasks.

### The other gotcha: rewording a task changes its downstream identity

`bugwarrior-silverbullet` derives `sbid` from `sha1(page + normalized task text)`, and the
indexed task name includes the mention. So editing task text orphans the old Taskwarrior
task and creates a new one. Adding mentions across the space on 2026-10-11 completed and
recreated 102 Taskwarrior tasks — one-time, nothing of Cam's lost (no `start`, no `due`),
but do not repeat it casually. Backfilling an explicit `[id: ...]` attribute makes `sbid`
stable and is the durable fix.

## Anatomy of a task

A task is a Markdown checklist bullet with attributes inline:

```markdown
- [ ] Add `192.168.1.88  bullet.coder.cam` to `/etc/hosts` on Warrig … #agent [assignee: cam] [author: claude-code] [created: 2026-09-04] [priority: low]
- [/] Audit Windmill variables integrity [assignee: barbossa] [priority: high] [wip_by: local_9402e31d] [wip_at: 2026-05-20T14:00:00Z]
- [x] Phase 6: hybrid embedding layer via Ollama [assignee: barbossa] [completed: 2026-05-21]
```

Cam writes attributes as `[key: value]` **with a space**; `[key:value]` also indexes the same way, but any grep has to allow both (`\[assignee: ?cam\]`). Bullets may be `-` or `*`.

States:

- `- [ ]` — open
- `- [/]` — in progress (claimed by an agent fire)
- `- [x]` — done
- `- [~]` — abandoned / cancelled

Attributes (inline `[key: value]`, all optional):

- `[assignee: cam]` / `[assignee: barbossa]` — **legacy** owner field. Read it on old
  tasks; write an `@name` mention instead. See the section above.
- `[author: claude-code]` / `[author: barbossa-worker]` — who filed it, when that isn't the owner
- `[priority: high|medium|low]` — sort key
- `[created: YYYY-MM-DD]` — when the task was filed
- `[completed: YYYY-MM-DD]` — when it closed
- `[wip_by: <session_id>]` `[wip_at: <ISO8601>]` — claim metadata while in progress

Tags: `#agent` marks a task an agent filed for a human (the handoff pattern below).

## The correct query

SilverBullet indexes tasks as `index.tag "task"` objects with fields including `done: bool`, `state: " "/"x"/"~"`, `assignee`, `priority`, `created`, `name`, `page`, `pos`. **There is no `status` field.**

The right way to pull open tasks assigned to barbossa:

```bash
sb query 'from index.tag "task" where assignee == "barbossa" and done == false and not table.includes(itags, "meta/template/slash") order by priority desc, created desc'
```

The `not table.includes(itags, "meta/template/slash")` exclusion filters out template scaffolding so example tasks inside slash-command templates don't show up in real work pulls.

Substitute `assignee == "cam"` for Cam's tasks, or drop the assignee filter to see everything.

For the **mention-first** convention, match the recipient instead, and fall back to the
legacy attribute so older tasks still show up:

```bash
sb query 'from index.tag "task" where done == false and (table.includes(recipients, "@cam") or assignee == "cam") and not table.includes(itags, "meta/template/slash") order by priority desc, created desc'
```

`recipients` is only present on objects carrying a mention, so guard it rather than
assuming the field exists. Remember this returns only **tagged** tasks, by design — that is
the whole work-item set, not a partial view. Untagged checkboxes are deliberately absent.

## The query that DOES NOT work

```bash
# WRONG — there is no `status` field. Returns {} silently.
sb query '... where status == "open" or status == "in_progress" ...'
```

An earlier version of this skill used the `status ==` form and was the source of multiple days of false "SB index lag" reports. Two days of Barbossa fires fell through to filesystem-grep mode because the query returned empty — not from index lag, from a non-existent field. Cleaned up 2026-05-22.

## Pulling from the filesystem

When you don't want to depend on the SB server (or want a sanity-check against the index):

```bash
grep -rEn '^\s*[-*]\s*\[ \].*\[assignee: ?cam\]' ~/silverbullet/ 2>/dev/null \
  | head -50
```

This catches open `- [ ]` / `* [ ]` bullets assigned to Cam, including the handoff tasks agents leave in the Captain's Log. Replace `cam` with `barbossa` for Barbossa's set.

## Tasks vs bullets

A task implies **action** and an **owner**. A bullet is anything that doesn't satisfy both.

- ✅ Task: `- [ ] Confirm Meilisearch data dir is in borgmatic [assignee: cam]` — there is a specific action and someone owns it
- ❌ Not a task: `- Consider mxbai-embed-large after a week of use` — this is a consideration, not committed work; if it stays a bullet it's clearer
- ✅ Task: `- [ ] Bisect remaining plugs for headless-Chrome readiness [assignee: barbossa]` — specific action, owned
- ❌ Not a task: `- The bridge wedge might be silversearch` — observation, not action

Don't promote considerations to tasks just because they're written down. Bullets are fine for thinking; tasks are commitments.

## Handing work back to Cam

When an agent finishes work that needs a human step, it ends its Captain's Log entry with a task for Cam, carrying the full context needed to act without re-reading the session:

```markdown
- [ ] Sign the 31 commits on branch `feat/edge-integration` in `~/git_local/sb-cli`, then merge to main. … #agent [assignee: cam] [author: claude-code] [created: 2026-09-04] [priority: medium]
```

Rules that keep these useful:

- **Say what, where, and how** — repo path, branch, commit, the exact command if there is one.
- **Re-checks annotate, they don't duplicate.** A later session that finds the task still open appends `**[barbossa YYYY-MM-DD re-check]** what changed` to the same line.
- **Closing** flips `[ ]` → `[x]`, appends `**[who YYYY-MM-DD]** Done: how` and `[completed: YYYY-MM-DD]`.
- An `@cam` mention in the task is optional: it also surfaces the task in Cam's Mention Inbox (`sb inbox`), and it drops out of the inbox once the task is done.

### The unsigned-commit handoff

Agents can't sign commits: Cam's GPG key needs a passphrase from KeePassXC, which a non-interactive session can't supply (`gpg: signing failed: No pinentry`). So agents commit **unsigned on a feature branch** — never on `main` — and file a task like the one above. Cam's quickest resolution, especially when a branch has grown merges from parallel agents, is to squash it into one signed commit on top of `main`:

```bash
git switch -c feat/x-signed origin/main
git merge --squash feat/x && git commit -S
```

Verify with `git log --format='%h %G? %s'` (`G` = good signature) before pushing.

## Captain's Log + tasks

When Barbossa completes a task in a fire, the Captain's Log entry references it:

```markdown
## 09:34 — barbossa-worker
**Task:** Confirm the Meilisearch data dir is in backup ([[Projects/SilverBullet Fast Search]])
**Tier:** opus → claude-opus-5
**State:** done

Found two redundant paths (gastown rsnapshot + warrig borgmatic); restore procedure documented. Marked `[x]` on the task line.
```

This makes the audit trail across the log + project doc consistent.

## See also

- The companion `silverbullet` plugin's SKILL.md — covers the `sb query` syntax in more depth
- `/sb-tasks` slash command — runs the corrected query and renders the result
- `[[Projects/SilverBullet Chrome Runtime Issue]]` in Cam's space — the wedge investigation that was over-reported because of the malformed query
