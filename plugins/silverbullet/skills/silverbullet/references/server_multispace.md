# The server: multi-space mode

Verified 2026-10-11 unless noted. Re-check the mode with the `.dashboard` probe below.

Since **2026-10-11** `bullet.coder.cam` runs SilverBullet 2.12.0 in **multi-space** mode
(it was legacy single-space before). Mostly this is invisible to `sb` and `zk`, but a few
things matter.

**Layout.** `~/docker_services/silverbullet/data` is the *data folder*, mounted at `/data`,
holding `spaces.json`, `users.json`, `server.json` and `.chrome-data/`. The markdown did
**not** move: it is still `~/docker_services/silverbullet/space`, mounted at `/space`, and
`spaces.json` points the space at that absolute path. So every sidecar mount and host
script path is unchanged.

**Which mode am I on?** `curl -s -o /dev/null -w '%{http_code}' localhost:6934/.dashboard`
returns `200` in multi-space and `404` in legacy. The boot log says
`boot mode: multi-space (spaces.json present)`.

**Accounts.** `cam` (admin, so always write plus Runtime API) and `barbossa`
(`role: write`, `runtimeApi: true`). Anonymous access is `none`: the space is invisible
without a session. Per-account API tokens replace the old `SB_AUTH_TOKEN` env var and are
stored **hashed**, so a token's plaintext is visible only once at creation.

**The space is bound at the server root** (`binding.prefix: ""`). This is load-bearing:
`sb` can override the server URL (`SB_SERVER_URL`) but has **no way to select a
server-side space**, so binding the space to a path prefix would strand the CLI entirely.

**Admin API** lives under `/.dashboard`, not `/api`:

| Action | Call |
|---|---|
| session identity | `GET /.dashboard/api/session` |
| list / create accounts | `GET`/`POST /.dashboard/api/admin/users` |
| issue a token | `POST /.dashboard/api/admin/users/<name>/tokens` `{name}` (plaintext returned once) |
| read space config | `GET /.dashboard/api/admin/spaces` |
| partial space edit | `PATCH /.dashboard/api/admin/spaces/<id>` (`PUT` wants the whole object and 422s) |
| log in | `POST /.auth`, form `username`/`password`/`next` |

**Per-account Chrome runtimes.** The Runtime API that `sb lua` and `sb query` depend on
runs one headless Chrome per (account, space), each in its own
`data/.chrome-data/runtime-<random6>/`. Consequences:

- A first call from a new account cold-indexes the whole space (about **4 minutes** for
  ~3300 pages on 2026-10-11), during which `sb lua` reports
  `could not connect to .../.runtime/lua`. That is normal, not a wedged bridge.
- The directory name is random, so a warm profile **cannot** be pre-seeded.
- **Any change to a space's config rebuilds the instance and tears down its runtimes**, so
  `sb lua` 503s for a few minutes after an admin edit. Check
  `GET /.dashboard/api/admin/runtimes` for `status: starting` vs `running`.
- Two accounts' runtimes coexist fine (~140M of profile each on 2026-10-11); they do not evict each other.

**`Library/Std` is not on disk.** Its ~70 pages are embedded in the server binary and
served over the API, so `fd`/`rg` across `~/silverbullet` will never find them. Read them
with `curl -H "Authorization: Bearer $TOKEN" .../.fs/Library/Std/<page>.md`. The index
therefore reports more pages than there are `.md` files on disk, which is expected.

**Shell is per-space and off by default** since 2.10 (`shell.enabled` in `spaces.json`).
It is enabled for this space; a `whitelist` alone does not turn it on.

## Revisions in multi-space

Since the **multi-space** cut (2026-10-11) two things changed here:

- `SB_REVISIONS=managed` is gone from the compose file. Revisions are **per-space config**
  (`revisions` in the data folder's `spaces.json`, or the space's Dashboard settings). The
  env var is still read in legacy single-space mode but is ignored in multi-space.
  **Hand-editing `spaces.json` and omitting the `revisions` key silently defaults it to
  `"disabled"`**, which stops recording history with no error.
- Commits are authored by the **account that made the write** (`cam`, `barbossa`), not the
  generic `SilverBullet` of single-space mode. Writes made by an outside process (a
  sidecar writing straight to the bind mount) are authored `External`.

The commit worker only commits writes it **observes**. A page written in the window right
after a space-config change rebuilt the instance can sit uncommitted until something
touches it again, and `git -C space status` will show it as dirty.
