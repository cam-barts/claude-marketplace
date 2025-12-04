#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "semver>=3.0",
# ]
# ///
"""
Validate and assist with changelog maintenance.

Features:
- Validate Keep a Changelog format
- Check version ordering
- Detect missing release dates
- Suggest entries based on git commits
- Validate semver compliance

Usage:
    uv run changelog_validator.py [OPTIONS] [CHANGELOG]

Examples
--------
    uv run changelog_validator.py
    uv run changelog_validator.py CHANGELOG.md
    uv run changelog_validator.py --suggest
    uv run changelog_validator.py --since v1.0.0
    uv run changelog_validator.py --fix
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import semver
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Keep a Changelog format patterns
VERSION_HEADER_PATTERN = re.compile(
    r"^##\s+\[?(\d+\.\d+\.\d+(?:-[\w.]+)?(?:\+[\w.]+)?|Unreleased)\]?"
    r"(?:\s*[-–]\s*(\d{4}-\d{2}-\d{2}))?\s*$",
    re.IGNORECASE,
)

SECTION_PATTERN = re.compile(
    r"^###\s+(Added|Changed|Deprecated|Removed|Fixed|Security)\s*$",
    re.IGNORECASE,
)

VALID_SECTIONS = {"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"}


@dataclass
class ChangelogEntry:
    """A single entry in a changelog section."""

    text: str
    line_number: int


@dataclass
class ChangelogSection:
    """A section within a version (Added, Changed, etc.)."""

    name: str
    entries: list[ChangelogEntry] = field(default_factory=list)


@dataclass
class ChangelogVersion:
    """A version entry in the changelog."""

    version: str
    date: str | None
    line_number: int
    sections: dict[str, ChangelogSection] = field(default_factory=dict)
    is_unreleased: bool = False


@dataclass
class ValidationIssue:
    """A validation issue found in the changelog."""

    line_number: int
    severity: str  # error, warning, info
    message: str


@dataclass
class ChangelogReport:
    """Report of changelog validation."""

    versions: list[ChangelogVersion] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    has_unreleased: bool = False

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)


def parse_changelog(path: Path) -> tuple[ChangelogReport, str]:
    """Parse a changelog file and extract versions and sections."""
    report = ChangelogReport()

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        report.issues.append(
            ValidationIssue(0, "error", f"Could not read file: {e}"),
        )
        return report, ""

    lines = content.split("\n")
    current_version: ChangelogVersion | None = None
    current_section: str | None = None

    for i, line in enumerate(lines, 1):
        # Check for version header
        version_match = VERSION_HEADER_PATTERN.match(line)
        if version_match:
            version_str = version_match.group(1)
            date_str = version_match.group(2)

            is_unreleased = version_str.lower() == "unreleased"
            if is_unreleased:
                report.has_unreleased = True

            current_version = ChangelogVersion(
                version=version_str,
                date=date_str,
                line_number=i,
                is_unreleased=is_unreleased,
            )
            report.versions.append(current_version)
            current_section = None
            continue

        # Check for section header
        section_match = SECTION_PATTERN.match(line)
        if section_match and current_version:
            section_name = section_match.group(1).title()
            current_section = section_name
            if section_name not in current_version.sections:
                current_version.sections[section_name] = ChangelogSection(
                    name=section_name,
                )
            continue

        # Check for list entries
        if current_version and current_section and line.strip().startswith("-"):
            entry_text = line.strip()[1:].strip()
            if entry_text:
                current_version.sections[current_section].entries.append(
                    ChangelogEntry(text=entry_text, line_number=i),
                )

    return report, content


def validate_changelog(report: ChangelogReport) -> None:
    """Validate the parsed changelog and add issues."""
    # Check for presence of versions
    if not report.versions:
        report.issues.append(
            ValidationIssue(0, "error", "No version entries found in changelog"),
        )
        return

    # Check Unreleased section exists
    if not report.has_unreleased:
        report.issues.append(
            ValidationIssue(0, "warning", "No [Unreleased] section found"),
        )

    # Validate each version
    previous_version: str | None = None
    for version in report.versions:
        # Skip unreleased
        if version.is_unreleased:
            if version.date:
                report.issues.append(
                    ValidationIssue(
                        version.line_number,
                        "warning",
                        "Unreleased section should not have a date",
                    ),
                )
            continue

        # Validate semver format
        try:
            parsed = semver.Version.parse(version.version)
        except ValueError:
            report.issues.append(
                ValidationIssue(
                    version.line_number,
                    "error",
                    f"Invalid semver: {version.version}",
                ),
            )
            continue

        # Check date presence
        if not version.date:
            report.issues.append(
                ValidationIssue(
                    version.line_number,
                    "error",
                    f"Version {version.version} is missing release date",
                ),
            )
        else:
            # Validate date format
            try:
                datetime.strptime(version.date, "%Y-%m-%d")
            except ValueError:
                report.issues.append(
                    ValidationIssue(
                        version.line_number,
                        "error",
                        f"Invalid date format: {version.date} (expected YYYY-MM-DD)",
                    ),
                )

        # Check version ordering (should be descending)
        if previous_version:
            try:
                prev_parsed = semver.Version.parse(previous_version)
                if parsed >= prev_parsed:
                    report.issues.append(
                        ValidationIssue(
                            version.line_number,
                            "error",
                            f"Version {version.version} should come "
                            f"after {previous_version}",
                        ),
                    )
            except ValueError:
                pass

        previous_version = version.version

        # Check for empty sections
        if not version.sections:
            report.issues.append(
                ValidationIssue(
                    version.line_number,
                    "warning",
                    f"Version {version.version} has no changes listed",
                ),
            )


def get_git_commits(since_tag: str | None = None) -> list[dict[str, str]]:
    """Get git commits since a tag or recent commits."""
    try:
        if since_tag:
            cmd = [
                "git",
                "log",
                f"{since_tag}..HEAD",
                "--pretty=format:%H|%s|%an",
            ]
        else:
            cmd = ["git", "log", "-20", "--pretty=format:%H|%s|%an"]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        commits = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|", 2)
                if len(parts) >= 2:
                    commits.append(
                        {
                            "hash": parts[0][:8],
                            "message": parts[1],
                            "author": parts[2] if len(parts) > 2 else "",
                        },
                    )
        return commits

    except subprocess.CalledProcessError:
        return []
    except FileNotFoundError:
        return []


def suggest_changelog_entries(commits: list[dict[str, str]]) -> dict[str, list[str]]:
    """Suggest changelog entries from commit messages."""
    suggestions: dict[str, list[str]] = {
        "Added": [],
        "Changed": [],
        "Fixed": [],
        "Removed": [],
    }

    # Keywords that suggest categories
    add_keywords = ["add", "new", "create", "implement", "introduce"]
    fix_keywords = ["fix", "bug", "patch", "resolve", "correct"]
    change_keywords = ["update", "change", "modify", "refactor", "improve"]
    remove_keywords = ["remove", "delete", "drop", "deprecate"]

    for commit in commits:
        msg = commit["message"].lower()
        entry = commit["message"]

        # Try to categorize
        if any(kw in msg for kw in fix_keywords):
            suggestions["Fixed"].append(entry)
        elif any(kw in msg for kw in add_keywords):
            suggestions["Added"].append(entry)
        elif any(kw in msg for kw in remove_keywords):
            suggestions["Removed"].append(entry)
        elif any(kw in msg for kw in change_keywords):
            suggestions["Changed"].append(entry)
        else:
            suggestions["Changed"].append(entry)

    # Remove empty categories
    return {k: v for k, v in suggestions.items() if v}


def print_report(
    report: ChangelogReport,
    suggestions: dict[str, list[str]] | None = None,
    verbose: bool = False,
) -> None:
    """Print the validation report."""
    console.print(Panel("[bold]Changelog Validation Report[/bold]"))

    # Summary
    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Versions", str(len(report.versions)))
    summary_table.add_row(
        "Has Unreleased",
        "[green]Yes[/green]" if report.has_unreleased else "[yellow]No[/yellow]",
    )

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

    # Versions
    if verbose and report.versions:
        console.print("\n[bold]Versions[/bold]")
        for v in report.versions[:10]:
            date_str = v.date or "(no date)"
            sections = ", ".join(v.sections.keys()) or "(empty)"
            console.print(f"  {v.version} - {date_str}")
            console.print(f"    [dim]Sections: {sections}[/dim]")

    # Issues
    if report.issues:
        console.print("\n[bold]Issues[/bold]")
        for issue in report.issues:
            color = {"error": "red", "warning": "yellow", "info": "blue"}[
                issue.severity
            ]
            line_info = f"Line {issue.line_number}: " if issue.line_number else ""
            console.print(
                f"  [{color}]{issue.severity.upper()}[/{color}] "
                f"{line_info}{issue.message}"
            )

    # Suggestions
    if suggestions:
        console.print("\n[bold blue]Suggested Entries[/bold blue]")
        for section, entries in suggestions.items():
            console.print(f"\n### {section}")
            for entry in entries[:5]:
                console.print(f"  - {entry}")
            if len(entries) > 5:
                console.print(f"  ... and {len(entries) - 5} more")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "changelog",
        type=Path,
        nargs="?",
        default=Path("CHANGELOG.md"),
        help="Changelog file (default: CHANGELOG.md)",
    )
    parser.add_argument(
        "--format",
        choices=["keepachangelog", "conventional"],
        default="keepachangelog",
        help="Changelog format (default: keepachangelog)",
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Suggest entries from recent commits",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Only consider commits since this tag",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix formatting issues (not yet implemented)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    if not args.changelog.exists():
        console.print(
            f"[red]Error:[/red] Changelog '{args.changelog}' does not exist",
            file=sys.stderr,
        )
        return 1

    # Parse and validate
    report, _content = parse_changelog(args.changelog)
    validate_changelog(report)

    # Get suggestions if requested
    suggestions = None
    if args.suggest:
        commits = get_git_commits(args.since)
        if commits:
            suggestions = suggest_changelog_entries(commits)
        else:
            console.print("[yellow]No commits found for suggestions[/yellow]")

    # Output results
    if args.output == "json":
        result: dict[str, Any] = {
            "file": str(args.changelog),
            "summary": {
                "versions": len(report.versions),
                "has_unreleased": report.has_unreleased,
                "errors": len([i for i in report.issues if i.severity == "error"]),
                "warnings": len([i for i in report.issues if i.severity == "warning"]),
            },
            "versions": [
                {
                    "version": v.version,
                    "date": v.date,
                    "line": v.line_number,
                    "sections": list(v.sections.keys()),
                }
                for v in report.versions
            ],
            "issues": [
                {
                    "line": i.line_number,
                    "severity": i.severity,
                    "message": i.message,
                }
                for i in report.issues
            ],
        }
        if suggestions:
            result["suggestions"] = suggestions

        print(json.dumps(result, indent=2))
    else:
        print_report(report, suggestions, verbose=args.verbose)

    return 1 if report.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
