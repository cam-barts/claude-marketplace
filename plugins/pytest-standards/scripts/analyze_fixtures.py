#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
# ]
# ///
"""
Analyze pytest fixture complexity and dependencies.

Features:
- Map fixture dependency graph
- Detect circular dependencies
- Find deeply nested fixtures (depth > 3)
- Identify scope mismatches
- Find unused fixtures
- Suggest fixture consolidation

Usage:
    uv run analyze_fixtures.py [OPTIONS] PATH

Examples
--------
    uv run analyze_fixtures.py tests/
    uv run analyze_fixtures.py tests/ --max-depth 3
    uv run analyze_fixtures.py tests/ --graph
    uv run analyze_fixtures.py tests/ --unused
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class Fixture:
    """A pytest fixture definition."""

    name: str
    file_path: Path
    line_number: int
    scope: str
    dependencies: list[str] = field(default_factory=list)
    params: list[str] = field(default_factory=list)
    autouse: bool = False


@dataclass
class FixtureUsage:
    """A usage of a fixture in a test."""

    fixture_name: str
    test_name: str
    file_path: Path
    line_number: int


@dataclass
class FixtureIssue:
    """An issue found with fixtures."""

    fixture_name: str
    issue_type: str  # deep_nesting, scope_mismatch, circular, unused
    severity: str  # error, warning, info
    message: str
    file_path: Path | None = None
    line_number: int | None = None


@dataclass
class FixtureReport:
    """Report of fixture analysis."""

    fixtures: dict[str, Fixture] = field(default_factory=dict)
    usages: list[FixtureUsage] = field(default_factory=list)
    issues: list[FixtureIssue] = field(default_factory=list)
    dependency_depths: dict[str, int] = field(default_factory=dict)

    @property
    def has_issues(self) -> bool:
        return any(i.severity == "error" for i in self.issues)


class FixtureVisitor(ast.NodeVisitor):
    """AST visitor to extract fixture definitions and usages."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.fixtures: list[Fixture] = []
        self.usages: list[FixtureUsage] = []
        self.current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._process_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._process_function(node)

    def _process_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        # Check for fixture decorator
        fixture_decorator: ast.Name | ast.Attribute | ast.Call | None = None
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "fixture":
                fixture_decorator = decorator
            elif isinstance(decorator, ast.Attribute):
                if decorator.attr == "fixture":
                    fixture_decorator = decorator
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    if decorator.func.id == "fixture":
                        fixture_decorator = decorator
                elif (
                    isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "fixture"
                ):
                    fixture_decorator = decorator

        if fixture_decorator:
            # This is a fixture
            scope = "function"
            autouse = False
            params: list[str] = []

            # Extract decorator arguments
            if isinstance(fixture_decorator, ast.Call):
                for keyword in fixture_decorator.keywords:
                    if keyword.arg == "scope" and isinstance(
                        keyword.value,
                        ast.Constant,
                    ):
                        scope = str(keyword.value.value)
                    elif keyword.arg == "autouse" and isinstance(
                        keyword.value,
                        ast.Constant,
                    ):
                        autouse = bool(keyword.value.value)
                    elif keyword.arg == "params" and isinstance(
                        keyword.value,
                        ast.List,
                    ):
                        params = [ast.unparse(e) for e in keyword.value.elts]

            # Extract dependencies (function arguments)
            dependencies = [
                arg.arg for arg in node.args.args if arg.arg not in ("self", "cls")
            ]

            self.fixtures.append(
                Fixture(
                    name=node.name,
                    file_path=self.file_path,
                    line_number=node.lineno,
                    scope=scope,
                    dependencies=dependencies,
                    params=params,
                    autouse=autouse,
                ),
            )
        # This is a test or helper function
        elif node.name.startswith("test_"):
            self.current_function = node.name
            # Record fixture usages
            for arg in node.args.args:
                if arg.arg not in ("self", "cls"):
                    self.usages.append(
                        FixtureUsage(
                            fixture_name=arg.arg,
                            test_name=node.name,
                            file_path=self.file_path,
                            line_number=node.lineno,
                        ),
                    )

        self.generic_visit(node)


def find_test_files(path: Path) -> list[Path]:
    """Find all test files and conftest.py files."""
    if path.is_file():
        return [path] if path.suffix == ".py" else []

    files = []
    for py_file in path.rglob("*.py"):
        # Skip hidden and cache directories
        if any(part.startswith(".") or part == "__pycache__" for part in py_file.parts):
            continue
        # Include test files and conftest.py
        if py_file.name.startswith("test_") or py_file.name == "conftest.py":
            files.append(py_file)

    return files


def extract_fixtures(path: Path) -> tuple[dict[str, Fixture], list[FixtureUsage]]:
    """Extract all fixtures and usages from test files."""
    fixtures: dict[str, Fixture] = {}
    usages: list[FixtureUsage] = []

    test_files = find_test_files(path)

    for file_path in test_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
            visitor = FixtureVisitor(file_path)
            visitor.visit(tree)

            for fixture in visitor.fixtures:
                # Later definitions override earlier ones (like pytest)
                fixtures[fixture.name] = fixture

            usages.extend(visitor.usages)

        except Exception as e:
            console.print(
                f"[yellow]Warning:[/yellow] Could not parse {file_path}: {e}",
            )

    return fixtures, usages


def calculate_depths(fixtures: dict[str, Fixture]) -> dict[str, int]:
    """Calculate the dependency depth of each fixture."""
    depths: dict[str, int] = {}

    def get_depth(name: str, path: set[str]) -> int:
        if name in path:
            return -1  # Circular dependency

        if name in depths:
            return depths[name]

        if name not in fixtures:
            return 0  # Built-in or unknown fixture

        fixture = fixtures[name]
        if not fixture.dependencies:
            depths[name] = 1
            return 1

        max_dep_depth = 0
        for dep in fixture.dependencies:
            if dep in fixtures:
                dep_depth = get_depth(dep, path | {name})
                if dep_depth == -1:
                    return -1
                max_dep_depth = max(max_dep_depth, dep_depth)

        depths[name] = max_dep_depth + 1
        return depths[name]

    for name in fixtures:
        if name not in depths:
            get_depth(name, set())

    return depths


def detect_circular_deps(fixtures: dict[str, Fixture]) -> list[list[str]]:
    """Detect circular dependencies between fixtures."""
    cycles: list[list[str]] = []
    visited: set[str] = set()

    def dfs(name: str, path: list[str]) -> None:
        if name in path:
            cycle_start = path.index(name)
            cycle = path[cycle_start:] + [name]
            if cycle not in cycles:
                cycles.append(cycle)
            return

        if name in visited:
            return

        if name not in fixtures:
            return

        for dep in fixtures[name].dependencies:
            dfs(dep, path + [name])

        visited.add(name)

    for name in fixtures:
        dfs(name, [])

    return cycles


def detect_scope_mismatches(fixtures: dict[str, Fixture]) -> list[FixtureIssue]:
    """Detect scope mismatches in fixture dependencies."""
    issues: list[FixtureIssue] = []

    scope_order = {"session": 4, "package": 3, "module": 2, "class": 1, "function": 0}

    for name, fixture in fixtures.items():
        fixture_scope = scope_order.get(fixture.scope, 0)

        for dep_name in fixture.dependencies:
            if dep_name in fixtures:
                dep_fixture = fixtures[dep_name]
                dep_scope = scope_order.get(dep_fixture.scope, 0)

                if dep_scope < fixture_scope:
                    issues.append(
                        FixtureIssue(
                            fixture_name=name,
                            issue_type="scope_mismatch",
                            severity="warning",
                            message=f"Fixture '{name}' ({fixture.scope} scope) "
                            f"depends on '{dep_name}' ({dep_fixture.scope} scope)",
                            file_path=fixture.file_path,
                            line_number=fixture.line_number,
                        ),
                    )

    return issues


def find_unused_fixtures(
    fixtures: dict[str, Fixture],
    usages: list[FixtureUsage],
) -> list[Fixture]:
    """Find fixtures that are never used."""
    used_names: set[str] = set()

    # Direct usages
    for usage in usages:
        used_names.add(usage.fixture_name)

    # Dependencies of used fixtures
    def add_deps(name: str) -> None:
        if name in fixtures:
            for dep in fixtures[name].dependencies:
                used_names.add(dep)
                add_deps(dep)

    for name in list(used_names):
        add_deps(name)

    # Autouse fixtures are always "used"
    for name, fixture in fixtures.items():
        if fixture.autouse:
            used_names.add(name)
            add_deps(name)

    # Built-in pytest fixtures
    builtin_fixtures = {
        "request",
        "tmp_path",
        "tmp_path_factory",
        "tmpdir",
        "tmpdir_factory",
        "capfd",
        "capfdbinary",
        "capsys",
        "capsysbinary",
        "caplog",
        "monkeypatch",
        "pytestconfig",
        "recwarn",
        "cache",
        "doctest_namespace",
    }
    used_names.update(builtin_fixtures)

    unused = []
    for name, fixture in fixtures.items():
        if name not in used_names:
            unused.append(fixture)

    return unused


def analyze_fixtures(
    path: Path,
    max_depth: int = 3,
    find_unused: bool = False,
) -> FixtureReport:
    """Analyze fixtures in test files."""
    fixtures, usages = extract_fixtures(path)

    report = FixtureReport(fixtures=fixtures, usages=usages)

    # Calculate depths
    report.dependency_depths = calculate_depths(fixtures)

    # Find deep nesting
    for name, depth in report.dependency_depths.items():
        if depth > max_depth:
            fixture = fixtures[name]
            report.issues.append(
                FixtureIssue(
                    fixture_name=name,
                    issue_type="deep_nesting",
                    severity="warning",
                    message=f"Fixture '{name}' has depth {depth} (max: {max_depth})",
                    file_path=fixture.file_path,
                    line_number=fixture.line_number,
                ),
            )

    # Detect circular dependencies
    cycles = detect_circular_deps(fixtures)
    for cycle in cycles:
        report.issues.append(
            FixtureIssue(
                fixture_name=cycle[0],
                issue_type="circular",
                severity="error",
                message=f"Circular dependency: {' -> '.join(cycle)}",
            ),
        )

    # Detect scope mismatches
    report.issues.extend(detect_scope_mismatches(fixtures))

    # Find unused fixtures
    if find_unused:
        unused = find_unused_fixtures(fixtures, usages)
        for fixture in unused:
            report.issues.append(
                FixtureIssue(
                    fixture_name=fixture.name,
                    issue_type="unused",
                    severity="info",
                    message=f"Fixture '{fixture.name}' appears to be unused",
                    file_path=fixture.file_path,
                    line_number=fixture.line_number,
                ),
            )

    return report


def generate_dot_graph(fixtures: dict[str, Fixture]) -> str:
    """Generate a DOT graph of fixture dependencies."""
    lines = ["digraph fixtures {", "  rankdir=LR;", "  node [shape=box];"]

    # Color by scope
    scope_colors = {
        "session": "#ff9999",
        "package": "#ffcc99",
        "module": "#ffff99",
        "class": "#99ff99",
        "function": "#99ccff",
    }

    for name, fixture in fixtures.items():
        color = scope_colors.get(fixture.scope, "#ffffff")
        label = f"{name}\\n({fixture.scope})"
        lines.append(
            f'  "{name}" [label="{label}", style=filled, fillcolor="{color}"];'
        )

    for name, fixture in fixtures.items():
        for dep in fixture.dependencies:
            if dep in fixtures:
                lines.append(f'  "{name}" -> "{dep}";')

    lines.append("}")
    return "\n".join(lines)


def print_report(report: FixtureReport, verbose: bool = False) -> None:
    """Print the analysis report."""
    console.print(Panel("[bold]Fixture Analysis Report[/bold]"))

    # Summary
    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")

    summary_table.add_row("Total Fixtures", str(len(report.fixtures)))
    summary_table.add_row("Total Usages", str(len(report.usages)))

    error_count = len([i for i in report.issues if i.severity == "error"])
    warning_count = len([i for i in report.issues if i.severity == "warning"])

    summary_table.add_row(
        "Errors",
        f"[red]{error_count}[/red]" if error_count else "0",
    )
    summary_table.add_row(
        "Warnings",
        f"[yellow]{warning_count}[/yellow]" if warning_count else "0",
    )

    console.print(summary_table)

    # Fixtures by scope
    by_scope: dict[str, list[str]] = defaultdict(list)
    for name, fixture in report.fixtures.items():
        by_scope[fixture.scope].append(name)

    if by_scope:
        console.print("\n[bold]Fixtures by Scope[/bold]")
        scope_table = Table()
        scope_table.add_column("Scope", style="cyan")
        scope_table.add_column("Count", justify="right")
        scope_table.add_column("Fixtures", style="dim")

        for scope in ["session", "package", "module", "class", "function"]:
            if scope in by_scope:
                fixtures_list = ", ".join(by_scope[scope][:5])
                if len(by_scope[scope]) > 5:
                    fixtures_list += f" (+{len(by_scope[scope]) - 5})"
                scope_table.add_row(scope, str(len(by_scope[scope])), fixtures_list)

        console.print(scope_table)

    # Dependency tree (verbose)
    if verbose and report.fixtures:
        console.print("\n[bold]Fixture Dependencies[/bold]")
        for name, depth in sorted(
            report.dependency_depths.items(),
            key=lambda x: -x[1],
        )[:10]:
            fixture = report.fixtures[name]
            deps = ", ".join(fixture.dependencies) if fixture.dependencies else "(none)"
            console.print(f"  {name} (depth {depth}): {deps}")

    # Issues
    if report.issues:
        console.print("\n[bold]Issues[/bold]")
        by_type: dict[str, list[FixtureIssue]] = defaultdict(list)
        for issue in report.issues:
            by_type[issue.issue_type].append(issue)

        for issue_type, issues in by_type.items():
            severity = issues[0].severity
            color = {"error": "red", "warning": "yellow", "info": "blue"}[severity]
            console.print(f"\n[{color}]{issue_type.upper()} ({len(issues)})[/{color}]")
            for issue in issues[:5]:
                loc = (
                    f"{issue.file_path}:{issue.line_number}" if issue.file_path else ""
                )
                console.print(f"  {issue.message}")
                if loc:
                    console.print(f"    [dim]{loc}[/dim]")
            if len(issues) > 5:
                console.print(f"  ... and {len(issues) - 5} more")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Test directory to analyze")
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum acceptable fixture depth (default: 3)",
    )
    parser.add_argument(
        "--graph",
        action="store_true",
        help="Output DOT format for visualization",
    )
    parser.add_argument(
        "--unused",
        action="store_true",
        help="Report unused fixtures",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output",
        choices=["text", "json", "dot"],
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

    # Analyze fixtures
    report = analyze_fixtures(
        args.path,
        max_depth=args.max_depth,
        find_unused=args.unused,
    )

    # Output
    if args.output == "dot" or args.graph:
        print(generate_dot_graph(report.fixtures))
    elif args.output == "json":
        result: dict[str, Any] = {
            "summary": {
                "total_fixtures": len(report.fixtures),
                "total_usages": len(report.usages),
                "errors": len([i for i in report.issues if i.severity == "error"]),
                "warnings": len([i for i in report.issues if i.severity == "warning"]),
            },
            "fixtures": [
                {
                    "name": f.name,
                    "file": str(f.file_path),
                    "line": f.line_number,
                    "scope": f.scope,
                    "dependencies": f.dependencies,
                    "autouse": f.autouse,
                    "depth": report.dependency_depths.get(f.name, 0),
                }
                for f in report.fixtures.values()
            ],
            "issues": [
                {
                    "fixture": i.fixture_name,
                    "type": i.issue_type,
                    "severity": i.severity,
                    "message": i.message,
                    "file": str(i.file_path) if i.file_path else None,
                    "line": i.line_number,
                }
                for i in report.issues
            ],
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(report, verbose=args.verbose)

    return 1 if report.has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
