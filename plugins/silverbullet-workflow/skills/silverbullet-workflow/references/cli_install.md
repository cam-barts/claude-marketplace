---
documentation_type: how-to
---

# Installing the `sb` CLI

The `sb` command is the CLI for talking to a SilverBullet v2 server's runtime API — runs Space Lua, queries the object index, syncs working-copy edits to the server. It's a separate binary from the SilverBullet server itself.

## Where it lives upstream

The CLI source ships inside the main SilverBullet repository:

- Repo: <https://github.com/silverbulletmd/silverbullet>
- Releases: <https://github.com/silverbulletmd/silverbullet/releases>

Releases include prebuilt binaries for Linux (amd64/arm64), macOS (amd64/arm64), and Windows. Cam runs the Linux amd64 build on warrig.

## Install — Linux (Cam's typical path)

```bash
# Latest release URL — sb is bundled with the silverbullet binary in newer
# releases, look in the release notes for the exact asset name.
mkdir -p ~/.local/bin
cd /tmp
curl -L -o silverbullet.tar.gz \
  "https://github.com/silverbulletmd/silverbullet/releases/latest/download/silverbullet-linux-x86_64.tar.gz"
tar xzf silverbullet.tar.gz
# Place sb on PATH
mv sb ~/.local/bin/sb
chmod +x ~/.local/bin/sb

# Verify
sb --version
```

If `sb` isn't bundled in the release asset (the upstream layout has changed before), the fallback is building from source — see "Build from source" below.

## Install — macOS

```bash
# Homebrew tap if available, otherwise grab the macOS binary from the
# releases page and drop it in /usr/local/bin or ~/.local/bin.
curl -L -o silverbullet.tar.gz \
  "https://github.com/silverbulletmd/silverbullet/releases/latest/download/silverbullet-darwin-aarch64.tar.gz"
tar xzf silverbullet.tar.gz
mv sb /usr/local/bin/sb
chmod +x /usr/local/bin/sb

sb --version
```

Adjust the asset name for amd64 if you're on Intel.

## Build from source (fallback)

If the release doesn't ship a `sb` binary for your platform, or you want to track main:

```bash
git clone https://github.com/silverbulletmd/silverbullet.git
cd silverbullet
# silverbullet uses Deno
deno task build-sb   # or check the Makefile for the current target name
cp dist/sb ~/.local/bin/sb
```

Confirm Deno is installed (`deno --version`); if not, install from <https://deno.land>.

## PATH check

```bash
which sb
sb --version
```

If `which sb` returns nothing, your shell init doesn't have `$HOME/.local/bin` on `$PATH`. Add this to `~/.bashrc` (or zshrc):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then `source ~/.bashrc` or open a fresh shell.

## What's next

Once `sb --version` works, move to [`first_time_setup.md`](first_time_setup.md) for environment variables and the auth token. After that, `/sb-setup` walks through a smoke test.
