#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
# ]
# ///
"""
Plan and analyze refactoring operations across a codebase.

Operations:
- find: Find all usages of a symbol
- rename: Plan renaming a symbol across files
- move: Plan moving code between modules

Features:
- Analyzes all references before changes
- Generates detailed impact reports
- Creates rollback instructions
- Validates safety before proceeding

Usage:
    uv run refactoring_planner.py OPERATION [OPTIONS] PATH

Examples
--------
    uv run refactoring_planner.py find MyClass src/
    uv run refactoring_planner.py rename old_name new_name src/
    uv run refactoring_planner.py rename old_name new_name src/ --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class Reference:
    """A reference to a symbol in code."""

    file_path: Path
    line_number: int
    column: int
    line_content: str
    ref_type: str  # definition, import, usage, string


@dataclass
class RefactoringPlan:
    """Plan for a refactoring operation."""

    operation: str
    old_name: str
    new_name: str | None
    references: list[Reference] = field(default_factory=list)
    files_affected: set[Path] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)
    risk_level: str = "LOW"

    @property
    def definitions(self) -> list[Reference]:
        return [r for r in self.references if r.ref_type == "definition"]

    @property
    def imports(self) -> list[Reference]:
        return [r for r in self.references if r.ref_type == "import"]

    @property
    def usages(self) -> list[Reference]:
        return [r for r in self.references if r.ref_type == "usage"]

    @property
    def string_refs(self) -> list[Reference]:
        return [r for r in self.references if r.ref_type == "string"]


def find_symbol_references(name: str, path: Path) -> list[Reference]:
    """Find all references to a symbol in Python files."""
    references: list[Reference] = []

    files = [path] if path.is_file() else list(path.rglob("*.py"))

    # Patterns for different reference types
    patterns = {
        # Function/class definition
        "definition": re.compile(
            rf"^\s*(async\s+)?(def|class)\s+{re.escape(name)}\s*[\(:]",
            re.MULTILINE,
        ),
        # Import statement
        "import": re.compile(
            rf"^\s*(from\s+\S+\s+)?import\s+.*\b{re.escape(name)}\b",
            re.MULTILINE,
        ),
        # General usage (word boundary)
        "usage": re.compile(rf"\b{re.escape(name)}\b"),
        # String reference (potential dynamic access)
        "string": re.compile(rf'["\']({re.escape(name)})["\']'),
    }

    for file_path in files:
        # Skip hidden and cache directories
        if any(
            part.startswith(".") or part == "__pycache__" for part in file_path.parts
        ):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                # Check for definition
                if patterns["definition"].search(line):
                    match = patterns["usage"].search(line)
                    if match:
                        references.append(
                            Reference(
                                file_path=file_path,
                                line_number=line_num,
                                column=match.start(),
                                line_content=line.strip(),
                                ref_type="definition",
                            ),
                        )
                    continue

                # Check for import
                if patterns["import"].search(line):
                    match = patterns["usage"].search(line)
                    if match:
                        references.append(
                            Reference(
                                file_path=file_path,
                                line_number=line_num,
                                column=match.start(),
                                line_content=line.strip(),
                                ref_type="import",
                            ),
                        )
                    continue

                # Check for string reference
                string_match = patterns["string"].search(line)
                if string_match:
                    references.append(
                        Reference(
                            file_path=file_path,
                            line_number=line_num,
                            column=string_match.start(),
                            line_content=line.strip(),
                            ref_type="string",
                        ),
                    )
                    # Don't continue - might also be a usage

                # Check for general usage
                for match in patterns["usage"].finditer(line):
                    # Skip if it's part of a larger word or in a comment
                    if line.strip().startswith("#"):
                        continue

                    # Check if already captured as definition or import
                    existing = any(
                        r.file_path == file_path
                        and r.line_number == line_num
                        and r.ref_type in ("definition", "import")
                        for r in references
                    )
                    if existing:
                        continue

                    references.append(
                        Reference(
                            file_path=file_path,
                            line_number=line_num,
                            column=match.start(),
                            line_content=line.strip(),
                            ref_type="usage",
                        ),
                    )
                    break  # One usage per line is enough

        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not read {file_path}: {e}")

    return references


def create_rename_plan(
    old_name: str,
    new_name: str,
    path: Path,
) -> RefactoringPlan:
    """Create a plan for renaming a symbol."""
    references = find_symbol_references(old_name, path)

    plan = RefactoringPlan(
        operation="rename",
        old_name=old_name,
        new_name=new_name,
        references=references,
        files_affected={r.file_path for r in references},
    )

    # Check for potential issues
    if not plan.definitions:
        plan.warnings.append(f"No definition found for '{old_name}'")
        plan.risk_level = "MEDIUM"

    if plan.string_refs:
        plan.warnings.append(
            f"Found {len(plan.string_refs)} string references - may need manual update",
        )
        plan.risk_level = "MEDIUM"

    # Check if new name already exists
    existing = find_symbol_references(new_name, path)
    if existing:
        plan.warnings.append(f"'{new_name}' already exists in codebase")
        plan.risk_level = "HIGH"

    # Check for dynamic access patterns
    dynamic_patterns = ["getattr", "setattr", "hasattr", "__getattribute__"]
    for ref in references:
        if any(p in ref.line_content for p in dynamic_patterns):
            plan.warnings.append(
                f"Dynamic access detected at {ref.file_path}:{ref.line_number}",
            )
            plan.risk_level = "HIGH"

    return plan


def generate_rollback_script(plan: RefactoringPlan) -> str:
    """Generate a shell script to rollback changes."""
    lines = [
        "#!/bin/bash",
        f"# Rollback: {plan.operation} {plan.old_name} -> {plan.new_name}",
        f"# Files affected: {len(plan.files_affected)}",
        "",
        "# Restore files from git",
    ]

    for file_path in sorted(plan.files_affected):
        lines.append(f"git checkout HEAD -- {file_path}")

    lines.append("")
    lines.append("echo 'Rollback complete'")

    return "\n".join(lines)


def apply_rename(plan: RefactoringPlan, dry_run: bool = True) -> dict[Path, str]:
    """Apply rename changes to files."""
    changes: dict[Path, str] = {}

    for file_path in plan.files_affected:
        try:
            content = file_path.read_text(encoding="utf-8")

            # Replace the symbol
            # Use word boundary to avoid partial matches
            pattern = re.compile(rf"\b{re.escape(plan.old_name)}\b")
            new_content = pattern.sub(plan.new_name or "", content)

            if new_content != content:
                changes[file_path] = new_content

                if not dry_run:
                    file_path.write_text(new_content, encoding="utf-8")

        except Exception as e:
            console.print(f"[red]Error processing {file_path}:[/red] {e}")

    return changes


def print_find_results(references: list[Reference], name: str) -> None:
    """Print symbol search results."""
    console.print(Panel(f"[bold]References to '{name}'[/bold]"))

    if not references:
        console.print("[yellow]No references found[/yellow]")
        return

    # Group by type
    by_type: dict[str, list[Reference]] = {}
    for ref in references:
        if ref.ref_type not in by_type:
            by_type[ref.ref_type] = []
        by_type[ref.ref_type].append(ref)

    # Print definitions first
    if "definition" in by_type:
        console.print("\n[bold green]Definitions[/bold green]")
        for ref in by_type["definition"]:
            console.print(f"  {ref.file_path}:{ref.line_number}")
            console.print(f"    [dim]{ref.line_content}[/dim]")

    # Then imports
    if "import" in by_type:
        console.print("\n[bold blue]Imports[/bold blue]")
        for ref in by_type["import"]:
            console.print(f"  {ref.file_path}:{ref.line_number}")
            console.print(f"    [dim]{ref.line_content}[/dim]")

    # Then usages
    if "usage" in by_type:
        console.print(f"\n[bold cyan]Usages ({len(by_type['usage'])})[/bold cyan]")
        for ref in by_type["usage"][:20]:
            console.print(f"  {ref.file_path}:{ref.line_number}")
            console.print(f"    [dim]{ref.line_content[:80]}[/dim]")

        if len(by_type["usage"]) > 20:
            console.print(f"  ... and {len(by_type['usage']) - 20} more usages")

    # String references (warnings)
    if "string" in by_type:
        console.print(
            f"\n[bold yellow]String References ({len(by_type['string'])})[/bold yellow]"
        )
        console.print("  [yellow]These may need manual review[/yellow]")
        for ref in by_type["string"][:5]:
            console.print(f"  {ref.file_path}:{ref.line_number}")
            console.print(f"    [dim]{ref.line_content}[/dim]")

    # Summary
    file_count = len({r.file_path for r in references})
    console.print(
        f"\n[bold]Total: {len(references)} references in {file_count} files[/bold]"
    )


def print_rename_plan(plan: RefactoringPlan, show_changes: bool = False) -> None:
    """Print rename plan details."""
    console.print(Panel(f"[bold]Rename Plan: {plan.old_name} → {plan.new_name}[/bold]"))

    # Summary
    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Files Affected", str(len(plan.files_affected)))
    summary_table.add_row("Definitions", str(len(plan.definitions)))
    summary_table.add_row("Imports", str(len(plan.imports)))
    summary_table.add_row("Usages", str(len(plan.usages)))
    summary_table.add_row("String Refs", str(len(plan.string_refs)))

    risk_color = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red"}[plan.risk_level]
    summary_table.add_row(
        "Risk Level", f"[{risk_color}]{plan.risk_level}[/{risk_color}]"
    )

    console.print(summary_table)

    # Warnings
    if plan.warnings:
        console.print("\n[bold yellow]Warnings[/bold yellow]")
        for warning in plan.warnings:
            console.print(f"  ⚠ {warning}")

    # Files to modify
    console.print("\n[bold]Files to Modify[/bold]")
    for file_path in sorted(plan.files_affected):
        refs_in_file = [r for r in plan.references if r.file_path == file_path]
        console.print(f"  {file_path} ({len(refs_in_file)} changes)")

    # Show specific changes if requested
    if show_changes:
        console.print("\n[bold]Changes[/bold]")
        for ref in plan.references[:30]:
            new_line = ref.line_content.replace(
                plan.old_name, f"[green]{plan.new_name}[/green]"
            )
            console.print(f"  {ref.file_path}:{ref.line_number}")
            console.print(f"    [red]-[/red] {ref.line_content[:80]}")
            console.print(f"    [green]+[/green] {new_line[:80]}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="operation", required=True)

    # Find command
    find_parser = subparsers.add_parser("find", help="Find all references to a symbol")
    find_parser.add_argument("name", help="Symbol name to find")
    find_parser.add_argument("path", type=Path, help="Directory to search")

    # Rename command
    rename_parser = subparsers.add_parser("rename", help="Plan renaming a symbol")
    rename_parser.add_argument("old_name", help="Current symbol name")
    rename_parser.add_argument("new_name", help="New symbol name")
    rename_parser.add_argument("path", type=Path, help="Directory to search")
    rename_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show plan without making changes",
    )
    rename_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the changes (default is dry-run)",
    )
    rename_parser.add_argument(
        "--rollback",
        action="store_true",
        help="Generate rollback script",
    )
    rename_parser.add_argument(
        "--show-changes",
        action="store_true",
        help="Show detailed line changes",
    )

    # Common arguments
    for p in [find_parser, rename_parser]:
        p.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
        p.add_argument(
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

    if args.operation == "find":
        references = find_symbol_references(args.name, args.path)

        if args.output == "json":
            result: dict[str, Any] = {
                "symbol": args.name,
                "references": [
                    {
                        "file": str(r.file_path),
                        "line": r.line_number,
                        "column": r.column,
                        "type": r.ref_type,
                        "content": r.line_content,
                    }
                    for r in references
                ],
                "total": len(references),
                "files": len({r.file_path for r in references}),
            }
            print(json.dumps(result, indent=2))
        else:
            print_find_results(references, args.name)

    elif args.operation == "rename":
        plan = create_rename_plan(args.old_name, args.new_name, args.path)

        if args.output == "json":
            rename_result: dict[str, Any] = {
                "operation": "rename",
                "old_name": plan.old_name,
                "new_name": plan.new_name,
                "files_affected": [str(f) for f in plan.files_affected],
                "references": [
                    {
                        "file": str(r.file_path),
                        "line": r.line_number,
                        "type": r.ref_type,
                    }
                    for r in plan.references
                ],
                "warnings": plan.warnings,
                "risk_level": plan.risk_level,
            }
            print(json.dumps(rename_result, indent=2))

        elif args.rollback:
            print(generate_rollback_script(plan))

        else:
            print_rename_plan(plan, args.show_changes)

            if args.apply and plan.risk_level != "HIGH":
                console.print("\n[bold]Applying changes...[/bold]")
                changes = apply_rename(plan, dry_run=False)
                console.print(f"[green]Modified {len(changes)} files[/green]")
            elif args.apply and plan.risk_level == "HIGH":
                console.print(
                    "\n[red]Cannot apply: Risk level is HIGH. Fix warnings first.[/red]"
                )
                return 1
            else:
                console.print(
                    "\n[dim]Use --apply for changes, --rollback for rollback[/dim]"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
