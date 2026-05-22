---
description: Scaffold a new project doc from Library/Personal/Templates/Project, sync to server, open for editing
argument-hint: <name> [summary]
---

Create a new project doc in `~/silverbullet/Projects/` using Cam's Project template as the starting point. Always from the template — never write a project doc blank.

## Arguments

- `name` (required) — project name in title-case, e.g. "Karakeep Capture Time Rewriting". Becomes the filename + the heading.
- `summary` (optional) — one-line description used in the doc's initial state. If absent, leave the Project Description section as the template's prompt for the user to fill.

## Steps

1. **Verify `sb` is reachable.** `sb lua '"ok"'` should return `"ok"`. If not, dispatch to `/sb-setup`.

2. **Confirm the template exists and read it:**

   ```bash
   TEMPLATE=~/silverbullet/Library/Personal/Templates/Project.md
   test -f "$TEMPLATE" || { echo "Template missing — check Library/Personal/Templates/Project.md"; exit 1; }
   ```

3. **Compute the target path:**

   ```bash
   NAME="$1"
   FILENAME=$(echo "$NAME" | sed 's/[^A-Za-z0-9 ]//g')
   TARGET="$HOME/silverbullet/Projects/${FILENAME}.md"
   test -e "$TARGET" && { echo "Project already exists at $TARGET — refusing to overwrite."; exit 1; }
   ```

4. **Copy template into target, adjust frontmatter:**

   ```bash
   cp "$TEMPLATE" "$TARGET"
   ```

   Then:
   - Make sure frontmatter is `tags: project` and `state: todo`. Don't pre-set `state: doing` until Cam actually starts.
   - Replace the heading "# Project Description" placeholder (if any) with the actual project name + the summary if provided.

5. **Sync to server:**

   ```bash
   cd ~/silverbullet && PATH="$HOME/.local/bin:$PATH" sb sync 2>&1 | tail -3
   ```

   Expect `Push complete: 1 uploaded`.

6. **Surface the SB URL** so Cam can click straight into it:

   ```text
   Created [[Projects/${FILENAME}]] from the Project template.
   Open: https://bullet.coder.cam/Projects/$(echo "${FILENAME}" | sed 's/ /%20/g')
   ```

## Template guidance to share with the user

When you scaffold, also remind Cam (briefly):

- Sections are starting places, not handcuffs. Adapt.
- `### Intermediate Packets` stays empty by default — only fill if there's reusable output with value outside this project.
- `## Open Questions` should shrink over time as items resolve into `## Decisions Locked In` with a "locked YYYY-MM-DD" date.
- Frontmatter `state` walks `todo` → `doing` → `done`.

For the full guide see [`project_template.md`](../skills/silverbullet-workflow/references/project_template.md).

## See also

- The template itself: `~/silverbullet/Library/Personal/Templates/Project.md`
- Memory: `feedback_use_project_template.md`, `feedback_intermediate_packets_are_reusable.md`
