---
name: silverbullet-workflow
description: |
  Cam's action-layer playbook for working with SilverBullet from the CLI.
  Use this skill when the task involves: starting a new project doc (always from the Project template),
  pulling or annotating tasks (`[assignee: cam]` or `[assignee: barbossa]`),
  appending an entry to today's Captain's Log, checking what's waiting for someone (`sb inbox`,
  @mentions, handoff tasks), signing an entry with `--sign`, searching the space, syncing edits and
  resolving sync conflicts with `sb sync`, evaluating Space Lua, fixing aspiring (short-name) wikilinks,
  or first-time CLI setup on a fresh machine.
  Triggers on mentions of `~/silverbullet`, `bullet.coder.cam`,
  "my SB", "my space", a project doc, a Captain's Log, an `[assignee:]` task, swabs, or any
  `sb` or `zk` CLI invocation. Do NOT use for Space Lua plug development (that's plug.js territory)
  or for browser-side SB workflows; this skill is CLI-driven.
---

# SilverBullet Workflow — Cam's CLI Playbook

This is the action layer. The companion `silverbullet` plugin is the reference manual — read that for what every tool does and how the directories fit together. Read this one when you're about to **do something**: start a project, pull tasks, write a log entry, set up a fresh machine.

## Before you do anything: check the CLI is installed

The first thing any session using this skill should do is verify `sb` is on `$PATH`. The check fits in one line:

```bash
command -v sb >/dev/null 2>&1 || echo "MISSING"
```

If you see `MISSING` (or the command resolves to a wrong binary), **stop and direct the user to** [`references/cli_install.md`](references/cli_install.md) before attempting any of the workflows below. The install steps and first-time configuration live there. Once `sb version` returns cleanly, come back here.

**Run `sb` like an agent:** `--no-input` (never block on a prompt), JSON output (automatic off a TTY), `--yes` only for destructive operations you've been cleared to run, and branch on exit codes — `2` usage/Lua error · `3` auth · `4` not found · `5` conflict · `6` needs `--yes`. `sb <command> --help` is the source of truth for flags; the companion `silverbullet` skill has the details.

A correctly-configured shell also has:

```bash
export ZK_NOTEBOOK_DIR="$HOME/silverbullet"
export PATH="$HOME/.local/bin:$PATH"
```

If those aren't set, walk through [`references/first_time_setup.md`](references/first_time_setup.md).

## The jobs this skill handles

Each maps to a slash command Cam can also invoke directly. The skill description's job is to recognise the situation and either run the command itself or surface the relevant reference.

### 1. Start a new project

**Trigger phrases:** "new project for X", "draft up a project doc", "scope out X", "let's plan X".

**Rule:** *Always start from `[[Library/Personal/Templates/Project]]`* — never write a project doc from scratch. The template is the starting place. Adapt sections as needed; leave sections empty if they don't apply (especially "Intermediate Packets" — only fill it when there's reusable output with value outside the project; otherwise leave it empty rather than padding). Detailed in [`references/project_template.md`](references/project_template.md).

Use `/sb-new-project` to scaffold from the template.

### 2. Pull or annotate tasks

**Trigger phrases:** "my open tasks", "what's on my plate", "Barbossa's backlog", "find tasks tagged X".

**The query.** The correct form is `done == false`, NOT `status == "open"` or `status == "in_progress"`. SB tasks don't have a `status` field — only `done: bool` and `state: " "/"x"/"~"`. An older form of this guidance used the broken filter and was the source of multi-day "SB index lag" false positives:

```bash
sb query 'from index.tag "task" where assignee == "barbossa" and done == false and not table.includes(itags, "meta/template/slash") order by priority desc, created desc'
```

`[assignee: cam]` for tasks Cam owns, `[assignee: barbossa]` for the autonomous agent. Tasks are `- [ ]` bullets with attributes in `[key:value]` form on the same line. Do NOT track "consideration" or "look into this" items as tasks — those are bullets or notes. A task implies action and an owner. Detailed in [`references/task_patterns.md`](references/task_patterns.md).

Use `/sb-tasks` to pull the current open set.

### 3. Append a Captain's Log entry

**Trigger phrases:** "log this", "Captain's Log", "what did I do today", "EOD summary".

**Structure.** One file per day at `Journals/Captains Log/YYYY-MM-DD.md`. Each entry is a `## HH:MM — author` section with `**Task:**` (linking the page touched) and `**State:**` lines, then prose: outcome first, then the surprise, then the evidence. Work left for Cam goes at the end as `[assignee: cam]` tasks (see job 6). Barbossa writes here around the clock, so **pull before appending**. Day roll-ups go at the bottom under `## Day summary`.

Use `/sb-log` to append.

### 4. Search the space

**Trigger phrases:** "find notes about X", "where did I write about Y", "show me everything tagged Z".

**Tool choice.**

- **Full-text content search** → `zk list --match "phrase"`. zk reads the filesystem directly, doesn't depend on the SB server being healthy.
- **Structured query against the SB index** (tags, frontmatter attributes, links) → `sb query 'from index.tag "X" where …'`.
- **Cam's Fast Search** (Meilisearch-backed, hybrid keyword+semantic) → in the SB browser UI, `Ctrl-Shift-F` opens the modal. Not currently CLI-accessible.

If full-text matters most, prefer `zk`. If you need link analysis, orphans, or backlinks, `zk list --link-to` / `--linked-by`. If you need to filter on indexed fields (tags, state, priority), `sb query`. Both [`references/space_lua_pitfalls.md`](references/space_lua_pitfalls.md) and the companion `silverbullet` plugin cover the syntax in more depth.

Use `/sb-search` to dispatch a search.

### 5. Sync after edits

`sb sync` is bidirectional. Run it after any direct edit to a file in `~/silverbullet` — including `sb page append` and `sb daily`, which write the **local** file — so the server sees your changes. For a bulk edit, run `sb sync --dry-run` first and read the plan. After syncing, `sb sync status` should show zero `conflicts`, `marker_conflicts`, and `readonly`.

If there are conflicts, don't guess: `sb sync resolve PATH --diff` to look, then `--keep-local` / `--keep-remote`. Never resolve away Barbossa's writes without reading them. `sb sync prune-stashes --dry-run` shows conflict stashes that are safe to clear.

Common gotchas:

- **Edits during a fix-links pass** can race with `sb sync`; run fix-links first, sync after.
- **`sb sync` after Readwise or Zotero pulls** may surface aspiring (short-name) wikilinks — run `fix-links.py` to resolve them.

### 6. Hand-offs: what's waiting, and leaving work for Cam

**Trigger phrases:** "what's waiting for me", "anything for me", "check my inbox", "hand this back to Cam", "leave Cam a note".

- **Picking up:** `/sb-inbox` shows open `@mentions` (`sb inbox`) plus open assigned tasks. Run it at the start of a session.
- **Handing back:** end the Captain's Log entry with a task carrying enough context to act cold — `- [ ] … #agent [assignee: cam] [author: claude-code] [created: YYYY-MM-DD] [priority: …]`. Tasks are the established channel; an `@cam` inside one also puts it in his Mention Inbox.
- **Crediting vs addressing:** `--sign @name` (on `sb page append` / `sb daily`) *credits* the author and never reaches an inbox. Sign what you append to shared pages; `@mention` only when someone needs to act.
- **Commits you can't sign:** commit on a feature branch, never `main`, and file the signing task — see [`references/task_patterns.md`](references/task_patterns.md#the-unsigned-commit-handoff).

## Space Lua sharp edges (read once)

Three subtle bugs that have eaten multiple days. They live in detail in [`references/space_lua_pitfalls.md`](references/space_lua_pitfalls.md); the headlines:

1. **`sb lua` takes an expression, not a statement block.** `sb lua '1+1'` returns `2`. `sb lua 'return 1+1'` is a `script_error` (exit `2`) because the endpoint doesn't accept statements — use `sb lua --script FILE` (or `-` for stdin) for those. A `script_error` is bad input, NOT a wedged bridge; a wedge surfaces as `bridge_unavailable` (HTTP 503).

2. **`query` is a reserved Space Lua keyword.** Using `query` as a variable name in a `space-lua` block triggers a confusing "unexpected symbol near 'q'" parse error. Use `qstr`, `qtext`, `searchTerm`, anything else.

3. **`net.proxyFetch` returns JS-wrapped userdata for leaf values.** `:method()` calls on returned strings (e.g. `hit.body:gsub(...)`) and `#` / `table.concat` on returned arrays throw "attempt to index a userdata value". Use functional `string.gsub(s, ...)` / `string.sub(...)` forms and `ipairs`-rebuild before length/concat ops. The top-level `.field` access works fine because the bridge implements `__index` — only the leaf values are JS-wrapped.

## Cam's collaboration patterns (apply throughout)

- **Templates as starting places.** The Project template (and any other) is a starting point, not handcuffs — adapt as the work demands. Empty sections that don't apply are a feature, not a bug.
- **Tasks vs bullets.** A task implies action and an owner. Notes, observations, considerations stay as bullets.
- **`[assignee: cam]` for Cam, `[assignee: barbossa]` for the autonomous agent.** No assignee = nobody owns it.
- **Report-only first for destructive ops.** Bulk deletes, mass edits, anything irreversible — propose the plan, wait for explicit approval, then execute.
- **Verify before relaying.** When a sub-agent reports work done, check the diff or output before passing the claim up the chain.
- **Captain framing.** Cam addresses agents as Captain and is addressed as same; light pirate vocabulary is welcome but not overdone.

## References

- [`references/cli_install.md`](references/cli_install.md) — install `sb` (slim vs AI build), `sb upgrade`, install `zk`
- [`references/first_time_setup.md`](references/first_time_setup.md) — copy config from warrig, the config format, first pull, `zk` index
- [`references/task_patterns.md`](references/task_patterns.md) — the corrected query, `[assignee: ]` convention, hand-off patterns (including unsigned commits), do/don't list
- [`references/project_template.md`](references/project_template.md) — what the Project template has, what to fill, what to skip
- [`references/space_lua_pitfalls.md`](references/space_lua_pitfalls.md) — the three sharp edges with examples and fixes, plus `--script`
