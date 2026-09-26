---
name: silverbullet
description: |
  How to work with Cam's SilverBullet knowledge base and its CLI tools (sb, zk).
  Use this skill whenever the task involves: SilverBullet pages, notes, or space content;
  wikilinks, backlinks, or aspiring notes; the zk CLI for searching, tagging, link analysis,
  or graph traversal; the sb CLI for querying, syncing, or running Space Lua; note organization,
  tag management, or knowledge graph analysis; the Readwise or Zotero integrations in SB;
  or any mention of ~/silverbullet, bullet.coder.cam,
  "my notes", "my knowledge base", or "my wiki". Also trigger when the user asks about
  links between notes, orphan pages, note connections, or wants to search/filter their notes.
---

# SilverBullet Knowledge Base

Cam's knowledge base runs on SilverBullet v2 with Space Lua scripting. Two CLI tools
and a link-fixing script operate against the space at `~/silverbullet/`. This skill
tells you when and how to use each one.

## Quick Reference: Which Tool for What

Pick the right tool for the job — reaching for the wrong one wastes time:

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

## Environment Setup

Both CLI tools need environment variables that come from `~/.profile`. Set these before
running commands in any shell session:

```bash
export ZK_NOTEBOOK_DIR="$HOME/silverbullet"
export PATH="$HOME/.local/bin:$PATH"
```

## The `sb` CLI

`sb` is Cam's own Rust CLI ([cam-barts/sb-cli](https://github.com/cam-barts/sb-cli)), not
the upstream SilverBullet binary. It syncs a local working copy with the server and talks to
the server's Runtime API. This section tracks **sb 1.9.0**; `sb version` shows what's installed.

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

A push no longer aborts on one bad file: read-only (403) paths and per-file failures are
reported at the end while every other upload still lands (`0 read-only, 0 failed` in the summary).

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
sb query 'from index.tag "annotation" where page == "Zotero/Some Paper" limit 10'
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
sb page append "Projects/X" --content "Checked the backups." --sign @claude-code
```

- An **`@mention`** *addresses* someone: it lands in their Mention Inbox until the task it
  sits in is done.
- A **signature** (`--sign @name`, rendered `-- @name`) *credits* an author and never lands
  in anyone's inbox. Sign what you write; `@mention` only when you need someone to act.
- `sb inbox` without `--to` uses `identity` from config or `SB_IDENTITY`.
- `sb page append` and `sb daily` write the **local** file; `sb sync` afterwards.

### Page history

```bash
sb page history "Projects/X"                    # revisions (--limit, --before HASH)
sb page diff "Projects/X"                       # uncommitted local changes vs HEAD
sb page diff "Projects/X" --rev <40-char hash>  # what one revision changed
sb page restore "Projects/X" --rev <hash> --yes # write old content locally, then sb sync
```

Use it to review or roll back a bulk edit; a restore goes through normal sync conflict
handling. `bullet.coder.cam` runs in **managed** mode (`SB_REVISIONS=managed` in the
compose file, since 2026-09-26): SilverBullet commits changes ~30 s after edits go quiet,
authored `SilverBullet`, so the newest seconds of an edit may not have a revision yet. The
JSON's `mode` says `managed`; `unmanaged` or `disabled` means history won't be recorded.
Hidden files and the tool/cache folders in the space's `.gitignore` are never committed.

### Troubleshooting sb

**`sb lua` takes an expression, NOT a statement block.** `sb lua '1+1'` returns `2`;
`sb lua '"ok"'` returns `"ok"`. `sb lua 'return 1+1'` is a Lua syntax error — reported as a
`script_error`, **exit code 2** — because `/.runtime/lua` doesn't accept statements. Use
`--script` for statements. (Before 1.9.0 this surfaced as a bare HTTP 500, which caused
multiple false-positive "bridge wedged" reports.)

A genuinely wedged headless-Chrome bridge reports **`bridge_unavailable`** (HTTP 503) — distinct
from a malformed-expression error. Probe with `sb lua '"ok"'`; if the server stays down on
well-formed input, fall back to `zk` for search tasks — zk reads the filesystem directly.

## The `zk` CLI

A command-line tool that indexes the SilverBullet space and provides fast search, link
traversal, tag management, and graph analysis. It reads from `~/silverbullet/`
(set via `ZK_NOTEBOOK_DIR`). The config lives at `~/.config/zk/config.toml` and
excludes `Library/` from indexing.

### Reindexing

After significant changes to the space, reindex so zk has current data:

```bash
zk index          # incremental (fast)
zk index --force  # full rebuild
```

**If zk errors with "database is locked"**, another `zk index` process is still running.
Find and kill it with `lsof ~/silverbullet/.zk/notebook.db` or wait for it to finish.

### Searching notes

```bash
# Full-text search (default, tokenized — matches inflections)
zk list --match "deliberate practice"

# Search with operators
zk list --match "tesla OR edison"
zk list --match "NOT journal"
zk list --match "title: mastery"

# Exact match (good for special chars, wikilinks)
zk list --match "[[Confirmation Bias]]" --match-strategy exact

# Regex match
zk list --match "^## .+" --match-strategy re

# Scope to a directory
zk list Readwise/
zk list Z/
```

### Output formatting

Use `-f` with predefined formats or custom templates. Custom templates use Handlebars
syntax with double-quoted strings in bash (single quotes get parsed by the shell):

```bash
zk list -f oneline --limit 10
zk list -f json --limit 5
zk list -f "{{title}}" --limit 5
```

**Template variables:** `filename`, `filename-stem`, `path`, `abs-path`, `title`, `link`,
`lead`, `body`, `raw-content`, `snippets`, `word-count`, `tags`, `metadata`, `created`,
`modified`, `checksum`.

Use `--quiet` (`-q`) to suppress the "Found N notes" footer.

### Tag operations

```bash
zk tag list                              # all tags with counts
zk list --tag "bias"                     # notes with this tag
zk list --tag "bias, fallacy"            # AND (both)
zk list --tag "bias OR fallacy"          # OR (either)
zk list --tag "NOT done"                 # exclude
zk list --tag "readwise/books"           # hierarchical
zk list --tag "year/201*"               # glob patterns
zk list --tagless                        # untagged notes
zk tag list -f json                      # JSON output
```

### Link analysis

This is zk's most powerful feature — traversing the link graph.

```bash
# Inbound links (who links TO this note)
zk list --link-to "Readwise/Mastery.md"

# Outbound links (what this note LINKS TO)
zk list --linked-by "Readwise/Mastery.md"

# Recursive traversal (follow the full link web)
zk list --link-to "Persuasion Techniques/Confirmation Bias.md" --recursive
zk list --linked-by "Z/Apprenticeship.md" --recursive --max-distance 2

# Structural analysis
zk list --orphan                          # no incoming links
zk list --missing-backlink                # A→B exists but B→A doesn't
zk list --related "Z/Confirmation Bias.md"   # share links but aren't connected
```

### Mentions

Mentions find notes by title text, not explicit wikilinks. This catches unlinked references
where a note's title appears in another note's body text.

```bash
# Notes whose titles appear in the given note
zk list --mentioned-by "Readwise/Mastery.md"

# Notes that mention the given note's title
zk list --mention "Z/Confirmation Bias.md"

# The real power: find unlinked mentions (titles mentioned but not wikilinked)
zk list --mentioned-by "Readwise/Mastery.md" --no-linked-by "Readwise/Mastery.md"
zk list --mention "Z/Confirmation Bias.md" --no-link-to "Z/Confirmation Bias.md"
```

### Graph output

Produces a JSON representation of the note network for programmatic analysis:

```bash
zk graph --format json "Readwise/Mastery.md" --quiet
zk graph --format json --tag "bias" --quiet
zk graph --format json Z/ --quiet
```

Returns `{ "notes": [...], "links": [...] }` where each link has `source` and `target`
indices into the notes array.

### Date filtering and sorting

```bash
zk list --created-after "last monday"
zk list --modified-after "2025-01-01"
zk list --sort modified-        # most recent first (- = descending)
zk list --sort title             # alphabetical
zk list --sort word-count-       # longest first
```

### Practical compound queries

Filters compose naturally. These are patterns that come up often:

```bash
# Orphaned concept notes (Z/ notes nobody links to)
zk list Z/ --orphan

# Notes mentioning "mastery" that aren't already linked
zk list --mention "Readwise/Mastery.md" --no-link-to "Readwise/Mastery.md"

# Recently touched bias/fallacy notes
zk list --tag "bias OR fallacy" --modified-after "last month" --sort modified-

# Readwise articles modified this week
zk list Readwise/ --tag "readwise/articles" --modified-after "last monday"
```

## Space structure

| Folder | Contents |
|--------|----------|
| `Readwise/` | Readwise-synced books and articles with `#highlight` data blocks |
| `Zotero/` | Zotero-synced papers with `#annotation` data blocks |
| `Z/` | Concept/idea notes (zettelkasten-style) |
| `Persuasion Techniques/` | Cognitive biases, fallacies, rhetoric, propaganda |
| `Library/Personal/` | Integration code: Readwise.md, Zotero.md, Widgets.md, etc. |
| `Inbox/` | Incoming/unsorted notes |
| `Homelab/` | Tech/infrastructure notes |
| `Projects/` | Active projects |
| `Work/` | Work-related notes |
| `People/` | People pages |
| `Sources/` | Source references |

## Standard workflow for making changes

1. Edit files in `~/silverbullet/`
2. Run `sb sync` to push changes to the server
3. If you changed Space Lua code, the user needs to run `System: Reload` from the SB command palette
4. Run `zk index` if you need zk to see the changes

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

- `` ```#highlight `` — Readwise highlights (`readwiseId`, `text`, `location`, `color`, etc.)
- `` ```#annotation `` — Zotero annotations (`zoteroKey`, `text`, `page`, `color`, `pdfUrl`, etc.)

Query them with `sb query` or in Space Lua with `query[[from index.tag "highlight" where ...]]`.

## Common Pitfalls

Things that have tripped up agents before — avoid repeating these:

1. **Forgetting to `sb sync` after edits.** Edits to `~/silverbullet/` don't reach the
   server until you sync. If you skip the sync, the server's view drifts from local.

2. **Forgetting environment variables.** Every new shell session needs `ZK_NOTEBOOK_DIR`
   and `PATH` set. Without them, `zk` won't find the notebook and `sb` won't be on PATH.

3. **Running `zk index --force` while another index is running.** The SQLite database
   locks. Check with `lsof` before forcing a reindex.

4. **Trying `sb query` when the server is down.** Fall back to `zk` — it works offline
   against the local filesystem.
