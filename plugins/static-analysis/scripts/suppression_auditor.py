#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
# ]
# ///
"""
Audit linter suppression comments.

Features:
- Find all suppression comments (noqa, pylint: disable, etc.)
- Check each has documented reasoning
- Flag undocumented suppressions
- Track suppression trends over time
- Generate suppression report

Usage:
    uv run suppression_auditor.py [OPTIONS] PATH

Examples
--------
    uv run suppression_auditor.py src/
    uv run suppression_auditor.py src/ --require-reason
    uv run suppression_auditor.py src/ --stats
    uv run suppression_auditor.py src/ --report report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Patterns for suppression comments
SUPPRESSION_PATTERNS: dict[str, re.Pattern[str]] = {
    # Python
    "noqa": re.compile(
        r"#\s*noqa(?::?\s*([A-Z0-9, ]+))?(?:\s*[-–—]\s*(.+))?", re.IGNORECASE
    ),
    "type: ignore": re.compile(
        r"#\s*type:\s*ignore(?:\[([^\]]+)\])?(?:\s*[-–—]\s*(.+))?"
    ),
    "pylint: disable": re.compile(
        r"#\s*pylint:\s*disable=([a-z0-9-,]+)(?:\s*[-–—]\s*(.+))?", re.IGNORECASE
    ),
    "mypy: ignore": re.compile(r"#\s*mypy:\s*ignore-errors?(?:\s*[-–—]\s*(.+))?"),
    "fmt: off": re.compile(r"#\s*fmt:\s*(?:off|skip)(?:\s*[-–—]\s*(.+))?"),
    "isort: skip": re.compile(r"#\s*isort:\s*(?:skip|off)(?:\s*[-–—]\s*(.+))?"),
    # JavaScript/TypeScript
    "eslint-disable": re.compile(
        r"//\s*eslint-disable(?:-next)?-line(?:\s+([a-z0-9-/, ]+))?"
        r"(?:\s*[-–—]\s*(.+))?",
        re.IGNORECASE,
    ),
    "ts-ignore": re.compile(r"//\s*@ts-(?:ignore|expect-error)(?:\s*[-–—]\s*(.+))?"),
    "prettier-ignore": re.compile(r"//\s*prettier-ignore(?:\s*[-–—]\s*(.+))?"),
    # General
    "noinspection": re.compile(r"//\s*noinspection\s+(\w+)(?:\s*[-–—]\s*(.+))?"),
}


@dataclass
class Suppression:
    """A suppression comment found in code."""

    file_path: Path
    line_number: int
    line_content: str
    suppression_type: str
    rules: list[str]
    reason: str | None
    has_reason: bool


@dataclass
class SuppressionReport:
    """Report of suppression audit."""

    suppressions: list[Suppression] = field(default_factory=list)
    by_type: dict[str, list[Suppression]] = field(default_factory=dict)
    by_rule: dict[str, list[Suppression]] = field(default_factory=dict)
    undocumented: list[Suppression] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.suppressions)

    @property
    def documented_count(self) -> int:
        return len([s for s in self.suppressions if s.has_reason])

    @property
    def undocumented_count(self) -> int:
        return len(self.undocumented)


def find_source_files(path: Path) -> list[Path]:
    """Find all source files to analyze."""
    if path.is_file():
        return [path]

    extensions = {".py", ".js", ".ts", ".jsx", ".tsx"}
    files = []

    for file_path in path.rglob("*"):
        # Skip hidden, cache, node_modules
        if any(
            part.startswith(".")
            or part == "__pycache__"
            or part == "node_modules"
            or part in ("venv", ".venv", "env")
            for part in file_path.parts
        ):
            continue

        if file_path.suffix in extensions:
            files.append(file_path)

    return files


def extract_suppressions(file_path: Path) -> list[Suppression]:
    """Extract suppression comments from a file."""
    suppressions: list[Suppression] = []

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for supp_type, pattern in SUPPRESSION_PATTERNS.items():
                match = pattern.search(line)
                if match:
                    groups = match.groups()

                    # Extract rules and reason based on pattern type
                    rules: list[str] = []
                    reason: str | None = None

                    if (
                        supp_type in ("noqa", "eslint-disable", "pylint: disable")
                        or supp_type == "type: ignore"
                    ):
                        rules_str = groups[0] if groups[0] else ""
                        rules = [r.strip() for r in rules_str.split(",") if r.strip()]
                        reason = groups[1] if len(groups) > 1 else None
                    else:
                        reason = groups[-1] if groups[-1] else None

                    has_reason = bool(reason and reason.strip())

                    suppressions.append(
                        Suppression(
                            file_path=file_path,
                            line_number=line_num,
                            line_content=line.strip(),
                            suppression_type=supp_type,
                            rules=rules,
                            reason=reason.strip() if reason else None,
                            has_reason=has_reason,
                        ),
                    )
                    break  # Only count first match per line

    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not read {file_path}: {e}")

    return suppressions


def audit_suppressions(
    path: Path,
    require_reason: bool = False,  # noqa: ARG001
) -> SuppressionReport:
    """Audit all suppression comments in a codebase."""
    report = SuppressionReport()

    files = find_source_files(path)

    for file_path in files:
        suppressions = extract_suppressions(file_path)
        report.suppressions.extend(suppressions)

    # Group by type
    for supp in report.suppressions:
        if supp.suppression_type not in report.by_type:
            report.by_type[supp.suppression_type] = []
        report.by_type[supp.suppression_type].append(supp)

        # Group by rule
        for rule in supp.rules:
            if rule not in report.by_rule:
                report.by_rule[rule] = []
            report.by_rule[rule].append(supp)

        # Track undocumented
        if not supp.has_reason:
            report.undocumented.append(supp)

    return report


def print_stats(report: SuppressionReport) -> None:
    """Print suppression statistics."""
    console.print(Panel("[bold]Suppression Statistics[/bold]"))

    # By type
    console.print("\n[bold]By Suppression Type[/bold]")
    type_table = Table()
    type_table.add_column("Type", style="cyan")
    type_table.add_column("Count", justify="right")
    type_table.add_column("With Reason", justify="right")
    type_table.add_column("Without", justify="right")

    for supp_type, items in sorted(report.by_type.items(), key=lambda x: -len(x[1])):
        with_reason = len([s for s in items if s.has_reason])
        without = len(items) - with_reason
        type_table.add_row(
            supp_type,
            str(len(items)),
            str(with_reason),
            f"[yellow]{without}[/yellow]" if without else "0",
        )

    console.print(type_table)

    # By rule (top 20)
    if report.by_rule:
        console.print("\n[bold]Top Suppressed Rules[/bold]")
        rule_table = Table()
        rule_table.add_column("Rule", style="cyan")
        rule_table.add_column("Count", justify="right")

        for rule, items in sorted(report.by_rule.items(), key=lambda x: -len(x[1]))[
            :20
        ]:
            rule_table.add_row(rule, str(len(items)))

        console.print(rule_table)


def print_report(report: SuppressionReport, verbose: bool = False) -> None:
    """Print the audit report."""
    console.print(Panel("[bold]Suppression Audit Report[/bold]"))

    # Summary
    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")

    summary_table.add_row("Total Suppressions", str(report.total))
    summary_table.add_row("With Reason", str(report.documented_count))
    summary_table.add_row(
        "Without Reason",
        f"[yellow]{report.undocumented_count}[/yellow]"
        if report.undocumented_count
        else "0",
    )

    if report.total > 0:
        pct = (report.documented_count / report.total) * 100
        color = "green" if pct >= 80 else "yellow" if pct >= 50 else "red"
        summary_table.add_row("Documentation Rate", f"[{color}]{pct:.1f}%[/{color}]")

    console.print(summary_table)

    # Undocumented suppressions
    if report.undocumented:
        console.print("\n[bold yellow]Undocumented Suppressions[/bold yellow]")
        for idx, supp in enumerate(report.undocumented):
            if idx >= 20:
                console.print(f"  ... and {len(report.undocumented) - idx} more")
                break
            console.print(f"  {supp.file_path}:{supp.line_number}")
            console.print(f"    [dim]{supp.line_content[:80]}[/dim]")

    # All suppressions (verbose)
    if verbose:
        console.print("\n[bold]All Suppressions[/bold]")
        for supp in report.suppressions[:50]:
            status = "[green]✓[/green]" if supp.has_reason else "[yellow]?[/yellow]"
            console.print(
                f"  {status} {supp.file_path}:{supp.line_number} "
                f"({supp.suppression_type})"
            )
            if supp.reason:
                console.print(f"    [dim]Reason: {supp.reason}[/dim]")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Directory to analyze")
    parser.add_argument(
        "--require-reason",
        action="store_true",
        help="Fail on suppressions without reasons",
    )
    parser.add_argument(
        "--tools",
        type=str,
        help="Only check specific tools (comma-separated)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Generate detailed JSON report",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show suppression statistics",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    if not args.path.exists():
        console.print(
            f"[red]Error:[/red] Path '{args.path}' does not exist",
            file=sys.stderr,
        )
        return 1

    # Audit suppressions
    report = audit_suppressions(args.path, require_reason=args.require_reason)

    # Save report if requested
    if args.report:
        report_data = {
            "summary": {
                "total": report.total,
                "with_reason": report.documented_count,
                "without_reason": report.undocumented_count,
            },
            "by_type": {k: len(v) for k, v in report.by_type.items()},
            "by_rule": {k: len(v) for k, v in report.by_rule.items()},
            "suppressions": [
                {
                    "file": str(s.file_path),
                    "line": s.line_number,
                    "type": s.suppression_type,
                    "rules": s.rules,
                    "reason": s.reason,
                    "has_reason": s.has_reason,
                }
                for s in report.suppressions
            ],
        }
        args.report.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
        console.print(f"[green]Report saved to {args.report}[/green]")

    # Output
    if args.stats:
        print_stats(report)
    elif args.output == "json":
        result: dict[str, Any] = {
            "summary": {
                "total": report.total,
                "with_reason": report.documented_count,
                "without_reason": report.undocumented_count,
            },
            "by_type": {k: len(v) for k, v in report.by_type.items()},
            "undocumented": [
                {
                    "file": str(s.file_path),
                    "line": s.line_number,
                    "type": s.suppression_type,
                    "content": s.line_content,
                }
                for s in report.undocumented
            ],
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(report, verbose=args.verbose)

    # Exit code
    if args.require_reason and report.undocumented:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
