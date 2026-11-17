---
name: silverbullet
description: |
  How Cam's SilverBullet knowledge base and its CLI tools (sb, zk) work, and what the space contains.
  Use it for: SilverBullet pages, notes, or space content; wikilinks, backlinks, aspiring notes, orphans;
  zk for searching, tagging, link analysis, or graph traversal; sb for querying the index, syncing,
  page history, or running Space Lua; tags and space layout; the Readwise or Zotero integrations and
  `#highlight` objects; the multi-space server at bullet.coder.cam; or any mention of ~/silverbullet,
  "my notes", "my knowledge base", or "my wiki". Cam's conventions for tasks, hand-offs, the Captain's
  Log, and new project docs are in silverbullet-workflow; a gardening/connection-hunting round is
  serendipity-gardening; enriching one Zotero paper is enrich-paper.
---

# SilverBullet Knowledge Base

Cam's knowledge base runs on SilverBullet v2 with Space Lua scripting, in `~/silverbullet/`. The
shell needs `ZK_NOTEBOOK_DIR=~/silverbullet` and `~/.local/bin` on PATH; the login profile sets both.

Last verified against: claude-opus-5-5, 2026-11-16.

## Quick Reference: Which Tool for What

| I need to… | Use |
|-----------|-----|
| Search notes by text, tag, or date | `zk list` |
| Find what links to/from a note | `zk list --link-to` / `--linked-by` |
| Find orphan or poorly-connected notes | `zk list --orphan` / `--missing-backlink` |
| Discover notes related to a topic | `zk list --related` or `--mention` |
| Get the link graph as JSON | `zk graph --format json` |
| Backlinks from the **server's** index (fresh even if zk's index is stale) | `sb links PAGE` / `sb links PAGE --from` |
| Find out which tags/attributes exist before querying | `sb describe` / `sb describe TAG` |
| Query SilverBullet data objects (highlights, annotations) | `sb query` |
| Run Space Lua functions (widgets, custom queries) | `sb lua` (expressions) / `sb lua --script FILE` (statements) |
| Check `@mention`s addressed to you | `sb inbox` |
| See, diff, or roll back a page's past revisions | `sb page history` / `diff` / `restore` |
| Sync file changes to the server | `sb sync` |
| Append to a page, crediting the author | `sb page append NAME --content … --sign @name`, then `sb sync` |
| Edit note content directly | Edit files in `~/silverbullet/`, then `sb sync` |

## The `sb` CLI

`sb` is Cam's own Rust CLI ([cam-barts/sb-cli](https://github.com/cam-barts/sb-cli)), not
the upstream SilverBullet binary. It syncs a local working copy with the server and talks to
the server's Runtime API. This section tracks **sb 1.9.1**; `sb version` shows what's installed.

**The CLI documents itself — trust it over this page.** `sb <command> --help` is always
current, `sb query --help` carries verified worked examples, and (AI build) `sb schema`
emits the whole command/flag surface as JSON.

### Running sb as an agent

- Pass **`--no-input`** so `sb` never blocks on a picker, `$EDITOR`, or confirmation
  (also implied when stdin/stdout isn't a TTY).
- Output is **JSON automatically when stdout isn't a TTY**; force it with `--format json`.
  Errors go to stderr as `{error, code, remediation}`, so stdout stays parseable.
- Destructive operations need **`--yes`** (or `--force`); without it they exit `6` with the
  exact re-run command.
- Branch on **exit codes**, not error text: `0` ok · `1` general · `2` usage (including a
  Lua `script_error`) · `3` auth · `4` not found · `5` conflict · `6` needs `--yes`.
- Slow query? `--timeout SECONDS` raises the HTTP timeout and the Runtime API's `X-Timeout` together.
- `--fields a,b` trims JSON output on `page list`, `query`, `describe`, `links`, `inbox`.

### Syncing

```bash
sb sync              # bidirectional sync
sb sync pull         # pull latest from server
sb sync push         # push local changes
sb sync status       # JSON: modified/new/deleted/conflicts/marker_conflicts/readonly
sb sync --dry-run    # preview actions without executing
```

A push reports read-only (403) paths and per-file failures at the end while every other upload
still lands (`0 read-only, 0 failed` in the summary).

**Conflicts.** A conflicted file's local copy is stashed under `~/.sb/conflicts/`.

```bash
sb sync conflicts                              # list them
sb sync resolve PATH --diff                    # inspect one
sb sync resolve PATH --keep-local|--keep-remote
sb sync resolve --all --keep-remote            # unattended: walk every conflict
sb sync prune-stashes --dry-run                # stashes that carry no information
sb sync prune-stashes                          # ...delete them (--all: also resolved paths)
```

`marker_conflicts` in `sb sync status` counts files the **server** wrote git-style
`<<<<<<<` markers into — fix those by editing the file, not with `resolve`.

**ETags.** Conditional writes (`If-Match`) only work when the server sends a *strong* ETag.
Through Cloudflare, `bullet.coder.cam` returns a weak one, so sync falls back to the old
behaviour; `sb --verbose` says which it got.

### Space Lua evaluation

Call any function defined in the space's Lua scripts. Cam has custom functions in
`Library/Personal/Readwise.md`, `Library/Personal/Zotero.md`, and `Library/Personal/Widgets.md`.

```bash
sb lua 'mostLinked(5)'
sb lua 'aspiringPagesSorted(20)'
sb lua --script check.lua          # statements, locals, explicit return
printf 'local n = 2\nreturn n * 21' | sb lua --script -
```

### Index queries

`index.tag "NAME"` is the **only** query source. Discover what exists first:

```bash
sb describe                        # every tag in the index, with object counts
sb describe highlight              # observed attributes and types for one tag
```

Then query:

```bash
sb query 'from index.tag "highlight" limit 5'
sb query 'from index.tag "highlight" where page == "Zotero/Some Paper" limit 10'
sb query 'from index.tag "page" where zoteroKey select name, zoteroKey'
```

Rules that cost an afternoon each (all in `sb query --help`): a bare attribute is an
existence filter (`where zoteroKey`); `select` projects **and** de-duplicates; selecting one
field returns a flat array; comparison is `==` — a single `=` is a syntax error.

### Links, mentions, and signing

```bash
sb links "Z/Apprenticeship"            # backlinks, from the server's relation index
sb links "Z/Apprenticeship" --from     # outgoing links
sb inbox --to @cam                     # open @mentions addressed to Cam
sb page append "Projects/X" --content "Checked the backups." --sign @barbossa
```

- An **`@mention`** *addresses* someone: it lands in their Mention Inbox until the task it
  sits in is done.
- A **signature** (`--sign @name`, rendered `-- @name`) *credits* an author and never lands
  in anyone's inbox. Sign what you write; `@mention` only when you need someone to act.
- `sb inbox` without `--to` uses `identity` from config or `SB_IDENTITY`. As of 1.9.1 (re-check on upgrade)
  `sb config show` **does** list the resolved `identity` under `server.identity`, with its
  source. With `--format json` and an empty inbox it prints `No mentions.` *before* the
  `[]`, which breaks a naive `| jq`.
- Run a command as a different account without touching the user config by exporting
  `SB_TOKEN` and `SB_IDENTITY` (both show as `env:` in `sb config show`). Barbossa's live
  at `~/.config/sb-barbossa/env`: `. ~/.config/sb-barbossa/env && sb ...`. Prefer this to
  `XDG_CONFIG_HOME`, which also redirects git's config lookup (`~/.config/git` exists) and
  silently detaches it for the whole process chain.
- `sb page append` and `sb daily` write the **local** file; `sb sync` afterwards.

### Page history

```bash
sb page history "Projects/X"                    # revisions (--limit, --before HASH)
sb page diff "Projects/X"                       # uncommitted local changes vs HEAD
sb page diff "Projects/X" --rev <40-char hash>  # what one revision changed
sb page restore "Projects/X" --rev <hash> --yes # write old content locally, then sb sync
```

Use it to review or roll back a bulk edit; a restore goes through normal sync conflict
handling. `bullet.coder.cam` runs in **managed** mode, so SilverBullet commits changes
~30 s after edits go quiet and the newest seconds of an edit may not have a revision yet.
The JSON's `mode` says `managed`; `unmanaged` or `disabled` means history won't be
recorded. Hidden files and the tool/cache folders in the space's `.gitignore` are never
committed.

Multi-space changed where revisions are configured and who commits are authored by; see
[`references/server_multispace.md`](references/server_multispace.md#revisions-in-multi-space).

### Troubleshooting sb

**`sb lua` takes an expression, NOT a statement block.** `sb lua '1+1'` returns `2`;
`sb lua '"ok"'` returns `"ok"`. `sb lua 'return 1+1'` is a Lua syntax error — reported as a
`script_error`, **exit code 2** — because `/.runtime/lua` doesn't accept statements. Use
`--script` for statements. (Before 1.9.0 this surfaced as a bare HTTP 500, which caused
multiple false-positive "bridge wedged" reports.)

A genuinely wedged headless-Chrome bridge reports **`bridge_unavailable`** (HTTP 503) — distinct
from a malformed-expression error. Probe with `sb lua '"ok"'`; if the server stays down on
well-formed input, fall back to `zk` for search tasks — zk reads the filesystem directly.

## The server

Since 2026-10-11 `bullet.coder.cam` runs SilverBullet in **multi-space** mode. It is mostly
invisible to `sb` and `zk`; the layout, accounts, admin API, per-account Chrome runtimes (a new
account's first `sb lua` cold-indexes for minutes, which is not a wedge), and the embedded
`Library/Std` pages are in [`references/server_multispace.md`](references/server_multispace.md).

## The `zk` CLI

zk indexes the space for fast search, link traversal, tags, and graph analysis. Config is
`~/.config/zk/config.toml` and excludes `Library/`. After significant changes run `zk index`
(`--force` for a full rebuild); "database is locked" means another index is still running
(`lsof ~/silverbullet/.zk/notebook.db`).

The flags worth knowing beyond `zk list --help`:

```bash
zk list --orphan                                   # no incoming links
zk list --missing-backlink                         # A→B exists but B→A doesn't
zk list --related "Z/Confirmation Bias.md"         # share links but aren't connected
zk list --mention "Z/Confirmation Bias.md" --no-link-to "Z/Confirmation Bias.md"        # unlinked mentions
zk list --mentioned-by "Readwise/Mastery.md" --no-linked-by "Readwise/Mastery.md"
zk graph --format json Z/ --quiet                  # {notes, links} with index-based edges
```

A multi-word `--match` phrase has silently returned zero (verified 2026-11-16); use single words or
`--match-strategy re` with `.` between words. More recipes (operators, tags, templates, dates):
[`references/zk_recipes.md`](references/zk_recipes.md).

## Space structure

| Folder | Contents |
|--------|----------|
| `Readwise/` | Readwise-synced books and articles with `#highlight` data blocks |
| `Zotero/` | Zotero-synced papers with `#highlight` data blocks (Cam's annotations, plus enrich-paper's AI picks) |
| `Z/` | Concept/idea notes (zettelkasten-style) |
| `Persuasion Techniques/` | Cognitive biases, fallacies, rhetoric, propaganda |
| `Library/Personal/` | Integration code: Readwise.md, Zotero.md, Widgets.md, etc. |
| `Inbox/` | Incoming/unsorted notes |
| `Homelab/` | Tech/infrastructure notes |
| `Projects/` | Active projects |
| `Work/` | Work-related notes |
| `People/` | People pages |
| `Sources/` | Source references |

## Editing the space

Edit files in `~/silverbullet/`, then `sb sync`. If you changed Space Lua, Cam needs to run
`System: Reload` from the command palette (or `sb lua 'system.loadSpaceScripts()'`). Run `zk index`
if zk needs to see the change.

Short (aspiring) wikilinks that should point at full paths are fixed with
`~/docker_services/silverbullet/fix-links.py` (dry run by default):
`cd ~/docker_services/silverbullet && uv run fix-links.py --space ~/silverbullet fix` (add `--apply`
to write; `resolve` maps an aspiring note to an existing page). It also rewrites `Readwise/` pages,
which are other people's words, so read the plan first.

## Tags

Cam's space uses a lean tag system. The meaningful tags are:

- **Content type:** `bias`, `fallacy`, `propaganda`, `rhetoric`, `concept`, `quote`, `person`, `project`
- **Source type:** `readwise`, `readwise/articles`, `readwise/books`, `zotero`, `zotero/journalArticle`, `zotero/book`
- **Meta:** `meta`, `meta/template/page`, `meta/template/slash`, `meta/api`
- **State:** `state/0` (zettelkasten processing state), `excalidraw`, `clippings`, `technique-map`
- **Utility:** `todo`, `wishlist`, `query`, `jira`, `reference`

Tags are for categorization, not entity encoding. Use wikilinks for relationships between
specific notes. Don't create one-off tags — if only one note would have it, it's not a tag.

## SilverBullet data objects

SilverBullet v2 indexes fenced code blocks as queryable data objects:

- `` ```#highlight ``: every highlight in the space, one tag since 2026-10-15. Tell the source by field:
  - Readwise: `readwiseId`, `text`, `location`, `color`, `readwiseNote`, ...
  - Cam's Zotero annotations: `zoteroKey`, `text`, `pdfPage`, `color` (hex), `comment`, `pdfUrl`, ...
  - AI impact highlights (enrich-paper): `aiGenerated: true`, `text`, `reason`, `model`, `generatedAt`, `pdfPage` when known.
    These are the AI's picks, not Cam's: filter with `where not _.aiGenerated` when you mean his.
- `` ```#annotation ``: the pre-2026-10-15 name for Zotero annotations. The Zotero sync still reads it.

Query them with `sb query` or in Space Lua with `query[[from index.tag "highlight" where ...]]`.

## Pitfalls

- **Readwise and Zotero syncs are not idempotent.** Don't fire one to "test" something; it
  rewrites locally fixed links. Measured damage and the counter-intuitive recovery:
  [`references/readwise_sync_pitfall.md`](references/readwise_sync_pitfall.md).
- **Reading `#` on a widget return value as a count.** Space Lua widget helpers return
  tables with only string keys (`_isWidget`, `markdown`/`html`), so `#someWidget(...)` is
  always `0` and looks like "no results". Inspect `type(...)` and the `.markdown` /
  `.html` field instead. Relatedly, some widget functions 500 under `sb lua` while working
  fine in the browser — that is a known headless-only limitation, not a breakage.

## Maintaining this skill

Taste here is small and durable: sign vs mention, lean tags, AI highlights are not Cam's. Most of
the rest is environment fact (sb version, server mode, counts), dated where it was measured;
`sb <command> --help` beats this page when they disagree. Prune what a newer model or a newer `sb`
makes unnecessary.
