# zk recipes

`zk list --help` is the source of truth; these are the patterns that come up in Cam's space.

## Searching notes

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

## Output formatting

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

## Tag operations

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

## Link analysis

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

## Mentions

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

## Graph output

Produces a JSON representation of the note network for programmatic analysis:

```bash
zk graph --format json "Readwise/Mastery.md" --quiet
zk graph --format json --tag "bias" --quiet
zk graph --format json Z/ --quiet
```

Returns `{ "notes": [...], "links": [...] }` where each link has `source` and `target`
indices into the notes array.

## Date filtering and sorting

```bash
zk list --created-after "last monday"
zk list --modified-after "2025-01-01"
zk list --sort modified-        # most recent first (- = descending)
zk list --sort title             # alphabetical
zk list --sort word-count-       # longest first
```

## Practical compound queries

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
