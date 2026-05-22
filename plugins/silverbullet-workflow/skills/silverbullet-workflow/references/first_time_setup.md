---
documentation_type: how-to
---

# First-time `sb` CLI setup

After the binary is on PATH, the CLI needs to know **where the server is** and **how to authenticate**. There's also a `zk` CLI most workflows here pair with — same setup needed.

## Required environment variables

Add these to your shell init (`~/.bashrc`, `~/.zshrc`, or whichever):

```bash
# zk reads the SilverBullet space at ~/silverbullet.
export ZK_NOTEBOOK_DIR="$HOME/silverbullet"

# Make sure sb is found.
export PATH="$HOME/.local/bin:$PATH"
```

## Auth token

`sb` talks to the SilverBullet server over HTTPS. If your server is behind auth (Cam's is — at `https://bullet.coder.cam`), `sb` needs a token. The token lives in `~/.config/sb/config.toml`:

```toml
# ~/.config/sb/config.toml
[server]
url = "https://bullet.coder.cam"
auth_token = "your-token-here"
user = "nux"
```

To create the file:

```bash
mkdir -p ~/.config/sb
cat > ~/.config/sb/config.toml <<'EOF'
[server]
url = "https://bullet.coder.cam"
auth_token = "PASTE_TOKEN_HERE"
user = "nux"
EOF
chmod 600 ~/.config/sb/config.toml
```

**How to get the token:** SilverBullet generates tokens server-side. Cam has his in KeePassXC. On a fresh machine, copy it from KeePassXC and paste in. **Never commit this file** — `.gitignore` it.

## Local space

`sb sync` operates against the local space at `~/silverbullet`. First-time clone:

```bash
mkdir -p ~/silverbullet
cd ~/silverbullet
sb sync pull   # downloads everything from the server
```

On Cam's primary host (warrig) `~/silverbullet/` already exists. On a fresh laptop, this is the bootstrap.

## `zk` CLI install

`zk` is the companion CLI for full-text search, link analysis, tags. The skill's search workflows lean on it heavily.

```bash
# Linux (binary)
go install github.com/zk-org/zk@latest
# or download from https://github.com/zk-org/zk/releases

# Initialize against the SB space
cd ~/silverbullet
zk init   # creates .zk/ and config
```

Cam's `.zk/config.toml` already exists in `~/silverbullet/.zk/`. On a fresh checkout you may need to run `zk init`.

## Smoke test

```bash
sb --version          # CLI is there
sb lua '1+1'          # returns 2 — server is reachable, auth works
sb sync status        # shows whether there are local-vs-server differences
zk list --limit 1     # zk sees the space
```

If any of those fail:

- `sb lua` returns `bridge_unavailable` → server-side headless Chrome wedge; see [[Projects/SilverBullet Chrome Runtime Issue]] in Cam's space (parked, recurrence-driven).
- `sb lua` returns HTTP 500 on a well-formed expression → see [`space_lua_pitfalls.md`](space_lua_pitfalls.md) — most often the syntax is wrong (expression vs statement).
- `sb sync` returns HTTP 401 → token is wrong or missing.
- `zk list` returns nothing → `$ZK_NOTEBOOK_DIR` not exported in current shell, or the space is empty.

## Common gotchas

- **`source ~/.bashrc` after editing init.** New env vars don't propagate to existing shells until you source the file or open a fresh one.
- **`~/.config/sb/config.toml` permissions.** `chmod 600` so the token isn't world-readable. The CLI may refuse to read it otherwise.

## Next

Once the smoke test passes, the skill's five main commands (`/sb-setup`, `/sb-tasks`, `/sb-new-project`, `/sb-search`, `/sb-log`) are usable. `/sb-setup` re-runs the smoke test on demand.
