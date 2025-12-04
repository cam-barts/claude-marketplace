#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "tomli>=2.0",
# ]
# ///
"""
Discover appropriate linters for a repository.

Features:
- Analyze repository file types
- Map file types to recommended linters
- Check which linters are already installed
- Prioritize Rust-based tools where available
- Generate installation commands
- Create baseline configuration files

Usage:
    uv run discover_linters.py [OPTIONS] [PATH]

Examples
--------
    uv run discover_linters.py
    uv run discover_linters.py --install
    uv run discover_linters.py --config
    uv run discover_linters.py --rust-first
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Linter recommendations by file type
LINTER_MAP: dict[str, list[dict[str, Any]]] = {
    ".py": [
        {
            "name": "ruff",
            "rust": True,
            "install": "uv tool install ruff",
            "description": "Fast Python linter+formatter (replaces flake8, isort)",
            "config_file": "ruff.toml",
        },
        {
            "name": "mypy",
            "rust": False,
            "install": "uv tool install mypy",
            "description": "Static type checker",
            "config_file": "mypy.ini",
        },
        {
            "name": "bandit",
            "rust": False,
            "install": "uv tool install bandit",
            "description": "Security linter",
            "config_file": ".bandit",
        },
    ],
    ".js": [
        {
            "name": "biome",
            "rust": True,
            "install": "npm install -D @biomejs/biome",
            "description": "Fast JS/TS linter + formatter (Rust)",
            "config_file": "biome.json",
        },
        {
            "name": "eslint",
            "rust": False,
            "install": "npm install -D eslint",
            "description": "Configurable JavaScript linter",
            "config_file": ".eslintrc.json",
        },
    ],
    ".ts": [
        {
            "name": "biome",
            "rust": True,
            "install": "npm install -D @biomejs/biome",
            "description": "Fast JS/TS linter + formatter (Rust)",
            "config_file": "biome.json",
        },
        {
            "name": "typescript",
            "rust": False,
            "install": "npm install -D typescript",
            "description": "TypeScript compiler with type checking",
            "config_file": "tsconfig.json",
        },
    ],
    ".md": [
        {
            "name": "markdownlint-cli2",
            "rust": False,
            "install": "npm install -D markdownlint-cli2",
            "description": "Markdown linting",
            "config_file": ".markdownlint.json",
        },
    ],
    ".json": [
        {
            "name": "biome",
            "rust": True,
            "install": "npm install -D @biomejs/biome",
            "description": "JSON formatter and linter",
            "config_file": "biome.json",
        },
    ],
    ".yaml": [
        {
            "name": "yamllint",
            "rust": False,
            "install": "uv tool install yamllint",
            "description": "YAML linter",
            "config_file": ".yamllint.yml",
        },
    ],
    ".yml": [
        {
            "name": "yamllint",
            "rust": False,
            "install": "uv tool install yamllint",
            "description": "YAML linter",
            "config_file": ".yamllint.yml",
        },
    ],
    ".sh": [
        {
            "name": "shellcheck",
            "rust": False,
            "install": "apt install shellcheck",
            "description": "Shell script linter",
            "config_file": ".shellcheckrc",
        },
    ],
    ".dockerfile": [
        {
            "name": "hadolint",
            "rust": False,
            "install": "apt install hadolint",
            "description": "Dockerfile linter",
            "config_file": ".hadolint.yaml",
        },
    ],
    ".go": [
        {
            "name": "golangci-lint",
            "rust": False,
            "install": "go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest",  # noqa: E501
            "description": "Go meta linter",
            "config_file": ".golangci.yml",
        },
    ],
    ".rs": [
        {
            "name": "clippy",
            "rust": True,
            "install": "rustup component add clippy",
            "description": "Rust linter (part of rustup)",
            "config_file": "clippy.toml",
        },
    ],
}


@dataclass
class FileStats:
    """Statistics about files in the repository."""

    extension: str
    count: int
    lines: int = 0


@dataclass
class LinterInfo:
    """Information about a linter."""

    name: str
    is_rust: bool
    install_command: str
    description: str
    config_file: str
    is_installed: bool = False
    file_types: list[str] = field(default_factory=list)


@dataclass
class DiscoveryReport:
    """Report of linter discovery."""

    file_stats: list[FileStats] = field(default_factory=list)
    recommended_linters: list[LinterInfo] = field(default_factory=list)
    installed_linters: list[str] = field(default_factory=list)
    existing_configs: list[str] = field(default_factory=list)


def count_files(path: Path) -> list[FileStats]:
    """Count files by extension in a directory."""
    counter: Counter[str] = Counter()
    line_counts: dict[str, int] = {}

    files = [path] if path.is_file() else list(path.rglob("*"))

    for file_path in files:
        # Skip hidden, cache, node_modules, venv
        if any(
            part.startswith(".")
            or part == "__pycache__"
            or part == "node_modules"
            or part in ("venv", ".venv", "env")
            for part in file_path.parts
        ):
            continue

        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext:
                counter[ext] += 1
                # Count lines for top extensions
                if counter[ext] <= 100:  # Limit line counting
                    try:
                        lines = len(file_path.read_text(encoding="utf-8").split("\n"))
                        line_counts[ext] = line_counts.get(ext, 0) + lines
                    except Exception:
                        pass

    # Special case for Dockerfile
    dockerfile_count = sum(
        1 for f in files if f.name.lower() in ("dockerfile", "dockerfile.dev")
    )
    if dockerfile_count:
        counter[".dockerfile"] = dockerfile_count

    return [
        FileStats(extension=ext, count=count, lines=line_counts.get(ext, 0))
        for ext, count in counter.most_common()
    ]


def check_linter_installed(name: str) -> bool:
    """Check if a linter is installed and available."""
    # Map tool names to commands
    command_map = {
        "ruff": "ruff",
        "mypy": "mypy",
        "bandit": "bandit",
        "biome": "biome",
        "eslint": "eslint",
        "typescript": "tsc",
        "markdownlint-cli2": "markdownlint-cli2",
        "yamllint": "yamllint",
        "shellcheck": "shellcheck",
        "hadolint": "hadolint",
        "golangci-lint": "golangci-lint",
        "clippy": "cargo-clippy",
    }

    command = command_map.get(name, name)

    # Check if command exists
    return shutil.which(command) is not None


def find_existing_configs(path: Path) -> list[str]:
    """Find existing linter configuration files."""
    config_patterns = [
        "ruff.toml",
        "pyproject.toml",
        ".ruff.toml",
        "mypy.ini",
        ".mypy.ini",
        ".bandit",
        "biome.json",
        ".eslintrc*",
        "eslint.config.*",
        "tsconfig.json",
        ".markdownlint*",
        ".yamllint*",
        ".shellcheckrc",
        ".hadolint.yaml",
        ".golangci.yml",
        ".pre-commit-config.yaml",
        "setup.cfg",
    ]

    found = []
    for pattern in config_patterns:
        matches = list(path.glob(pattern))
        for match in matches:
            found.append(str(match.relative_to(path)))

    return sorted(set(found))


def discover_linters(
    path: Path,
    rust_first: bool = True,
) -> DiscoveryReport:
    """Discover appropriate linters for a repository."""
    report = DiscoveryReport()

    # Count files
    report.file_stats = count_files(path)

    # Find existing configs
    report.existing_configs = find_existing_configs(path)

    # Determine recommended linters
    seen_linters: set[str] = set()

    for stats in report.file_stats:
        if stats.extension in LINTER_MAP:
            for linter_info in LINTER_MAP[stats.extension]:
                if linter_info["name"] not in seen_linters:
                    is_installed = check_linter_installed(linter_info["name"])

                    report.recommended_linters.append(
                        LinterInfo(
                            name=linter_info["name"],
                            is_rust=linter_info["rust"],
                            install_command=linter_info["install"],
                            description=linter_info["description"],
                            config_file=linter_info["config_file"],
                            is_installed=is_installed,
                            file_types=[stats.extension],
                        ),
                    )
                    seen_linters.add(linter_info["name"])

                    if is_installed:
                        report.installed_linters.append(linter_info["name"])
                else:
                    # Add file type to existing linter
                    for linter in report.recommended_linters:
                        if linter.name == linter_info["name"]:
                            if stats.extension not in linter.file_types:
                                linter.file_types.append(stats.extension)
                            break

    # Sort by Rust-first if requested
    if rust_first:
        report.recommended_linters.sort(key=lambda x: (not x.is_rust, x.name))

    return report


def generate_install_script(report: DiscoveryReport, rust_first: bool = True) -> str:
    """Generate a script to install missing linters."""
    lines = ["#!/bin/bash", "# Install missing linters", "set -e", ""]

    pip_installs = []
    npm_installs = []
    other_installs = []

    for linter in report.recommended_linters:
        if linter.is_installed:
            continue

        # Skip non-Rust alternatives if rust_first
        if rust_first and not linter.is_rust:
            # Check if there's a Rust alternative that handles same files
            rust_alt = any(
                x.is_rust
                and x.is_installed
                and set(x.file_types) & set(linter.file_types)
                for x in report.recommended_linters
            )
            if rust_alt:
                continue

        if linter.install_command.startswith("pip"):
            pip_installs.append(linter.name)
        elif linter.install_command.startswith("npm"):
            npm_installs.append(linter.install_command.split()[-1])
        else:
            other_installs.append((linter.name, linter.install_command))

    if pip_installs:
        lines.append("# Python linters")
        lines.append(f"uv tool install {' '.join(pip_installs)}")
        lines.append("")

    if npm_installs:
        lines.append("# JavaScript linters")
        lines.append(f"npm install -D {' '.join(npm_installs)}")
        lines.append("")

    for name, command in other_installs:
        lines.append(f"# {name}")
        lines.append(command)
        lines.append("")

    lines.append("echo 'Linter installation complete'")
    return "\n".join(lines)


def print_report(report: DiscoveryReport, verbose: bool = False) -> None:  # noqa: ARG001
    """Print the discovery report."""
    console.print(Panel("[bold]Linter Discovery Report[/bold]"))

    # File statistics
    if report.file_stats:
        console.print("\n[bold]File Types Found[/bold]")
        file_table = Table()
        file_table.add_column("Extension", style="cyan")
        file_table.add_column("Count", justify="right")
        file_table.add_column("Lines", justify="right")

        for stats in report.file_stats[:15]:
            file_table.add_row(
                stats.extension,
                str(stats.count),
                str(stats.lines) if stats.lines else "-",
            )

        console.print(file_table)

    # Existing configs
    if report.existing_configs:
        console.print("\n[bold]Existing Configurations[/bold]")
        for config in report.existing_configs:
            console.print(f"  [green]✓[/green] {config}")

    # Recommended linters
    if report.recommended_linters:
        console.print("\n[bold]Recommended Linters[/bold]")
        linter_table = Table()
        linter_table.add_column("Linter", style="cyan")
        linter_table.add_column("Status")
        linter_table.add_column("Type")
        linter_table.add_column("Description")

        for linter in report.recommended_linters:
            status = (
                "[green]✓ Installed[/green]"
                if linter.is_installed
                else "[yellow]Not installed[/yellow]"
            )
            linter_type = "[blue]Rust[/blue]" if linter.is_rust else "Other"
            linter_table.add_row(
                linter.name,
                status,
                linter_type,
                linter.description,
            )

        console.print(linter_table)

    # Installation summary
    not_installed = [
        linter for linter in report.recommended_linters if not linter.is_installed
    ]
    if not_installed:
        console.print("\n[bold yellow]Missing Linters[/bold yellow]")
        for linter in not_installed:
            console.print(f"  {linter.name}: [dim]{linter.install_command}[/dim]")


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
        "--install",
        action="store_true",
        help="Generate installation script",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Generate configuration files",
    )
    parser.add_argument(
        "--rust-first",
        action="store_true",
        default=True,
        help="Prioritize Rust-based tools (default: true)",
    )
    parser.add_argument(
        "--no-rust-first",
        action="store_false",
        dest="rust_first",
        help="Don't prioritize Rust-based tools",
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

    # Discover linters
    report = discover_linters(args.path, rust_first=args.rust_first)

    # Generate install script if requested
    if args.install:
        script = generate_install_script(report, rust_first=args.rust_first)
        print(script)
        return 0

    # Output
    if args.output == "json":
        result: dict[str, Any] = {
            "file_stats": [
                {"extension": s.extension, "count": s.count, "lines": s.lines}
                for s in report.file_stats
            ],
            "existing_configs": report.existing_configs,
            "recommended_linters": [
                {
                    "name": linter.name,
                    "is_rust": linter.is_rust,
                    "installed": linter.is_installed,
                    "install_command": linter.install_command,
                    "description": linter.description,
                    "file_types": linter.file_types,
                }
                for linter in report.recommended_linters
            ],
            "installed": report.installed_linters,
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(report, verbose=args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
