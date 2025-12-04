#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pillow>=10.0",
#     "rich>=13.0",
# ]
# ///
"""
Validate image references and accessibility in markdown files.

Features:
- Verify referenced images exist on disk
- Check all images have alt text
- Warn about oversized images (configurable threshold)
- Detect unused images in assets folder
- Validate image format compatibility

Usage:
    uv run validate_images.py [OPTIONS] PATH

Examples
--------
    uv run validate_images.py docs/
    uv run validate_images.py docs/ --max-size 200
    uv run validate_images.py docs/ --find-unused
    uv run validate_images.py docs/ --output json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

DEFAULT_MAX_SIZE_KB = 500
DEFAULT_FORMATS = {"png", "jpg", "jpeg", "gif", "svg", "webp"}


@dataclass
class ImageReference:
    """An image reference found in a markdown file."""

    markdown_file: Path
    line_number: int
    image_path: str
    alt_text: str
    resolved_path: Path | None = None
    exists: bool = False
    size_kb: float = 0.0
    dimensions: tuple[int, int] | None = None


@dataclass
class ImageReport:
    """Report of image validation results."""

    references: list[ImageReference] = field(default_factory=list)
    missing_images: list[ImageReference] = field(default_factory=list)
    missing_alt_text: list[ImageReference] = field(default_factory=list)
    oversized_images: list[ImageReference] = field(default_factory=list)
    unused_images: list[Path] = field(default_factory=list)
    invalid_formats: list[ImageReference] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(
            self.missing_images
            or self.missing_alt_text
            or self.oversized_images
            or self.invalid_formats,
        )


def find_markdown_files(path: Path) -> list[Path]:
    """Find all markdown files in a directory."""
    if path.is_file():
        return [path] if path.suffix.lower() in {".md", ".markdown"} else []
    return list(path.rglob("*.md")) + list(path.rglob("*.markdown"))


def find_image_files(path: Path) -> set[Path]:
    """Find all image files in a directory."""
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}
    if path.is_file():
        return set()

    images: set[Path] = set()
    for ext in image_extensions:
        images.update(path.rglob(f"*{ext}"))
        images.update(path.rglob(f"*{ext.upper()}"))

    return images


def extract_image_references(file_path: Path) -> list[ImageReference]:
    """Extract image references from a markdown file."""
    references: list[ImageReference] = []

    # Pattern for markdown images: ![alt text](path)
    # Also handles optional title: ![alt](path "title")
    md_pattern = re.compile(r'!\[([^\]]*)\]\(([^)"\s]+)(?:\s+"[^"]*")?\)')

    # Pattern for HTML images: <img src="path" alt="text">
    html_pattern = re.compile(
        r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE
    )
    alt_pattern = re.compile(r'alt=["\']([^"\']*)["\']', re.IGNORECASE)

    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Check markdown image syntax
            for match in md_pattern.finditer(line):
                alt_text = match.group(1)
                image_path = match.group(2)

                # Skip external URLs
                if image_path.startswith(("http://", "https://", "//")):
                    continue

                references.append(
                    ImageReference(
                        markdown_file=file_path,
                        line_number=line_num,
                        image_path=image_path,
                        alt_text=alt_text,
                    ),
                )

            # Check HTML img tags
            for match in html_pattern.finditer(line):
                image_path = match.group(1)

                # Skip external URLs
                if image_path.startswith(("http://", "https://", "//")):
                    continue

                # Find alt text
                alt_match = alt_pattern.search(line)
                alt_text = alt_match.group(1) if alt_match else ""

                references.append(
                    ImageReference(
                        markdown_file=file_path,
                        line_number=line_num,
                        image_path=image_path,
                        alt_text=alt_text,
                    ),
                )

    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not read {file_path}: {e}")

    return references


def resolve_image_path(ref: ImageReference, base_path: Path) -> Path | None:
    """Resolve an image path relative to the markdown file or base path."""
    md_dir = ref.markdown_file.parent

    # Try relative to markdown file first
    resolved = (md_dir / ref.image_path).resolve()
    if resolved.exists():
        return resolved

    # Try relative to base path
    resolved = (base_path / ref.image_path).resolve()
    if resolved.exists():
        return resolved

    # Try stripping leading slash
    if ref.image_path.startswith("/"):
        resolved = (base_path / ref.image_path[1:]).resolve()
        if resolved.exists():
            return resolved

    return None


def get_image_info(path: Path) -> tuple[float, tuple[int, int] | None]:
    """Get image size in KB and dimensions."""
    size_kb = path.stat().st_size / 1024

    dimensions = None
    if path.suffix.lower() != ".svg":
        try:
            with Image.open(path) as img:
                dimensions = img.size
        except Exception:
            pass

    return size_kb, dimensions


def validate_images(
    path: Path,
    max_size_kb: float = DEFAULT_MAX_SIZE_KB,
    check_alt: bool = True,
    find_unused: bool = False,
    allowed_formats: set[str] | None = None,
) -> ImageReport:
    """Validate all image references in markdown files."""
    report = ImageReport()
    allowed = allowed_formats or DEFAULT_FORMATS

    # Find all markdown files
    md_files = find_markdown_files(path)

    # Find all images in directory
    all_images = find_image_files(path) if find_unused else set()
    referenced_images: set[Path] = set()

    for md_file in md_files:
        refs = extract_image_references(md_file)

        for ref in refs:
            # Resolve the image path
            resolved = resolve_image_path(ref, path)
            ref.resolved_path = resolved
            ref.exists = resolved is not None

            if resolved:
                referenced_images.add(resolved)
                ref.size_kb, ref.dimensions = get_image_info(resolved)

                # Check format
                ext = resolved.suffix.lower().lstrip(".")
                if ext not in allowed:
                    report.invalid_formats.append(ref)

                # Check size
                if ref.size_kb > max_size_kb:
                    report.oversized_images.append(ref)
            else:
                report.missing_images.append(ref)

            # Check alt text
            if check_alt and not ref.alt_text.strip():
                report.missing_alt_text.append(ref)

            report.references.append(ref)

    # Find unused images
    if find_unused:
        report.unused_images = sorted(all_images - referenced_images)

    return report


def print_report(report: ImageReport, verbose: bool = False) -> None:  # noqa: ARG001
    """Print the validation report."""
    console.print(Panel("[bold]Image Validation Report[/bold]"))

    # Summary
    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="green")

    summary_table.add_row("Total References", str(len(report.references)))
    summary_table.add_row(
        "Missing Images",
        f"[red]{len(report.missing_images)}[/red]" if report.missing_images else "0",
    )
    summary_table.add_row(
        "Missing Alt Text",
        f"[yellow]{len(report.missing_alt_text)}[/yellow]"
        if report.missing_alt_text
        else "0",
    )
    summary_table.add_row(
        "Oversized Images",
        f"[yellow]{len(report.oversized_images)}[/yellow]"
        if report.oversized_images
        else "0",
    )
    summary_table.add_row(
        "Invalid Formats",
        f"[red]{len(report.invalid_formats)}[/red]" if report.invalid_formats else "0",
    )
    summary_table.add_row("Unused Images", str(len(report.unused_images)))

    console.print(summary_table)

    # Missing images
    if report.missing_images:
        console.print("\n[bold red]Missing Images[/bold red]")
        for ref in report.missing_images:
            console.print(f"  {ref.markdown_file}:{ref.line_number}")
            console.print(f"    [dim]→ {ref.image_path}[/dim]")

    # Missing alt text
    if report.missing_alt_text:
        console.print("\n[bold yellow]Missing Alt Text[/bold yellow]")
        for ref in report.missing_alt_text[:10]:
            console.print(f"  {ref.markdown_file}:{ref.line_number}")
            console.print(f"    [dim]→ {ref.image_path}[/dim]")
        if len(report.missing_alt_text) > 10:
            console.print(
                f"  ... and {len(report.missing_alt_text) - 10} more",
            )

    # Oversized images
    if report.oversized_images:
        console.print("\n[bold yellow]Oversized Images[/bold yellow]")
        for ref in sorted(report.oversized_images, key=lambda r: -r.size_kb):
            console.print(f"  {ref.resolved_path}")
            dims = (
                f" ({ref.dimensions[0]}x{ref.dimensions[1]})" if ref.dimensions else ""
            )
            console.print(f"    [dim]{ref.size_kb:.1f} KB{dims}[/dim]")

    # Invalid formats
    if report.invalid_formats:
        console.print("\n[bold red]Invalid Formats[/bold red]")
        for ref in report.invalid_formats:
            console.print(f"  {ref.markdown_file}:{ref.line_number}")
            console.print(f"    [dim]→ {ref.image_path}[/dim]")

    # Unused images
    if report.unused_images:
        console.print("\n[bold blue]Unused Images[/bold blue]")
        for img_path in report.unused_images[:20]:
            size_kb = img_path.stat().st_size / 1024
            console.print(f"  {img_path} [dim]({size_kb:.1f} KB)[/dim]")
        if len(report.unused_images) > 20:
            console.print(f"  ... and {len(report.unused_images) - 20} more")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Directory or file to validate")
    parser.add_argument(
        "--max-size",
        type=float,
        default=DEFAULT_MAX_SIZE_KB,
        help=f"Maximum image size in KB (default: {DEFAULT_MAX_SIZE_KB})",
    )
    parser.add_argument(
        "--check-alt",
        action="store_true",
        default=True,
        help="Require alt text on all images (default: true)",
    )
    parser.add_argument(
        "--no-check-alt",
        action="store_false",
        dest="check_alt",
        help="Don't check for alt text",
    )
    parser.add_argument(
        "--find-unused",
        action="store_true",
        help="Report images not referenced anywhere",
    )
    parser.add_argument(
        "--formats",
        type=str,
        help="Allowed formats, comma-separated (default: png,jpg,jpeg,gif,svg,webp)",
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

    # Parse allowed formats
    allowed_formats = None
    if args.formats:
        allowed_formats = {f.strip().lower() for f in args.formats.split(",")}

    # Run validation
    report = validate_images(
        args.path,
        max_size_kb=args.max_size,
        check_alt=args.check_alt,
        find_unused=args.find_unused,
        allowed_formats=allowed_formats,
    )

    # Output results
    if args.output == "json":
        result: dict[str, Any] = {
            "summary": {
                "total_references": len(report.references),
                "missing_images": len(report.missing_images),
                "missing_alt_text": len(report.missing_alt_text),
                "oversized_images": len(report.oversized_images),
                "invalid_formats": len(report.invalid_formats),
                "unused_images": len(report.unused_images),
            },
            "missing_images": [
                {
                    "file": str(r.markdown_file),
                    "line": r.line_number,
                    "path": r.image_path,
                }
                for r in report.missing_images
            ],
            "missing_alt_text": [
                {
                    "file": str(r.markdown_file),
                    "line": r.line_number,
                    "path": r.image_path,
                }
                for r in report.missing_alt_text
            ],
            "oversized_images": [
                {
                    "file": str(r.resolved_path),
                    "size_kb": round(r.size_kb, 1),
                    "dimensions": list(r.dimensions) if r.dimensions else None,
                }
                for r in report.oversized_images
            ],
            "unused_images": [str(p) for p in report.unused_images],
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(report, verbose=args.verbose)

    return 1 if report.has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
