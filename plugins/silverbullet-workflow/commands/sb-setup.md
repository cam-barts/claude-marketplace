---
description: Verify the sb + zk CLIs are installed and configured, or guide the user through first-time setup
---

Run a smoke test on the SilverBullet CLI environment. If anything fails, surface the specific install / config step needed.

## Steps

1. **Check `sb` is on PATH:**

   ```bash
   command -v sb >/dev/null 2>&1 || echo "MISSING"
   ```

   If missing, read [`skills/silverbullet-workflow/references/cli_install.md`](../skills/silverbullet-workflow/references/cli_install.md) and walk the user through the install. Stop here until `sb --version` returns cleanly.

2. **Check `zk` is on PATH:**

   ```bash
   command -v zk >/dev/null 2>&1 || echo "MISSING"
   ```

   Same path if missing — surface the install instructions.

3. **Check env vars:**

   ```bash
   echo "ZK_NOTEBOOK_DIR=${ZK_NOTEBOOK_DIR:-UNSET}"
   echo "PATH includes ~/.local/bin: $(echo "$PATH" | grep -q "$HOME/.local/bin" && echo yes || echo no)"
   ```

   If `ZK_NOTEBOOK_DIR` is unset, point to [`first_time_setup.md`](../skills/silverbullet-workflow/references/first_time_setup.md) and the export line to add to shell init.

4. **Check `sb` config:**

   ```bash
   test -f ~/.config/sb/config.toml && echo "config exists" || echo "MISSING"
   ```

   If missing, walk through the `~/.config/sb/config.toml` setup in [`first_time_setup.md`](../skills/silverbullet-workflow/references/first_time_setup.md). The server URL + auth token come from KeePassXC on Cam's setup.

5. **Smoke test the server reachability:**

   ```bash
   sb lua '"ok"' 2>&1 | tail -3
   ```

   Expected: `"ok"`.

   - If `bridge_unavailable` (HTTP 503): real bridge wedge, `docker restart silverbullet-silverbullet-1` on warrig is the fix.
   - If HTTP 401: auth token wrong.
   - If HTTP 500 on a well-formed expression: see [`space_lua_pitfalls.md`](../skills/silverbullet-workflow/references/space_lua_pitfalls.md). Almost always a malformed input issue, not a server one.

6. **Smoke test the local space:**

   ```bash
   sb sync status 2>&1 | head -10
   zk list --limit 1 2>&1
   ```

   `sb sync status` shows whether the local space is in step with the server. `zk list --limit 1` confirms zk sees the space.

## Report format

Render a short status block to the user:

```text
sb CLI:        ✓ v0.x.x
zk CLI:        ✓ installed
ZK_NOTEBOOK_DIR: /home/nux/silverbullet
~/.config/sb:  ✓ configured
Server reach:  ✓ sb lua '"ok"' returned "ok"
Local space:   ✓ in sync (or: N files pending)
```

Any `✗` line gets a one-line "fix this by …" pointing at the right reference doc.
