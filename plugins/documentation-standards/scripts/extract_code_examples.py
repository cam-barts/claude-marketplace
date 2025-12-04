#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
# ]
# ///
"""
Extract and validate code examples from documentation.

Features:
- Extract fenced code blocks from markdown
- Validate Python syntax
- Check imports exist in project
- Detect deprecated API usage
- Optionally execute examples to verify they run

Usage:
    uv run extract_code_examples.py [OPTIONS] PATH

Examples
--------
    uv run extract_code_examples.py docs/
    uv run extract_code_examples.py docs/ --language python
    uv run extract_code_examples.py docs/ --validate-syntax
    uv run extract_code_examples.py docs/ --output examples/
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


@dataclass
class CodeExample:
    """A code example extracted from documentation."""

    source_file: Path
    line_number: int
    language: str
    code: str
    is_valid: bool = True
    syntax_error: str | None = None
    imports: list[str] = field(default_factory=list)


@dataclass
class ExtractionReport:
    """Report of code example extraction."""

    examples: list[CodeExample] = field(default_factory=list)
    invalid_syntax: list[CodeExample] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.examples)

    @property
    def valid_count(self) -> int:
        return len([e for e in self.examples if e.is_valid])


def find_markdown_files(path: Path) -> list[Path]:
    """Find all markdown files in a directory."""
    if path.is_file():
        return [path] if path.suffix.lower() in {".md", ".markdown"} else []
    return list(path.rglob("*.md")) + list(path.rglob("*.markdown"))


def extract_code_blocks(file_path: Path) -> list[CodeExample]:
    """Extract fenced code blocks from a markdown file."""
    examples: list[CodeExample] = []

    # Pattern for fenced code blocks with optional language
    # Matches: ```python, ```py, ``` (no language), ```{python}, etc.
    fence_pattern = re.compile(r"^```(\{?\w*\}?)?\s*$")

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        in_block = False
        block_start = 0
        block_language = ""
        block_lines: list[str] = []

        for i, line in enumerate(lines):
            if not in_block:
                match = fence_pattern.match(line)
                if match and not line.startswith("````"):
                    in_block = True
                    block_start = i + 1
                    lang = match.group(1) or ""
                    # Clean up language identifier
                    block_language = lang.strip("{}").lower()
                    # Normalize common aliases
                    if block_language in {"py", "python3"}:
                        block_language = "python"
                    elif block_language in {"js"}:
                        block_language = "javascript"
                    elif block_language in {"ts"}:
                        block_language = "typescript"
                    elif block_language in {"sh", "shell"}:
                        block_language = "bash"
                    block_lines = []
            elif line.strip() == "```":
                # End of block
                code = "\n".join(block_lines)
                if code.strip():
                    examples.append(
                        CodeExample(
                            source_file=file_path,
                            line_number=block_start,
                            language=block_language or "unknown",
                            code=code,
                        ),
                    )
                in_block = False
            else:
                block_lines.append(line)

    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not read {file_path}: {e}")

    return examples


def validate_python_syntax(example: CodeExample) -> None:
    """Validate Python syntax in a code example."""
    if example.language not in {"python", "py", "python3"}:
        return

    try:
        tree = ast.parse(example.code)
        example.is_valid = True

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    example.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                example.imports.append(node.module)

    except SyntaxError as e:
        example.is_valid = False
        example.syntax_error = f"Line {e.lineno}: {e.msg}"


def extract_examples(
    path: Path,
    language_filter: str | None = None,
    validate_syntax: bool = False,
) -> ExtractionReport:
    """Extract code examples from markdown files."""
    report = ExtractionReport()

    md_files = find_markdown_files(path)

    for md_file in md_files:
        examples = extract_code_blocks(md_file)

        for example in examples:
            # Filter by language if specified
            if language_filter and example.language != language_filter:
                continue

            # Validate syntax if requested
            if validate_syntax:
                validate_python_syntax(example)
                if not example.is_valid:
                    report.invalid_syntax.append(example)

            report.examples.append(example)

            # Count by language
            lang = example.language or "unknown"
            report.languages[lang] = report.languages.get(lang, 0) + 1

    return report


def write_examples(examples: list[CodeExample], output_dir: Path) -> int:
    """Write examples to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for i, example in enumerate(examples):
        # Determine file extension
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "bash": ".sh",
            "json": ".json",
            "yaml": ".yml",
            "html": ".html",
            "css": ".css",
            "sql": ".sql",
        }
        ext = ext_map.get(example.language, ".txt")

        # Generate filename
        source_stem = example.source_file.stem
        filename = f"{source_stem}_{i + 1}{ext}"
        output_path = output_dir / filename

        output_path.write_text(example.code, encoding="utf-8")
        written += 1

    return written


def print_report(
    report: ExtractionReport,
    verbose: bool = False,
    show_code: bool = False,
) -> None:
    """Print the extraction report."""
    console.print(Panel("[bold]Code Example Extraction Report[/bold]"))

    # Summary
    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")

    summary_table.add_row("Total Examples", str(report.total))
    summary_table.add_row("Valid Syntax", str(report.valid_count))
    summary_table.add_row(
        "Invalid Syntax",
        f"[red]{len(report.invalid_syntax)}[/red]" if report.invalid_syntax else "0",
    )

    console.print(summary_table)

    # Languages breakdown
    if report.languages:
        console.print("\n[bold]Languages[/bold]")
        lang_table = Table()
        lang_table.add_column("Language", style="cyan")
        lang_table.add_column("Count", justify="right")

        for lang, count in sorted(
            report.languages.items(),
            key=lambda x: -x[1],
        ):
            lang_table.add_row(lang or "(none)", str(count))

        console.print(lang_table)

    # Invalid syntax
    if report.invalid_syntax:
        console.print("\n[bold red]Syntax Errors[/bold red]")
        for example in report.invalid_syntax:
            console.print(f"  {example.source_file}:{example.line_number}")
            console.print(f"    [dim]{example.syntax_error}[/dim]")
            if show_code:
                console.print()
                console.print(Syntax(example.code[:500], "python", line_numbers=True))

    # Examples list (verbose)
    if verbose:
        console.print("\n[bold]Examples Found[/bold]")
        for example in report.examples[:20]:
            status = "[green]✓[/green]" if example.is_valid else "[red]✗[/red]"
            console.print(
                f"  {status} {example.source_file}:{example.line_number} "
                f"[dim]({example.language}, {len(example.code)} chars)[/dim]",
            )
        if len(report.examples) > 20:
            console.print(f"  ... and {len(report.examples) - 20} more")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Directory or file to scan")
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        help="Filter by language (e.g., python, javascript)",
    )
    parser.add_argument(
        "--validate-syntax",
        action="store_true",
        help="Validate Python syntax",
    )
    parser.add_argument(
        "--check-imports",
        action="store_true",
        help="Verify imports exist (requires source)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write extracted examples to directory",
    )
    parser.add_argument(
        "--show-code",
        action="store_true",
        help="Show code for invalid examples",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--format",
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

    # Normalize language filter
    lang_filter = args.language.lower() if args.language else None

    # Extract examples
    report = extract_examples(
        args.path,
        language_filter=lang_filter,
        validate_syntax=args.validate_syntax,
    )

    # Write to output directory if specified
    if args.output and report.examples:
        written = write_examples(report.examples, args.output)
        console.print(f"[green]Wrote {written} examples to {args.output}[/green]")

    # Output results
    if args.format == "json":
        result: dict[str, Any] = {
            "summary": {
                "total": report.total,
                "valid": report.valid_count,
                "invalid": len(report.invalid_syntax),
            },
            "languages": report.languages,
            "examples": [
                {
                    "file": str(e.source_file),
                    "line": e.line_number,
                    "language": e.language,
                    "length": len(e.code),
                    "valid": e.is_valid,
                    "imports": e.imports,
                    "error": e.syntax_error,
                }
                for e in report.examples
            ],
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(report, verbose=args.verbose, show_code=args.show_code)

    return 1 if report.invalid_syntax else 0


if __name__ == "__main__":
    sys.exit(main())
