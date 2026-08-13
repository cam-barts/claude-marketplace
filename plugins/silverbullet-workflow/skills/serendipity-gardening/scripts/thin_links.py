#!/usr/bin/env python3
"""Rank SilverBullet pages by inbound wikilink count — thinnest first.

Orphan mode for the serendipity-gardening ritual: surfaces the notes that
`serendipity.randomPage()` will almost never hand you attention for, because
nothing points at them.

Usage:
    thin_links.py [--space DIR] [--max-inbound N] [--count N] [--seed N]
    thin_links.py --self-check
"""

import argparse
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

# Mirrors the exclusions in serendipity.randomPage() on the Serendipity page,
# so orphan mode draws from the same universe as the uniform draw...
EXCLUDE_PREFIXES = [
    "Library/",
    "_plug/",
    "Readwise/",
    "Persuasion Techniques/",
    # ...plus pages that are records rather than notes. Nothing ever links to a
    # daily log, a raw transcript, or a ticket mirror, so by inbound-count they
    # are all "orphans" and they drown out the real ones. They stay valid link
    # *targets* — they are just not worth spending a draw slot on.
    "Jira/",
    "Journals/Captains Log/",
    "Barbossa/Captains Log/",
    "Transcripts/",
    "AI Generated/Serendipity/",
]
EXCLUDE_EXACT = {"CONFIG", "index", "Serendipity"}

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def page_names(space: Path) -> list[str]:
    out = []
    for p in space.rglob("*.md"):
        rel = p.relative_to(space).with_suffix("").as_posix()
        if rel.startswith(tuple(EXCLUDE_PREFIXES)) or rel in EXCLUDE_EXACT:
            continue
        if any(part.startswith(".") for part in Path(rel).parts):
            continue
        out.append(rel)
    return sorted(out)


def inbound_counts(space: Path, pages: list[str]) -> dict[str, int]:
    """Count inbound wikilinks per page.

    SilverBullet links come in two shapes: full-path (`[[Z/Threshold]]`) and
    aspiring short-name (`[[Threshold]]`). Both must count, or every page Cam
    links to by short name looks like an orphan.
    """
    by_basename = defaultdict(list)
    for name in pages:
        by_basename[name.rsplit("/", 1)[-1]].append(name)

    counts = dict.fromkeys(pages, 0)
    known = set(pages)

    for md in space.rglob("*.md"):
        rel = md.relative_to(space).with_suffix("").as_posix()
        if any(part.startswith(".") for part in Path(rel).parts):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for raw in WIKILINK.findall(text):
            target = raw.strip()
            if not target or target == rel:  # ignore self-links
                continue
            if target in known:
                counts[target] += 1
            elif "/" not in target:
                # Bare short name only. A link that already carries an explicit path
                # (`[[Inbox/2026-04-27/Problems With ADM]]`) names a specific page; if
                # that page does not exist the link is aspiring, and crediting some
                # unrelated page with the same basename inflates its inbound count.
                matches = by_basename.get(target, [])
                if len(matches) == 1 and matches[0] != rel:
                    counts[matches[0]] += 1
    return counts


def pick(
    space: Path, max_inbound: int, count: int, seed: int | None
) -> list[tuple[str, int]]:
    pages = page_names(space)
    counts = inbound_counts(space, pages)
    thin = [(n, c) for n, c in counts.items() if c <= max_inbound]
    rng = random.Random(seed)
    rng.shuffle(thin)
    # Thinnest first among the sample, so true orphans lead the batch.
    return sorted(thin[:count], key=lambda nc: nc[1])


def self_check() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        space = Path(d)
        (space / "Z").mkdir()
        (space / "Library").mkdir()
        (space / "Z/Threshold.md").write_text("empty\n")
        (space / "Z/Hub.md").write_text("[[Z/Linked]] and [[Threshold]] again\n")
        (space / "Z/Linked.md").write_text("[[Z/Hub]]\n")
        (space / "Z/Orphan.md").write_text("nobody points here\n")
        (space / "Library/Ignored.md").write_text("[[Z/Orphan]]\n")

        (space / "Jira").mkdir()
        (space / "Jira/ST-1234 Some Ticket.md").write_text("ticket mirror\n")

        pages = page_names(space)
        assert "Library/Ignored" not in pages, pages
        assert "Jira/ST-1234 Some Ticket" not in pages, pages
        assert set(pages) == {"Z/Hub", "Z/Linked", "Z/Orphan", "Z/Threshold"}, pages

        counts = inbound_counts(space, pages)
        # Excluded dirs still count as link *sources*: Library/Ignored points at Orphan.
        assert counts["Z/Orphan"] == 1, counts
        assert counts["Z/Linked"] == 1, counts
        assert counts["Z/Hub"] == 1, counts
        # Short-name [[Threshold]] resolves to the single Z/Threshold page.
        assert counts["Z/Threshold"] == 1, counts

        # An explicitly-pathed link to a non-existent page must NOT credit a
        # same-basename page elsewhere.
        (space / "Z/Decoy.md").write_text("[[Inbox/Orphan]]\n")
        counts = inbound_counts(space, page_names(space))
        assert counts["Z/Orphan"] == 1, counts

        (space / "Z/Second Hub.md").write_text("[[Z/Threshold]]\n")
        counts = inbound_counts(space, page_names(space))
        assert counts["Z/Threshold"] == 2, counts
        assert counts["Z/Second Hub"] == 0, counts

        picked = pick(space, max_inbound=0, count=5, seed=1)
        assert sorted(n for n, _ in picked) == ["Z/Decoy", "Z/Second Hub"], picked

    print("self-check OK")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--space", default=str(Path.home() / "silverbullet"))
    ap.add_argument("--max-inbound", type=int, default=1)
    ap.add_argument("--count", type=int, default=14)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    if args.self_check:
        self_check()
        return 0

    space = Path(args.space).expanduser()
    if not space.is_dir():
        print(f"space not found: {space}", file=sys.stderr)
        return 1

    for name, n in pick(space, args.max_inbound, args.count, args.seed):
        print(f"{n}\t{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
