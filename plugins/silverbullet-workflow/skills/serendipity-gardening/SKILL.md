---
name: serendipity-gardening
description: |
  Cam's digital-gardening ritual in SilverBullet. Draw a wide random batch of notes using his
  Serendipity page's own pickers, read them, then hunt for non-obvious connections between them
  and propose the exact wikilinks he could add. Output goes to a deliberately ephemeral scratch
  page per round — Cam harvests the links by hand and deletes it. Rounds chain: each new round
  opens with feedback on the edits he made after the last one.
  Use when Cam says he is bored, uninspired, or wants to garden, asks for a serendipity session, a
  gardening session, or a digital-gardening session, wants random notes surfaced for
  connection-making, says "let's go again" or "another round" mid-ritual, or invokes /sb-garden.
  Also fits "what should I be linking", "find connections in my notes", and gardening the orphans
  or thinly-linked notes that nothing points at.
  Do NOT use for targeted search, task triage, writing one specific note, or Zotero paper
  enrichment (that is enrich-paper).
---

# Serendipity Gardening

Cam built a [[Serendipity]] page to beat his own attentional bias — a wall of random pickers whose
whole job is showing him notes he is not already primed to look at. This skill is the conversational
half of that: use his pickers to deal a hand of notes, read them properly, and find what they are
secretly about.

**The connections are the main event.** Questions and seeds are supporting acts. A handful of
genuinely illuminating links beats a long shallow list every time.

## Hard rules

1. **Write exactly one file: the session page.** Never edit a content note — not the body, not the
   frontmatter, not a `tags:` line, not a one-word "hygiene" fix, however obviously correct it is.
   Propose it and let Cam do it. That hands-on part is the part he enjoys, and taking it from him
   guts the ritual.
2. **The session page is disposable and must say so.** He harvests it and deletes it. Frontmatter
   carries `ephemeral: true` / `disposable: true` plus a warning admonition at the top.
3. **Additive and non-destructive** — *within the session page*. Never delete, move, or restructure
   anything in the space.
4. **Nothing goes to agent memory.** Cam said so explicitly, twice, in the original brief.
5. **Ground everything in his real material.** Quote his own notes back at him verbatim. Generic
   PKM advice is worthless here.
6. **Run a humanizer pass before writing.** He asked for this explicitly. No "delve", no rule of
   three, no throat-clearing. Read it back and cut anything that sounds generated.

## Setup

```bash
export ZK_NOTEBOOK_DIR="$HOME/silverbullet"
export PATH="$HOME/.local/bin:$PATH"
sb --version || echo "MISSING — see the silverbullet-workflow skill's references/cli_install.md"

# Resolve this skill's own script dir (works for skills-dir and plugin installs alike)
SG="$HOME/.claude/skills/serendipity-gardening/scripts/thin_links.py"
[ -f "$SG" ] || SG="$CLAUDE_PLUGIN_ROOT/skills/serendipity-gardening/scripts/thin_links.py"
```

Two directories, do not mix them up:

- `~/silverbullet` — the `sb sync` working copy. **Write here.**
- `~/docker_services/silverbullet/space` — what the server container serves. Do not write here.

## Step 0 — Which round is this?

**Do this before dealing anything.** If Cam has processed a previous round, the new round opens with
feedback on his edits, not with a fresh draw. Jump to [Rounds 2+](#rounds-2--the-feedback-pass),
run the feedback pass, then come back to Step 1.

Signals that a previous round happened:

- He says "let's go again", "another round", or refers to having processed the last page.
- `ls ~/silverbullet/"AI Generated/Serendipity/"` — a page still sitting there means he has not
  processed it yet; ask before dealing a new one. **An empty or missing directory after a prior
  round means he processed and deleted it** — that is the signal to run the feedback pass.

**Bound it by recency.** The feedback pass only works on edits you can still find. If you cannot
establish that a round happened in roughly the last two weeks, treat this as round 1 — an empty
`Serendipity/` folder from months ago is not a signal, it is just an old folder.

If none of those hold, this is round 1. Continue.

## Step 1 — Deal the hand

Sync first, so the local copy you will read matches the server-side index the pickers query:

```bash
cd ~/silverbullet && sb sync 2>&1 | tail -4
```

### Uniform draw (default)

His actual mechanism: loop his own Space Lua pickers from the CLI and scrape the wikilink out.
`sb lua` takes an **expression**, never a `return` statement.

Probe one picker first, without swallowing stderr — `sb` exits 0 even on a server 500, so a silenced
loop turns a broken runtime into an empty draw with no error:

```bash
sb lua 'serendipity.randomPage().markdown'    # must print a [[wikilink]]
```

If that errors or prints nothing, read `~/silverbullet/Serendipity.md` — the pickers are defined in
its `space-lua` block and the names may have changed since this skill was written. If `sb lua`
itself is down, use the fallback below.

`randomPage()` draws from every `#page`-tagged note, which includes pages that are *records* rather
than notes: ticket mirrors and daily logs. They have no connective tissue and burn draw slots. Filter
them out, and pull a few extra to cover the loss:

```bash
DRAW_SKIP='^(Jira/|Barbossa/Captains Log/|Journals/Captains Log/|Transcripts/)'

for i in $(seq 1 24); do
  sb lua 'serendipity.randomPage().markdown' 2>/dev/null | grep -oP '\[\[\K[^]]+'
done | grep -Ev "$DRAW_SKIP" | sort -u
for i in $(seq 1 4); do sb lua 'serendipity.randomBias().markdown'    2>/dev/null | grep -oP '\[\[\K[^]]+'; done
for i in $(seq 1 3); do sb lua 'serendipity.randomConcept().markdown' 2>/dev/null | grep -oP '\[\[\K[^]]+'; done
```

`sort -u` matters: 24 draws from ~1400 pages collide often enough to notice.

Excluded from the *draw* is not excluded from the *space*. A Jira ticket is often exactly the right
place to land a connection — this round's second-best connection put two bias notes onto a live
`ST-7554` MTTR panel. Search for those deliberately in Step 3; just do not spend draw slots on them.

Also available: `randomFallacy`, `randomPropaganda`, `randomRhetoric`, `randomHighlight`,
`randomByCategory("articles")`, `randomByCategory("books")`, and — outside the `serendipity.*`
namespace — `quotes.random()`, `bridges.random()`, `ideas.random()`. Vary the themed pickers round
to round so consecutive rounds do not feel the same.

**Draw wide, then cut.** Pull ~24, expect ~20 to survive the filter and the dedupe, and keep the
**10–14 that have something to say to each other**.

But cut carefully: the pickers exist to defeat attentional bias, and a cut that optimises for a tight
theme quietly re-imposes it. A round where every kept note is the same idea *looks* successful and
is not. **Keep at least two notes that do not fit the through-line.** Prefer a note carrying Cam's
own marginal commentary or disagreement over a note that merely matches the theme.

If `sb lua` is down, fall back to `python3 "$SG" --max-inbound 99` for a uniform-ish sample rather
than abandoning the session.

### Orphan mode (on request)

When Cam asks for orphans, neglected notes, or "the stuff that never comes up", swap the draw:

```bash
python3 "$SG" --max-inbound 0 --count 14   # true orphans
python3 "$SG" --max-inbound 1 --count 14   # thinly linked
```

Prints `inbound_count<TAB>page_name`. It mirrors `randomPage()`'s exclusions and additionally drops
ticket mirrors, daily logs, transcripts, and this ritual's own session pages, all of which are
structurally orphaned and would otherwise flood the draw. Corpus scale for calibration: ~1400 pages, ~350 with
zero inbound links.

Note the two modes cover different universes: `randomConcept()` returns `Persuasion Techniques/`
pages, which orphan mode excludes by prefix. Roughly a quarter of zero-inbound pages are `Zotero/`
papers nothing links to yet.

**Do not reflexively discard Zotero pages.** An *enriched* one (it has an `## Enrichment` block with
"Impact highlights") carries pulled quotes with page-level commentary and is some of the richest
material in the space — three of the four Zotero pages in the 2026-08-12 round produced connections,
all from their enrichment quotes. An *unenriched* one is frontmatter and an abstract; that is the
one to discard, or hand to `/enrich-paper`.

## Step 2 — Read the hand

Size the hand first — it costs one command and tells you where the stubs are:

```bash
cd ~/silverbullet && wc -c <each surfaced page> | sort -n
```

Anything under ~300 bytes is a stub, and **stubs are the highest-yield item in the draw.** Both
recorded rounds had an abandoned one-liner as their top seed: `Z/Threshold` (empty since 2023) and
`Z/We Are Ambulances, Not Cops` (a borrowed slogan, an attribution, no body). A good phrase sitting
in an empty room is the easiest genuinely useful thing you can hand him.

Then `cat` each page, capping the greedy ones (`head -c 8000`) — the draw will hand you 26KB work
docs and notes that are four lines of thought inside a blob of excalidraw JSON. On a Zotero page,
read the `## Enrichment` block first; that is where the quotable material is.

Note the tells worth reporting: empty stubs, notes cold for years, and Cam's own margin
disagreements with a note's premise.

**Existence-check every link before proposing it — by search, not by guessed path.** Folder
structure does not follow from a concept's name (`Chauffeur Knowledge` lives under
`Persuasion Techniques/`, not `Z/`), and a guessed path returns a false ASPIRING that makes you
confidently propose duplicating a note that already exists:

Batch it — one pass over every link you are considering, so a false ASPIRING cannot slip through:

```bash
cd ~/silverbullet
for n in "Chauffeur Knowledge" "Commitment Device" "Z/Decision Matrix"; do
  hit=$(find . -iname "*${n##*/}*.md" -not -path "*/.*" | head -3 | tr '\n' '|')
  printf '%-34s %s\n' "$n" "${hit:-ASPIRING}"
done
```

For aliased links, check the path inside `[[Path|Alias]]`, not the alias. Aspiring links are fine to
propose — say so, and avoid bare generic titles like `[[Real]]` that will collide with future use of
the word.

## Step 3 — Hunt

Produce three things, in this order of effort:

**Connections (the main event).** Non-obvious links *between* the surfaced notes, and out to
existing ones. The shapes that land: "these two are secretly the same idea", "X reframes Y", "this
pattern recurs across A, B and C". For each, name the exact wikilinks and say **why the link is
illuminating, not merely adjacent**. Rank them — say which one is the find. When ranking, a verified
concrete finding beats a cleverer speculative one; do not bury a useful link under an interesting one.

**Questions worth sitting with.** Provocative and specific, built from what the notes actually say.
The best ones use his own words as the pivot, and are often uncomfortable.

**Worth writing down.** Gaps the draw exposed: a concept referenced everywhere that has no page, a
synthesis note bridging a cluster, a stub to either write or kill.

His territory, for grounding: homelab and SRE, epistemics and the Codex Vitae, BASB and PKM,
Stoicism, persuasion and cognitive bias, leadership and mentoring, and his own projects.

State claims plainly — but do not manufacture certainty about *his* history or motives. "You built
this field to do X" is an overreach when he may have inherited it from an Obsidian template. Be
direct about what the notes say, careful about why he wrote them.

Read [`references/session_page.md`](references/session_page.md) for the page template and worked
examples of the voice before writing anything.

## Step 4 — Write and sync

Path: `~/silverbullet/AI Generated/Serendipity/Session — YYYY-MM-DD.md`, and for later rounds the
same day append a round marker before the extension, e.g. `Session — 2026-06-30 (Round 2).md`.
Create the folder if it does not exist. Template and voice: see the reference file.

Aim for roughly 800–2000 words. Six thin connections are worse than three that land.

```bash
cd ~/silverbullet && sb sync 2>&1 | tail -4 && sb sync 2>&1 | tail -4 && sb sync status
```

Sync twice: the first pushes, the second should be a no-op. `sb sync status` returns JSON — report
`modified`/`new` and **check `conflicts`**; a non-zero count is pre-existing and worth telling him
about rather than pushing into silently. A first-pass *pull* means Cam was editing while you worked
— mention it, it is not a problem.

## Step 5 — Report back in chat

Do not just point at the page. Relay the goods: the draw, the sharpest question or two quoted, the
best connections with their exact wikilinks, the top seed. Close with an offer of another round —
`Ready to go again whenever, or leave it here.`

## Rounds 2+ — the feedback pass

This is what makes it a practice instead of a one-off. When Cam comes back having processed the last
page, **open the new round by grading what he did**, before dealing a new hand.

Find his edits:

```bash
cd ~/silverbullet && sb sync 2>&1 | tail -4
find . -name "*.md" -mtime -7 -not -path "*/.*" -printf "%TY-%Tm-%Td %TH:%TM  %p\n" | sort -r | head -40
```

`-mtime -7` catches a round he came back to days later. Narrow it if the list is noisy; widen it if
he has been away. The full date in the sort key matters — sorting on `%TH:%TM` alone puts last
night's 23:50 edit above this morning's 00:10.

Read every changed note and give real feedback:

- **Say when his call beat yours, and mean it.** He replaced a suggested `[[Curse of Knowledge]]`
  with `[[Mere Exposure Effect]]` once and it was the better link. That got said plainly.
- **Flag aspiring links he created** that are too generic to survive.
- **Note frontmatter the browser editor stripped on save** (`note_type`, `last-reviewed`).
- Untagged new notes still surface in the main draw — `randomPage()` queries `index.tag "page"`,
  which every page has. Missing `tags:` only hides a note from the *themed* pickers. Worth one
  mention, not a campaign, and never something you fix yourself (rule 1).
- He deletes frontmatter deliberately sometimes — Obsidian holdover. Do not nag twice about it.

Then run the next round normally. Let threads carry across rounds: when the dice return a note he
just wrote, say so and build on it.

## Ending

He ends it himself, usually by stopping. Do not push for another round beyond the one-line offer.
