# The session page — structure and voice

Read this before writing a session page. Examples are lifted from real rounds Cam kept and acted on.

> **Everything below is copy that goes into the session page.** "Add X to Y" is a sentence you
> write for Cam to act on — never an action you perform. You write exactly one file, the session
> page, and no content note is ever edited (hard rule 1).
>
> The fenced blocks below are samples of that copy, not commands.

## Contents

- [Template](#template)
- [Section by section](#section-by-section)
- [Voice](#voice)
- [Worked examples](#worked-examples)

## Template

```markdown
---
date: 2026-06-30
tags: serendipity
ephemeral: true
disposable: true
surfaced: 14
generator: Barbossa
---

# Serendipity Session — 2026-06-30 (Round 2)

> [!warning] Ephemeral scratch page
> Process it, harvest the links and seeds into their real homes, then delete.
> Nothing here is load-bearing.

[One paragraph: how the draw was made, and the through-line of this round if there is one.]

## Feedback on your round-1 edits      <!-- rounds 2+ only -->

## What came up

## Questions worth sitting with

## Connections to make (the main event)

## Worth writing down
```

Drop `(Round N)` and the feedback section on the first round of a day. `surfaced:` is however many
notes the page actually lists — be consistent within a session.

## Section by section

**Preamble.** One paragraph, no throat-clearing. Name the mechanism honestly, then say what the
round is about if a theme emerged:

```markdown
Ran the [[Serendipity]] page's own pickers from the CLI — `serendipity.randomPage()` about
eighteen times plus `randomBias()` and `randomConcept()` — and kept the fourteen that had
something to say to each other.

Third pull from the [[Serendipity]] page's own pickers. This round mostly *completes* a thread
you've been building across all three sessions — the expertise/intuition axis — because the dice
handed back [[Z/The Difference Between Insight and Intuition]] right on top of the note you just
wrote, [[Z/A Novice Relies on Heuristics]].
```

**What came up.** Bulleted wikilinks. Annotate the ones with a tell:

```markdown
- [[Z/Threshold]] — *(empty — frontmatter only, last touched 2023-12-22)*
- [[Z/Code can be Beautiful]]

*(also surfaced, quieter: [[Work/K6 Notes]] · [[People/Jenny Egley]] · [[Z/Error Budget]])*
```

The trailing quieter line is how the real rounds handled the ones that did not make the cut — it
keeps them visible for Cam without giving them a section. Better than discarding them silently.

**Questions worth sitting with.** Bold lead-in phrase, then prose. Two to four. Each ends on a real
question.

**Connections.** Numbered `###` sub-sections. Each names the exact wikilinks and closes on why the
link pays. Rank them — call out the find.

**Worth writing down.** Numbered. Each is a concrete page that should exist, or a stub to resolve.

## Voice

- **Quote his own notes back at him verbatim**, then turn them. This is the single highest-value move.
- Second person, direct. "You premortem your software" — not "Cam premortems his software".
- Rank openly: *"This one's the find."*
- Be willing to say a note is dead: *"Either write the thought or delete it."*
- Wit is welcome when it is doing work: *"the Curse of Knowledge wearing a hoodie."*
- No hedging, no "it might be interesting to consider". Make the claim.
- Humanizer pass at the end. Cut the rule-of-three lists, the "delve", the em-dash pileups, the
  symmetrical "not X, but Y" constructions.

## Worked examples

**A connection that landed:**

```markdown
### 1. The Curse of Knowledge is secretly the subject of three of these notes

This one's the find. [[Persuasion Techniques/Curse of Knowledge]] shows up disguised in a bias
note, a teaching note, and an aesthetics note, and none of them link to it.

- Add [[Persuasion Techniques/Curse of Knowledge]] to [[Work/Training/Aftab Ali - Training Plan]].
  The star-grading of a novice *is* the bias in the wild; the rubric is your attempt to engineer
  around it. Link back from Curse of Knowledge to the rubric as a concrete instance — right now
  that note only has textbook examples.

Why it's worth it: once the link exists, "can I grade a novice fairly?" and "is code beautiful or
just legible to me?" become *the same question*, and you'll see it everywhere.
```

**A question that landed:**

```markdown
**On beauty as legibility.** ThePrimeagen's counter that you saved in [[Z/Code can be Beautiful]] —
*"Code isn't beautiful, it just makes sense to you. You can grasp it easily"* — is the Curse of
Knowledge wearing a hoodie. If beauty is really just familiarity, then is your bespoke `sb` CLI
actually elegant, or do you just have the curse about your own code?
```

**A seed that became a real note:**

```markdown
**The prose note you're one link away from: "SRE is Applied Stoicism."** Error budgets as
[[Z/Memento Mori]] for uptime. Premortems as [[Z/Premeditatio Malorum]]. Runbooks as
[[Z/Trust the Prep List]]. The turkey as [[Persuasion Techniques/Induction]]. Blameless
postmortems as the Stoic refusal to moralize a system failure.
```

He wrote it. It came back on a later draw and the next round built on it.

**Feedback that landed:**

```markdown
You didn't just accept the links — you did real thinking, and a few of your calls are sharper than
mine were.

- **`Code can be Beautiful` → [[Persuasion Techniques/Mere Exposure Effect]]** on ThePrimeagen's
  counter — that's a *better* pick than my Curse of Knowledge suggestion. Mere Exposure ("you like
  it because you've seen it a lot") is more precise for "it just makes sense to you" than the curse
  is. Nice correction.
- **[[Z/SRE Is Applied Stoicism]]** — best thing to come out of the last session. One practical
  nit: **it has no frontmatter/tags**, so it won't show up in `index.tag "concept"` or the
  Serendipity concept picker. Worth adding `tags: concept` so this one doesn't become an orphan
  the graph can't see.
```

(That last bullet is quoted as written at the time. Keep the nuance straight when reusing it: a
missing `tags:` hides a note from the *themed* pickers only — `randomPage()` queries
`index.tag "page"`, which every page has. And you never add the tag yourself.)
