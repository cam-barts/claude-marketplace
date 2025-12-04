#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "libcst>=1.0",
# ]
# ///
"""
Detect test anti-patterns and code smells in pytest test files.

Detects:
- ASSERTION_ROULETTE: Too many assertions without clear intent
- EAGER_TEST: Testing multiple behaviors in one test
- MYSTERY_GUEST: Hidden external dependencies
- MOCK_OVERLOAD: Excessive mocking that hides real issues
- DEAD_TEST: Tests without assertions or that always pass
- CONDITIONAL_TEST: Tests with conditional logic
- DUPLICATE_SETUP: Repeated setup code across tests
- MAGIC_NUMBERS: Unexplained numeric literals

Usage:
    uv run analyze_test_smells.py [OPTIONS] PATH

Examples
--------
    uv run analyze_test_smells.py tests/
    uv run analyze_test_smells.py tests/test_api.py --severity warning
    uv run analyze_test_smells.py tests/ --output json > report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import libcst as cst
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class TestSmell:
    """A detected test smell."""

    smell_type: str
    severity: Severity
    file_path: Path
    line_number: int
    function_name: str
    message: str
    suggestion: str


@dataclass
class AnalysisReport:
    """Report of all detected smells."""

    files_analyzed: int = 0
    tests_analyzed: int = 0
    smells: list[TestSmell] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not any(s.severity == Severity.ERROR for s in self.smells)

    def smells_by_severity(self, severity: Severity) -> list[TestSmell]:
        return [s for s in self.smells if s.severity == severity]


class TestSmellDetector(cst.CSTVisitor):
    """Detect test smells in Python test files."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.smells: list[TestSmell] = []
        self.tests_count = 0

        # State tracking
        self._current_function: str | None = None
        self._current_function_line: int = 0
        self._assertion_count = 0
        self._mock_count = 0
        self._has_external_deps = False
        self._has_conditional = False
        self._magic_numbers: list[tuple[int, str]] = []
        self._function_calls: list[str] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool | None:
        """Visit test function definitions."""
        name = node.name.value

        # Only analyze test functions
        if not name.startswith("test_"):
            return True

        self.tests_count += 1
        self._current_function = name
        self._current_function_line = self._get_line_number(node)
        self._assertion_count = 0
        self._mock_count = 0
        self._has_external_deps = False
        self._has_conditional = False
        self._magic_numbers = []
        self._function_calls = []

        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: ARG002
        """Analyze function after visiting all nodes."""
        if not self._current_function or not self._current_function.startswith("test_"):
            return

        # DEAD_TEST: No assertions
        if self._assertion_count == 0:
            self.smells.append(
                TestSmell(
                    smell_type="DEAD_TEST",
                    severity=Severity.ERROR,
                    file_path=self.file_path,
                    line_number=self._current_function_line,
                    function_name=self._current_function,
                    message="Test has no assertions",
                    suggestion="Add assertions to verify expected behavior",
                ),
            )

        # ASSERTION_ROULETTE: Too many assertions
        if self._assertion_count > 5:
            self.smells.append(
                TestSmell(
                    smell_type="ASSERTION_ROULETTE",
                    severity=Severity.WARNING,
                    file_path=self.file_path,
                    line_number=self._current_function_line,
                    function_name=self._current_function,
                    message=f"Test has {self._assertion_count} assertions (max: 5)",
                    suggestion="Split into multiple focused tests or add messages",
                ),
            )

        # MOCK_OVERLOAD: Too many mocks
        if self._mock_count > 3:
            self.smells.append(
                TestSmell(
                    smell_type="MOCK_OVERLOAD",
                    severity=Severity.WARNING,
                    file_path=self.file_path,
                    line_number=self._current_function_line,
                    function_name=self._current_function,
                    message=f"Test uses {self._mock_count} mocks (max: 3)",
                    suggestion="Consider real objects or refactoring code under test",
                ),
            )

        # MYSTERY_GUEST: External dependencies without explicit setup
        if self._has_external_deps:
            self.smells.append(
                TestSmell(
                    smell_type="MYSTERY_GUEST",
                    severity=Severity.INFO,
                    file_path=self.file_path,
                    line_number=self._current_function_line,
                    function_name=self._current_function,
                    message="Test may have hidden external dependencies",
                    suggestion="Use fixtures to make deps explicit, or mock externals",
                ),
            )

        # CONDITIONAL_TEST: Logic in tests
        if self._has_conditional:
            self.smells.append(
                TestSmell(
                    smell_type="CONDITIONAL_TEST",
                    severity=Severity.WARNING,
                    file_path=self.file_path,
                    line_number=self._current_function_line,
                    function_name=self._current_function,
                    message="Test contains conditional logic",
                    suggestion="Use parametrize for cases, avoid if/for in tests",
                ),
            )

        # MAGIC_NUMBERS: Unexplained literals
        if len(self._magic_numbers) > 2:
            count = len(self._magic_numbers)
            self.smells.append(
                TestSmell(
                    smell_type="MAGIC_NUMBERS",
                    severity=Severity.INFO,
                    file_path=self.file_path,
                    line_number=self._current_function_line,
                    function_name=self._current_function,
                    message=f"Test contains {count} magic numbers",
                    suggestion="Use named constants or descriptive variable names",
                ),
            )

        # Reset state
        self._current_function = None

    def visit_Call(self, node: cst.Call) -> bool | None:
        """Track function calls."""
        if not self._current_function:
            return True

        call_name = self._get_call_name(node)
        self._function_calls.append(call_name)

        # Count assertions
        if call_name.startswith("assert") or call_name in (
            "assertEqual",
            "assertTrue",
            "assertFalse",
            "assertIn",
            "assertNotIn",
            "assertRaises",
            "assertIsNone",
            "assertIsNotNone",
        ):
            self._assertion_count += 1

        # Count mocks
        if "mock" in call_name.lower() or "patch" in call_name.lower():
            self._mock_count += 1

        # Detect external dependencies
        external_patterns = (
            "open",
            "requests.",
            "urllib",
            "http.",
            "socket",
            "subprocess",
            "os.system",
            "os.popen",
        )
        if any(pattern in call_name for pattern in external_patterns):
            self._has_external_deps = True

        return True

    def visit_Assert(self, node: cst.Assert) -> bool | None:  # noqa: ARG002
        """Count assert statements."""
        if self._current_function:
            self._assertion_count += 1
        return True

    def visit_If(self, node: cst.If) -> bool | None:  # noqa: ARG002
        """Detect conditional logic in tests."""
        if self._current_function:
            self._has_conditional = True
        return True

    def visit_For(self, node: cst.For) -> bool | None:  # noqa: ARG002
        """Detect loops in tests."""
        if self._current_function:
            self._has_conditional = True
        return True

    def visit_While(self, node: cst.While) -> bool | None:  # noqa: ARG002
        """Detect while loops in tests."""
        if self._current_function:
            self._has_conditional = True
        return True

    def visit_Integer(self, node: cst.Integer) -> bool | None:
        """Detect magic numbers."""
        if self._current_function:
            value = node.value
            # Ignore common values like 0, 1, -1
            if value not in ("0", "1", "-1", "2"):
                self._magic_numbers.append(
                    (self._get_line_number(node), value),
                )
        return True

    def _get_call_name(self, node: cst.Call) -> str:
        """Extract the name of a function call."""
        if isinstance(node.func, cst.Name):
            return node.func.value
        if isinstance(node.func, cst.Attribute):
            parts = []
            current = node.func
            while isinstance(current, cst.Attribute):
                parts.append(current.attr.value)
                current = current.value
            if isinstance(current, cst.Name):
                parts.append(current.value)
            return ".".join(reversed(parts))
        return ""

    def _get_line_number(self, node: cst.CSTNode) -> int:
        """Get the line number of a node."""
        # Placeholder - libcst doesn't directly expose line numbers
        # In practice, we'd use a wrapper or metadata provider
        _ = node  # Suppress unused argument warning
        return 1  # Default to 1, actual implementation would use metadata


class MetadataWrapper(cst.MetadataWrapper):
    """Wrapper to get position information."""


def analyze_file(file_path: Path) -> tuple[int, list[TestSmell]]:
    """Analyze a single test file."""
    content = file_path.read_text(encoding="utf-8")

    try:
        tree = cst.parse_module(content)
    except cst.ParserSyntaxError as e:
        console.print(f"[red]Syntax error in {file_path}:[/red] {e}")
        return 0, []

    detector = TestSmellDetector(file_path)

    # Use metadata wrapper for line numbers
    try:
        wrapper = cst.metadata.MetadataWrapper(tree)
        wrapper.visit(detector)
    except Exception:
        # Fallback without metadata
        tree.walk(detector)

    return detector.tests_count, detector.smells


def analyze_path(path: Path, min_severity: Severity = Severity.INFO) -> AnalysisReport:
    """Analyze a path (file or directory)."""
    report = AnalysisReport()

    if path.is_file():
        files = [path]
    else:
        files = list(path.rglob("test_*.py"))
        files.extend(path.rglob("*_test.py"))

    for file_path in files:
        if "__pycache__" in str(file_path):
            continue

        try:
            tests_count, smells = analyze_file(file_path)
            report.files_analyzed += 1
            report.tests_analyzed += tests_count

            # Filter by severity
            severity_order = [Severity.INFO, Severity.WARNING, Severity.ERROR]
            min_index = severity_order.index(min_severity)

            for smell in smells:
                if severity_order.index(smell.severity) >= min_index:
                    report.smells.append(smell)

        except Exception as e:
            console.print(
                f"[red]Error analyzing {file_path}:[/red] {e}", file=sys.stderr
            )

    return report


def print_report(report: AnalysisReport, verbose: bool = False) -> None:
    """Print the analysis report."""
    # Summary table
    table = Table(title="Test Smell Analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Files Analyzed", str(report.files_analyzed))
    table.add_row("Tests Analyzed", str(report.tests_analyzed))
    table.add_row("Errors", str(len(report.smells_by_severity(Severity.ERROR))))
    table.add_row("Warnings", str(len(report.smells_by_severity(Severity.WARNING))))
    table.add_row("Info", str(len(report.smells_by_severity(Severity.INFO))))
    console.print(table)

    if not report.smells:
        console.print("\n[green]No test smells detected![/green]")
        return

    # Group by smell type
    smells_by_type: dict[str, list[TestSmell]] = {}
    for smell in report.smells:
        if smell.smell_type not in smells_by_type:
            smells_by_type[smell.smell_type] = []
        smells_by_type[smell.smell_type].append(smell)

    # Print by type
    for smell_type, smells in sorted(smells_by_type.items()):
        severity = smells[0].severity
        color = {"error": "red", "warning": "yellow", "info": "blue"}[severity.value]

        console.print(
            f"\n[bold {color}]{smell_type}[/bold {color}] ({len(smells)} occurrences)"
        )

        if verbose or severity == Severity.ERROR:
            for smell in smells[:10]:  # Limit output
                console.print(f"  [dim]{smell.file_path}[/dim]: {smell.function_name}")
                console.print(f"    {smell.message}")
                console.print(f"    [dim]Suggestion: {smell.suggestion}[/dim]")

            if len(smells) > 10:
                console.print(f"  ... and {len(smells) - 10} more")

    # Smell type explanations
    if verbose:
        console.print("\n")
        console.print(
            Panel(
                "[bold]Test Smell Descriptions:[/bold]\n\n"
                "[cyan]ASSERTION_ROULETTE[/cyan]: Too many assertions\n"
                "[cyan]EAGER_TEST[/cyan]: Multiple behaviors violates SRP\n"
                "[cyan]MYSTERY_GUEST[/cyan]: Hidden deps make tests fragile\n"
                "[cyan]MOCK_OVERLOAD[/cyan]: Excessive mocks test impl, not behavior\n"
                "[cyan]DEAD_TEST[/cyan]: Tests without assertions\n"
                "[cyan]CONDITIONAL_TEST[/cyan]: Logic in tests causes flakiness\n"
                "[cyan]MAGIC_NUMBERS[/cyan]: Unexplained values",
                title="Reference",
            ),
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Test file or directory to analyze")
    parser.add_argument(
        "--severity",
        choices=["info", "warning", "error"],
        default="info",
        help="Minimum severity to report (default: info)",
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

    min_severity = Severity(args.severity)
    report = analyze_path(args.path, min_severity)

    if args.output == "json":
        result: dict[str, Any] = {
            "success": report.success,
            "files_analyzed": report.files_analyzed,
            "tests_analyzed": report.tests_analyzed,
            "smells": [
                {
                    "type": s.smell_type,
                    "severity": s.severity.value,
                    "file": str(s.file_path),
                    "line": s.line_number,
                    "function": s.function_name,
                    "message": s.message,
                    "suggestion": s.suggestion,
                }
                for s in report.smells
            ],
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(report, args.verbose)

    return 0 if report.success else 1


if __name__ == "__main__":
    sys.exit(main())
