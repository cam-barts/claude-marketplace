---
documentation_type: how-to
---

# Installing the `sb` CLI

`sb` is Cam's own Rust CLI for SilverBullet — [cam-barts/sb-cli](https://github.com/cam-barts/sb-cli). It is **not** part of the upstream SilverBullet release; don't look for it there. It syncs a local working copy of the space with the server and talks to the server's Runtime API (Space Lua, index queries, logs).

## Pick a flavor

Every release ships two builds of the same CLI:

- **slim** (`sb-vX.Y.Z-<target>`) — the full notes / sync / journal CLI. Use this unless an agent drives `sb` through MCP.
- **ai** (`sb-ai-vX.Y.Z-<target>`) — slim plus `sb mcp serve`, `sb skills init`, and `sb schema`.

`sb version` reports which one is installed (`features: skills,mcp` means the AI build). Warrig and the laptop both run the AI build.

## Install — prebuilt (Linux x86_64)

```bash
V=$(curl -fsSL https://api.github.com/repos/cam-barts/sb-cli/releases/latest | jq -r .tag_name)
cd /tmp
curl -fLO "https://github.com/cam-barts/sb-cli/releases/download/${V}/sb-ai-${V}-x86_64-unknown-linux-gnu.tar.gz"
tar xzf "sb-ai-${V}-x86_64-unknown-linux-gnu.tar.gz"
install -m 755 sb ~/.local/bin/sb
sb version
```

Drop `-ai` from the asset name for the slim build. Other targets: `aarch64-unknown-linux-gnu`, `x86_64-apple-darwin`, `aarch64-apple-darwin`, and `x86_64-pc-windows-msvc` (a `.zip`). `sha256sums.txt` on each release covers every asset.

## Upgrade

```bash
sb upgrade --check   # is there a newer release?
sb upgrade           # self-update, keeping the same flavor
```

## Install — from source

```bash
cargo install --git https://github.com/cam-barts/sb-cli                 # slim
cargo install --git https://github.com/cam-barts/sb-cli --features ai   # ai
```

On warrig, `~/.local/bin/sb` is a symlink into a local build (`~/git_local/sb-cli/target/release/sb`), so `cargo build --release --features ai` there updates it in place — and means warrig can run unreleased code. Check `sb version` → `commit:` if behaviour differs between machines.

## Install `zk`

`zk` is the companion CLI for full-text search and link analysis. On Arch/EndeavourOS it's packaged:

```bash
sudo pacman -S zk
```

Elsewhere, use a release binary from <https://github.com/zk-org/zk/releases>.

## PATH check

```bash
command -v sb zk
sb version
```

If `sb` isn't found, `$HOME/.local/bin` isn't on `$PATH` — Cam's `~/.profile` adds it; open a login shell or `export PATH="$HOME/.local/bin:$PATH"`.

## What's next

Once `sb version` works, move to [`first_time_setup.md`](first_time_setup.md) for the server, token, and local space. After that, `/sb-setup` runs the smoke test.
