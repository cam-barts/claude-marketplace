#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Add or update documentation_type frontmatter in markdown files.

Usage:
    ./add_doc_type.py <file_or_directory> [doc_type]

Examples
--------
    ./add_doc_type.py README.md explanation
    ./add_doc_type.py docs/ --interactive
    ./add_doc_type.py . --auto  # Auto-categorize based on file type
"""

import argparse
import re
import sys
from pathlib import Path

VALID_TYPES = ["tutorial", "how-to", "reference", "explanation"]


def categorize_file(file_path: Path) -> str:
    """Auto-categorize file based on path and name."""
    path_str = str(file_path).lower()
    name = file_path.stem.lower()

    # READMEs are typically explanations
    if name == "readme":
        return "explanation"

    # TODOs are reference
    if name == "todo":
        return "reference"

    # Files in commands/ are how-to guides
    if "/commands/" in path_str:
        return "how-to"

    # Files in agents/ or skills/ are reference
    if "/agents/" in path_str or "/skills/" in path_str:
        return "reference"

    # Files with "guide" or "tutorial" in name
    if "guide" in name or "tutorial" in name:
        return "tutorial"

    # Files with "how" in name
    if "how" in name:
        return "how-to"

    # Files with "api", "spec", or "reference" in name
    if any(word in name for word in ["api", "spec", "reference"]):
        return "reference"

    # Default to explanation for unclear cases
    return "explanation"


def get_frontmatter_and_content(content: str) -> tuple[str | None, str]:
    """Extract frontmatter and remaining content."""
    if content.startswith("---\n"):
        match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            rest = content[match.end() :]
            return frontmatter, rest
    return None, content


def add_or_update_frontmatter(
    file_path: Path, doc_type: str, dry_run: bool = False
) -> tuple[bool, str]:
    """Add or update documentation_type in frontmatter."""
    if doc_type not in VALID_TYPES:
        return (
            False,
            f"Invalid doc_type '{doc_type}'. Must be one of: {', '.join(VALID_TYPES)}",
        )

    try:
        content = file_path.read_text(encoding="utf-8")
        frontmatter, rest = get_frontmatter_and_content(content)

        if frontmatter is not None:
            # Check if documentation_type exists
            if "documentation_type:" in frontmatter:
                # Update existing
                new_frontmatter = re.sub(
                    r"documentation_type:\s*\S+",
                    f"documentation_type: {doc_type}",
                    frontmatter,
                )
                action = "updated"
            else:
                # Add to existing frontmatter
                new_frontmatter = f"{frontmatter}\ndocumentation_type: {doc_type}"
                action = "added"

            new_content = f"---\n{new_frontmatter}\n---\n{rest}"
        else:
            # Create new frontmatter
            new_content = f"---\ndocumentation_type: {doc_type}\n---\n\n{content}"
            action = "created"

        if not dry_run:
            file_path.write_text(new_content, encoding="utf-8")

        return True, f"{action} documentation_type: {doc_type}"

    except Exception as e:
        return False, f"Error: {e}"


def process_file(
    file_path: Path, doc_type: str | None, auto: bool, interactive: bool, dry_run: bool
):
    """Process a single markdown file."""
    if file_path.suffix != ".md":
        return

    # Determine doc_type
    if doc_type:
        selected_type = doc_type
    elif auto:
        selected_type = categorize_file(file_path)
    elif interactive:
        print(f"\n{file_path}")
        print(f"Suggested: {categorize_file(file_path)}")
        print(f"Options: {', '.join(VALID_TYPES)}")
        selected_type = input("Select type (or press Enter for suggestion): ").strip()
        if not selected_type:
            selected_type = categorize_file(file_path)
        if selected_type not in VALID_TYPES:
            print("Invalid type, skipping...")
            return
    else:
        print("Error: Must specify --doc-type, --auto, or --interactive")
        return

    success, message = add_or_update_frontmatter(file_path, selected_type, dry_run)

    prefix = "[DRY RUN] " if dry_run else ""
    status = "✅" if success else "❌"
    print(f"{prefix}{status} {file_path}: {message}")


def main():
    parser = argparse.ArgumentParser(
        description="Add or update documentation_type frontmatter in markdown files",
    )
    parser.add_argument("path", help="File or directory to process")
    parser.add_argument(
        "doc_type",
        nargs="?",
        choices=VALID_TYPES,
        help="Documentation type (tutorial, how-to, reference, explanation)",
    )
    parser.add_argument(
        "--auto", action="store_true", help="Auto-categorize based on file path/name"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactively choose type for each file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="Process directories recursively"
    )

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path '{path}' does not exist")
        sys.exit(1)

    # Collect files to process
    if path.is_file():
        files = [path]
    elif path.is_dir():
        glob_method = path.rglob if args.recursive else path.glob
        files = list(glob_method("*.md"))
    else:
        print(f"Error: '{path}' is not a file or directory")
        sys.exit(1)

    if not files:
        print("No markdown files found")
        sys.exit(0)

    print(f"Found {len(files)} markdown file(s)")

    for file_path in files:
        process_file(
            file_path, args.doc_type, args.auto, args.interactive, args.dry_run
        )


if __name__ == "__main__":
    main()
