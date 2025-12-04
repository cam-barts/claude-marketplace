#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "tomli>=2.0",
# ]
# ///
"""
Identify conflicting or redundant linting tools.

Features:
- Analyze installed linters and their coverage
- Detect overlapping rules between tools
- Identify redundant tools (e.g., black + ruff format)
- Suggest consolidation
- Generate migration plan

Usage:
    uv run detect_tool_conflicts.py [OPTIONS] [PATH]

Examples
--------
    uv run detect_tool_conflicts.py
    uv run detect_tool_conflicts.py --installed
    uv run detect_tool_conflicts.py --suggest
    uv run detect_tool_conflicts.py --migrate
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomli
except ImportError:
    tomli = None  # type: ignore

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Tool capabilities and overlaps
TOOL_CAPABILITIES: dict[str, dict[str, Any]] = {
    # Python formatters
    "black": {
        "type": "formatter",
        "language": "python",
        "capabilities": ["format"],
        "overlaps_with": ["ruff", "autopep8", "yapf"],
    },
    "autopep8": {
        "type": "formatter",
        "language": "python",
        "capabilities": ["format"],
        "overlaps_with": ["black", "ruff", "yapf"],
    },
    "yapf": {
        "type": "formatter",
        "language": "python",
        "capabilities": ["format"],
        "overlaps_with": ["black", "ruff", "autopep8"],
    },
    # Python linters
    "flake8": {
        "type": "linter",
        "language": "python",
        "capabilities": ["lint"],
        "overlaps_with": ["ruff", "pylint"],
    },
    "pylint": {
        "type": "linter",
        "language": "python",
        "capabilities": ["lint"],
        "overlaps_with": ["ruff", "flake8"],
    },
    "pyflakes": {
        "type": "linter",
        "language": "python",
        "capabilities": ["lint"],
        "overlaps_with": ["ruff", "flake8"],
    },
    "pycodestyle": {
        "type": "linter",
        "language": "python",
        "capabilities": ["lint"],
        "overlaps_with": ["ruff", "flake8"],
    },
    "isort": {
        "type": "formatter",
        "language": "python",
        "capabilities": ["import-sort"],
        "overlaps_with": ["ruff"],
    },
    # Ruff (all-in-one)
    "ruff": {
        "type": "all-in-one",
        "language": "python",
        "capabilities": ["lint", "format", "import-sort"],
        "replaces": [
            "black",
            "flake8",
            "isort",
            "pyflakes",
            "pycodestyle",
            "pydocstyle",
            "autopep8",
        ],
    },
    # JavaScript/TypeScript
    "prettier": {
        "type": "formatter",
        "language": "javascript",
        "capabilities": ["format"],
        "overlaps_with": ["biome", "dprint"],
    },
    "eslint": {
        "type": "linter",
        "language": "javascript",
        "capabilities": ["lint"],
        "overlaps_with": ["biome"],
    },
    "biome": {
        "type": "all-in-one",
        "language": "javascript",
        "capabilities": ["lint", "format"],
        "replaces": ["prettier", "eslint"],
    },
    # Type checkers (don't overlap with linters)
    "mypy": {
        "type": "type-checker",
        "language": "python",
        "capabilities": ["type-check"],
        "overlaps_with": ["pyright", "pytype"],
    },
    "pyright": {
        "type": "type-checker",
        "language": "python",
        "capabilities": ["type-check"],
        "overlaps_with": ["mypy", "pytype"],
    },
    "typescript": {
        "type": "type-checker",
        "language": "typescript",
        "capabilities": ["type-check"],
        "overlaps_with": [],
    },
    # Markdown linters
    "markdownlint": {
        "type": "linter",
        "language": "markdown",
        "capabilities": ["lint"],
        "overlaps_with": ["rumdl"],
    },
    "rumdl": {
        "type": "all-in-one",
        "language": "markdown",
        "capabilities": ["lint", "format"],
        "replaces": ["markdownlint"],
    },
}


@dataclass
class ToolConflict:
    """A conflict between tools."""

    tools: list[str]
    conflict_type: str  # overlap, redundant, conflict
    severity: str  # error, warning, info
    message: str
    suggestion: str


@dataclass
class InstalledTool:
    """An installed tool."""

    name: str
    version: str | None = None
    config_file: str | None = None


@dataclass
class ConflictReport:
    """Report of tool conflicts."""

    installed_tools: list[InstalledTool] = field(default_factory=list)
    conflicts: list[ToolConflict] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return any(c.severity == "error" for c in self.conflicts)


def check_tool_installed(name: str) -> tuple[bool, str | None]:
    """Check if a tool is installed and get its version."""
    command_map = {
        "black": ["black", "--version"],
        "autopep8": ["autopep8", "--version"],
        "yapf": ["yapf", "--version"],
        "flake8": ["flake8", "--version"],
        "pylint": ["pylint", "--version"],
        "pyflakes": ["pyflakes", "--version"],
        "pycodestyle": ["pycodestyle", "--version"],
        "isort": ["isort", "--version"],
        "ruff": ["ruff", "--version"],
        "prettier": ["prettier", "--version"],
        "eslint": ["eslint", "--version"],
        "biome": ["biome", "--version"],
        "mypy": ["mypy", "--version"],
        "pyright": ["pyright", "--version"],
        "markdownlint": ["markdownlint", "--version"],
        "rumdl": ["rumdl", "version"],
    }

    if name not in command_map:
        return False, None

    cmd = command_map[name]
    if shutil.which(cmd[0]) is None:
        return False, None

    try:
        import subprocess

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        version = result.stdout.strip().split("\n")[0]
        return True, version
    except Exception:
        return True, None


def find_tool_configs(path: Path) -> dict[str, str]:
    """Find configuration files for various tools."""
    config_patterns: dict[str, list[str]] = {
        "black": ["pyproject.toml", ".black.toml"],
        "flake8": [".flake8", "setup.cfg", "tox.ini"],
        "pylint": [".pylintrc", "pylintrc", "pyproject.toml"],
        "isort": [".isort.cfg", "pyproject.toml", "setup.cfg"],
        "ruff": ["ruff.toml", ".ruff.toml", "pyproject.toml"],
        "prettier": [".prettierrc", ".prettierrc.json", ".prettierrc.yml"],
        "eslint": [".eslintrc", ".eslintrc.json", ".eslintrc.js", "eslint.config.js"],
        "biome": ["biome.json"],
        "mypy": ["mypy.ini", ".mypy.ini", "pyproject.toml"],
        "markdownlint": [
            ".markdownlint.json",
            ".markdownlint.yaml",
            ".markdownlint.yml",
            ".markdownlintrc",
        ],
        "rumdl": [".rumdl.toml", "pyproject.toml"],
    }

    found: dict[str, str] = {}

    for tool, patterns in config_patterns.items():
        for pattern in patterns:
            config_path = path / pattern
            if config_path.exists():
                found[tool] = str(config_path)
                break

    return found


def analyze_pyproject(path: Path) -> list[str]:
    """Analyze pyproject.toml for configured tools."""
    if tomli is None:
        return []

    pyproject = path / "pyproject.toml"
    if not pyproject.exists():
        return []

    try:
        content = pyproject.read_bytes()
        data = tomli.loads(content.decode("utf-8"))

        tools = []

        # Check [tool.*] sections
        if "tool" in data:
            for tool_name in data["tool"]:
                if tool_name in TOOL_CAPABILITIES:
                    tools.append(tool_name)

        return tools
    except Exception:
        return []


def detect_conflicts(
    installed: list[InstalledTool],
    path: Path,  # noqa: ARG001
) -> list[ToolConflict]:
    """Detect conflicts between installed tools."""
    conflicts: list[ToolConflict] = []
    installed_names = {t.name for t in installed}

    # Check for overlapping tools
    for tool_name in installed_names:
        if tool_name not in TOOL_CAPABILITIES:
            continue

        tool_info = TOOL_CAPABILITIES[tool_name]

        # Check if this tool replaces others that are also installed
        if "replaces" in tool_info:
            for replaced in tool_info["replaces"]:
                if replaced in installed_names:
                    conflicts.append(
                        ToolConflict(
                            tools=[tool_name, replaced],
                            conflict_type="redundant",
                            severity="warning",
                            message=f"'{tool_name}' can replace '{replaced}'",
                            suggestion=f"Remove '{replaced}', use '{tool_name}'",
                        ),
                    )

        # Check overlaps
        if "overlaps_with" in tool_info:
            for overlap in tool_info["overlaps_with"]:
                # Only report each pair once
                if overlap in installed_names and tool_name < overlap:
                    conflicts.append(
                        ToolConflict(
                            tools=[tool_name, overlap],
                            conflict_type="overlap",
                            severity="info",
                            message=f"'{tool_name}' and '{overlap}' overlap",
                            suggestion="Consider using only one of them",
                        ),
                    )

    # Check for specific problematic combinations
    if "black" in installed_names and "ruff" in installed_names:
        # Check if ruff format is enabled
        conflicts.append(
            ToolConflict(
                tools=["black", "ruff"],
                conflict_type="redundant",
                severity="warning",
                message="Both 'black' and 'ruff' installed - ruff can format code",
                suggestion="Use 'ruff format' instead of 'black'",
            ),
        )

    if "flake8" in installed_names and "ruff" in installed_names:
        conflicts.append(
            ToolConflict(
                tools=["flake8", "ruff"],
                conflict_type="redundant",
                severity="warning",
                message="Both 'flake8' and 'ruff' - ruff includes flake8 rules",
                suggestion="Use 'ruff check' instead of 'flake8'",
            ),
        )

    if "prettier" in installed_names and "biome" in installed_names:
        conflicts.append(
            ToolConflict(
                tools=["prettier", "biome"],
                conflict_type="redundant",
                severity="warning",
                message="Both 'prettier' and 'biome' installed - biome can format",
                suggestion="Use 'biome format' instead of 'prettier'",
            ),
        )

    if "markdownlint" in installed_names:
        # Always recommend rumdl for markdownlint users
        if "rumdl" in installed_names:
            conflicts.append(
                ToolConflict(
                    tools=["markdownlint", "rumdl"],
                    conflict_type="redundant",
                    severity="warning",
                    message="Both 'markdownlint' and 'rumdl' - rumdl is faster",
                    suggestion="Use 'rumdl check --fix' instead of 'markdownlint'",
                ),
            )
        else:
            conflicts.append(
                ToolConflict(
                    tools=["markdownlint"],
                    conflict_type="upgrade",
                    severity="info",
                    message="'markdownlint' can be replaced with 'rumdl' (10x faster)",
                    suggestion="Install: uv tool install rumdl; run 'rumdl check'",
                ),
            )

    return conflicts


def generate_migration_plan(conflicts: list[ToolConflict]) -> list[str]:
    """Generate a migration plan based on conflicts."""
    steps: list[str] = []

    # Find tools to remove
    tools_to_remove: set[str] = set()
    for conflict in conflicts:
        if conflict.conflict_type == "redundant":
            # The second tool in the list is usually the one to remove
            if len(conflict.tools) == 2:
                # Prefer keeping ruff, biome, and rumdl (Rust-based tools)
                if "ruff" in conflict.tools:
                    tools_to_remove.add([t for t in conflict.tools if t != "ruff"][0])
                elif "biome" in conflict.tools:
                    tools_to_remove.add([t for t in conflict.tools if t != "biome"][0])
                elif "rumdl" in conflict.tools:
                    tools_to_remove.add([t for t in conflict.tools if t != "rumdl"][0])
                else:
                    tools_to_remove.add(conflict.tools[1])
        elif conflict.conflict_type == "upgrade" and "markdownlint" in conflict.tools:
            # Recommend upgrading from markdownlint to rumdl
            tools_to_remove.add("markdownlint")

    if tools_to_remove:
        steps.append("# Remove redundant tools")
        for tool in sorted(tools_to_remove):
            if tool in {"black", "flake8", "isort", "pylint", "pyflakes", "autopep8"}:
                steps.append(f"uv pip uninstall {tool}")
            elif tool in {"prettier", "eslint"}:
                steps.append(f"npm uninstall {tool}")
            elif tool == "markdownlint":
                steps.append("npm uninstall markdownlint-cli")

    # Migration steps for ruff
    python_tools = {"black", "flake8", "isort", "pylint", "pyflakes"} & tools_to_remove
    if python_tools:
        steps.append("")
        steps.append("# Configure ruff to replace removed tools")
        steps.append("# Add to ruff.toml or pyproject.toml [tool.ruff]:")
        steps.append("# select = [")
        steps.append('#     "E",    # pycodestyle errors')
        steps.append('#     "F",    # pyflakes')
        steps.append('#     "I",    # isort')
        steps.append('#     "W",    # pycodestyle warnings')
        steps.append("# ]")

    # Migration steps for rumdl
    if "markdownlint" in tools_to_remove:
        steps.append("")
        steps.append("# Install rumdl (Rust markdown linter)")
        steps.append(
            "uv tool install rumdl  # or: pip install rumdl, brew install rumdl"
        )
        steps.append("")
        steps.append("# Initialize rumdl config in pyproject.toml")
        steps.append("rumdl init --pyproject")
        steps.append("")
        steps.append("# Import existing markdownlint config (optional)")
        steps.append("# rumdl import .markdownlint.json")
        steps.append("")
        steps.append("# Remove old markdownlint config files")
        steps.append("# rm .markdownlint.json .markdownlintrc")

    return steps


def detect_tool_conflicts(
    path: Path,
    check_installed: bool = True,
) -> ConflictReport:
    """Detect conflicts between tools."""
    report = ConflictReport()

    # Find installed tools
    tools_to_check = list(TOOL_CAPABILITIES.keys())

    if check_installed:
        for tool_name in tools_to_check:
            is_installed, version = check_tool_installed(tool_name)
            if is_installed:
                report.installed_tools.append(
                    InstalledTool(name=tool_name, version=version),
                )
    else:
        # Check config files
        configs = find_tool_configs(path)
        for tool_name, config_file in configs.items():
            report.installed_tools.append(
                InstalledTool(name=tool_name, config_file=config_file),
            )

        # Also check pyproject.toml
        pyproject_tools = analyze_pyproject(path)
        for tool_name in pyproject_tools:
            if not any(t.name == tool_name for t in report.installed_tools):
                report.installed_tools.append(InstalledTool(name=tool_name))

    # Detect conflicts
    report.conflicts = detect_conflicts(report.installed_tools, path)

    # Generate suggestions
    if report.conflicts:
        report.suggestions = generate_migration_plan(report.conflicts)

    return report


def print_report(report: ConflictReport, verbose: bool = False) -> None:  # noqa: ARG001
    """Print the conflict report."""
    console.print(Panel("[bold]Tool Conflict Detection Report[/bold]"))

    # Installed tools
    if report.installed_tools:
        console.print("\n[bold]Installed Tools[/bold]")
        tool_table = Table()
        tool_table.add_column("Tool", style="cyan")
        tool_table.add_column("Version")
        tool_table.add_column("Type")

        for tool in report.installed_tools:
            tool_info = TOOL_CAPABILITIES.get(tool.name, {})
            tool_type = tool_info.get("type", "unknown")
            version = tool.version or "-"
            tool_table.add_row(tool.name, version, tool_type)

        console.print(tool_table)

    # Conflicts
    if report.conflicts:
        console.print("\n[bold]Conflicts Detected[/bold]")
        for conflict in report.conflicts:
            color = {
                "error": "red",
                "warning": "yellow",
                "info": "blue",
            }[conflict.severity]
            console.print(
                f"  [{color}]{conflict.severity.upper()}[/{color}] {conflict.message}",
            )
            console.print(f"    [dim]Suggestion: {conflict.suggestion}[/dim]")
    else:
        console.print("\n[green]No conflicts detected![/green]")

    # Migration plan
    if report.suggestions:
        console.print("\n[bold blue]Migration Plan[/bold blue]")
        for step in report.suggestions:
            console.print(f"  {step}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path(),
        help="Repository to analyze (default: current directory)",
    )
    parser.add_argument(
        "--installed",
        action="store_true",
        help="Only analyze installed tools",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Only analyze tools with config files",
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Show consolidation suggestions",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Generate migration commands",
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

    # Detect conflicts
    check_installed = not args.config
    report = detect_tool_conflicts(args.path, check_installed=check_installed)

    # Show migration plan if requested
    if args.migrate and report.suggestions:
        for step in report.suggestions:
            print(step)
        return 0

    # Output
    if args.output == "json":
        result: dict[str, Any] = {
            "installed_tools": [
                {
                    "name": t.name,
                    "version": t.version,
                    "config_file": t.config_file,
                }
                for t in report.installed_tools
            ],
            "conflicts": [
                {
                    "tools": c.tools,
                    "type": c.conflict_type,
                    "severity": c.severity,
                    "message": c.message,
                    "suggestion": c.suggestion,
                }
                for c in report.conflicts
            ],
            "migration_steps": report.suggestions,
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(report, verbose=args.verbose)

    return 1 if report.has_conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
