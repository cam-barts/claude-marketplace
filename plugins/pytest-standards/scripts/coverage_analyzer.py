#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "radon>=6.0",
# ]
# ///
"""
Advanced coverage analysis beyond line coverage.

Analyzes:
- Line coverage from coverage.py JSON reports
- Branch coverage analysis
- Function-level coverage with complexity weighting
- Identifies untested conditional branches
- Suggests high-value test targets

Features:
- Parse coverage.py JSON output
- Weight coverage by cyclomatic complexity
- Track coverage trends over time
- Prioritize functions to test

Usage:
    uv run coverage_analyzer.py [OPTIONS] COVERAGE_FILE

Examples
--------
    uv run coverage_analyzer.py coverage.json
    uv run coverage_analyzer.py coverage.json --branch
    uv run coverage_analyzer.py coverage.json --complexity --suggest 10
    uv run coverage_analyzer.py coverage.json --history coverage_history.json
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from radon.complexity import cc_visit
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

console = Console()


@dataclass
class FileCoverage:
    """Coverage data for a single file."""

    path: str
    covered_lines: set[int]
    missing_lines: set[int]
    excluded_lines: set[int]
    covered_branches: list[tuple[int, int]] = field(default_factory=list)
    missing_branches: list[tuple[int, int]] = field(default_factory=list)

    @property
    def total_lines(self) -> int:
        return len(self.covered_lines) + len(self.missing_lines)

    @property
    def line_coverage(self) -> float:
        total = self.total_lines
        if total == 0:
            return 100.0
        return len(self.covered_lines) / total * 100

    @property
    def total_branches(self) -> int:
        return len(self.covered_branches) + len(self.missing_branches)

    @property
    def branch_coverage(self) -> float:
        total = self.total_branches
        if total == 0:
            return 100.0
        return len(self.covered_branches) / total * 100


@dataclass
class FunctionCoverage:
    """Coverage data for a function with complexity."""

    name: str
    file_path: str
    line_start: int
    line_end: int
    complexity: int
    covered_lines: int
    total_lines: int

    @property
    def coverage(self) -> float:
        if self.total_lines == 0:
            return 100.0
        return self.covered_lines / self.total_lines * 100

    @property
    def priority_score(self) -> float:
        """Higher score = higher priority to test."""
        # Weight by complexity and inverse coverage
        uncovered_pct = 100 - self.coverage
        return self.complexity * uncovered_pct / 100


@dataclass
class CoverageReport:
    """Complete coverage analysis report."""

    files: list[FileCoverage] = field(default_factory=list)
    functions: list[FunctionCoverage] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def total_line_coverage(self) -> float:
        total_covered = sum(len(f.covered_lines) for f in self.files)
        total_lines = sum(f.total_lines for f in self.files)
        if total_lines == 0:
            return 100.0
        return total_covered / total_lines * 100

    @property
    def total_branch_coverage(self) -> float:
        total_covered = sum(len(f.covered_branches) for f in self.files)
        total_branches = sum(f.total_branches for f in self.files)
        if total_branches == 0:
            return 100.0
        return total_covered / total_branches * 100

    @property
    def total_lines(self) -> int:
        return sum(f.total_lines for f in self.files)

    @property
    def covered_lines(self) -> int:
        return sum(len(f.covered_lines) for f in self.files)

    @property
    def missing_lines(self) -> int:
        return sum(len(f.missing_lines) for f in self.files)


def parse_coverage_json(coverage_path: Path) -> CoverageReport:
    """Parse coverage.py JSON report."""
    data = json.loads(coverage_path.read_text())
    report = CoverageReport()

    files_data = data.get("files", {})

    for file_path, file_data in files_data.items():
        # Skip test files and virtual environments
        if "test_" in file_path or "/tests/" in file_path:
            continue
        if any(skip in file_path for skip in [".venv", "venv", "site-packages"]):
            continue

        executed_lines = set(file_data.get("executed_lines", []))
        missing_lines = set(file_data.get("missing_lines", []))
        excluded_lines = set(file_data.get("excluded_lines", []))

        # Branch data
        covered_branches: list[tuple[int, int]] = []
        missing_branches: list[tuple[int, int]] = []

        if "missing_branches" in file_data:
            for branch in file_data["missing_branches"]:
                if isinstance(branch, list) and len(branch) == 2:
                    missing_branches.append((branch[0], branch[1]))

        file_cov = FileCoverage(
            path=file_path,
            covered_lines=executed_lines,
            missing_lines=missing_lines,
            excluded_lines=excluded_lines,
            covered_branches=covered_branches,
            missing_branches=missing_branches,
        )
        report.files.append(file_cov)

    return report


def analyze_function_coverage(
    report: CoverageReport,
    source_path: Path | None = None,
) -> list[FunctionCoverage]:
    """Analyze coverage at function level with complexity."""
    functions: list[FunctionCoverage] = []

    for file_cov in report.files:
        file_path = Path(file_cov.path)

        # Try to read source file
        full_path = source_path / file_path if source_path else file_path

        if not full_path.exists():
            # Try relative to cwd
            full_path = Path.cwd() / file_path

        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(encoding="utf-8")
            cc_results = cc_visit(content)

            for result in cc_results:
                start_line = result.lineno
                end_line = getattr(result, "endline", start_line + 10)

                # Count covered lines in this function
                func_lines = set(range(start_line, end_line + 1))
                covered = len(func_lines & file_cov.covered_lines)
                total = len(func_lines - file_cov.excluded_lines)

                func_cov = FunctionCoverage(
                    name=result.name,
                    file_path=str(file_path),
                    line_start=start_line,
                    line_end=end_line,
                    complexity=result.complexity,
                    covered_lines=covered,
                    total_lines=total,
                )
                functions.append(func_cov)

        except Exception:
            pass

    return functions


def suggest_tests(
    functions: list[FunctionCoverage],
    n: int = 10,
) -> list[tuple[FunctionCoverage, str]]:
    """Suggest functions to test based on priority score."""
    suggestions: list[tuple[FunctionCoverage, str]] = []

    # Sort by priority score (complexity * uncovered)
    sorted_funcs = sorted(functions, key=lambda f: -f.priority_score)

    for func in sorted_funcs[:n]:
        if func.coverage >= 100:
            continue

        # Generate suggestion
        uncovered = 100 - func.coverage
        if func.complexity > 10:
            reason = f"High complexity ({func.complexity}), {uncovered:.0f}% uncovered"
        elif func.coverage < 50:
            reason = f"Low coverage ({func.coverage:.0f}%), cx {func.complexity}"
        else:
            reason = f"Partial coverage ({func.coverage:.0f}%) could improve"

        suggestions.append((func, reason))

    return suggestions


def save_history(report: CoverageReport, history_path: Path) -> None:
    """Save coverage snapshot to history file."""
    history: list[dict[str, Any]] = []

    if history_path.exists():
        with contextlib.suppress(Exception):
            history = json.loads(history_path.read_text())

    entry = {
        "timestamp": report.timestamp,
        "line_coverage": round(report.total_line_coverage, 2),
        "branch_coverage": round(report.total_branch_coverage, 2),
        "total_lines": report.total_lines,
        "covered_lines": report.covered_lines,
        "missing_lines": report.missing_lines,
        "files": len(report.files),
    }

    history.append(entry)
    history = history[-100:]  # Keep last 100

    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history, indent=2))


def show_trends(history_path: Path) -> None:
    """Display coverage trends from history."""
    if not history_path.exists():
        console.print("[yellow]No history file found[/yellow]")
        return

    history = json.loads(history_path.read_text())
    if len(history) < 2:
        console.print("[yellow]Not enough history for trends[/yellow]")
        return

    console.print("\n[bold]Coverage Trends[/bold]")

    # Compare latest to previous
    latest = history[-1]
    previous = history[-2]

    line_diff = latest["line_coverage"] - previous["line_coverage"]
    branch_diff = latest.get("branch_coverage", 0) - previous.get("branch_coverage", 0)

    if line_diff > 0:
        console.print(f"  Line Coverage: [green]+{line_diff:.1f}%[/green]")
    elif line_diff < 0:
        console.print(f"  Line Coverage: [red]{line_diff:.1f}%[/red]")
    else:
        console.print("  Line Coverage: No change")

    if branch_diff != 0:
        if branch_diff > 0:
            console.print(f"  Branch Coverage: [green]+{branch_diff:.1f}%[/green]")
        else:
            console.print(f"  Branch Coverage: [red]{branch_diff:.1f}%[/red]")

    # Show last 5 entries
    if len(history) >= 3:
        console.print("\n  Recent History:")
        for entry in history[-5:]:
            ts = entry["timestamp"][:10]
            line = entry["line_coverage"]
            console.print(f"    {ts}: {line:.1f}%")


def print_report(
    report: CoverageReport,
    show_branch: bool = False,
    suggestions: list[tuple[FunctionCoverage, str]] | None = None,
    verbose: bool = False,
) -> None:
    """Print the coverage analysis report."""
    # Summary
    console.print(Panel("[bold]Coverage Analysis[/bold]"))

    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Files", str(len(report.files)))
    summary_table.add_row("Total Lines", f"{report.total_lines:,}")
    summary_table.add_row("Covered Lines", f"{report.covered_lines:,}")
    summary_table.add_row("Missing Lines", f"{report.missing_lines:,}")

    # Color code coverage
    line_cov = report.total_line_coverage
    if line_cov >= 80:
        cov_color = "green"
    elif line_cov >= 60:
        cov_color = "yellow"
    else:
        cov_color = "red"

    summary_table.add_row(
        "Line Coverage", f"[{cov_color}]{line_cov:.1f}%[/{cov_color}]"
    )

    if show_branch:
        branch_cov = report.total_branch_coverage
        summary_table.add_row("Branch Coverage", f"{branch_cov:.1f}%")

    console.print(summary_table)

    # Files with low coverage
    low_coverage_files = [f for f in report.files if f.line_coverage < 80]
    if low_coverage_files:
        console.print("\n[bold yellow]Files Needing Coverage[/bold yellow]")

        files_table = Table()
        files_table.add_column("File", style="cyan")
        files_table.add_column("Coverage", justify="right")
        files_table.add_column("Missing Lines", justify="right")

        for f in sorted(low_coverage_files, key=lambda x: x.line_coverage)[:10]:
            cov = f.line_coverage
            color = "red" if cov < 50 else "yellow"
            files_table.add_row(
                f.path,
                f"[{color}]{cov:.1f}%[/{color}]",
                str(len(f.missing_lines)),
            )

        console.print(files_table)

    # Uncovered lines detail (verbose)
    if verbose:
        console.print("\n[bold]Uncovered Lines by File[/bold]")
        for f in sorted(report.files, key=lambda x: -len(x.missing_lines))[:5]:
            if f.missing_lines:
                missing = sorted(f.missing_lines)
                # Group consecutive lines
                ranges = []
                start = end = missing[0]
                for line in missing[1:]:
                    if line == end + 1:
                        end = line
                    else:
                        ranges.append(f"{start}-{end}" if start != end else str(start))
                        start = end = line
                ranges.append(f"{start}-{end}" if start != end else str(start))

                console.print(f"  {f.path}")
                console.print(f"    Lines: {', '.join(ranges[:10])}")
                if len(ranges) > 10:
                    console.print(f"    ... and {len(ranges) - 10} more ranges")

    # Test suggestions
    if suggestions:
        console.print("\n[bold blue]Suggested Functions to Test[/bold blue]")
        console.print("  (Prioritized by complexity × uncovered %)\n")

        for func, reason in suggestions:
            console.print(f"  [cyan]{func.file_path}[/cyan]::{func.name}")
            console.print(
                f"    Coverage: {func.coverage:.0f}% | Complexity: {func.complexity}"
            )
            console.print(f"    [dim]{reason}[/dim]\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "coverage_file",
        type=Path,
        help="Path to coverage.json file",
    )
    parser.add_argument(
        "--branch",
        action="store_true",
        help="Include branch coverage analysis",
    )
    parser.add_argument(
        "--complexity",
        action="store_true",
        help="Weight coverage by cyclomatic complexity",
    )
    parser.add_argument(
        "--suggest",
        type=int,
        metavar="N",
        help="Suggest top N functions to test",
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="Source directory for complexity analysis",
    )
    parser.add_argument(
        "--history",
        type=Path,
        help="Path to history file for trend tracking",
    )
    parser.add_argument(
        "--show-trends",
        action="store_true",
        help="Show coverage trends from history",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    if not args.coverage_file.exists():
        console.print(
            f"[red]Error:[/red] Coverage file '{args.coverage_file}' not found",
            file=sys.stderr,
        )
        return 1

    # Parse coverage data
    report = parse_coverage_json(args.coverage_file)

    # Function-level analysis with complexity
    suggestions = None
    if args.complexity or args.suggest:
        with Progress(console=console, transient=True) as progress:
            task = progress.add_task("Analyzing function coverage...", total=None)
            report.functions = analyze_function_coverage(report, args.source)
            progress.update(task, completed=True)

        if args.suggest:
            suggestions = suggest_tests(report.functions, args.suggest)

    # Save history
    if args.history:
        save_history(report, args.history)

    # Output
    if args.output == "json":
        result: dict[str, Any] = {
            "timestamp": report.timestamp,
            "summary": {
                "files": len(report.files),
                "total_lines": report.total_lines,
                "covered_lines": report.covered_lines,
                "missing_lines": report.missing_lines,
                "line_coverage": round(report.total_line_coverage, 2),
                "branch_coverage": round(report.total_branch_coverage, 2),
            },
            "files": [
                {
                    "path": f.path,
                    "line_coverage": round(f.line_coverage, 2),
                    "missing_lines": sorted(f.missing_lines),
                }
                for f in sorted(report.files, key=lambda x: x.line_coverage)
            ],
        }

        if report.functions:
            result["functions"] = [
                {
                    "name": f.name,
                    "file": f.file_path,
                    "coverage": round(f.coverage, 2),
                    "complexity": f.complexity,
                    "priority_score": round(f.priority_score, 2),
                }
                for f in sorted(report.functions, key=lambda x: -x.priority_score)[:20]
            ]

        if suggestions:
            result["suggestions"] = [
                {"function": f.name, "file": f.file_path, "reason": r}
                for f, r in suggestions
            ]

        print(json.dumps(result, indent=2))
    else:
        print_report(report, args.branch, suggestions, args.verbose)

        if args.show_trends and args.history:
            show_trends(args.history)

    # Return non-zero if coverage is low
    if report.total_line_coverage < 60:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
