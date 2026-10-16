# Cam's Claude Code Marketplace

Personal plugins for working with Cam's SilverBullet knowledge base from Claude Code.

## Installation

```bash
/plugin install cam-marketplace@github:cam-barts/claude-marketplace
```

Or install individual plugins:

```text
/plugin install silverbullet@cam-marketplace
/plugin install silverbullet-workflow@cam-marketplace
```

## Plugins

### silverbullet

Skill bundle for working with Cam's SilverBullet knowledge base. Encodes paths, the server URL, and Lua function names — highly personal; useful as a reference for similar setups but not turnkey for others.

**Key Features:**

- Decision table for picking between `sb`, `zk`, and direct file edits
- `sb sync` workflow for pushing edits to the server
- Space Lua evaluation and SilverBullet object index queries
- `zk` search, link traversal, tag management, graph analysis

**Skill:** `silverbullet` - Triggers on SilverBullet, wikilinks, backlinks, `sb`/`zk` CLI usage, or references to the user's notes/wiki/knowledge base

**Version:** 0.2.0 (pre-release)

---

### silverbullet-workflow

Action-oriented playbook companion to `silverbullet`. Where the reference plugin says what the tools are, this one says what to do with them — Cam's daily CLI workflows for starting projects, pulling tasks, appending Captain's Log entries, searching the space, and getting set up on a fresh machine. Bundles the correct `done == false` task query (replaces the older `status == "open"` form that silently returned empty), the Project template scaffold rule, and the three Space Lua sharp edges that have cost the most time.

**Key Features:**

- First-time CLI setup detection — checks `sb`/`zk` on PATH, env vars, config, server reachability; surfaces install instructions when missing
- Slash commands for the daily-driver moves: `/sb-setup`, `/sb-tasks`, `/sb-new-project`, `/sb-search`, `/sb-log`, `/sb-garden`
- Encodes Cam's collaboration patterns from memory — templates as starting places, tasks vs bullets, `[assignee:]` convention, report-before-commit
- Reference docs for install, first-time setup, task patterns, project template structure, Space Lua pitfalls (expression-vs-statement, reserved `query` keyword, `net.proxyFetch` userdata)

**Commands:**

- `/sb-setup` - Verify CLI install + config; surface setup steps when anything is missing
- `/sb-tasks` - Pull open tasks for an assignee using the corrected `done == false` query
- `/sb-new-project` - Scaffold a new project doc from `Library/Personal/Templates/Project`
- `/sb-search` - Dispatch a search, picking `zk` or `sb query` based on the kind
- `/sb-log` - Append an entry to today's Captain's Log
- `/sb-garden` - Run a serendipity gardening round over the space

**Skills:** `silverbullet-workflow` - Triggers when the task involves the SB CLI in any of these flavors: starting a new project, pulling or annotating `[assignee:]` tasks, writing Captain's Log entries, searching the space, syncing edits, evaluating Space Lua, fixing aspiring wikilinks, or first-time CLI setup

`serendipity-gardening` - Cam's digital-gardening ritual: deal a wide random hand of notes from the Serendipity page's own pickers (or from the orphans nothing links to), hunt non-obvious connections between them, and propose the exact wikilinks. Writes an ephemeral scratch page per round and never edits content notes — Cam does the linking

**Version:** 0.3.1 (pre-release)

## License

Provided as-is for personal and educational use.

## Contributing

This is a personal marketplace. Feel free to fork and adapt for your own use.
