---
description: Search Cam's SilverBullet space — picks zk or sb query based on the kind of search
argument-hint: <term> [fulltext|tag|links|orphans|related] [scope]
---

Dispatch a search across the SB space, choosing the right tool based on what the user wants:

- **Full-text content search** → `zk list --match` (filesystem-side, fast, works offline)
- **Structured / indexed-field search** → `sb query` (tags, frontmatter, links, priorities)
- **Link analysis** (orphans, backlinks, related) → `zk list --orphan` / `--link-to` / `--linked-by`

## Arguments

- `term` (required) — what to search for. Quoted phrase, regex, tag name, page path — depending on flavor.
- `kind` (optional, default: `fulltext`) — `fulltext` | `tag` | `links` | `orphans` | `related`.
- `scope` (optional) — folder to scope to, e.g. `Z/`, `Readwise/`, `Projects/`.

## Examples

```text
/sb-search "deliberate practice"          → zk list --match "deliberate practice"
/sb-search "bias" tag                     → zk list --tag "bias"
/sb-search "Z/Confirmation Bias" links    → zk list --link-to "Z/Confirmation Bias.md"
/sb-search "" orphans Z/                  → zk list Z/ --orphan
/sb-search "Z/Apprenticeship" related     → zk list --related "Z/Apprenticeship.md"
```

## Steps

1. **Pick the tool** based on `kind`:

   - `fulltext` (default) → `zk list --match "$TERM" --limit 25 -f oneline`
   - `tag` → `zk list --tag "$TERM" --limit 25 -f oneline`
   - `links` → `zk list --link-to "$TERM" --limit 25 -f oneline` (use `--linked-by` if asking the opposite)
   - `orphans` → `zk list --orphan --limit 50 -f oneline`
   - `related` → `zk list --related "$TERM" --limit 25 -f oneline`

   For all forms, `--scope` adds a directory filter (e.g. `zk list Z/ --match "$TERM"`).

2. **Ensure `ZK_NOTEBOOK_DIR` is set** before running zk:

   ```bash
   export ZK_NOTEBOOK_DIR="${ZK_NOTEBOOK_DIR:-$HOME/silverbullet}"
   export PATH="$HOME/.local/bin:$PATH"
   ```

3. **Run the chosen command.** zk's output with `-f oneline` is `path | title`. Parse and render as a compact markdown list:

   ```text
   - [[Z/Decontextualization]] — Decontextualization
   - [[Z/Levels Of Proficiency]] — Levels Of Proficiency
   ...
   ```

4. **Fall back to `sb query`** if the user explicitly wants the indexed view (tags, frontmatter fields) rather than the filesystem view. Example: "find all docs with `state: doing`" → `sb query 'from index.page where state == "doing"'`.

## When to pick which tool

| User asks | Use | Why |
|-----------|-----|-----|
| "find notes about X" | `zk list --match` | Full-text, fast, ignores tags |
| "find notes tagged X" | `zk list --tag` (or `sb query 'from index.tag "X"'`) | Both work; zk doesn't need the SB server up |
| "what links to X" | `zk list --link-to` | Link graph is zk's domain |
| "what does X link to" | `zk list --linked-by` | Outbound links |
| "orphan notes in Z/" | `zk list Z/ --orphan` | Structural analysis |
| "all tasks assigned to barbossa" | `sb query` (see `/sb-tasks`) | Needs the indexed view |
| "recent edits this week" | `zk list --modified-after "last monday" --sort modified-` | Time filtering |

## See also

- The companion `silverbullet` plugin's SKILL.md — full zk + sb reference
- [`/sb-tasks`](sb-tasks.md) — for task-specific search
