---
description: Append an entry to today's Captain's Log
argument-hint: <entry> [task|swab|note|summary]
---

Append a short prose entry to today's Captain's Log (`Journals/Captains Log/YYYY-MM-DD.md`). Creates the file if it doesn't exist, using the standard log template.

## Arguments

- `entry` (required) — the prose body. One or more paragraphs. Will be appended verbatim.
- `kind` (optional, default: `task`) — `task` | `swab` | `note` | `summary`. Controls the entry header.

## Steps

1. **Resolve today's log path** in the user's local timezone:

   ```bash
   TODAY=$(date +%Y-%m-%d)
   LOG=~/silverbullet/Journals/Captains\ Log/${TODAY}.md
   ```

2. **Create the file if absent.** Use Cam's standard log template:

   ```markdown
   ---
   tags: log
   ---

   # Captain's Log — YYYY-MM-DD

   ```

   (One blank line after the heading, ready for entries.)

3. **Compose the entry header** based on `kind`:

   - `task` → `**Task picked:**` + the entry
   - `swab` → `**Swab picked:**` + the entry
   - `note` → `**Note:**` + the entry
   - `summary` → `## Day summary` + the entry (used by the trailing-day roll-up swab; goes at the bottom of the file rather than appended mid-stream)

4. **Append to the file:**

   ```bash
   {
     echo ""
     echo "**${HEADER}** ${ENTRY}"
   } >> "$LOG"
   ```

   For `kind: summary`, prefix with a heading instead:

   ```bash
   {
     echo ""
     echo "## Day summary"
     echo ""
     echo "${ENTRY}"
   } >> "$LOG"
   ```

5. **Sync to server:**

   ```bash
   cd ~/silverbullet && PATH="$HOME/.local/bin:$PATH" sb sync 2>&1 | tail -3
   ```

   Expect `Push complete: 1 uploaded` (or 0 if the file already had today's entries).

6. **Surface the URL** so Cam can review:

   ```text
   Appended to [[Journals/Captains Log/YYYY-MM-DD]].
   Open: https://bullet.coder.cam/Journals/Captains%20Log/YYYY-MM-DD
   ```

## Entry style guide

- Prose, not bullets. The log is for reading later, not parsing.
- Reference the project doc / page that work touched via wikilink: `[[Projects/X]]`.
- Third-person-ish — works for both Cam's own entries and Barbossa's autonomous fires. Examples:
  - `**Task picked:** [[Projects/Y]] — wired up the embedder. Hybrid query latency 5–25ms.`
  - `**Swab picked:** Captain's Log roll-up. Added trailing-day summaries to 05-19 and 05-20.`
  - `**Note:** SilverSearcher fully uninstalled; bridge healthy with the proper expression-form probe.`
- One blank line between entries for readability.

## See also

- Memory: `feedback_chief_of_staff_mode.md` — when Barbossa logs autonomous fires
- `task_patterns.md` — how task-completion entries reference back to the source `[ ]` line
