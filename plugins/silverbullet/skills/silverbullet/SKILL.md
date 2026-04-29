---
name: silverbullet
description: |
  How to work with Cam's SilverBullet knowledge base and its CLI tools (sb, zk).
  Use this skill whenever the task involves: SilverBullet pages, notes, or space content;
  wikilinks, backlinks, or aspiring notes; the zk CLI for searching, tagging, link analysis,
  or graph traversal; the sb CLI for querying, syncing, or running Space Lua; note organization,
  tag management, or knowledge graph analysis; the Readwise or Zotero integrations in SB;
  or any mention of ~/silverbullet, "my notes", "my knowledge base", or "my wiki". Also trigger when the user asks about
  links between notes, orphan pages, note connections, or wants to search/filter their notes.
---

# SilverBullet Knowledge Base

Cam's knowledge base runs on SilverBullet v2 with Space Lua scripting. There are two key
directories, two CLI tools, and a link-fixing script. This skill tells you when and how
to use each one.

## Quick Reference: Which Tool for What

Pick the right tool for the job — reaching for the wrong one wastes time:

| I need to… | Use |
|-----------|-----|
| Search notes by text, tag, or date | `zk list` |
| Find what links to/from a note | `zk list --link-to` / `--linked-by` |
| Find orphan or poorly-connected notes | `zk list --orphan` / `--missing-backlink` |
| Discover notes related to a topic | `zk list --related` or `--mention` |
| Get the link graph as JSON | `zk graph --format json` |
| Query SilverBullet data objects (highlights, annotations) | `sb query` |
| Run Space Lua functions (widgets, custom queries) | `sb lua` |
| Sync file changes to the server | `sb sync` |
| Edit note content directly | Edit files in `~/silverbullet/`, then `sb sync` |

## Environment Setup

Both CLI tools need environment variables that come from `~/.profile`. Set these before
running commands in any shell session:

```bash
export ZK_NOTEBOOK_DIR="$HOME/silverbullet"
export PATH="$HOME/.local/bin:$PATH"
```

## The `sb` CLI

Talks directly to the SilverBullet server's runtime API. Use it for syncing, evaluating
Lua, and querying the object index. Details can be found at <https://github.com/cam-barts/sb-cli>

### Syncing

```bash
sb sync              # bidirectional sync
sb sync pull         # pull latest from server
sb sync push         # push local changes
sb sync status       # check what's changed
```

### Space Lua evaluation

Call any function defined in the space's Lua scripts. Cam has custom functions in
`Library/Personal/Readwise.md`, `Library/Personal/Zotero.md`, and `Library/Personal/Widgets.md`.

```bash
sb lua 'mostLinked(5)'
sb lua 'aspiringPagesSorted(20)'
```

### Index queries

Query SilverBullet's indexed data objects directly:

```bash
sb query 'from index.tag "highlight" limit 5'
sb query 'from index.tag "annotation" where _.page == "Zotero/Some Paper" limit 10'
sb query 'from index.tag "link" limit 5'
sb query 'from index.tag "tag" limit 5'
```

### Troubleshooting sb

If `sb lua` or `sb query` returns a 500 error, the Space Lua runtime may be overloaded
from a recent reload. Wait a few seconds and retry with `sb lua 'return "ok"'` to check.
If the server stays down, fall back to `zk` for search tasks — zk reads the filesystem
directly and doesn't depend on the SB server being healthy.

## The `zk` CLI

A command-line tool that indexes the SilverBullet space and provides fast search, link
traversal, tag management, and graph analysis. It reads from `~/silverbullet/`
(set via `ZK_NOTEBOOK_DIR`). The config lives at `~/.config/zk/config.toml` and
excludes `Library/` from indexing. Information can be found for this CLI at <https://github.com/zk-org/zk>.

### Reindexing

After significant changes to the space, reindex so zk has current data:

```bash
zk index          # incremental (fast)
zk index --force  # full rebuild
```

**If zk errors with "database is locked"**, another `zk index` process is still running.
Find and kill it with `lsof ~/.zk/notebook.db` or wait for it to finish.

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
    - Typically, you would use `meta` tags for library files or system configuration, anything that would be considered a content note should not have the meta tag.

Tags are for categorization, not entity encoding. Use wikilinks for relationships between
specific notes. Don't create one-off tags — if only one note would have it, it's not a tag.

## SilverBullet data objects

SilverBullet v2 indexes fenced code blocks as queryable data objects:

- `` ```#highlight `` — Readwise highlights (`readwiseId`, `text`, `location`, `color`, etc.)
- `` ```#annotation `` — Zotero annotations (`zoteroKey`, `text`, `page`, `color`, `pdfUrl`, etc.)

Query them with `sb query` or in Space Lua with `query[[from index.tag "highlight" where ...]]`.

## Common Pitfalls

Things that have tripped up agents before — avoid repeating these:

1. **Editing `~/docker_services/silverbullet/space/` directly without syncing.** The server
   reads from the Docker mount, but `zk` reads from `~/silverbullet/`. If you edit one
   without syncing, they diverge. Always use `~/silverbullet/` + `sb sync`.

2. **Forgetting environment variables.** Every new shell session needs `ZK_NOTEBOOK_DIR`
   and `PATH` set. Without them, `zk` won't find the notebook and `sb` won't be on PATH.

3. **Running `zk index --force` while another index is running.** The SQLite database
   locks. Check with `lsof` before forcing a reindex.

4. **Trying `sb query` when the server is down.** Fall back to `zk` — it works offline
   against the local filesystem.
