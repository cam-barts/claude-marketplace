#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Comprehensive markdown validation that respects code block boundaries.

Usage:
    ./validate_markdown.py <file_or_directory>

Examples
--------
    ./validate_markdown.py README.md
    ./validate_markdown.py docs/ --recursive
    ./validate_markdown.py . -r --json
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ValidationIssue:
    """Represents a validation issue."""

    file: str
    line: int | None
    severity: str  # 'error', 'warning', 'info'
    category: str
    message: str


class MarkdownValidator:
    """Validates markdown files with code-block awareness."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text(encoding="utf-8")
        self.lines = self.content.split("\n")
        self.issues: list[ValidationIssue] = []

    def add_issue(self, line: int | None, severity: str, category: str, message: str):
        """Add a validation issue."""
        self.issues.append(
            ValidationIssue(
                file=str(self.file_path),
                line=line,
                severity=severity,
                category=category,
                message=message,
            )
        )

    def get_code_block_ranges(self) -> list[tuple[int, int]]:
        """Get line ranges for all code blocks."""
        ranges = []
        in_block = False
        start = 0

        for i, line in enumerate(self.lines, 1):
            if line.startswith("```"):
                if not in_block:
                    start = i
                    in_block = True
                else:
                    ranges.append((start, i))
                    in_block = False

        return ranges

    def is_in_code_block(self, line_num: int, ranges: list[tuple[int, int]]) -> bool:
        """Check if a line number is within a code block."""
        return any(start <= line_num <= end for start, end in ranges)

    def validate_frontmatter(self):
        """Validate YAML frontmatter."""
        if not self.content.startswith("---\n"):
            self.add_issue(1, "error", "frontmatter", "Missing frontmatter")
            return

        match = re.match(r"^---\n(.*?)\n---", self.content, re.DOTALL)
        if not match:
            self.add_issue(1, "error", "frontmatter", "Invalid frontmatter format")
            return

        frontmatter = match.group(1)

        # Check for documentation_type
        if "documentation_type:" not in frontmatter:
            self.add_issue(
                None, "error", "frontmatter", "Missing documentation_type field"
            )
        else:
            doc_type_match = re.search(r"documentation_type:\s*(\S+)", frontmatter)
            if doc_type_match:
                doc_type = doc_type_match.group(1)
                valid_types = ["tutorial", "how-to", "reference", "explanation"]
                if doc_type not in valid_types:
                    valid_str = ", ".join(valid_types)
                    self.add_issue(
                        None,
                        "error",
                        "frontmatter",
                        f"Invalid documentation_type '{doc_type}'. "
                        f"Must be: {valid_str}",
                    )

    def validate_code_blocks(self):
        """Validate code block structure and language identifiers."""
        in_block = False
        block_start = 0

        for i, line in enumerate(self.lines, 1):
            if line.startswith("```"):
                if not in_block:
                    # Opening block
                    if line.strip() == "```":
                        self.add_issue(
                            i,
                            "warning",
                            "code-block",
                            "Code block without language identifier",
                        )
                    block_start = i
                    in_block = True
                else:
                    # Closing block
                    if line.strip() != "```":
                        self.add_issue(
                            i,
                            "error",
                            "code-block",
                            f"Invalid code block closure: '{line}'",
                        )
                    in_block = False

        if in_block:
            self.add_issue(block_start, "error", "code-block", "Unclosed code block")

    def validate_headers(self):
        """Validate header hierarchy (outside code blocks)."""
        code_ranges = self.get_code_block_ranges()
        prev_level = 0

        for i, line in enumerate(self.lines, 1):
            if self.is_in_code_block(i, code_ranges):
                continue

            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                title = match.group(2)

                # Check for skipped levels
                if level > prev_level + 1 and prev_level != 0:
                    self.add_issue(
                        i,
                        "warning",
                        "header-hierarchy",
                        f"H{level} '{title}' follows H{prev_level} "
                        f"(skipped H{prev_level + 1})",
                    )

                prev_level = level

    def validate_links(self):
        """Validate markdown links."""
        code_ranges = self.get_code_block_ranges()

        for i, line in enumerate(self.lines, 1):
            if self.is_in_code_block(i, code_ranges):
                continue

            # Find all markdown links
            links = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", line)

            for text, url in links:
                # Validate relative file links
                if not url.startswith(("http://", "https://", "#", "mailto:")):
                    target_path = (self.file_path.parent / url).resolve()
                    if not target_path.exists():
                        self.add_issue(i, "error", "link", f"Broken link: '{url}'")

                # Warn about bare URLs (should use link syntax)
                if url.startswith(("http://", "https://")) and text == url:
                    self.add_issue(
                        i,
                        "info",
                        "link",
                        "Consider using descriptive link text instead of URL",
                    )

    def validate_list_formatting(self):
        """Validate list formatting."""
        code_ranges = self.get_code_block_ranges()

        for i, line in enumerate(self.lines, 1):
            if self.is_in_code_block(i, code_ranges):
                continue

            # Check for inconsistent list markers
            if re.match(r"^\s*[-*+]\s+", line):
                # It's a list item
                indent = len(line) - len(line.lstrip())
                if indent % 2 != 0:
                    self.add_issue(
                        i,
                        "info",
                        "formatting",
                        "List indentation should be multiples of 2 spaces",
                    )

    def validate(self) -> list[ValidationIssue]:
        """Run all validations."""
        self.validate_frontmatter()
        self.validate_code_blocks()
        self.validate_headers()
        self.validate_links()
        self.validate_list_formatting()

        return self.issues


def format_issues(issues: list[ValidationIssue], use_json: bool = False) -> str:
    """Format validation issues for output."""
    if use_json:
        return json.dumps([asdict(issue) for issue in issues], indent=2)

    if not issues:
        return "✅ No issues found"

    # Group by file
    by_file: dict[str, list[ValidationIssue]] = {}
    for issue in issues:
        if issue.file not in by_file:
            by_file[issue.file] = []
        by_file[issue.file].append(issue)

    output = []
    for file_path, file_issues in by_file.items():
        output.append(f"\n{file_path}:")

        # Group by severity
        errors = [i for i in file_issues if i.severity == "error"]
        warnings = [i for i in file_issues if i.severity == "warning"]
        infos = [i for i in file_issues if i.severity == "info"]

        for issue_list, icon in [(errors, "❌"), (warnings, "⚠️ "), (infos, "ℹ️ ")]:
            for issue in issue_list:
                line_info = f"Line {issue.line}: " if issue.line else ""
                output.append(f"  {icon} {line_info}{issue.message} [{issue.category}]")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive markdown validation with code-block awareness",
    )
    parser.add_argument("path", help="File or directory to validate")
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="Process directories recursively"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--severity",
        choices=["error", "warning", "info"],
        help="Only show issues of this severity or higher",
    )

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path '{path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Collect files to process
    if path.is_file():
        files = [path]
    elif path.is_dir():
        glob_method = path.rglob if args.recursive else path.glob
        files = list(glob_method("*.md"))
    else:
        print(f"Error: '{path}' is not a file or directory", file=sys.stderr)
        sys.exit(1)

    if not files:
        print("No markdown files found")
        sys.exit(0)

    # Validate all files
    all_issues = []
    for file_path in sorted(files):
        validator = MarkdownValidator(file_path)
        issues = validator.validate()
        all_issues.extend(issues)

    # Filter by severity if requested
    if args.severity:
        severity_order = {"error": 3, "warning": 2, "info": 1}
        min_level = severity_order[args.severity]
        all_issues = [i for i in all_issues if severity_order[i.severity] >= min_level]

    # Output results
    print(format_issues(all_issues, args.json))

    # Exit with error code if there are errors
    error_count = sum(1 for i in all_issues if i.severity == "error")
    if error_count > 0:
        print(f"\n❌ Found {error_count} error(s)", file=sys.stderr)
        sys.exit(1)
    else:
        warning_count = sum(1 for i in all_issues if i.severity == "warning")
        if warning_count > 0:
            print(f"\n⚠️  Found {warning_count} warning(s)")


if __name__ == "__main__":
    main()
