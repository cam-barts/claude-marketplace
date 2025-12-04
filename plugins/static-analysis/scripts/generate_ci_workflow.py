#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "pyyaml>=6.0",
#     "tomli>=2.0",
# ]
# ///
"""
Generate GitHub Actions CI/CD quality workflows.

Analyzes repository to detect:
- Python projects (pyproject.toml, requirements.txt)
- Quality tools (ruff, pytest, pre-commit, prek)
- Node.js projects (package.json, biome)
- MegaLinter configuration

Generates appropriate workflow with:
- Pre-commit/prek hooks
- Linting and formatting checks
- Test execution with coverage
- MegaLinter comprehensive analysis

Usage:
    uv run generate_ci_workflow.py [OPTIONS] PATH

Examples
--------
    uv run generate_ci_workflow.py .
    uv run generate_ci_workflow.py . --platform github
    uv run generate_ci_workflow.py . --matrix 3.11,3.12
    uv run generate_ci_workflow.py . --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


@dataclass
class RepoAnalysis:
    """Analysis results for a repository."""

    has_python: bool = False
    has_nodejs: bool = False
    has_ruff: bool = False
    has_pytest: bool = False
    has_precommit: bool = False
    has_prek: bool = False
    has_megalinter: bool = False
    has_biome: bool = False
    has_uv: bool = False
    python_versions: list[str] = field(default_factory=lambda: ["3.12"])
    package_manager: str = "uv"  # uv, pip, poetry


def analyze_repo(repo_path: Path) -> RepoAnalysis:
    """Analyze a repository to detect tools and configuration."""
    analysis = RepoAnalysis()

    # Check for Python project
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        analysis.has_python = True
        try:
            content = tomli.loads(pyproject.read_text())

            # Check for ruff
            if "tool" in content and "ruff" in content["tool"]:
                analysis.has_ruff = True

            # Check for pytest
            if "tool" in content and "pytest" in content["tool"]:
                analysis.has_pytest = True

            # Check for uv
            if "tool" in content and "uv" in content["tool"]:
                analysis.has_uv = True
                analysis.package_manager = "uv"

            # Check python version requirement
            if "project" in content:
                requires_python = content["project"].get("requires-python", "")
                if "3.13" in requires_python:
                    analysis.python_versions = ["3.13"]
                elif "3.12" in requires_python:
                    analysis.python_versions = ["3.12"]
                elif "3.11" in requires_python:
                    analysis.python_versions = ["3.11", "3.12"]

        except Exception:
            pass

    # Check for standalone ruff config
    if (repo_path / "ruff.toml").exists():
        analysis.has_ruff = True

    # Check for requirements.txt (indicates legacy pip-based project - recommend uv)
    if (repo_path / "requirements.txt").exists():
        analysis.has_python = True
        if not analysis.has_uv:
            analysis.package_manager = "pip"

    # Check for pytest.ini
    if (repo_path / "pytest.ini").exists():
        analysis.has_pytest = True

    # Check for pre-commit
    if (repo_path / ".pre-commit-config.yaml").exists():
        analysis.has_precommit = True

    # Check for prek
    if (repo_path / "prek.yaml").exists() or (repo_path / ".prek.yaml").exists():
        analysis.has_prek = True

    # Check for MegaLinter
    if (repo_path / ".mega-linter.yml").exists() or (
        repo_path / ".mega-linter.yaml"
    ).exists():
        analysis.has_megalinter = True

    # Check for Node.js
    if (repo_path / "package.json").exists():
        analysis.has_nodejs = True

    # Check for Biome
    if (repo_path / "biome.json").exists() or (repo_path / "biome.jsonc").exists():
        analysis.has_biome = True

    # Check for uv.lock (strong indicator of uv usage)
    if (repo_path / "uv.lock").exists():
        analysis.has_uv = True
        analysis.package_manager = "uv"

    return analysis


def generate_workflow(
    analysis: RepoAnalysis,
    python_matrix: list[str] | None = None,
    include_cache: bool = True,
    include_megalinter: bool = True,
) -> dict[str, Any]:
    """Generate a GitHub Actions workflow based on analysis."""
    workflow: dict[str, Any] = {
        "name": "Code Quality",
        "on": {
            "push": {"branches": ["main", "master", "develop"]},
            "pull_request": {"branches": ["main", "master", "develop"]},
        },
        "jobs": {},
    }

    # Pre-commit / prek job
    if analysis.has_prek or analysis.has_precommit:
        if analysis.has_prek:
            workflow["jobs"]["prek"] = {
                "name": "Pre-commit Hooks",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {
                        "name": "Run prek",
                        "uses": "j178/prek-action@v1",
                        "with": {"args": "run --all-files"},
                    },
                ],
            }
        else:
            workflow["jobs"]["pre-commit"] = {
                "name": "Pre-commit Hooks",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {
                        "uses": "actions/setup-python@v5",
                        "with": {"python-version": "3.12"},
                    },
                    {
                        "name": "Run pre-commit",
                        "uses": "pre-commit/action@v3.0.1",
                    },
                ],
            }

    # Python quality job
    if analysis.has_python:
        versions = python_matrix or analysis.python_versions
        use_matrix = len(versions) > 1

        python_job: dict[str, Any] = {
            "name": "Python Quality"
            + (" (${{ matrix.python-version }})" if use_matrix else ""),
            "runs-on": "ubuntu-latest",
            "steps": [{"uses": "actions/checkout@v4"}],
        }

        if use_matrix:
            python_job["strategy"] = {
                "matrix": {"python-version": versions},
                "fail-fast": False,
            }

        # Setup Python
        python_version = "${{ matrix.python-version }}" if use_matrix else versions[0]
        python_job["steps"].append(
            {
                "name": "Set up Python",
                "uses": "actions/setup-python@v5",
                "with": {"python-version": python_version},
            },
        )

        # Setup uv if used
        if analysis.has_uv or analysis.package_manager == "uv":
            python_job["steps"].append(
                {
                    "name": "Install uv",
                    "uses": "astral-sh/setup-uv@v4",
                },
            )

            # Add cache
            if include_cache:
                python_job["steps"].append(
                    {
                        "name": "Cache dependencies",
                        "uses": "actions/cache@v4",
                        "with": {
                            "path": "~/.cache/uv\n.venv",
                            "key": (
                                "${{ runner.os }}-uv-"
                                "${{ hashFiles('**/pyproject.toml', '**/uv.lock') }}"
                            ),
                            "restore-keys": "${{ runner.os }}-uv-",
                        },
                    },
                )

            # Install dependencies
            python_job["steps"].append(
                {
                    "name": "Install dependencies",
                    "run": "uv sync --all-extras --dev",
                },
            )

        # Ruff checks
        if analysis.has_ruff:
            python_job["steps"].append(
                {
                    "name": "Run ruff linter",
                    "run": "uvx ruff check ."
                    if analysis.has_uv
                    else "uv tool install ruff && ruff check .",
                },
            )
            python_job["steps"].append(
                {
                    "name": "Run ruff formatter",
                    "run": "uvx ruff format --check ."
                    if analysis.has_uv
                    else "ruff format --check .",
                },
            )

        workflow["jobs"]["python-quality"] = python_job

    # Test job
    if analysis.has_pytest:
        test_job: dict[str, Any] = {
            "name": "Tests",
            "runs-on": "ubuntu-latest",
            "steps": [
                {"uses": "actions/checkout@v4"},
                {
                    "name": "Set up Python",
                    "uses": "actions/setup-python@v5",
                    "with": {"python-version": "3.12"},
                },
            ],
        }

        if analysis.has_uv:
            test_job["steps"].extend(
                [
                    {"name": "Install uv", "uses": "astral-sh/setup-uv@v4"},
                    {
                        "name": "Install dependencies",
                        "run": "uv sync --all-extras --dev",
                    },
                    {
                        "name": "Run tests",
                        "run": "uv run pytest --cov --cov-report=xml",
                    },
                ],
            )
        else:
            test_job["steps"].extend(
                [
                    {"name": "Install uv", "uses": "astral-sh/setup-uv@v4"},
                    {"name": "Install dependencies", "run": "uv pip install -e .[dev]"},
                    {"name": "Run tests", "run": "pytest --cov --cov-report=xml"},
                ],
            )

        # Add coverage upload
        test_job["steps"].append(
            {
                "name": "Upload coverage",
                "uses": "codecov/codecov-action@v4",
                "with": {"file": "./coverage.xml", "fail_ci_if_error": False},
            },
        )

        workflow["jobs"]["test"] = test_job

    # Node.js quality job
    if analysis.has_nodejs:
        node_job: dict[str, Any] = {
            "name": "Node.js Quality",
            "runs-on": "ubuntu-latest",
            "steps": [
                {"uses": "actions/checkout@v4"},
                {
                    "name": "Set up Node.js",
                    "uses": "actions/setup-node@v4",
                    "with": {"node-version": "20", "cache": "npm"},
                },
                {"name": "Install dependencies", "run": "npm ci"},
            ],
        }

        if analysis.has_biome:
            node_job["steps"].append(
                {"name": "Run Biome", "run": "npx @biomejs/biome check ."}
            )
        else:
            node_job["steps"].append(
                {"name": "Run lint", "run": "npm run lint --if-present"}
            )

        workflow["jobs"]["node-quality"] = node_job

    # MegaLinter job
    if include_megalinter:
        megalinter_flavor = "python" if analysis.has_python else "all"
        workflow["jobs"]["megalinter"] = {
            "name": "MegaLinter",
            "runs-on": "ubuntu-latest",
            "steps": [
                {"uses": "actions/checkout@v4", "with": {"fetch-depth": 0}},
                {
                    "name": "MegaLinter",
                    "uses": f"oxsecurity/megalinter/flavors/{megalinter_flavor}@v8",
                    "env": {
                        "VALIDATE_ALL_CODEBASE": "${{ github.event_name == 'push' }}",
                        "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
                    },
                },
                {
                    "name": "Upload MegaLinter artifacts",
                    "if": "always()",
                    "uses": "actions/upload-artifact@v4",
                    "with": {
                        "name": "MegaLinter-reports",
                        "path": "megalinter-reports\nmega-linter.log",
                    },
                },
            ],
        }

    return workflow


def workflow_to_yaml(workflow: dict[str, Any]) -> str:
    """Convert workflow dict to YAML string."""

    # Custom representer for multiline strings
    def str_representer(dumper: yaml.Dumper, data: str) -> yaml.Node:
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    yaml.add_representer(str, str_representer)

    return yaml.dump(
        workflow, sort_keys=False, default_flow_style=False, allow_unicode=True
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Repository path to analyze")
    parser.add_argument(
        "--platform",
        choices=["github"],
        default="github",
        help="CI platform (default: github)",
    )
    parser.add_argument(
        "--matrix",
        type=str,
        help="Python versions for matrix (comma-separated, e.g., 3.11,3.12)",
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        default=True,
        help="Include caching configuration (default: True)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_false",
        dest="cache",
        help="Exclude caching configuration",
    )
    parser.add_argument(
        "--megalinter",
        action="store_true",
        default=True,
        help="Include MegaLinter job (default: True)",
    )
    parser.add_argument(
        "--no-megalinter",
        action="store_false",
        dest="megalinter",
        help="Exclude MegaLinter job",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path (default: .github/workflows/quality.yml)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without creating files"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format for results",
    )

    args = parser.parse_args()

    if not args.path.exists():
        console.print(
            f"[red]Error:[/red] Path '{args.path}' does not exist", file=sys.stderr
        )
        return 1

    # Analyze repository
    console.print(f"[bold]Analyzing repository:[/bold] {args.path}")
    analysis = analyze_repo(args.path)

    if args.verbose:
        table = Table(title="Detected Tools")
        table.add_column("Tool", style="cyan")
        table.add_column("Detected", style="green")
        table.add_row("Python", "Yes" if analysis.has_python else "No")
        table.add_row("Node.js", "Yes" if analysis.has_nodejs else "No")
        table.add_row("Ruff", "Yes" if analysis.has_ruff else "No")
        table.add_row("Pytest", "Yes" if analysis.has_pytest else "No")
        table.add_row("Pre-commit", "Yes" if analysis.has_precommit else "No")
        table.add_row("Prek", "Yes" if analysis.has_prek else "No")
        table.add_row("MegaLinter", "Yes" if analysis.has_megalinter else "No")
        table.add_row("Biome", "Yes" if analysis.has_biome else "No")
        table.add_row("uv", "Yes" if analysis.has_uv else "No")
        table.add_row("Package Manager", analysis.package_manager)
        console.print(table)

    # Parse matrix versions
    python_matrix = None
    if args.matrix:
        python_matrix = [v.strip() for v in args.matrix.split(",")]

    # Generate workflow
    workflow = generate_workflow(
        analysis,
        python_matrix=python_matrix,
        include_cache=args.cache,
        include_megalinter=args.megalinter,
    )

    workflow_yaml = workflow_to_yaml(workflow)

    # Determine output path
    output_path = args.output or (args.path / ".github" / "workflows" / "quality.yml")

    if args.dry_run:
        console.print(Panel(f"[bold blue]Would create:[/bold blue] {output_path}"))
        console.print(Syntax(workflow_yaml, "yaml", theme="monokai", line_numbers=True))
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(workflow_yaml, encoding="utf-8")
        console.print(f"[green]Created:[/green] {output_path}")

    if args.output_format == "json":
        result = {
            "success": True,
            "output_path": str(output_path),
            "analysis": {
                "has_python": analysis.has_python,
                "has_nodejs": analysis.has_nodejs,
                "has_ruff": analysis.has_ruff,
                "has_pytest": analysis.has_pytest,
                "package_manager": analysis.package_manager,
            },
            "jobs": list(workflow["jobs"].keys()),
        }
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
