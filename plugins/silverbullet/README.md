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
- Syncing the Docker volume with the local working copy
- Running Space Lua and querying the SilverBullet object index
- Searching, tagging, and graph traversal with `zk`

## Requirements

- SilverBullet v2 server running locally or remotely
- `sb` CLI on `$PATH`
- `zk` with `ZK_NOTEBOOK_DIR` pointing at the synced working copy

## Version

0.2.0 (pre-release)

## Attribution

- **SilverBullet** — <https://silverbullet.md>
- **zk** — <https://github.com/zk-org/zk>
