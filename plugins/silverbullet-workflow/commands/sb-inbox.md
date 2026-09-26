---
description: Show what's waiting for someone — open @mentions plus open assigned tasks
argument-hint: [identity]
---

Answer "what's waiting for me?" in one pass: the `@mention`s addressed to an identity (the Mention Inbox) and the open tasks assigned to them. Run it at the start of a session to pick up handoffs.

## Arguments

- `identity` (optional) — `cam`, `barbossa`, or any `@name`, with or without the `@`. Defaults to `identity` in the sb config (or `$SB_IDENTITY`); if neither is set, ask rather than guess.

## Steps

1. **Resolve the identity** without the leading `@`:

   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   WHO="${1:-${SB_IDENTITY:-}}"
   WHO="${WHO#@}"
   ```

   If `$WHO` is empty, `sb inbox` (no `--to`) will use the configured `identity`; if that's unset too it exits `2` telling you to pass `--to`.

2. **Mentions** — open `@mention`s from the server's relation index. A mention inside a task drops out once the task is done:

   ```bash
   sb --no-input --format json inbox ${WHO:+--to "$WHO"}
   ```

3. **Assigned tasks** — the same query `/sb-tasks` uses:

   ```bash
   sb --no-input --format json query "from index.tag \"task\" where assignee == \"$WHO\" and done == false and not table.includes(itags, \"meta/template/slash\") order by priority desc, created desc limit 20"
   ```

4. **Render** two short sections, newest-relevant first, each item linked to its source page:

   ```text
   ## Mentions (2)
   - [[Journals/Captains Log/2026-09-25]] — "@cam can you confirm the WebDAV creds…"

   ## Open tasks (5)
   | Priority | Page | Task | Created |
   ```

   If both are empty, say so in one line.

## When to use a mention versus a task

Tasks are the established handoff: `[assignee: cam]` on a `- [ ]` line, which `/sb-tasks` and this command both surface. Reach for an `@mention` when you need someone's attention on something that **isn't** a task of theirs — a question in a project doc, a review request on a page. Don't mention yourself, and don't use a mention to credit authorship: that's `--sign @name`, which never reaches an inbox.

## Configure a default identity

So `sb inbox` works without `--to` on this machine, add a top-level key to `~/.config/sb/config.toml`:

```toml
identity = "@cam"
```

`sb inbox` with no `--to` confirms it resolved (exit `2` means it didn't; `sb config show` doesn't list `identity` as of 1.9.0). An agent's own environment can set `SB_IDENTITY=@barbossa` instead. Cam's machines have `identity = "@cam"` set.

## See also

- [`/sb-tasks`](sb-tasks.md) — tasks only, with the filesystem fallback
- [`task_patterns.md`](../skills/silverbullet-workflow/references/task_patterns.md) — task anatomy, handoff patterns
