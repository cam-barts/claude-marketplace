#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.27",
#     "rich>=13.0",
#     "anyio>=4.0",
# ]
# ///
"""
Validate internal and external links in markdown files.

Checks:
- Internal links between markdown files exist
- External URLs are reachable (with caching)
- Anchor links point to valid headings
- Detects orphaned files not linked from anywhere

Usage:
    uv run validate_links.py [OPTIONS] PATH

Examples
--------
    uv run validate_links.py docs/
    uv run validate_links.py docs/ --internal-only
    uv run validate_links.py docs/ --external-only
    uv run validate_links.py docs/ --output json > report.json
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import anyio
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# Regex to find markdown links: [text](url) and reference links
LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
REFERENCE_LINK_PATTERN = re.compile(r"\[([^\]]+)\]:\s*(\S+)")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


@dataclass
class LinkInfo:
    """Information about a link."""

    source_file: Path
    line_number: int
    link_text: str
    url: str
    is_external: bool
    is_anchor: bool = False


@dataclass
class ValidationResult:
    """Result of validating a link."""

    link: LinkInfo
    valid: bool
    status_code: int | None = None
    error: str | None = None


@dataclass
class ValidationReport:
    """Full validation report."""

    files_scanned: int = 0
    total_links: int = 0
    internal_links: int = 0
    external_links: int = 0
    broken_links: list[ValidationResult] = field(default_factory=list)
    orphaned_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.broken_links) == 0


def extract_links(file_path: Path, content: str) -> list[LinkInfo]:
    """Extract all links from a markdown file."""
    links: list[LinkInfo] = []
    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        # Find inline links
        for match in LINK_PATTERN.finditer(line):
            link_text = match.group(1)
            url = match.group(2)

            # Skip image links (start with !)
            if match.start() > 0 and line[match.start() - 1] == "!":
                continue

            is_external = url.startswith(("http://", "https://", "//"))
            is_anchor = url.startswith("#")

            links.append(
                LinkInfo(
                    source_file=file_path,
                    line_number=line_num,
                    link_text=link_text,
                    url=url,
                    is_external=is_external,
                    is_anchor=is_anchor,
                ),
            )

        # Find reference-style links
        for match in REFERENCE_LINK_PATTERN.finditer(line):
            link_text = match.group(1)
            url = match.group(2)

            is_external = url.startswith(("http://", "https://", "//"))

            links.append(
                LinkInfo(
                    source_file=file_path,
                    line_number=line_num,
                    link_text=link_text,
                    url=url,
                    is_external=is_external,
                ),
            )

    return links


def extract_headings(content: str) -> set[str]:
    """Extract all heading anchors from markdown content."""
    headings = set()
    for match in HEADING_PATTERN.finditer(content):
        heading_text = match.group(1).strip()
        # Convert heading to anchor format (lowercase, spaces to hyphens)
        anchor = re.sub(r"[^\w\s-]", "", heading_text.lower())
        anchor = re.sub(r"\s+", "-", anchor)
        headings.add(anchor)
    return headings


def validate_internal_link(
    link: LinkInfo,
    all_files: dict[Path, str],
    base_path: Path,
) -> ValidationResult:
    """Validate an internal link."""
    url = link.url

    # Handle anchor links
    if link.is_anchor:
        content = all_files.get(link.source_file, "")
        headings = extract_headings(content)
        anchor_only = url[1:]  # Remove leading #
        if anchor_only in headings:
            return ValidationResult(link=link, valid=True)
        return ValidationResult(
            link=link,
            valid=False,
            error=f"Anchor '{anchor_only}' not found in {link.source_file.name}",
        )

    # Parse the URL for anchor
    anchor: str | None
    if "#" in url:
        path_part, anchor = url.split("#", 1)
    else:
        path_part = url
        anchor = None

    # Resolve relative path
    if path_part.startswith("/"):
        target_path = base_path / path_part[1:]
    else:
        target_path = (link.source_file.parent / path_part).resolve()

    # Check if file exists
    if not target_path.exists():
        # Try with .md extension
        if not target_path.suffix and (target_path.with_suffix(".md")).exists():
            target_path = target_path.with_suffix(".md")
        else:
            return ValidationResult(
                link=link,
                valid=False,
                error=f"File not found: {target_path}",
            )

    # If there's an anchor, validate it
    if anchor:
        content = all_files.get(target_path, "")
        if not content and target_path.exists():
            content = target_path.read_text(encoding="utf-8")
        headings = extract_headings(content)
        if anchor not in headings:
            return ValidationResult(
                link=link,
                valid=False,
                error=f"Anchor '#{anchor}' not found in {target_path.name}",
            )

    return ValidationResult(link=link, valid=True)


async def validate_external_link(
    link: LinkInfo,
    client: httpx.AsyncClient,
    cache: dict[str, tuple[bool, int | None, str | None]],
) -> ValidationResult:
    """Validate an external link."""
    url = link.url

    # Normalize URL
    if url.startswith("//"):
        url = "https:" + url

    # Check cache
    cache_key = hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()
    if cache_key in cache:
        valid, status, error = cache[cache_key]
        return ValidationResult(link=link, valid=valid, status_code=status, error=error)

    try:
        # Use HEAD request first (faster)
        response = await client.head(url, follow_redirects=True)

        # Some servers don't support HEAD, fallback to GET
        if response.status_code == 405:
            response = await client.get(url, follow_redirects=True)

        valid = response.status_code < 400
        result = ValidationResult(
            link=link,
            valid=valid,
            status_code=response.status_code,
            error=None if valid else f"HTTP {response.status_code}",
        )

        # Cache result
        cache[cache_key] = (valid, response.status_code, result.error)

        return result

    except httpx.TimeoutException:
        result = ValidationResult(link=link, valid=False, error="Timeout")
        cache[cache_key] = (False, None, "Timeout")
        return result
    except httpx.RequestError as e:
        error = str(e)[:100]
        result = ValidationResult(link=link, valid=False, error=error)
        cache[cache_key] = (False, None, error)
        return result
    except Exception as e:
        error = str(e)[:100]
        result = ValidationResult(link=link, valid=False, error=error)
        cache[cache_key] = (False, None, error)
        return result


async def validate_links(
    path: Path,
    check_internal: bool = True,
    check_external: bool = True,
    timeout: float = 10.0,
    cache_file: Path | None = None,
    max_concurrent: int = 10,
) -> ValidationReport:
    """Validate all links in markdown files."""
    report = ValidationReport()

    # Load cache
    cache: dict[str, tuple[bool, int | None, str | None]] = {}
    if cache_file and cache_file.exists():
        try:
            cache_data = json.loads(cache_file.read_text())
            cache = {k: tuple(v) for k, v in cache_data.items()}
        except Exception:
            pass

    # Collect all markdown files
    if path.is_file():
        md_files = [path]
        base_path = path.parent
    else:
        md_files = list(path.rglob("*.md"))
        base_path = path

    # Read all files and extract links
    all_files: dict[Path, str] = {}
    all_links: list[LinkInfo] = []
    linked_files: set[Path] = set()

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            all_files[md_file] = content
            report.files_scanned += 1

            links = extract_links(md_file, content)
            all_links.extend(links)

            # Track linked internal files
            for link in links:
                if not link.is_external and not link.is_anchor:
                    url = link.url.split("#")[0]
                    if url.startswith("/"):
                        target = base_path / url[1:]
                    else:
                        target = (md_file.parent / url).resolve()
                    if not target.suffix:
                        target = target.with_suffix(".md")
                    linked_files.add(target)

        except Exception as e:
            report.warnings.append(f"Could not read {md_file}: {e}")

    report.total_links = len(all_links)
    report.internal_links = sum(1 for link in all_links if not link.is_external)
    report.external_links = sum(1 for link in all_links if link.is_external)

    # Validate internal links
    if check_internal:
        for link in all_links:
            if not link.is_external:
                result = validate_internal_link(link, all_files, base_path)
                if not result.valid:
                    report.broken_links.append(result)

    # Validate external links concurrently
    if check_external:
        external_links = [link for link in all_links if link.is_external]

        if external_links:
            semaphore = anyio.Semaphore(max_concurrent)

            async def check_with_semaphore(link: LinkInfo) -> ValidationResult:
                async with semaphore, httpx.AsyncClient(timeout=timeout) as client:
                    return await validate_external_link(link, client, cache)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Checking {len(external_links)} external links...",
                    total=len(external_links),
                )

                async def run_checks() -> list[ValidationResult]:
                    results = []
                    for link in external_links:
                        result = await check_with_semaphore(link)
                        results.append(result)
                        progress.advance(task)
                    return results

                results = await run_checks()

            for result in results:
                if not result.valid:
                    report.broken_links.append(result)

    # Find orphaned files
    for md_file in md_files:
        is_not_linked = md_file not in linked_files and md_file.name != "README.md"
        is_not_root = md_file.resolve() != (base_path / "README.md").resolve()
        if is_not_linked and is_not_root:
            report.orphaned_files.append(md_file)

    # Save cache
    if cache_file:
        try:
            cache_data = {k: list(v) for k, v in cache.items()}
            cache_file.write_text(json.dumps(cache_data, indent=2))
        except Exception:
            pass

    return report


def print_report(report: ValidationReport, verbose: bool = False) -> None:
    """Print validation report."""
    # Summary table
    table = Table(title="Link Validation Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Files Scanned", str(report.files_scanned))
    table.add_row("Total Links", str(report.total_links))
    table.add_row("Internal Links", str(report.internal_links))
    table.add_row("External Links", str(report.external_links))
    table.add_row(
        "Broken Links",
        f"[red]{len(report.broken_links)}[/red]"
        if report.broken_links
        else "[green]0[/green]",
    )
    table.add_row("Orphaned Files", str(len(report.orphaned_files)))
    console.print(table)

    # Broken links details
    if report.broken_links:
        console.print("\n[bold red]Broken Links:[/bold red]")
        for result in report.broken_links:
            location = f"{result.link.source_file}:{result.link.line_number}"
            console.print(f"  [dim]{location}[/dim]")
            console.print(f"    URL: {result.link.url}")
            console.print(f"    Error: [red]{result.error}[/red]")

    # Orphaned files
    if report.orphaned_files and verbose:
        console.print(
            "\n[bold yellow]Orphaned Files (not linked from anywhere):[/bold yellow]"
        )
        for orphan in report.orphaned_files:
            console.print(f"  {orphan}")

    # Warnings
    if report.warnings and verbose:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in report.warnings:
            console.print(f"  {warning}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="File or directory to validate")
    parser.add_argument(
        "--internal-only",
        action="store_true",
        help="Only check internal links",
    )
    parser.add_argument(
        "--external-only",
        action="store_true",
        help="Only check external links",
    )
    parser.add_argument(
        "--cache-file",
        type=Path,
        help="Path to cache file for external URL results",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout for external requests in seconds (default: 10)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Maximum concurrent external requests (default: 10)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report issues without failing"
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

    # Determine what to check
    check_internal = not args.external_only
    check_external = not args.internal_only

    # Run validation
    report = asyncio.run(
        validate_links(
            path=args.path,
            check_internal=check_internal,
            check_external=check_external,
            timeout=args.timeout,
            cache_file=args.cache_file,
            max_concurrent=args.max_concurrent,
        ),
    )

    if args.output == "json":
        result = {
            "success": report.success,
            "files_scanned": report.files_scanned,
            "total_links": report.total_links,
            "internal_links": report.internal_links,
            "external_links": report.external_links,
            "broken_links": [
                {
                    "source_file": str(r.link.source_file),
                    "line_number": r.link.line_number,
                    "url": r.link.url,
                    "error": r.error,
                }
                for r in report.broken_links
            ],
            "orphaned_files": [str(f) for f in report.orphaned_files],
            "warnings": report.warnings,
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(report, args.verbose)

    if args.dry_run:
        return 0

    return 0 if report.success else 1


if __name__ == "__main__":
    sys.exit(main())
