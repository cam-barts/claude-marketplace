---
documentation_type: explanation
---

# SilverBullet Plugin

Bundles the `silverbullet` skill: how to work with Cam's SilverBullet knowledge base, the `sb` and `zk` CLIs, and Space Lua.

This plugin is **highly personal** — it encodes paths (`~/silverbullet`), a server URL, and references to Lua functions that live in Cam's space. Useful as a reference for a similar SilverBullet setup, but not turnkey for someone else.

## Skills

### silverbullet

Triggers when the task involves SilverBullet pages, wikilinks, backlinks, aspiring notes, the `sb` or `zk` CLIs, Space Lua functions, the Readwise/Zotero integrations, or any reference to the user's notes/wiki/knowledge base.

Covers:

- Choosing between `sb`, `zk`, and direct file edits
- Running `sb` safely as an agent — `--no-input`, JSON output, exit codes, `--yes`
- Syncing the local working copy, and resolving conflicts and conflict stashes
- Running Space Lua (`sb lua`, `--script`) and querying the object index (`sb describe`, `sb query`)
- Server-side links, the Mention Inbox, and `--sign` (credit versus address)
- Page history (`sb page history|diff|restore`) over the server's managed git revisions
- Searching, tagging, and graph traversal with `zk`

## Requirements

- SilverBullet v2 server running locally or remotely
- `sb` CLI 1.9.0+ on `$PATH` — [cam-barts/sb-cli](https://github.com/cam-barts/sb-cli)
- `zk` with `ZK_NOTEBOOK_DIR` pointing at the synced working copy

## Version

0.3.0 (pre-release)

## Attribution

- **SilverBullet** — <https://silverbullet.md>
- **sb CLI** — <https://github.com/cam-barts/sb-cli>
- **zk** — <https://github.com/zk-org/zk>
