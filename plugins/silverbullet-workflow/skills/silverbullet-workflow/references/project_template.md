---
documentation_type: reference
---

# Cam's Project doc template

When a new project is being scoped, Cam starts from `Library/Personal/Templates/Project` — never from a blank page. The template is a starting place, not handcuffs. Sections that don't apply stay empty; sections that need expansion get expanded. The template's structure exists so future-Cam (and Barbossa) can find the same shape every time.

## Where the template lives

```text
~/silverbullet/Library/Personal/Templates/Project.md
```

In the SB UI, the slash command `/Project` (or `Page: From Template` → "Project") scaffolds a new doc with the template's content.

From the CLI, the `/sb-new-project` command in this plugin does the same — reads the template, writes a new page, opens it for editing.

## Sections (and what to do with each)

The template structure as of 2026-05-22:

### `# Project Description`

Plain-prose explanation of the problem, the proposed fix, and the load-bearing design choice. 2–5 paragraphs. **Front-load the pain** — what hurts today, why it hurts, what the architectural fix is.

### `## Definition Of Done`

Checklist of conditions that mean the project is complete. Each is a checkbox bullet. The headline outcome goes first. Add `[x]` when items resolve; the doc state flips from `state: doing` → `state: done` when ALL DoD items are checked.

### `## Expected Deliverable or Output`

Concrete artifacts. "A SilverBullet plug at `Library/cambarts/fastsearch.plug.js`." "An indexing sidecar service." Names of files, not vague capabilities.

### `### Intermediate Packets`

**Empty by default.** Only fill this if there are reusable outputs with value OUTSIDE this project. A benchmark harness reusable for future FTS engine comparisons → packet. A one-off plug specific to this project → NOT a packet. Cam's note in memory: "Intermediate Packets are reusable outputs in the narrow BASB sense — deliverables that have value outside this project. Not just any phase deliverable — those are tasks." If nothing reusable exists, leave the section blank rather than padding.

### `## Brag Sheet Write Up`

One paragraph, present-tense first-person, that you could lift verbatim into a resume bullet or quarterly self-review. Written at the end of the project when DoD is met. While work is in progress, this section can be empty or sketchy.

### `## Plan`

Phase-by-phase breakdown. Each phase is a `### Phase N — Name` heading with a numbered list of steps. The plan should be small enough that an individual phase is independently valuable — if the project stalls after Phase 2, what's been built so far should still be worth something. Don't pad; if there are only two real phases, write two.

### `## Outline`

Load-bearing design choices and rationale. Different from "plan" — this is the architectural skeleton, not the implementation sequence. Read by future-Cam when wondering "why did we build it this way."

### `### Open Questions`

Things that need answers before (or during) execution. As they resolve, **move them to `## Decisions Locked In`** with a "locked YYYY-MM-DD" date. The Open Questions section should shrink over time; if it doesn't, that's a signal the project is stuck on something.

### `## Dependencies`

What this project needs to exist first. Other docker services, env vars, hardware, other projects. Skip the obvious (Docker, internet); include the non-obvious (a specific Pi being online, a credential being rotated, an upstream PR).

### `## People Involved`

Cam owns most projects solo; the agent role is barbossa. Cross-functional projects may name other people. Each entry: name + short role description.

### `## Contingencies`

What's the rollback / Plan B for each big architectural choice. "If Meilisearch ranking is worse than SilverSearcher → fall back to Typesense." One contingency per major decision is enough.

### `## Premortem`

How could this fail? Each item is a single sentence describing the failure mode, sometimes with a brief mitigation. Honest projection of risk — the premortem is for Cam to know what to watch for, not a hedge against criticism.

### `## Tasks`

Bullet list of `- [ ]` task items with `[assignee:]` and other metadata. The unit of work, separate from "Plan" (which is the structure) and "Decisions Locked In" (which is the rationale). When a task closes, flip `[x]` and optionally add `[completed:YYYY-MM-DD]`.

### `## Decisions Locked In`

Each decision is a `### Decision title (locked YYYY-MM-DD)` heading followed by 2–5 paragraphs explaining what was decided and why. Includes trade-offs considered and ruled out. This is the section future-Cam reads when wondering "why didn't we just use X." Append-only — don't rewrite history when context shifts; add a new dated decision that supersedes the old one.

### `## Log`

Chronological record of work. Each entry is a `### YYYY-MM-DD — Title` heading with prose describing what happened. Captures both progress and dead ends. Most-recent entry at the top.

## Anti-patterns to avoid

- **Padding empty sections** so the doc "looks complete." If Intermediate Packets is blank because there aren't any, leave it blank.
- **Promoting bullets to tasks.** Considerations belong as plain bullets in Outline / Premortem, not as `- [ ]` items in Tasks.
- **Open Questions that never get answered.** A question sitting open for 4+ weeks is either resolved (and forgot to move) or not actually load-bearing (and should be deleted).
- **Mixing Decisions Locked In with current Log entries.** Decisions are append-only and stable; Log is chronological narrative. Keep them separate.
- **Frontmatter without `state`.** Every project doc needs `state: todo` / `state: doing` / `state: done` so the index can filter.

## Frontmatter

```yaml
---
tags: project
state: doing
---
```

Other tags appropriate to the project (e.g. `homelab`, `personal`, `work`) can be added but `project` is the load-bearing one.

## See also

- `/sb-new-project` — slash command that scaffolds from the template
- `task_patterns.md` — how tasks inside a project doc should be structured
- Memory: `feedback_use_project_template.md` — Cam's preference to start from the template every time
- Memory: `feedback_intermediate_packets_are_reusable.md` — narrow BASB sense of Intermediate Packets
