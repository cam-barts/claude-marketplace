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

4. **Check `sb` config** — let `sb` report what it resolved and from where:

   ```bash
   sb version                     # version, commit, and flavor (features: skills,mcp = AI build)
   sb --no-input config show      # every setting with its source (env / space file / user file / default)
   sb config get-space            # which local space root it will use
   ```

   Needs `server_url`, a token, and `[sync] dir = "/home/nux/silverbullet"`. If the config is missing, walk through [`first_time_setup.md`](../skills/silverbullet-workflow/references/first_time_setup.md) — the easiest path on a new machine is copying `~/.config/sb/config.toml` from warrig. Flag an unset `identity` as a warning, not a failure: only `sb inbox` needs it.

5. **Smoke test the server reachability:**

   ```bash
   sb --no-input lua '"ok"'; echo "exit=$?"
   ```

   Expected: `"ok"`, exit `0`. Otherwise branch on the exit code:

   - Exit `3` — auth: the token is wrong or missing (`sb auth set`).
   - Exit `2` with `script_error` — the Lua was malformed. Can't happen with `'"ok"'`; if you changed the probe, see [`space_lua_pitfalls.md`](../skills/silverbullet-workflow/references/space_lua_pitfalls.md).
   - `bridge_unavailable` (HTTP 503) — real headless-Chrome wedge; `docker restart silverbullet-silverbullet-1` on warrig is the fix.

6. **Smoke test the local space:**

   ```bash
   sb --no-input sync status          # conflicts / marker_conflicts / readonly should be 0
   zk list --limit 1 2>&1
   ```

   `sb sync status` shows whether the local space is in step with the server. `zk list --limit 1` confirms zk sees the space.

## Report format

Render a short status block to the user:

```text
sb CLI:        ✓ 1.9.0 (slim|ai)
zk CLI:        ✓ installed
ZK_NOTEBOOK_DIR: /home/nux/silverbullet
sb config:     ✓ server_url, token, sync dir (identity: set|unset)
Server reach:  ✓ sb lua '"ok"' returned "ok"
Local space:   ✓ in sync (or: N files pending)
```

Any `✗` line gets a one-line "fix this by …" pointing at the right reference doc.
