#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "radon>=6.0",
# ]
# ///
"""
Calculate and track code quality metrics for Python projects.

Calculates:
- Cyclomatic complexity per function/method
- Maintainability index per module
- Lines of code (SLOC, comments, blank)
- Code smells (long methods, deep nesting, etc.)

Features:
- Quality gate enforcement
- Historical tracking
- Trend analysis
- Multiple output formats

Usage:
    uv run quality_metrics.py [OPTIONS] PATH

Examples
--------
    uv run quality_metrics.py src/
    uv run quality_metrics.py src/ --metrics complexity,loc
    uv run quality_metrics.py src/ --threshold max_complexity:15 --fail-gates
    uv run quality_metrics.py src/ --history metrics.json
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

from radon.complexity import cc_rank, cc_visit
from radon.metrics import mi_rank, mi_visit
from radon.raw import analyze
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class FunctionMetrics:
    """Metrics for a single function."""

    name: str
    file_path: str
    line_number: int
    complexity: int
    rank: str  # A, B, C, D, E, F
    parameters: int = 0
    length: int = 0


@dataclass
class FileMetrics:
    """Metrics for a single file."""

    path: Path
    sloc: int = 0  # Source lines of code
    lloc: int = 0  # Logical lines of code
    comments: int = 0
    blank: int = 0
    maintainability: float = 0.0
    mi_rank: str = ""
    functions: list[FunctionMetrics] = field(default_factory=list)


@dataclass
class CodeSmell:
    """A detected code smell."""

    smell_type: str
    file_path: str
    location: str
    value: int | float
    threshold: int | float
    message: str


@dataclass
class QualityReport:
    """Complete quality metrics report."""

    files: list[FileMetrics] = field(default_factory=list)
    smells: list[CodeSmell] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def total_sloc(self) -> int:
        return sum(f.sloc for f in self.files)

    @property
    def total_lloc(self) -> int:
        return sum(f.lloc for f in self.files)

    @property
    def total_comments(self) -> int:
        return sum(f.comments for f in self.files)

    @property
    def all_functions(self) -> list[FunctionMetrics]:
        funcs = []
        for f in self.files:
            funcs.extend(f.functions)
        return funcs

    @property
    def avg_complexity(self) -> float:
        funcs = self.all_functions
        if not funcs:
            return 0.0
        return sum(f.complexity for f in funcs) / len(funcs)

    @property
    def max_complexity(self) -> int:
        funcs = self.all_functions
        if not funcs:
            return 0
        return max(f.complexity for f in funcs)

    @property
    def avg_maintainability(self) -> float:
        if not self.files:
            return 0.0
        mi_scores = [f.maintainability for f in self.files if f.maintainability > 0]
        return sum(mi_scores) / len(mi_scores) if mi_scores else 0.0

    @property
    def min_maintainability(self) -> float:
        if not self.files:
            return 0.0
        mi_scores = [f.maintainability for f in self.files if f.maintainability > 0]
        return min(mi_scores) if mi_scores else 0.0


def analyze_file(file_path: Path) -> FileMetrics:
    """Analyze a single Python file."""
    content = file_path.read_text(encoding="utf-8")
    metrics = FileMetrics(path=file_path)

    # Raw metrics (lines of code)
    try:
        raw = analyze(content)
        metrics.sloc = raw.sloc
        metrics.lloc = raw.lloc
        metrics.comments = raw.comments
        metrics.blank = raw.blank
    except Exception:
        pass

    # Maintainability index
    try:
        mi = mi_visit(content, multi=False)
        metrics.maintainability = mi
        metrics.mi_rank = mi_rank(mi)
    except Exception:
        pass

    # Cyclomatic complexity
    try:
        cc_results = cc_visit(content)
        for result in cc_results:
            func = FunctionMetrics(
                name=result.name,
                file_path=str(file_path),
                line_number=result.lineno,
                complexity=result.complexity,
                rank=cc_rank(result.complexity),
            )

            # Try to get additional info
            if hasattr(result, "endline"):
                func.length = result.endline - result.lineno + 1

            metrics.functions.append(func)
    except Exception:
        pass

    return metrics


def detect_smells(report: QualityReport) -> list[CodeSmell]:
    """Detect code smells from metrics."""
    smells: list[CodeSmell] = []

    # Thresholds
    MAX_FUNCTION_LENGTH = 50
    MAX_COMPLEXITY = 15
    _MAX_NESTING = 4  # Would need AST analysis (reserved for future use)
    _MAX_PARAMETERS = 5  # Reserved for future use
    MIN_MAINTAINABILITY = 50

    for file_metrics in report.files:
        # Low maintainability
        if 0 < file_metrics.maintainability < MIN_MAINTAINABILITY:
            smells.append(
                CodeSmell(
                    smell_type="LowMaintainability",
                    file_path=str(file_metrics.path),
                    location=file_metrics.path.name,
                    value=file_metrics.maintainability,
                    threshold=MIN_MAINTAINABILITY,
                    message=f"Maintainability {file_metrics.maintainability:.1f} "
                    f"< {MIN_MAINTAINABILITY}",
                ),
            )

        for func in file_metrics.functions:
            # High complexity
            if func.complexity > MAX_COMPLEXITY:
                smells.append(
                    CodeSmell(
                        smell_type="HighComplexity",
                        file_path=str(file_metrics.path),
                        location=f"{func.name} (line {func.line_number})",
                        value=func.complexity,
                        threshold=MAX_COMPLEXITY,
                        message=f"Complexity {func.complexity} > {MAX_COMPLEXITY}",
                    ),
                )

            # Long method
            if func.length > MAX_FUNCTION_LENGTH:
                smells.append(
                    CodeSmell(
                        smell_type="LongMethod",
                        file_path=str(file_metrics.path),
                        location=f"{func.name} (line {func.line_number})",
                        value=func.length,
                        threshold=MAX_FUNCTION_LENGTH,
                        message=f"Function {func.length} lines > {MAX_FUNCTION_LENGTH}",
                    ),
                )

    return smells


def check_quality_gates(
    report: QualityReport,
    thresholds: dict[str, float],
) -> list[tuple[str, bool, float, float]]:
    """Check quality gates against thresholds."""
    results: list[tuple[str, bool, float, float]] = []

    for gate, threshold in thresholds.items():
        actual: int | float
        if gate == "max_complexity":
            actual = report.max_complexity
            passed = actual <= threshold
        elif gate == "avg_complexity":
            actual = report.avg_complexity
            passed = actual <= threshold
        elif gate == "min_maintainability":
            actual = report.min_maintainability
            passed = actual >= threshold
        elif gate == "avg_maintainability":
            actual = report.avg_maintainability
            passed = actual >= threshold
        elif gate == "max_sloc":
            actual = report.total_sloc
            passed = actual <= threshold
        else:
            continue

        results.append((gate, passed, actual, threshold))

    return results


def analyze_path(path: Path) -> QualityReport:
    """Analyze all Python files in a path."""
    report = QualityReport()

    files = [path] if path.is_file() else list(path.rglob("*.py"))

    for file_path in files:
        # Skip hidden files, tests, and venvs
        path_str = str(file_path)
        if any(
            skip in path_str
            for skip in ["__pycache__", ".venv", "venv", "site-packages", ".git"]
        ):
            continue

        try:
            file_metrics = analyze_file(file_path)
            report.files.append(file_metrics)
        except Exception as e:
            console.print(
                f"[yellow]Warning:[/yellow] Could not analyze {file_path}: {e}"
            )

    # Detect smells
    report.smells = detect_smells(report)

    return report


def save_history(report: QualityReport, history_path: Path) -> None:
    """Append metrics to history file."""
    history: list[dict[str, Any]] = []

    if history_path.exists():
        with contextlib.suppress(Exception):
            history = json.loads(history_path.read_text())

    entry = {
        "timestamp": report.timestamp,
        "total_sloc": report.total_sloc,
        "total_files": len(report.files),
        "total_functions": len(report.all_functions),
        "avg_complexity": round(report.avg_complexity, 2),
        "max_complexity": report.max_complexity,
        "avg_maintainability": round(report.avg_maintainability, 2),
        "min_maintainability": round(report.min_maintainability, 2),
        "smell_count": len(report.smells),
    }

    history.append(entry)

    # Keep last 100 entries
    history = history[-100:]

    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history, indent=2))


def print_report(
    report: QualityReport,
    gate_results: list[tuple[str, bool, float, float]] | None = None,
    verbose: bool = False,
) -> None:
    """Print the quality report."""
    # Summary
    console.print(Panel("[bold]Code Quality Metrics[/bold]"))

    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Files Analyzed", str(len(report.files)))
    summary_table.add_row("Total SLOC", f"{report.total_sloc:,}")
    summary_table.add_row("Total Comments", f"{report.total_comments:,}")
    summary_table.add_row("Functions", str(len(report.all_functions)))

    console.print(summary_table)

    # Complexity
    if report.all_functions:
        console.print("\n[bold]Complexity[/bold]")

        # Rating for average
        avg_cc = report.avg_complexity
        if avg_cc <= 5:
            rating = "[green]Good[/green]"
        elif avg_cc <= 10:
            rating = "[yellow]Moderate[/yellow]"
        else:
            rating = "[red]High[/red]"

        console.print(f"  Average Complexity: {avg_cc:.1f} ({rating})")
        console.print(f"  Max Complexity: {report.max_complexity}")

        # Top complex functions
        top_complex = sorted(report.all_functions, key=lambda f: -f.complexity)[:5]
        if top_complex and top_complex[0].complexity > 5:
            console.print("\n  Most Complex Functions:")
            for func in top_complex:
                color = (
                    "red"
                    if func.complexity > 10
                    else "yellow"
                    if func.complexity > 5
                    else "green"
                )
                console.print(
                    f"    [{color}]{func.complexity:3d}[/{color}]  "
                    f"{func.file_path}::{func.name}",
                )

    # Maintainability
    if report.files:
        console.print("\n[bold]Maintainability[/bold]")

        avg_mi = report.avg_maintainability
        if avg_mi >= 85:
            rating = "[green]Excellent[/green]"
        elif avg_mi >= 65:
            rating = "[green]Good[/green]"
        elif avg_mi >= 40:
            rating = "[yellow]Moderate[/yellow]"
        else:
            rating = "[red]Poor[/red]"

        console.print(f"  Average MI: {avg_mi:.1f} ({rating})")
        console.print(f"  Lowest MI: {report.min_maintainability:.1f}")

        # Files needing attention
        low_mi = [f for f in report.files if 0 < f.maintainability < 65]
        if low_mi:
            console.print("\n  Files Needing Attention:")
            for f in sorted(low_mi, key=lambda x: x.maintainability)[:5]:
                console.print(f"    {f.maintainability:.1f}  {f.path}")

    # Code Smells
    if report.smells:
        console.print("\n[bold yellow]Code Smells[/bold yellow]")

        # Group by type
        by_type: dict[str, list[CodeSmell]] = {}
        for smell in report.smells:
            if smell.smell_type not in by_type:
                by_type[smell.smell_type] = []
            by_type[smell.smell_type].append(smell)

        for smell_type, smells in by_type.items():
            console.print(f"  {smell_type}: {len(smells)}")
            if verbose:
                for smell in smells[:3]:
                    console.print(f"    • {smell.file_path}: {smell.location}")
                    console.print(f"      {smell.message}")

    # Quality Gates
    if gate_results:
        console.print("\n[bold]Quality Gates[/bold]")

        all_passed = True
        for gate, passed, actual, threshold in gate_results:
            if passed:
                console.print(
                    f"  [green]✓[/green] {gate} <= {threshold} (actual: {actual:.1f})"
                )
            else:
                console.print(
                    f"  [red]✗[/red] {gate} <= {threshold} (actual: {actual:.1f})"
                )
                all_passed = False

        if all_passed:
            console.print("\n[bold green]All quality gates passed![/bold green]")
        else:
            console.print("\n[bold red]Quality gates failed![/bold red]")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Python file or directory to analyze")
    parser.add_argument(
        "--metrics",
        type=str,
        help="Metrics to calculate (comma-separated): complexity,maintainability,loc",
    )
    parser.add_argument(
        "--threshold",
        action="append",
        help="Quality gate threshold (e.g., max_complexity:15)",
    )
    parser.add_argument(
        "--fail-gates",
        action="store_true",
        help="Exit with error if quality gates fail",
    )
    parser.add_argument(
        "--history",
        type=Path,
        help="Path to history file for tracking over time",
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
            f"[red]Error:[/red] Path '{args.path}' does not exist", file=sys.stderr
        )
        return 1

    # Analyze
    report = analyze_path(args.path)

    # Parse thresholds
    thresholds: dict[str, float] = {}
    if args.threshold:
        for t in args.threshold:
            if ":" in t:
                name, value = t.split(":", 1)
                thresholds[name] = float(value)

    # Check gates
    gate_results = check_quality_gates(report, thresholds) if thresholds else None

    # Save history
    if args.history:
        save_history(report, args.history)

    # Output
    if args.output == "json":
        result: dict[str, Any] = {
            "timestamp": report.timestamp,
            "summary": {
                "files": len(report.files),
                "sloc": report.total_sloc,
                "lloc": report.total_lloc,
                "comments": report.total_comments,
                "functions": len(report.all_functions),
            },
            "complexity": {
                "average": round(report.avg_complexity, 2),
                "max": report.max_complexity,
                "functions": [
                    {
                        "name": f.name,
                        "file": f.file_path,
                        "line": f.line_number,
                        "complexity": f.complexity,
                        "rank": f.rank,
                    }
                    for f in sorted(report.all_functions, key=lambda x: -x.complexity)[
                        :20
                    ]
                ],
            },
            "maintainability": {
                "average": round(report.avg_maintainability, 2),
                "min": round(report.min_maintainability, 2),
                "files": [
                    {
                        "path": str(f.path),
                        "mi": round(f.maintainability, 2),
                        "rank": f.mi_rank,
                    }
                    for f in sorted(report.files, key=lambda x: x.maintainability)[:20]
                ],
            },
            "smells": [
                {
                    "type": s.smell_type,
                    "file": s.file_path,
                    "location": s.location,
                    "value": s.value,
                    "threshold": s.threshold,
                }
                for s in report.smells
            ],
        }

        if gate_results:
            result["gates"] = [
                {"name": g, "passed": p, "actual": a, "threshold": t}
                for g, p, a, t in gate_results
            ]
            result["gates_passed"] = all(p for _, p, _, _ in gate_results)

        print(json.dumps(result, indent=2))
    else:
        print_report(report, gate_results, args.verbose)

    # Exit code
    if args.fail_gates and gate_results and not all(p for _, p, _, _ in gate_results):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
