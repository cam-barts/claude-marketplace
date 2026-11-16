---
name: serendipity-gardening
description: |
  Cam's digital-gardening ritual in SilverBullet. Draw a wide random batch of notes using his
  Serendipity page's own pickers, read them, then hunt for non-obvious connections between them
  and propose the exact wikilinks he could add. Output goes to a deliberately ephemeral scratch
  page per round; Cam harvests the links by hand and deletes it. Rounds chain: each new round
  opens with feedback on the edits he made after the last one.
  Use when Cam says he is bored, uninspired, or wants to garden, asks for a serendipity session, a
  gardening session, or a digital-gardening session, wants random notes surfaced for
  connection-making, says "let's go again" or "another round" mid-ritual, or invokes /sb-garden.
  Also fits "what should I be linking", "find connections in my notes", and gardening the orphans
  or thinly-linked notes that nothing points at (a bare "list my orphans" is just a zk query).
  Do NOT use for targeted search, task triage, writing one specific note, or Zotero paper
  enrichment (that is enrich-paper).
---

# Serendipity Gardening

Cam built a [[Serendipity]] page to beat his own attentional bias: a wall of random pickers whose
whole job is showing him notes he is not already primed to look at. This skill is the conversational
half of that: use his pickers to deal a hand of notes, read them properly, and find what they are
secretly about.

**The connections are the main event.** Questions and seeds are supporting acts. A handful of
genuinely illuminating links beats a long shallow list every time.

Last verified against: claude-opus-5-5, 2026-11-16.

## Hard rules

These are Cam's, and they win over anything a companion skill says about editing the space.

1. **Write exactly one file: the session page.** Never edit a content note: not the body, not the
   frontmatter, not a `tags:` line, not a one-word "hygiene" fix, however obviously correct it is.
   Propose it and let Cam do it. That hands-on part is the part he enjoys, and taking it from him
   guts the ritual.
2. **The session page is disposable and must say so.** He harvests it and deletes it. Frontmatter
   carries `ephemeral: true` / `disposable: true` plus a warning admonition at the top.
3. **Additive and non-destructive**, *within the session page*. Never delete, move, or restructure
   anything in the space.
4. **Nothing goes to agent memory.** Cam said so explicitly, twice, in the original brief.
5. **Ground everything in his real material.** Quote his own notes back at him verbatim. Generic
   PKM advice is worthless here.
6. **Run the humanizer skill over the page before writing it.** He asked for this explicitly. Read
   it back and cut anything that sounds generated.

## Where things are

Write in `~/silverbullet` (the `sb sync` working copy), never in
`~/docker_services/silverbullet/space` (what the server container serves). Helpers live in this
skill's `scripts/` (`~/.claude/skills/serendipity-gardening/scripts/`, or under
`$CLAUDE_PLUGIN_ROOT/skills/serendipity-gardening/` for a plugin install):

- `uv run scripts/garden.py deal` draws from his pickers (24 `randomPage`, 4 `randomBias`, 3
  `randomConcept` by default; `--picker EXPR` to choose others), drops records, dedupes, and stops
  loudly if a picker fails.
- `uv run scripts/garden.py check NAME...` existence-checks link targets by file name across the
  space and prints `ASPIRING` for ones that don't exist.
- `uv run scripts/thin_links.py --max-inbound 0 --count 14` is orphan mode (`1` for thinly linked).

## Which round is this?

If Cam processed a previous round, the new one opens with feedback on his edits, not a fresh draw.
He may say so ("let's go again"). Otherwise look in `~/silverbullet/AI Generated/Serendipity/`: a
page still there means he hasn't processed it (ask before dealing another); an empty folder right
after a recent round means he processed and deleted it, so start with the feedback pass. If you
can't place a round in roughly the last two weeks, treat this as round 1; an old empty folder is
not a signal.

## Dealing the hand

Sync first so the local copy matches the index the pickers query. Then draw wide and cut to the
dozen or so notes that have something to say to each other. The pickers are defined in the
`space-lua` block of `~/silverbullet/Serendipity.md` (on 2026-11-16: `randomPage`, `randomBias`,
`randomConcept`, `randomFallacy`, `randomPropaganda`, `randomRhetoric`, `randomByCategory("articles"
| "books")`, plus `quotes.random()`, `bridges.random()`, `ideas.random()` outside the namespace).
If one fails, read that page; names change. Vary the themed pickers round to round so consecutive
rounds don't feel the same. If `sb lua` is down, `thin_links.py --max-inbound 99` gives a
uniform-ish sample instead.

Records (Jira mirrors, Captain's Logs, transcripts) are dropped from the *draw*, not from the
*space*. A ticket is sometimes exactly the right place to land a connection, so search for those
deliberately when hunting; just don't spend draw slots on them.

Cut carefully: the pickers exist to defeat attentional bias, and a cut that optimises for a tight
theme quietly re-imposes it. A round where every kept note is the same idea *looks* successful and
is not. **Keep at least two notes that do not fit the through-line.** Prefer a note carrying Cam's
own marginal commentary or disagreement over a note that merely matches the theme.

**Orphan mode** (when he asks for orphans, neglected notes, or "the stuff that never comes up")
swaps the draw for `thin_links.py`. It mirrors `randomPage()`'s exclusions and also drops records
and this ritual's own session pages. The two modes cover different universes: `randomConcept()`
returns `Persuasion Techniques/` pages, which orphan mode excludes by prefix, and a good share of
zero-inbound pages are `Zotero/` papers nothing links to yet.

**Do not reflexively discard Zotero pages.** An *enriched* one (it has an `## Enrichment` block with
"Impact highlights") carries pulled quotes with page-level commentary and is some of the richest
material in the space — three of the four Zotero pages in the 2026-08-12 round produced connections,
all from their enrichment quotes. An *unenriched* one is frontmatter and an abstract; that is the
one to discard, or hand to `/enrich-paper`.

## Reading the hand

Read the pages properly. Stubs, cheap to spot by size, are often the easiest useful thing to hand
him (a good phrase sitting in an empty room); past rounds' best seeds were abandoned one-liners.
Cap the greedy pages, since a draw can hand you a 26KB work doc or four lines of thought inside an
excalidraw blob. On a Zotero page, read `## Enrichment` first. Worth reporting: empty stubs, notes
cold for years, and Cam's own margin disagreements with a note's premise.

**Existence-check every link before proposing it, by search, not by guessed path** (`garden.py
check`). Folders don't follow from a concept's name, and a guessed path returns a false ASPIRING
that has you propose duplicating a note that already exists. For `[[Path|Alias]]`, check the path.
Aspiring links are fine to propose if you say so; avoid bare generic titles like `[[Real]]` that
will collide with future use of the word.

## The hunt

**Connections (the main event).** Non-obvious links *between* the surfaced notes, and out to
existing ones. The shapes that land: "these two are secretly the same idea", "X reframes Y", "this
pattern recurs across A, B and C". For each, name the exact wikilinks and say **why the link is
illuminating, not merely adjacent**. Rank them and say which one is the find. A verified concrete
finding beats a cleverer speculative one; do not bury a useful link under an interesting one.

**Questions worth sitting with.** Provocative and specific, built from what the notes actually say.
The best ones use his own words as the pivot, and are often uncomfortable.

**Worth writing down.** Gaps the draw exposed: a concept referenced everywhere that has no page, a
synthesis note bridging a cluster, a stub to either write or kill.

His territory, for grounding: homelab and SRE, epistemics and the Codex Vitae, BASB and PKM,
Stoicism, persuasion and cognitive bias, leadership and mentoring, and his own projects.

State claims plainly, but do not manufacture certainty about *his* history or motives. "You built
this field to do X" is an overreach when he may have inherited it from an Obsidian template. Be
direct about what the notes say, careful about why he wrote them.

## Writing the page

Read [`references/session_page.md`](references/session_page.md) for the template and voice first.
Path: `~/silverbullet/AI Generated/Serendipity/Session — YYYY-MM-DD.md`, with a `(Round 2)` suffix
before the extension for later rounds the same day. Six thin connections are worse than three that
land.

Write it as Barbossa (`. ~/.config/sb-barbossa/env`) and `sb sync`. Check `sb sync status`: report
pre-existing `conflicts` to Cam rather than pushing into them, and a pull on the way means he was
editing while you worked, which is worth a mention, not a problem.

## Reporting back

Don't just point at the page. Relay the goods: the draw, the sharpest question or two quoted, the
best connections with their exact wikilinks, the top seed. Close with an offer of another round:
`Ready to go again whenever, or leave it here.`

## Rounds 2+: the feedback pass

This is what makes it a practice instead of a one-off. Before dealing, grade what he did with the
last page. Sync, then find what he changed since that round (for example
`fd -e md --changed-within 7d . ~/silverbullet`, widened if he has been away), and read those notes.

- **Say when his call beat yours, and mean it.** (Once he swapped a suggested link for a better one;
  that got said plainly.)
- **Flag aspiring links he created** that are too generic to survive.
- **Note frontmatter the browser editor stripped on save** (`note_type`, `last-reviewed`).
- Untagged new notes still surface in the main draw (`randomPage()` queries `index.tag "page"`,
  which every page has); missing `tags:` only hides a note from the *themed* pickers. Worth one
  mention, not a campaign, and never something you fix yourself (rule 1).
- He deletes frontmatter deliberately sometimes, an Obsidian holdover. Do not nag twice about it.

Then run the next round normally. Let threads carry across rounds: when the dice return a note he
just wrote, say so and build on it.

## Ending

He ends it himself, usually by stopping. Do not push for another round beyond the one-line offer.

## Maintaining this skill

The hard rules, the two-misfits rule, the voice, and the feedback etiquette are Cam's taste and
stay. Picker names, folder prefixes, and the record skip-list are environment facts: `garden.py` and
`thin_links.py` carry the mechanics, so update them there. Re-check with
`sb lua 'serendipity.randomPage().markdown'` (should print a `[[wikilink]]`).
