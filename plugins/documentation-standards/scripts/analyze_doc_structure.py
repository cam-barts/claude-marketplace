#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "pyyaml>=6.0",
# ]
# ///
"""
Analyze documentation structure against the Diataxis framework.

Analyzes:
- Documentation type distribution (tutorial, how-to, reference, explanation)
- Coverage gaps and missing documentation types
- Word counts and file statistics
- Documentation health indicators

Generates:
- Distribution reports
- Improvement suggestions
- Documentation roadmaps
- zensical.yml navigation structure

Usage:
    uv run analyze_doc_structure.py [OPTIONS] PATH

Examples
--------
    uv run analyze_doc_structure.py docs/
    uv run analyze_doc_structure.py docs/ --suggest
    uv run analyze_doc_structure.py docs/ --roadmap
    uv run analyze_doc_structure.py docs/ --generate-nav
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class DocType:
    TUTORIAL = "tutorial"
    HOWTO = "how-to"
    REFERENCE = "reference"
    EXPLANATION = "explanation"
    UNKNOWN = "unknown"


@dataclass
class DocFile:
    """Information about a documentation file."""

    path: Path
    doc_type: str
    word_count: int
    title: str | None = None
    has_frontmatter: bool = False
    headings: list[str] = field(default_factory=list)


@dataclass
class AnalysisReport:
    """Documentation analysis report."""

    files: list[DocFile] = field(default_factory=list)
    base_path: Path = field(default_factory=Path)

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_words(self) -> int:
        return sum(f.word_count for f in self.files)

    def files_by_type(self, doc_type: str) -> list[DocFile]:
        return [f for f in self.files if f.doc_type == doc_type]

    def type_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {}
        for f in self.files:
            dist[f.doc_type] = dist.get(f.doc_type, 0) + 1
        return dist

    def type_word_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {}
        for f in self.files:
            dist[f.doc_type] = dist.get(f.doc_type, 0) + f.word_count
        return dist


# Keywords for auto-detecting document type
TYPE_KEYWORDS = {
    DocType.TUTORIAL: [
        "tutorial",
        "getting started",
        "learn",
        "walkthrough",
        "step by step",
        "first",
        "beginner",
        "introduction to",
        "hands-on",
        "workshop",
    ],
    DocType.HOWTO: [
        "how to",
        "how-to",
        "guide",
        "configure",
        "set up",
        "setup",
        "install",
        "deploy",
        "migrate",
        "upgrade",
        "troubleshoot",
        "fix",
        "resolve",
    ],
    DocType.REFERENCE: [
        "reference",
        "api",
        "specification",
        "spec",
        "configuration options",
        "parameters",
        "arguments",
        "cli",
        "command",
        "options",
        "schema",
    ],
    DocType.EXPLANATION: [
        "explanation",
        "architecture",
        "design",
        "concepts",
        "about",
        "why",
        "understanding",
        "overview",
        "background",
        "philosophy",
        "rationale",
    ],
}

# Ideal distribution ranges
IDEAL_DISTRIBUTION = {
    DocType.TUTORIAL: (0.15, 0.25),
    DocType.HOWTO: (0.30, 0.40),
    DocType.REFERENCE: (0.20, 0.30),
    DocType.EXPLANATION: (0.15, 0.25),
}


def extract_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter from content."""
    if not content.startswith("---"):
        return {}, content

    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return {}, content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        body = content[match.end() :]
        return frontmatter or {}, body
    except yaml.YAMLError:
        return {}, content


def count_words(text: str) -> int:
    """Count words in text, excluding code blocks."""
    # Remove code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", "", text)

    # Count words
    words = re.findall(r"\b\w+\b", text)
    return len(words)


def extract_headings(content: str) -> list[str]:
    """Extract headings from markdown."""
    headings = []
    for match in re.finditer(r"^#{1,6}\s+(.+)$", content, re.MULTILINE):
        headings.append(match.group(1).strip())
    return headings


def detect_doc_type(file_path: Path, content: str, frontmatter: dict[str, Any]) -> str:
    """Detect document type from content and metadata."""
    # Check frontmatter first
    if "documentation_type" in frontmatter:
        return frontmatter["documentation_type"]
    if "type" in frontmatter:
        return frontmatter["type"]

    # Check path for hints
    path_str = str(file_path).lower()
    for doc_type, keywords in TYPE_KEYWORDS.items():
        for keyword in keywords:
            if (
                keyword.replace(" ", "-") in path_str
                or keyword.replace(" ", "_") in path_str
            ):
                return doc_type

    # Check content for hints
    title_and_intro = content[:2000].lower()

    # Score each type based on keyword matches
    scores: dict[str, int] = dict.fromkeys(TYPE_KEYWORDS, 0)

    for doc_type, keywords in TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_and_intro:
                scores[doc_type] += 1

    # Return type with highest score, or unknown
    max_score = max(scores.values())
    if max_score > 0:
        for doc_type, score in scores.items():
            if score == max_score:
                return doc_type

    # Default based on common patterns
    if file_path.name.lower() == "readme.md":
        return DocType.EXPLANATION
    if "changelog" in file_path.name.lower():
        return DocType.REFERENCE

    return DocType.UNKNOWN


def analyze_file(file_path: Path) -> DocFile:
    """Analyze a single documentation file."""
    content = file_path.read_text(encoding="utf-8")
    frontmatter, body = extract_frontmatter(content)

    doc_type = detect_doc_type(file_path, content, frontmatter)
    word_count = count_words(body)
    headings = extract_headings(body)

    # Extract title
    title = frontmatter.get("title")
    if not title and headings:
        title = headings[0]

    return DocFile(
        path=file_path,
        doc_type=doc_type,
        word_count=word_count,
        title=title,
        has_frontmatter=bool(frontmatter),
        headings=headings,
    )


def analyze_path(path: Path) -> AnalysisReport:
    """Analyze all documentation in a path."""
    report = AnalysisReport(base_path=path)

    files = [path] if path.is_file() else list(path.rglob("*.md"))

    for file_path in files:
        # Skip hidden files and directories
        if any(part.startswith(".") for part in file_path.parts):
            continue
        if "__pycache__" in str(file_path):
            continue

        try:
            doc_file = analyze_file(file_path)
            report.files.append(doc_file)
        except Exception as e:
            console.print(
                f"[yellow]Warning:[/yellow] Could not analyze {file_path}: {e}"
            )

    return report


def generate_suggestions(report: AnalysisReport) -> list[str]:
    """Generate improvement suggestions."""
    suggestions = []
    dist = report.type_distribution()
    total = report.total_files

    if total == 0:
        suggestions.append("No documentation files found. Start with a README.md")
        return suggestions

    # Check each type against ideal distribution
    for doc_type, (min_pct, _max_pct) in IDEAL_DISTRIBUTION.items():
        count = dist.get(doc_type, 0)
        pct = count / total if total > 0 else 0

        if pct < min_pct:
            if doc_type == DocType.TUTORIAL:
                suggestions.append(
                    f"Low tutorial coverage ({pct:.0%}). "
                    "Add: Getting Started guide, First project walkthrough",
                )
            elif doc_type == DocType.HOWTO:
                suggestions.append(
                    f"Low how-to coverage ({pct:.0%}). "
                    "Add: Installation guide, Configuration guide, Troubleshooting",
                )
            elif doc_type == DocType.REFERENCE:
                suggestions.append(
                    f"Low reference coverage ({pct:.0%}). "
                    "Add: API reference, Configuration options, CLI reference",
                )
            elif doc_type == DocType.EXPLANATION:
                suggestions.append(
                    f"Low explanation coverage ({pct:.0%}). "
                    "Add: Architecture overview, Design decisions, Concepts",
                )

    # Check for common missing docs
    file_names = [f.path.name.lower() for f in report.files]

    if not any("readme" in n for n in file_names):
        suggestions.append("Missing README.md - Add project overview")

    if not any("changelog" in n or "changes" in n for n in file_names):
        suggestions.append("Missing CHANGELOG.md - Track version history")

    if not any("contribut" in n for n in file_names):
        suggestions.append("Missing CONTRIBUTING.md - Guide for contributors")

    # Check for frontmatter
    without_frontmatter = [f for f in report.files if not f.has_frontmatter]
    if without_frontmatter:
        suggestions.append(
            f"{len(without_frontmatter)} files missing frontmatter "
            "with documentation_type",
        )

    # Check for unknown types
    unknown = dist.get(DocType.UNKNOWN, 0)
    if unknown > 0:
        suggestions.append(
            f"{unknown} files with unknown documentation type - "
            "Add documentation_type frontmatter",
        )

    return suggestions


def generate_roadmap(report: AnalysisReport) -> list[tuple[int, str]]:
    """Generate a prioritized documentation roadmap."""
    roadmap: list[tuple[int, str]] = []
    dist = report.type_distribution()
    total = report.total_files

    # Priority 1: Critical missing docs
    file_names = [f.path.name.lower() for f in report.files]

    if not any("readme" in n for n in file_names):
        roadmap.append((1, "Create README.md with project overview"))

    if dist.get(DocType.TUTORIAL, 0) == 0:
        roadmap.append((1, "Add Getting Started tutorial for new users"))

    # Priority 2: Low coverage areas
    for doc_type, (min_pct, _) in IDEAL_DISTRIBUTION.items():
        count = dist.get(doc_type, 0)
        pct = count / total if total > 0 else 0

        if pct < min_pct * 0.5:  # Less than half the minimum
            if doc_type == DocType.TUTORIAL:
                roadmap.append(
                    (2, "Add comprehensive tutorial with practical examples")
                )
            elif doc_type == DocType.HOWTO:
                roadmap.append((2, "Add how-to guides for common tasks"))
            elif doc_type == DocType.REFERENCE:
                roadmap.append((2, "Add API/configuration reference documentation"))
            elif doc_type == DocType.EXPLANATION:
                roadmap.append((2, "Add architecture and design explanations"))

    # Priority 3: Nice to have
    if not any("changelog" in n for n in file_names):
        roadmap.append((3, "Create CHANGELOG.md for version history"))

    if not any("contribut" in n for n in file_names):
        roadmap.append((3, "Add CONTRIBUTING.md for contributors"))

    # Priority 4: Improvements
    without_frontmatter = len([f for f in report.files if not f.has_frontmatter])
    if without_frontmatter > 0:
        roadmap.append((4, f"Add frontmatter to {without_frontmatter} files"))

    return sorted(roadmap, key=lambda x: x[0])


def generate_zensical_nav(report: AnalysisReport) -> dict[str, Any]:
    """Generate zensical.yml navigation structure."""
    nav: list[Any] = []

    # Group files by type
    by_type: dict[str, list[DocFile]] = {}
    for f in report.files:
        if f.doc_type not in by_type:
            by_type[f.doc_type] = []
        by_type[f.doc_type].append(f)

    # Find index/readme
    for f in report.files:
        if f.path.name.lower() in ("index.md", "readme.md"):
            rel_path = f.path.relative_to(report.base_path)
            nav.append({"Home": str(rel_path)})
            break

    # Add sections by type
    type_names = {
        DocType.TUTORIAL: "Tutorials",
        DocType.HOWTO: "How-To Guides",
        DocType.REFERENCE: "Reference",
        DocType.EXPLANATION: "Explanation",
    }

    for doc_type in [
        DocType.TUTORIAL,
        DocType.HOWTO,
        DocType.REFERENCE,
        DocType.EXPLANATION,
    ]:
        files = by_type.get(doc_type, [])
        if files:
            section_items = []
            for f in sorted(files, key=lambda x: x.path.name):
                if f.path.name.lower() in ("index.md", "readme.md"):
                    continue
                rel_path = f.path.relative_to(report.base_path)
                title = (
                    f.title or f.path.stem.replace("-", " ").replace("_", " ").title()
                )
                section_items.append({title: str(rel_path)})

            if section_items:
                nav.append({type_names[doc_type]: section_items})

    return {"nav": nav}


def print_report(
    report: AnalysisReport,
    show_suggestions: bool = False,
    show_roadmap: bool = False,
    verbose: bool = False,
) -> None:
    """Print the analysis report."""
    # Summary
    console.print(
        Panel(f"[bold]Documentation Analysis[/bold]\nPath: {report.base_path}")
    )

    table = Table(title="Overview")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total Files", str(report.total_files))
    table.add_row("Total Words", f"{report.total_words:,}")
    console.print(table)

    # Distribution
    if report.total_files > 0:
        dist = report.type_distribution()
        word_dist = report.type_word_distribution()

        dist_table = Table(title="Distribution by Type")
        dist_table.add_column("Type", style="cyan")
        dist_table.add_column("Files", justify="right")
        dist_table.add_column("%", justify="right")
        dist_table.add_column("Words", justify="right")

        for doc_type in [
            DocType.TUTORIAL,
            DocType.HOWTO,
            DocType.REFERENCE,
            DocType.EXPLANATION,
            DocType.UNKNOWN,
        ]:
            count = dist.get(doc_type, 0)
            words = word_dist.get(doc_type, 0)
            pct = count / report.total_files * 100

            # Color based on ideal range
            ideal = IDEAL_DISTRIBUTION.get(doc_type)
            if ideal:
                min_pct, max_pct = ideal
                if pct / 100 < min_pct:
                    color = "red"
                elif pct / 100 > max_pct:
                    color = "yellow"
                else:
                    color = "green"
            else:
                color = "dim" if doc_type == DocType.UNKNOWN else "white"

            dist_table.add_row(
                doc_type,
                str(count),
                f"[{color}]{pct:.0f}%[/{color}]",
                f"{words:,}",
            )

        console.print(dist_table)

    # Files list (verbose)
    if verbose and report.files:
        files_table = Table(title="Files")
        files_table.add_column("Path", style="cyan")
        files_table.add_column("Type", style="green")
        files_table.add_column("Words", justify="right")
        files_table.add_column("FM", justify="center")  # Frontmatter

        for f in sorted(report.files, key=lambda x: x.path):
            rel_path = (
                f.path.relative_to(report.base_path)
                if report.base_path in f.path.parents
                else f.path
            )
            fm = "✓" if f.has_frontmatter else "✗"
            files_table.add_row(str(rel_path), f.doc_type, str(f.word_count), fm)

        console.print(files_table)

    # Suggestions
    if show_suggestions:
        suggestions = generate_suggestions(report)
        if suggestions:
            console.print("\n[bold yellow]Suggestions[/bold yellow]")
            for i, suggestion in enumerate(suggestions, 1):
                console.print(f"  {i}. {suggestion}")
        else:
            console.print(
                "\n[bold green]Documentation structure looks good![/bold green]"
            )

    # Roadmap
    if show_roadmap:
        roadmap = generate_roadmap(report)
        if roadmap:
            console.print("\n[bold blue]Documentation Roadmap[/bold blue]")
            current_priority = 0
            for priority, item in roadmap:
                if priority != current_priority:
                    console.print(f"\n[bold]Priority {priority}[/bold]")
                    current_priority = priority
                console.print(f"  • {item}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Documentation directory to analyze")
    parser.add_argument(
        "--suggest", action="store_true", help="Show improvement suggestions"
    )
    parser.add_argument(
        "--roadmap", action="store_true", help="Generate documentation roadmap"
    )
    parser.add_argument(
        "--generate-nav", action="store_true", help="Generate zensical.yml navigation"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed file list"
    )
    parser.add_argument(
        "--output",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    if not args.path.exists():
        console.print(
            f"[red]Error:[/red] Path '{args.path}' does not exist", file=sys.stderr
        )
        return 1

    report = analyze_path(args.path)

    if args.output == "json":
        result: dict[str, Any] = {
            "total_files": report.total_files,
            "total_words": report.total_words,
            "distribution": report.type_distribution(),
            "word_distribution": report.type_word_distribution(),
            "files": [
                {
                    "path": str(f.path),
                    "type": f.doc_type,
                    "words": f.word_count,
                    "title": f.title,
                    "has_frontmatter": f.has_frontmatter,
                }
                for f in report.files
            ],
        }
        if args.suggest:
            result["suggestions"] = generate_suggestions(report)
        if args.roadmap:
            result["roadmap"] = [
                {"priority": p, "item": i} for p, i in generate_roadmap(report)
            ]
        if args.generate_nav:
            result["nav"] = generate_zensical_nav(report)

        print(json.dumps(result, indent=2))

    elif args.generate_nav:
        nav = generate_zensical_nav(report)
        print(yaml.dump(nav, sort_keys=False, default_flow_style=False))

    else:
        print_report(report, args.suggest, args.roadmap, args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
