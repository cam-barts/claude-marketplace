#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "tomli>=2.0",
#     "packaging>=24.0",
# ]
# ///
"""
Analyze project dependencies.

Features:
- Parse requirements.txt, pyproject.toml, package.json
- Check for known vulnerabilities (via uv pip audit)
- Identify outdated dependencies
- Find unused dependencies
- Detect duplicate/conflicting versions
- Generate update plan

Usage:
    uv run dependency_analyzer.py [OPTIONS] [PATH]

Examples
--------
    uv run dependency_analyzer.py
    uv run dependency_analyzer.py --check-security
    uv run dependency_analyzer.py --check-outdated
    uv run dependency_analyzer.py --update-plan
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomli
except ImportError:
    tomli = None  # type: ignore

from packaging.requirements import Requirement
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class Dependency:
    """A project dependency."""

    name: str
    version_spec: str
    source_file: str
    is_dev: bool = False
    installed_version: str | None = None
    latest_version: str | None = None


@dataclass
class Vulnerability:
    """A security vulnerability."""

    package: str
    installed_version: str
    vulnerability_id: str
    description: str
    fix_version: str | None = None


@dataclass
class DependencyIssue:
    """An issue with a dependency."""

    package: str
    issue_type: str  # outdated, unused, conflict, vulnerable
    severity: str  # error, warning, info
    message: str
    fix: str | None = None


@dataclass
class DependencyReport:
    """Report of dependency analysis."""

    dependencies: list[Dependency] = field(default_factory=list)
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    issues: list[DependencyIssue] = field(default_factory=list)
    dev_dependencies: list[Dependency] = field(default_factory=list)

    @property
    def has_vulnerabilities(self) -> bool:
        return bool(self.vulnerabilities)

    @property
    def has_issues(self) -> bool:
        return any(i.severity == "error" for i in self.issues)


def parse_requirements_txt(path: Path) -> list[Dependency]:
    """Parse a requirements.txt file."""
    dependencies: list[Dependency] = []

    try:
        content = path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Skip editable installs
            if line.startswith("-e"):
                continue

            try:
                req = Requirement(line)
                version_spec = str(req.specifier) if req.specifier else "*"
                dependencies.append(
                    Dependency(
                        name=req.name,
                        version_spec=version_spec,
                        source_file=str(path),
                    ),
                )
            except Exception:
                # Try simple parsing
                match = re.match(r"^([a-zA-Z0-9_-]+)(.*)$", line)
                if match:
                    dependencies.append(
                        Dependency(
                            name=match.group(1),
                            version_spec=match.group(2).strip() or "*",
                            source_file=str(path),
                        ),
                    )

    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not parse {path}: {e}")

    return dependencies


def parse_pyproject_toml(path: Path) -> tuple[list[Dependency], list[Dependency]]:
    """Parse a pyproject.toml file."""
    dependencies: list[Dependency] = []
    dev_dependencies: list[Dependency] = []

    if tomli is None:
        return dependencies, dev_dependencies

    try:
        content = path.read_bytes()
        data = tomli.loads(content.decode("utf-8"))

        # Standard dependencies
        if "project" in data and "dependencies" in data["project"]:
            for dep in data["project"]["dependencies"]:
                try:
                    req = Requirement(dep)
                    version_spec = str(req.specifier) if req.specifier else "*"
                    dependencies.append(
                        Dependency(
                            name=req.name,
                            version_spec=version_spec,
                            source_file=str(path),
                        ),
                    )
                except Exception:
                    pass

        # Optional dependencies
        if "project" in data and "optional-dependencies" in data["project"]:
            for group, deps in data["project"]["optional-dependencies"].items():
                is_dev = group in ("dev", "test", "testing", "development")
                for dep in deps:
                    try:
                        req = Requirement(dep)
                        version_spec = str(req.specifier) if req.specifier else "*"
                        target = dev_dependencies if is_dev else dependencies
                        target.append(
                            Dependency(
                                name=req.name,
                                version_spec=version_spec,
                                source_file=str(path),
                                is_dev=is_dev,
                            ),
                        )
                    except Exception:
                        pass

        # Poetry format
        if "tool" in data and "poetry" in data["tool"]:
            poetry = data["tool"]["poetry"]

            if "dependencies" in poetry:
                for name, spec in poetry["dependencies"].items():
                    if name == "python":
                        continue
                    version_spec = (
                        spec if isinstance(spec, str) else spec.get("version", "*")
                    )
                    dependencies.append(
                        Dependency(
                            name=name,
                            version_spec=version_spec,
                            source_file=str(path),
                        ),
                    )

            if "dev-dependencies" in poetry:
                for name, spec in poetry["dev-dependencies"].items():
                    version_spec = (
                        spec if isinstance(spec, str) else spec.get("version", "*")
                    )
                    dev_dependencies.append(
                        Dependency(
                            name=name,
                            version_spec=version_spec,
                            source_file=str(path),
                            is_dev=True,
                        ),
                    )

    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not parse {path}: {e}")

    return dependencies, dev_dependencies


def parse_package_json(path: Path) -> tuple[list[Dependency], list[Dependency]]:
    """Parse a package.json file."""
    dependencies: list[Dependency] = []
    dev_dependencies: list[Dependency] = []

    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)

        if "dependencies" in data:
            for name, version in data["dependencies"].items():
                dependencies.append(
                    Dependency(
                        name=name,
                        version_spec=version,
                        source_file=str(path),
                    ),
                )

        if "devDependencies" in data:
            for name, version in data["devDependencies"].items():
                dev_dependencies.append(
                    Dependency(
                        name=name,
                        version_spec=version,
                        source_file=str(path),
                        is_dev=True,
                    ),
                )

    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not parse {path}: {e}")

    return dependencies, dev_dependencies


def check_uv_audit() -> list[Vulnerability]:
    """Run uv pip audit to check for vulnerabilities."""
    vulnerabilities: list[Vulnerability] = []

    try:
        result = subprocess.run(
            ["uv", "pip", "audit", "--format", "json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0 or result.stdout:
            data = json.loads(result.stdout)
            for vuln in data:
                vulnerabilities.append(
                    Vulnerability(
                        package=vuln.get("name", "unknown"),
                        installed_version=vuln.get("version", "unknown"),
                        vulnerability_id=vuln.get("id", "unknown"),
                        description=vuln.get("description", ""),
                        fix_version=vuln.get("fix_versions", [None])[0],
                    ),
                )
    except FileNotFoundError:
        console.print("[dim]uv not installed, skipping vulnerability check[/dim]")
    except subprocess.TimeoutExpired:
        console.print("[yellow]uv pip audit timed out[/yellow]")
    except Exception as e:
        console.print(f"[yellow]Could not run uv pip audit: {e}[/yellow]")

    return vulnerabilities


def check_outdated_uv() -> dict[str, tuple[str, str]]:
    """Check for outdated packages using uv."""
    outdated: dict[str, tuple[str, str]] = {}

    try:
        result = subprocess.run(
            ["uv", "pip", "list", "--outdated", "--format", "json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            for pkg in data:
                outdated[pkg["name"].lower()] = (pkg["version"], pkg["latest_version"])

    except Exception as e:
        console.print(f"[yellow]Could not check outdated packages: {e}[/yellow]")

    return outdated


def find_dependency_files(path: Path) -> list[Path]:
    """Find all dependency files in a project."""
    files: list[Path] = []

    # Python files
    for pattern in ["requirements*.txt", "pyproject.toml", "setup.py"]:
        files.extend(path.glob(pattern))
        # Also check in subdirectories
        files.extend(path.glob(f"*/{pattern}"))

    # JavaScript files
    files.extend(path.glob("package.json"))

    return files


def analyze_dependencies(
    path: Path,
    check_security: bool = False,
    check_outdated: bool = False,
) -> DependencyReport:
    """Analyze project dependencies."""
    report = DependencyReport()

    # Find and parse dependency files
    dep_files = find_dependency_files(path)

    for dep_file in dep_files:
        if dep_file.name.endswith(".txt"):
            deps = parse_requirements_txt(dep_file)
            report.dependencies.extend(deps)
        elif dep_file.name == "pyproject.toml":
            deps, dev_deps = parse_pyproject_toml(dep_file)
            report.dependencies.extend(deps)
            report.dev_dependencies.extend(dev_deps)
        elif dep_file.name == "package.json":
            deps, dev_deps = parse_package_json(dep_file)
            report.dependencies.extend(deps)
            report.dev_dependencies.extend(dev_deps)

    # Check for security vulnerabilities
    if check_security:
        report.vulnerabilities = check_uv_audit()
        for vuln in report.vulnerabilities:
            report.issues.append(
                DependencyIssue(
                    package=vuln.package,
                    issue_type="vulnerable",
                    severity="error",
                    message=f"Vuln {vuln.vulnerability_id}: {vuln.description[:80]}",
                    fix=f"Upgrade to {vuln.fix_version}" if vuln.fix_version else None,
                ),
            )

    # Check for outdated packages
    if check_outdated:
        outdated = check_outdated_uv()
        for dep in report.dependencies:
            key = dep.name.lower()
            if key in outdated:
                current, latest = outdated[key]
                dep.installed_version = current
                dep.latest_version = latest
                report.issues.append(
                    DependencyIssue(
                        package=dep.name,
                        issue_type="outdated",
                        severity="info",
                        message=f"Outdated: {current} → {latest}",
                        fix=f"uv add {dep.name}>={latest}",
                    ),
                )

    # Check for duplicates
    seen: dict[str, list[Dependency]] = {}
    for dep in report.dependencies:
        key = dep.name.lower()
        if key not in seen:
            seen[key] = []
        seen[key].append(dep)

    for name, deps in seen.items():
        if len(deps) > 1:
            specs = [d.version_spec for d in deps]
            if len(set(specs)) > 1:
                report.issues.append(
                    DependencyIssue(
                        package=name,
                        issue_type="conflict",
                        severity="warning",
                        message=f"Multiple version specs: {', '.join(specs)}",
                        fix="Consolidate to a single version specification",
                    ),
                )

    return report


def generate_update_plan(report: DependencyReport) -> list[str]:
    """Generate an update plan for dependencies."""
    lines = ["# Dependency Update Plan", ""]

    # Security fixes first
    security_updates = [
        i for i in report.issues if i.issue_type == "vulnerable" and i.fix
    ]
    if security_updates:
        lines.append("## Security Updates (URGENT)")
        for issue in security_updates:
            fix = issue.fix or ""
            lines.append(f"uv add '{issue.package}>={fix.split()[-1]}'")
        lines.append("")

    # Regular updates
    other_updates = [i for i in report.issues if i.issue_type == "outdated" and i.fix]
    if other_updates:
        lines.append("## Package Updates")
        for issue in other_updates:
            lines.append(f"# {issue.package}: {issue.message}")
            fix = issue.fix or ""
            lines.append(f"uv add '{fix.replace('uv add ', '')}'")
        lines.append("")

    return lines


def print_report(report: DependencyReport, verbose: bool = False) -> None:
    """Print the dependency report."""
    console.print(Panel("[bold]Dependency Analysis Report[/bold]"))

    # Summary
    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")

    summary_table.add_row("Dependencies", str(len(report.dependencies)))
    summary_table.add_row("Dev Dependencies", str(len(report.dev_dependencies)))
    summary_table.add_row(
        "Vulnerabilities",
        f"[red]{len(report.vulnerabilities)}[/red]" if report.vulnerabilities else "0",
    )
    summary_table.add_row(
        "Issues",
        f"[yellow]{len(report.issues)}[/yellow]" if report.issues else "0",
    )

    console.print(summary_table)

    # Vulnerabilities
    if report.vulnerabilities:
        console.print("\n[bold red]Security Vulnerabilities[/bold red]")
        for vuln in report.vulnerabilities:
            console.print(f"  {vuln.package} ({vuln.installed_version})")
            console.print(
                f"    [red]{vuln.vulnerability_id}[/red]: {vuln.description[:80]}"
            )
            if vuln.fix_version:
                console.print(f"    [green]Fix: upgrade to {vuln.fix_version}[/green]")

    # Other issues
    other_issues = [i for i in report.issues if i.issue_type != "vulnerable"]
    if other_issues:
        console.print("\n[bold yellow]Issues[/bold yellow]")
        for issue in other_issues[:20]:
            color = {"error": "red", "warning": "yellow", "info": "blue"}[
                issue.severity
            ]
            console.print(
                f"  [{color}]{issue.issue_type}[/{color}] "
                f"{issue.package}: {issue.message}"
            )

    # Dependencies list (verbose)
    if verbose and report.dependencies:
        console.print("\n[bold]Dependencies[/bold]")
        dep_table = Table()
        dep_table.add_column("Package", style="cyan")
        dep_table.add_column("Version Spec")
        dep_table.add_column("Installed")
        dep_table.add_column("Latest")

        for dep in report.dependencies[:30]:
            dep_table.add_row(
                dep.name,
                dep.version_spec,
                dep.installed_version or "-",
                dep.latest_version or "-",
            )

        console.print(dep_table)


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
        help="Project directory (default: current directory)",
    )
    parser.add_argument(
        "--check-security",
        action="store_true",
        help="Check for vulnerabilities (requires uv)",
    )
    parser.add_argument(
        "--check-outdated",
        action="store_true",
        help="Check for newer versions",
    )
    parser.add_argument(
        "--check-unused",
        action="store_true",
        help="Find unused dependencies (not implemented)",
    )
    parser.add_argument(
        "--update-plan",
        action="store_true",
        help="Generate safe update plan",
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

    # Analyze dependencies
    report = analyze_dependencies(
        args.path,
        check_security=args.check_security,
        check_outdated=args.check_outdated,
    )

    # Generate update plan if requested
    if args.update_plan:
        plan = generate_update_plan(report)
        for line in plan:
            print(line)
        return 0

    # Output
    if args.output == "json":
        result: dict[str, Any] = {
            "summary": {
                "dependencies": len(report.dependencies),
                "dev_dependencies": len(report.dev_dependencies),
                "vulnerabilities": len(report.vulnerabilities),
                "issues": len(report.issues),
            },
            "dependencies": [
                {
                    "name": d.name,
                    "version_spec": d.version_spec,
                    "source": d.source_file,
                    "is_dev": d.is_dev,
                    "installed": d.installed_version,
                    "latest": d.latest_version,
                }
                for d in report.dependencies
            ],
            "vulnerabilities": [
                {
                    "package": v.package,
                    "installed": v.installed_version,
                    "id": v.vulnerability_id,
                    "description": v.description,
                    "fix_version": v.fix_version,
                }
                for v in report.vulnerabilities
            ],
            "issues": [
                {
                    "package": i.package,
                    "type": i.issue_type,
                    "severity": i.severity,
                    "message": i.message,
                    "fix": i.fix,
                }
                for i in report.issues
            ],
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(report, verbose=args.verbose)

    return 1 if report.has_vulnerabilities else 0


if __name__ == "__main__":
    sys.exit(main())
