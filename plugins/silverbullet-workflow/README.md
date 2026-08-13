---
documentation_type: explanation
---

# SilverBullet Workflow Plugin

Cam's daily-driver playbook for working with SilverBullet from the CLI. Where the `silverbullet` plugin is the reference manual (what `sb` and `zk` do, what the directories are), **this plugin is the action layer** — start a new project from the right template, pull your open tasks, append a Captain's Log entry, search the space, get the CLI installed and pointed at the server on a fresh machine.

This plugin is **highly personal**. It encodes Cam's paths (`~/silverbullet`), his server (`https://bullet.coder.cam`), his template locations (`Library/Personal/Templates/Project`), his convention for `[assignee:]` tasks, his Captain's Log structure. v1 doesn't try to generalize for anyone else — that may come in a v2 split between SB-specific and Cam-workflow halves.

## Skills

### silverbullet-workflow

Triggers whenever a task involves the SilverBullet CLI in any of these flavors: starting a new project (`/home/nux/silverbullet/Projects/`), pulling or annotating tasks (`[assignee:cam]` / `[assignee:barbossa]`), writing a Captain's Log entry, searching the space with `sb query` / `zk list`, syncing edits with `sb sync`, evaluating Space Lua expressions, fixing aspiring (short-name) wikilinks, or first-time CLI setup on a fresh machine. The skill detects whether `sb` is on `$PATH`; if not, it directs the user to the install guide before doing anything else.

Covers:

- First-time CLI setup — detection, install steps, `$ZK_NOTEBOOK_DIR` config, server URL probe
- Task workflows — the correct `done == false` query (not the older `status == "open"` form), tasks vs bullets, `[assignee:]` convention
- Project creation — always start from `Library/Personal/Templates/Project` rather than blank
- Captain's Log — daily roll-up structure, when to write entries
- Searching — `zk list` for filesystem-side full-text, `sb query` / `sb lua` for the indexed view, when to pick which
- Space Lua quirks — expression-not-statement form, reserved `query` keyword, `net.proxyFetch` userdata pitfalls

### serendipity-gardening

Cam's digital-gardening ritual, reconstructed from the 2026-06-30 session. Deals a wide random hand of notes using the [[Serendipity]] page's own Space Lua pickers, keeps the ones that talk to each other, and hunts for non-obvious connections between them. Output is a deliberately **ephemeral** scratch page per round — Cam harvests the wikilinks by hand and deletes it.

Covers:

- Two draw modes — uniform (`serendipity.randomPage()` looped ~24×, keep 10–14) and orphan mode (`scripts/thin_links.py`, notes with zero or one inbound link). Both skip pages that are records rather than notes: `Jira/` ticket mirrors, Captain's Logs, transcripts
- The connection hunt — exact wikilinks plus why each link is illuminating rather than merely adjacent, ranked
- The ephemeral session page — frontmatter flags, warning admonition, template and voice guide in [`references/session_page.md`](skills/serendipity-gardening/references/session_page.md)
- The round-to-round feedback pass — detect the notes Cam edited since the last round, grade his link choices, catch frontmatter that would hide a new note from the pickers
- **Never edits content notes.** It proposes; Cam links.

## Slash Commands

- `/sb-setup` — first-time CLI setup wizard. Detects what's installed, walks through `$ZK_NOTEBOOK_DIR`, server URL, auth token.
- `/sb-tasks` — pull Cam's (or Barbossa's) open tasks from the indexed view, using the corrected `done == false` query.
- `/sb-new-project` — start a new project doc from `Library/Personal/Templates/Project`, sync to server.
- `/sb-search` — full-text search across the space, choosing between `zk` and `sb query` based on what the user wants.
- `/sb-log` — append an entry to today's Captain's Log.
- `/sb-garden` — run a serendipity gardening round: random draw, connection hunt, ephemeral scratch page.

## Requirements

- SilverBullet v2 server (Cam runs his at `https://bullet.coder.cam`)
- `sb` CLI on `$PATH` — install instructions in [`skills/silverbullet-workflow/references/cli_install.md`](skills/silverbullet-workflow/references/cli_install.md)
- `zk` with `$ZK_NOTEBOOK_DIR` pointing at `~/silverbullet`
- The companion `silverbullet` plugin for deeper CLI reference

## Companion plugins

- [`silverbullet`](../silverbullet/) — broad reference plugin for the SB knowledge base, `sb` CLI, `zk` CLI, Space Lua. Installs alongside this one.

## Version

0.3.1

## Attribution

- **SilverBullet** — <https://silverbullet.md>
- **sb CLI** — <https://github.com/silverbulletmd/silverbullet/tree/main/cmd/sb>
- **zk** — <https://github.com/zk-org/zk>
