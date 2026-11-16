#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts"]
# ///
"""Mechanical helpers for a serendipity gardening round.

    uv run garden.py deal                      # 24 randomPage + 4 randomBias + 3 randomConcept
    uv run garden.py deal --picker "serendipity.randomFallacy()" --picker "quotes.random()"
    uv run garden.py check "Chauffeur Knowledge" "Z/Decision Matrix"

`deal` calls Cam's own Serendipity pickers through `sb lua`, drops pages that are
records rather than notes, dedupes, and stops loudly if a picker errors or prints
no wikilink. `check` finds existing pages by file name anywhere in the space, since
a concept's folder can't be guessed from its name.
"""

import re
import subprocess
import sys
from pathlib import Path

import cyclopts

app = cyclopts.App()
SPACE = Path.home() / "silverbullet"
# Records, not notes: they burn draw slots. Still valid link *targets*.
DRAW_SKIP = re.compile(r"^(Jira/|Barbossa/Captains Log/|Journals/Captains Log/|Transcripts/)")
WIKILINK = re.compile(r"\[\[([^\]|]+)")
DEFAULT_PICKERS = ["serendipity.randomPage()"] * 24 + ["serendipity.randomBias()"] * 4 + [
    "serendipity.randomConcept()"
] * 3


def pick(expr: str) -> str:
    out = subprocess.run(["sb", "--no-input", "lua", f"{expr}.markdown"], capture_output=True, text=True)
    hit = WIKILINK.search(out.stdout)
    if out.returncode != 0 or not hit:
        sys.exit(f"picker {expr} failed (exit {out.returncode}): {out.stderr.strip() or out.stdout.strip()}\n"
                 f"Check the picker names in {SPACE / 'Serendipity.md'}.")
    return hit.group(1)


def keep(names: list[str]) -> list[str]:
    return sorted({n for n in names if not DRAW_SKIP.match(n)})


@app.command
def deal(*, picker: list[str] | None = None):
    """Draw from the pickers; print surviving page names, one per line."""
    for name in keep([pick(e) for e in (picker or DEFAULT_PICKERS)]):
        print(name)


@app.command
def check(*names: str):
    """Print each link target with matching files, or ASPIRING if none exist."""
    for n in names:
        stem = n.split("|")[0].rsplit("/", 1)[-1].lower()
        hits = [str(p.relative_to(SPACE)) for p in SPACE.rglob("*.md")
                if stem in p.stem.lower() and not any(part.startswith(".") for part in p.parts)]
        print(f"{n:<34} {' | '.join(hits[:3]) or 'ASPIRING'}")


if __name__ == "__main__":
    assert keep(["Jira/ST-1", "Z/Threshold", "Z/Threshold", "Journals/Captains Log/2026-11-16"]) == ["Z/Threshold"]
    app()
