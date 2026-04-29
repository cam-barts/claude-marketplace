#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "tomli>=2.0",
#     "cyclopts>=3.0",
#     "pydantic>=2.0",
# ]
# ///
"""Identify conflicting or redundant linting tools."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli  # type: ignore[no-redef]
    except ImportError:
        tomli = None  # type: ignore[assignment]

from cyclopts import App
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

app = App(help="Detect overlapping or redundant linters and suggest consolidation.")

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


class ToolConflict(BaseModel):
    """A conflict between tools."""

    tools: list[str]
    conflict_type: str  # overlap, redundant, conflict
    severity: str  # error, warning, info
    message: str
    suggestion: str


class InstalledTool(BaseModel):
    """An installed tool."""

    name: str
    version: str | None = None
    config_file: str | None = None


class RedundantTool(BaseModel):
    """A tool identified as redundant."""

    tool: str
    replaces: str
    suggestion: str


class MigrationSuggestion(BaseModel):
    """A suggestion for tool migration."""

    source: str
    target: str
    reason: str
    commands: list[str] = Field(default_factory=list)


class ConflictReport(BaseModel):
    """Report of tool conflicts."""

    installed_tools: list[InstalledTool] = Field(default_factory=list)
    conflicts: list[ToolConflict] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    redundant: list[RedundantTool] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    config_conflicts: list[str] = Field(default_factory=list)
    overlapping_rules: list[str] = Field(default_factory=list)

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


def _detect_redundant_tools(installed_names: set[str]) -> list[RedundantTool]:
    """Detect redundant tools from a set of installed tool names."""
    redundant: list[RedundantTool] = []
    for tool_name in installed_names:
        if tool_name not in TOOL_CAPABILITIES:
            continue
        tool_info = TOOL_CAPABILITIES[tool_name]
        if "replaces" in tool_info:
            for replaced in tool_info["replaces"]:
                if replaced in installed_names:
                    redundant.append(
                        RedundantTool(
                            tool=replaced,
                            replaces=tool_name,
                            suggestion=f"Remove '{replaced}', use '{tool_name}'",
                        )
                    )
    return redundant


def _detect_config_conflicts(path: Path) -> list[str]:
    """Detect configuration conflicts between tools."""
    if tomli is None:
        return []

    pyproject = path / "pyproject.toml"
    if not pyproject.exists():
        return []

    conflicts: list[str] = []
    try:
        data = tomli.loads(pyproject.read_bytes().decode("utf-8"))
        tool = data.get("tool", {})

        ruff_line = None
        black_line = None

        if "ruff" in tool:
            ruff_line = tool["ruff"].get("line-length")
        if "black" in tool:
            black_line = tool["black"].get("line-length")

        if ruff_line is not None and black_line is not None and ruff_line != black_line:
            conflicts.append(
                f"Line length conflict: ruff={ruff_line}, black={black_line}"
            )
        elif "ruff" in tool and "black" in tool:
            # Both configured — flag as potential conflict even if line lengths match
            conflicts.append("Both ruff and black are configured in pyproject.toml")

    except Exception:
        pass

    return conflicts


def detect_conflicts(
    path: Path,
    check_installed: bool = False,
) -> ConflictReport:
    """Detect conflicts between tools in a repository."""
    report = ConflictReport()

    # Find tools via config files or installed binaries
    if check_installed:
        for tool_name in list(TOOL_CAPABILITIES.keys()):
            is_installed, version = check_tool_installed(tool_name)
            if is_installed:
                report.installed_tools.append(
                    InstalledTool(name=tool_name, version=version),
                )
    else:
        configs = find_tool_configs(path)
        for tool_name, config_file in configs.items():
            report.installed_tools.append(
                InstalledTool(name=tool_name, config_file=config_file),
            )

        pyproject_tools = analyze_pyproject(path)
        for tool_name in pyproject_tools:
            if not any(t.name == tool_name for t in report.installed_tools):
                report.installed_tools.append(InstalledTool(name=tool_name))

    installed_names = {t.name for t in report.installed_tools}

    # Detect redundant tools
    report.redundant = _detect_redundant_tools(installed_names)
    for r in report.redundant:
        report.warnings.append(r.suggestion)

    # Detect config conflicts
    report.config_conflicts = _detect_config_conflicts(path)
    if report.config_conflicts:
        report.warnings.extend(report.config_conflicts)

    # Detect overlapping rules (tools with shared capabilities that are both present)
    for tool_name in installed_names:
        if tool_name not in TOOL_CAPABILITIES:
            continue
        tool_info = TOOL_CAPABILITIES[tool_name]
        for overlap in tool_info.get("overlaps_with", []):
            if overlap in installed_names and tool_name < overlap:
                overlap_msg = f"'{tool_name}' and '{overlap}' have overlapping rules"
                report.overlapping_rules.append(overlap_msg)

    # Build legacy conflicts list for print_report compatibility
    for r in report.redundant:
        report.conflicts.append(
            ToolConflict(
                tools=[r.replaces, r.tool],
                conflict_type="redundant",
                severity="warning",
                message=f"'{r.replaces}' can replace '{r.tool}'",
                suggestion=r.suggestion,
            )
        )

    # Generate suggestions (migration plan)
    if report.redundant:
        report.suggestions = generate_migration_plan(report.conflicts)

    return report


def suggest_migrations(path: Path) -> list[MigrationSuggestion]:
    """Suggest tool migrations for a repository."""
    report = detect_conflicts(path)
    suggestions: list[MigrationSuggestion] = []

    for conflict in report.conflicts:
        if conflict.conflict_type == "redundant" and len(conflict.tools) == 2:
            keeper = conflict.tools[0]
            removed = conflict.tools[1]
            suggestions.append(
                MigrationSuggestion(
                    source=removed,
                    target=keeper,
                    reason=conflict.message,
                    commands=[conflict.suggestion],
                )
            )

    # Also suggest ruff for flake8/black users even without explicit conflict
    configs = find_tool_configs(path)
    has_flake8 = "flake8" in configs or (path / ".flake8").exists()
    has_black = "black" in configs
    has_ruff = "ruff" in configs or (path / "ruff.toml").exists()

    if (has_flake8 or has_black) and not has_ruff:
        suggestions.append(
            MigrationSuggestion(
                source="flake8/black",
                target="ruff",
                reason="ruff replaces flake8 and black with a single fast tool",
                commands=["uv tool install ruff"],
            )
        )

    return suggestions


def generate_migration_config(path: Path, target: str) -> str:  # noqa: ARG001
    """Generate migration configuration for moving to a target tool."""
    if target == "ruff":
        # Parse existing flake8 config if present
        flake8_path = path / ".flake8"
        line_length = 88
        ignore: list[str] = []

        if flake8_path.exists() and tomli is not None:
            try:
                import configparser

                cfg = configparser.ConfigParser()
                cfg.read(str(flake8_path))
                if "flake8" in cfg:
                    if "max-line-length" in cfg["flake8"]:
                        line_length = int(cfg["flake8"]["max-line-length"])
                    if "extend-ignore" in cfg["flake8"]:
                        ignore = [
                            x.strip()
                            for x in cfg["flake8"]["extend-ignore"].split(",")
                            if x.strip()
                        ]
            except Exception:
                pass

        parts = [f'line-length = {line_length}', 'select = ["E", "F", "W", "I"]']
        if ignore:
            ignore_str = ", ".join(f'"{i}"' for i in ignore)
            parts.append(f"ignore = [{ignore_str}]")

        return "\n".join(parts)

    return ""


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

    return steps


def detect_tool_conflicts(
    path: Path,
    check_installed: bool = True,
) -> ConflictReport:
    """Detect conflicts between tools (alias for detect_conflicts)."""
    return detect_conflicts(path, check_installed=check_installed)


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


@app.default
def main(
    path: Path = Path(),
    /,
    *,
    _installed: bool = False,
    config: bool = False,
    _suggest: bool = False,
    migrate: bool = False,
    verbose: bool = False,
    output: str = "text",
) -> int:
    """Detect overlapping or redundant linters and suggest consolidation."""
    if not path.exists():
        print(f"Error: Path '{path}' does not exist", file=sys.stderr)
        return 1

    # Detect conflicts
    check_installed = not config
    report = detect_conflicts(path, check_installed=check_installed)

    # Show migration plan if requested
    if migrate and report.suggestions:
        for step in report.suggestions:
            print(step)
        return 0

    # Output
    if output == "json":
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
        print_report(report, verbose=verbose)

    return 1 if report.has_conflicts else 0


if __name__ == "__main__":
    app()
