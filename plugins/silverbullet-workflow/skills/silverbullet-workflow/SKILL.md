---
name: silverbullet-workflow
description: |
  Cam's conventions for doing things in his SilverBullet space: starting a new project doc from the
  Project template, pulling, filing, or handing off tasks (owned by an `@cam` / `@barbossa` mention),
  appending to today's Captain's Log, checking what's waiting (`sb inbox`, the Mention Inbox),
  crediting authorship with `--sign`, writing as Barbossa, resolving `sb sync` conflicts, and
  first-time `sb`/`zk` setup on a fresh machine. Use it for "new project for X", "what's on my plate",
  "Barbossa's backlog", "log this", "Captain's Log", "EOD summary", "anything for me", "hand this back
  to Cam", swabs, or a sync conflict. For how the sb/zk tools work, searching notes, Space Lua, or the
  space layout, use the silverbullet skill instead. Not for plug development or browser-side work.
---

# SilverBullet workflow

The `silverbullet` skill says how the tools work. This one holds Cam's conventions for the jobs
below. It needs `sb` and `zk` on PATH and `ZK_NOTEBOOK_DIR=~/silverbullet`; if `sb version` fails,
see [`references/cli_install.md`](references/cli_install.md) and
[`references/first_time_setup.md`](references/first_time_setup.md) (or run `/sb-setup`).

Last verified against: claude-opus-5-5, 2026-11-16.

## Identity: agent writes are Barbossa

Barbossa is the name of Cam's agent; `claude-code` is only the harness and does not belong on new
work. The server attributes managed-revision commits by account (since the 2026-10-11 multi-space
cut), so an agent writing through Cam's default config looks exactly like Cam. When you write as
the agent (`page append`, `daily`, `sync push`, a `/.fs` PUT or DELETE), use Barbossa's credentials:

```bash
. ~/.config/sb-barbossa/env   # exports SB_TOKEN + SB_IDENTITY=@barbossa (checked 2026-11-16)
```

Leave `~/.config/sb/config.toml` alone: it is Cam's interactive identity and stays `@cam`. Do not
reach for `XDG_CONFIG_HOME` either; it also redirects git's config lookup and silently detaches it
for the whole process chain. Use `barbossa` for in-content authorship too (`--sign @barbossa`,
`[author: barbossa]`, log headings). A first `sb lua` under a fresh identity cold-indexes the space
for a few minutes before it answers.

## Jobs

### New project

Start from `[[Library/Personal/Templates/Project]]` rather than a blank page (`/sb-new-project`
scaffolds it). The template is a starting place, not handcuffs: adapt sections, and leave ones that
don't apply empty. "Intermediate Packets" in particular stays empty unless there is reusable output
with value outside the project. Details: [`references/project_template.md`](references/project_template.md).

### Tasks

Ownership is an `@name` mention (`@cam`, `@barbossa`) placed after the task text and before the
`#tags` and `[attributes]`; that is what reaches the Mention Inbox. `[assignee: x]` is legacy: still
read on older tasks, never written. A task is only a work item if it carries an inline channel tag
(`#agent`, `#shared`, `#review`); untagged checkboxes are plan steps and are not indexed, so never
put a mention on one.

The canonical open-task query (the same filter `/sb-tasks` and `/sb-inbox` run). Substitute the name:

```bash
sb query 'from index.tag "task" where (table.includes(recipients, "@cam") or assignee == "cam") and done == false and not table.includes(itags, "meta/template/slash") order by priority desc, created desc'
```

Matching only `assignee` misses every mention-only task written since 2026-10-11 (60 of Cam's 234
open tasks on 2026-11-16). There is no `status` field; `done == false` is the open filter.

A task implies action and an owner. Considerations, observations, and "look into this" items stay as
bullets. Anatomy, attributes, and the do/don't list: [`references/task_patterns.md`](references/task_patterns.md).

### Captain's Log

One file per day at `Journals/Captains Log/YYYY-MM-DD.md`, and it is Barbossa's daily note: with
`~/.config/sb-barbossa/env` sourced, `sb daily --sign @barbossa "…"` appends a log entry and
`sb daily -n 20` / `--contains X` reads it back. `/sb-log` has the entry format. Each entry is one
item: the task link and a `[result:: …]` attribute, then prose (outcome first, then the surprise,
then the evidence). Work left for Cam goes in `--task-tag agent` entries with an `@cam` mention.
Barbossa appends around the clock, so pull before appending and keep both sides of any conflict.
Day roll-ups are a `--star` entry starting `Day summary:`.

### Hand-offs

- **Picking up:** `/sb-inbox` shows open `@mentions` plus open owned tasks. Worth running at the
  start of a session.
- **Handing back:** end the log entry with a task Cam can act on cold: what, where, and how (repo,
  branch, the exact command). `- [ ] … @cam #agent [author: barbossa] [created: YYYY-MM-DD] [priority: …]`
- **Crediting vs addressing:** `--sign @name` credits the author and never reaches an inbox. Sign
  what you append to shared pages; `@mention` only when someone needs to act.
- **Commits you can't sign:** commit on a feature branch, never `main`, and file the signing task.
  See [`references/task_patterns.md`](references/task_patterns.md#the-unsigned-commit-handoff).

### Sync

`sb sync` is bidirectional. Run it after any direct edit under `~/silverbullet`, including
`sb page append` and `sb daily`, which write the local file. For a bulk edit, read the
`sb sync --dry-run` plan first. On conflicts, look before choosing
(`sb sync resolve PATH --diff`, then `--keep-local` / `--keep-remote`), and never resolve away
Barbossa's writes without reading them. A full-file rewrite of a page another session may be
appending to silently drops that append, so wrap the read-modify-write in
`~/bin/sb-edit <page-file> <command...>` (an flock on the page path; checked 2026-11-16).

## Cam's collaboration rules

- **Report-only first for destructive ops.** Bulk deletes, mass edits, anything irreversible:
  propose the plan, wait for explicit approval, then execute.
- **Verify before relaying** a sub-agent's claim; check the diff or output.
- **Captain framing.** Cam addresses agents as Captain and is addressed as same; light pirate
  vocabulary is welcome but not overdone.

## References

- [`references/task_patterns.md`](references/task_patterns.md): task anatomy, the indexing rule, hand-off patterns
- [`references/project_template.md`](references/project_template.md): what the Project template has, what to fill
- [`references/cli_install.md`](references/cli_install.md), [`references/first_time_setup.md`](references/first_time_setup.md): fresh-machine setup
- [`references/space_lua_pitfalls.md`](references/space_lua_pitfalls.md): `sb lua` expression form, reserved `query`, `net.proxyFetch` userdata

## Maintaining this skill

Taste (the rules above, the template stance, tasks vs bullets) is durable. Environment facts (paths,
the credential file, the task schema, counts) are dated; re-check them with the query above and
`sb describe task` when they look off. If a newer model handles a job well without a section, cut it.
