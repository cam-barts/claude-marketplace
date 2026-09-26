---
documentation_type: how-to
---

# First-time `sb` CLI setup

After the binary is on PATH ([`cli_install.md`](cli_install.md)), `sb` needs to know **where the server is**, **how to authenticate**, and **where the local space lives**. `zk` needs the same local space.

## Fastest path on a new machine: copy warrig's config

Cam's machines share one layout, so the quickest setup is copying the user config and the space's small config file from warrig — **never** its sync state:

```bash
mkdir -p ~/.config/sb ~/.sb
scp warrig:.config/sb/config.toml ~/.config/sb/config.toml
scp warrig:.sb/config.toml ~/.sb/config.toml
chmod 600 ~/.config/sb/config.toml
```

Do **not** copy `~/.sb/state.db`. It records which files warrig has synced; on another machine it makes `sb sync` believe the local files were deleted, and a push would delete them from the server.

## The config format

`sb` merges settings from, highest precedence first: environment variables (`SB_SERVER_URL`, `SB_TOKEN`, `SB_IDENTITY`, `SB_SYNC_DIR`, …) → the space's `.sb/config.toml` → the user config `~/.config/sb/config.toml` → defaults. Cam's user config looks like:

```toml
# ~/.config/sb/config.toml
server_url = "https://bullet.coder.cam"
token = "..."                 # from KeePassXC; or `sb auth set`
space = "/home/nux/"          # space root: where .sb/ lives
identity = "@cam"             # default recipient for `sb inbox`

[sync]
dir = "/home/nux/silverbullet"
workers = 10
attachments = true
exclude = ["_plug/*", ".zk/*"]

[daily]
path = "Inbox/{{date}}"
dateFormat = "%Y-%m-%d"
template = "Daily"

[shell]
enabled = true

[runtime]
available = true              # enables sb lua / query / describe / logs
```

`sb config show` prints every resolved value with its source — use it instead of reading files.

## From scratch (no warrig to copy from)

```bash
sb init https://bullet.coder.cam     # create a local space linked to the server
sb auth set                          # prompts for the token (or: --token ...)
sb config set-space /home/nux/       # record the space root in the user config
```

Then add the `[sync] dir` and `[runtime] available = true` settings above. The token lives in KeePassXC.

## Pull the space

```bash
sb sync pull --dry-run   # preview: should be all downloads, nothing else
sb sync pull
sb sync status           # all zeros = in step with the server
```

The whole space is ~3,500 files / ~160 MB with attachments.

## Environment

`~/.profile` (from Cam's dotfiles) already exports these; set them by hand only in a bare shell:

```bash
export ZK_NOTEBOOK_DIR="$HOME/silverbullet"
export PATH="$HOME/.local/bin:$PATH"
```

## `zk`

zk's notebook config lives inside the space at `~/silverbullet/.zk/` (excluded from sync) and its user config at `~/.config/zk/`. Copy both from warrig, then build the index locally — don't copy `notebook.db`:

```bash
mkdir -p ~/.config/zk ~/silverbullet/.zk
scp -r warrig:.config/zk/config.toml warrig:.config/zk/templates ~/.config/zk/
scp -r warrig:silverbullet/.zk/config.toml warrig:silverbullet/.zk/templates ~/silverbullet/.zk/
zk index                 # ~2–3 minutes for the full space
```

## Smoke test

```bash
sb version               # CLI present, which flavor
sb --no-input lua '"ok"' # → "ok": server reachable, token works
sb sync status           # local vs server
zk list --limit 1        # zk sees the space
```

If any of those fail:

- Exit `3` from `sb` → token wrong or missing: `sb auth set`.
- `bridge_unavailable` → server-side headless Chrome wedge; see [[Projects/SilverBullet Chrome Runtime Issue]] in Cam's space.
- Exit `2` with `script_error` from `sb lua` → malformed Lua, not a server fault; see [`space_lua_pitfalls.md`](space_lua_pitfalls.md).
- `zk list` returns nothing → `$ZK_NOTEBOOK_DIR` not exported, or `zk index` hasn't run.

## Next

Once the smoke test passes, the slash commands are usable: `/sb-setup`, `/sb-tasks`, `/sb-inbox`, `/sb-new-project`, `/sb-search`, `/sb-log`, `/sb-garden`. `/sb-setup` re-runs the smoke test on demand.
