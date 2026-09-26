---
documentation_type: reference
---

# Space Lua sharp edges

Three pitfalls in SilverBullet's Space Lua dialect that have each eaten significant time. Each one looks like a runtime issue ("the bridge is wedged", "the index is lagging") on first glance but is actually a dialect quirk. Worth memorising — these aren't standard-Lua bugs.

## 1. `sb lua` takes an expression, NOT a statement block

This is the biggest one. The CLI `sb lua` evaluates whatever you pass as a **Space Lua expression**. There is no implicit function wrapping; top-level `return` is a parse error.

### Right

```bash
sb lua '1+1'             # → 2
sb lua '"ok"'            # → "ok"
sb lua 'tostring(os.time())'  # → "1779413010"
sb lua 'mostLinked(5)'   # → calls the user-defined function, returns its result
```

### Wrong

```bash
sb lua 'return 1+1'             # → script_error, exit 2
sb lua 'return "ok"'            # → script_error, exit 2
sb lua 'local x = 1; return x'  # → script_error, exit 2
```

The web UI's "Run Lua script" command has the same expression-only behavior.

### Statements: use `--script`

Anything with statements, locals, or an explicit `return` goes through `--script` (sb 1.9.0+):

```bash
sb lua --script check.lua
printf 'local n = 0\nfor _ in ipairs(query[[from index.tag "page" limit 5]]) do n = n + 1 end\nreturn n' \
  | sb lua --script -
```

### Why this matters

Since sb 1.9.0 the CLI reads the Runtime API's error code and reports malformed Lua as a **`script_error` with exit code 2** (a usage error) — it is the server **correctly rejecting** your input. Before 1.9.0 the same thing surfaced as a bare HTTP 500, and an older form of this guidance recommended `sb lua 'return "ok"'` as a health probe: malformed Space Lua that *always* failed, leading to multi-day "bridge wedged" false-positive reports. The correct probe is `sb lua '"ok"'`. Confirmed 2026-05-21.

A genuine wedge surfaces as **`bridge_unavailable`** (HTTP 503) — a different code, a server fault.

### Diagnostic recipe

If `sb lua` fails:

1. **Exit 2 / `script_error`** — your Lua threw or didn't parse. Check expression-vs-statement first; switch to `--script` if you need statements.
2. **`bridge_unavailable`** — real wedge. `docker restart silverbullet-silverbullet-1` on warrig is the cure. See [[Projects/SilverBullet Chrome Runtime Issue]] in Cam's space.
3. **Unsure?** Run `sb lua '"ok"'`. If that returns `"ok"`, the server is fine and the problem is your input.

## 2. `query` is a reserved Space Lua keyword

Space Lua uses `query` as the keyword for its query DSL (`query[[from index.tag "X" ...]]`). Using `query` as a regular variable name in a `space-lua` block causes a confusing parse error reported at the **next** token, not at `query` itself.

### Wrong

```lua
local function search_index(query)
  if query == nil or query == "" then return {} end
  local res = net.proxyFetch(..., { body = { q = query } })
  ...
end
```

Standard `luac -p` accepts this. SilverBullet's parser rejects it with `unexpected symbol near 'q'` (or similar — the error name is the NEXT identifier after `query`).

### Right

```lua
local function search_index(qstr)
  if qstr == nil or qstr == "" then return {} end
  local res = net.proxyFetch(..., { body = { q = qstr } })
  ...
end
```

Rename `query` → `qstr` / `qtext` / `searchTerm` / `term`. Anything but `query`.

### Other DSL keywords to watch for

`query` is confirmed problematic. The others use namespaced forms (`tag.define`, `command.define`, `event`, `slashCommand`) which makes accidental collision rare, but they are reserved at the parser level. Treat any of these as suspect when a Space Lua block parses under standard Lua but fails in SB.

### Diagnostic recipe

1. Extract the Space Lua block: `awk '/^\`\`\`space-lua$/{flag=1;next}/^\`\`\`$/{flag=0}flag' <plugin.md> > /tmp/block.lua`
2. `luac -p /tmp/block.lua` — if it passes, the issue is dialect-level, not syntax.
3. Grep for reserved keywords used as identifiers: `grep -nE '\b(query|command|tag|event)\b' /tmp/block.lua`
4. Rename and re-sync.

## 3. `net.proxyFetch` returns JS-wrapped userdata for leaf values

`net.proxyFetch` auto-parses JSON response bodies. Top-level field access works because the bridge implements `__index` on the userdata wrapper: `res.body.hits`, `result.results`, `issue.fields.status.name` all work. **The trap is at leaf values** — strings and arrays inside the parsed body stay JS-wrapped userdata, and three Lua idioms fail against them.

### Failure 1: method-style string calls

Lua's `s:gsub(...)` sugar desugars to `s.gsub(s, ...)` — indexing the JS string for the `gsub` method throws `attempt to index a userdata value`. Same for `:sub`, `:match`, `:find`, `:upper`, `:lower`, `:format`.

```lua
-- WRONG
local snippet = hit.body:gsub("\n", " "):sub(1, 120)

-- RIGHT — functional string.* forms
local snippet = string.sub(string.gsub(hit.body, "\n", " "), 1, 120)
```

Coerce with `tostring(v)` first if `v` might be a JS string returned from `net.proxyFetch`.

### Failure 2: `#arr` length on JS arrays

The `#` operator needs a Lua table; JS arrays don't satisfy that contract.

```lua
-- WRONG
if hit.tags and #hit.tags > 0 then ... end

-- RIGHT — iterate with ipairs (which the bridge implements)
local n = 0
for _, _ in ipairs(hit.tags or {}) do n = n + 1 end
if n > 0 then ... end
```

### Failure 3: `table.concat(arr, ...)` on JS arrays

Same root cause as `#`.

```lua
-- WRONG
local tags_str = table.concat(hit.tags, " ")

-- RIGHT — rebuild as a Lua list first
local parts = {}
for _, t in ipairs(hit.tags or {}) do
  table.insert(parts, tostring(t))
end
local tags_str = table.concat(parts, " ")
```

### Working template

```lua
local res = net.proxyFetch(url, {...})
if not res.ok then return {} end

for _, item in ipairs(res.body.hits) do
  -- .field access is fine
  local title = tostring(item.title or item.path)
  local body  = tostring(item.body or "")

  -- functional string ops, NOT methods
  local snip = string.sub(string.gsub(body, "\n", " "), 1, 120)

  -- ipairs-rebuild before # or table.concat
  local tag_parts = {}
  for _, t in ipairs(item.tags or {}) do
    table.insert(tag_parts, "#" .. tostring(t))
  end
  local tag_str = table.concat(tag_parts, " ")

  -- ... use title, snip, tag_str
end
```

### Diagnostic recipe

If you see `attempt to index a userdata value` from a `net.proxyFetch`-using block:

1. Don't reach for `js.window.JSON.parse(...)` — the body IS already parsed.
2. Grep the Lua block for `:gsub`, `:sub`, `:match`, `:find`, `:upper`, `:lower`, `:format` patterns — usually the culprit.
3. Grep for `#` followed by a likely-array variable, and `table.concat(arr, ...)` — same class of bug.
4. Rewrite using `string.*` functional forms and `ipairs`-rebuild.

## Why these three keep biting

All three look like infrastructure problems on first glance:

- "sb lua failed" (a 500 before 1.9.0, `script_error` now) → "the runtime is broken"
- "unexpected symbol near 'q'" → "the parser has a bug"
- "attempt to index a userdata value" → "the bridge can't handle this response"

They're all dialect quirks. The pattern: a thing that works in standard Lua doesn't work in Space Lua. The skill is recognising the symptom early enough not to chase the wrong diagnosis. Each of these has cost at least a day before being identified — saving that time is the whole reason this reference exists.
