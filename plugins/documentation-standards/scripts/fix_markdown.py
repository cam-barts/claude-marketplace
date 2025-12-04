#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Auto-fix common markdown issues.

Fixes:
- Add frontmatter with documentation_type
- Add language identifiers to code blocks
- Fix incorrect code block closures
- Fix header hierarchy issues
- Remove trailing whitespace
- Ensure single blank line at end of file

Usage:
    ./fix_markdown.py <file_or_directory>

Examples
--------
    ./fix_markdown.py README.md
    ./fix_markdown.py docs/ --recursive
    ./fix_markdown.py . -r --dry-run
"""

import argparse
import re
import sys
from pathlib import Path


def categorize_file(file_path: Path) -> str:
    """Auto-categorize file based on path and name."""
    path_str = str(file_path).lower()
    name = file_path.stem.lower()

    if name == "readme":
        return "explanation"
    if name == "todo":
        return "reference"
    if "/commands/" in path_str:
        return "how-to"
    if "/agents/" in path_str or "/skills/" in path_str:
        return "reference"
    if "guide" in name or "tutorial" in name:
        return "tutorial"
    if "how" in name:
        return "how-to"
    if any(word in name for word in ["api", "spec", "reference"]):
        return "reference"

    return "explanation"


def detect_language(
    code_block: str, context_before: str = "", context_after: str = ""
) -> str:
    """Detect programming language based on code content."""
    code_lower = code_block.lower().strip()
    context = (context_before + context_after).lower()

    if code_block.strip().startswith("#!"):
        if "python" in code_block[:30]:
            return "python"
        if "bash" in code_block[:30] or "sh" in code_block[:30]:
            return "bash"

    if code_block.strip().startswith("$") or code_block.strip().startswith("> "):
        return "bash"

    if any(
        cmd in code_lower[:50]
        for cmd in ["npm ", "pip ", "cargo ", "go ", "apt ", "brew ", "git "]
    ):
        return "bash"

    starts_json = code_block.strip().startswith(("{", "["))
    if starts_json and '"' in code_block and re.search(r'["{]\s*"\w+"\s*:', code_block):
        return "json"

    yaml_pattern = re.search(r"^\w+:\s*$", code_block, re.MULTILINE)
    if yaml_pattern and ":" in code_block and "{" not in code_block[:20]:
        return "yaml"

    if any(kw in code_block for kw in ["def ", "import ", "class ", "from ", "print("]):
        return "python"

    if any(kw in code_block for kw in ["function ", "const ", "let ", "var ", "=>"]):
        return "javascript"

    if re.search(r"^\s*[#$]", code_block, re.MULTILINE):
        return "bash"

    if any(
        cmd in code_lower for cmd in ["echo ", "cd ", "ls ", "mkdir ", "cat ", "grep "]
    ):
        return "bash"

    if re.search(r"[├└│]", code_block) or (
        code_block.count("/") > 3 and "\n" in code_block
    ):
        return "text"

    if "bash" in context or "shell" in context or "command" in context:
        return "bash"

    return "text"


class MarkdownFixer:
    """Fix common markdown issues."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text(encoding="utf-8")
        self.fixes_applied: list[str] = []

    def fix_frontmatter(self):
        """Add or update frontmatter with documentation_type."""
        if not self.content.startswith("---\n"):
            # Add frontmatter
            doc_type = categorize_file(self.file_path)
            self.content = f"---\ndocumentation_type: {doc_type}\n---\n\n{self.content}"
            self.fixes_applied.append(
                f"Added frontmatter (documentation_type: {doc_type})"
            )
            return

        # Check if documentation_type exists
        match = re.match(r"^---\n(.*?)\n---\n", self.content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            if "documentation_type:" not in frontmatter:
                doc_type = categorize_file(self.file_path)
                new_frontmatter = f"{frontmatter}\ndocumentation_type: {doc_type}"
                self.content = self.content.replace(
                    f"---\n{frontmatter}\n---\n",
                    f"---\n{new_frontmatter}\n---\n",
                    1,
                )
                self.fixes_applied.append(f"Added documentation_type: {doc_type}")

    def fix_code_blocks(self):
        """Fix code block issues."""
        lines = self.content.split("\n")
        modified = False
        i = 0

        while i < len(lines):
            line = lines[i]

            # Fix code blocks without language
            if re.match(r"^```\s*$", line):
                context_before = "\n".join(lines[max(0, i - 3) : i])
                j = i + 1
                code_lines = []
                while j < len(lines) and not lines[j].startswith("```"):
                    code_lines.append(lines[j])
                    j += 1

                if j < len(lines):
                    context_after = "\n".join(lines[j + 1 : min(len(lines), j + 4)])
                    code_block = "\n".join(code_lines)
                    lang = detect_language(code_block, context_before, context_after)
                    lines[i] = f"```{lang}"
                    modified = True
                    self.fixes_applied.append(
                        f"Line {i + 1}: Added language '{lang}' to code block"
                    )

                i = j + 1
                continue

            # Fix incorrect code block closures (```bash instead of ```)
            if re.match(r"^```[a-z]+\s*$", line) and i > 0:
                # Check if this could be a mistaken closure
                # Look backwards for an opening ```
                opening_line = -1
                for k in range(i - 1, max(0, i - 50), -1):
                    if lines[k].startswith("```"):
                        opening_line = k
                        break

                if opening_line >= 0:
                    # Check if there's already a closing ``` between opening and here
                    has_closure = False
                    for check_line in range(opening_line + 1, i):
                        if lines[check_line] == "```":
                            has_closure = True
                            break

                    if not has_closure:
                        # This is likely a mistaken closure
                        lines[i] = "```"
                        modified = True
                        self.fixes_applied.append(
                            f"Line {i + 1}: Fixed code block closure"
                        )

            i += 1

        if modified:
            self.content = "\n".join(lines)

    def fix_trailing_whitespace(self):
        """Remove trailing whitespace from lines."""
        lines = self.content.split("\n")
        new_lines = [line.rstrip() for line in lines]

        if new_lines != lines:
            self.content = "\n".join(new_lines)
            self.fixes_applied.append("Removed trailing whitespace")

    def fix_eof_newline(self):
        """Ensure single blank line at end of file."""
        if not self.content.endswith("\n"):
            self.content += "\n"
            self.fixes_applied.append("Added newline at end of file")
        elif self.content.endswith("\n\n\n"):
            self.content = self.content.rstrip("\n") + "\n"
            self.fixes_applied.append("Reduced multiple newlines at end of file")

    def apply_fixes(self, dry_run: bool = False) -> tuple[bool, list[str]]:
        """Apply all fixes."""
        self.fix_frontmatter()
        self.fix_code_blocks()
        self.fix_trailing_whitespace()
        self.fix_eof_newline()

        if self.fixes_applied and not dry_run:
            self.file_path.write_text(self.content, encoding="utf-8")

        return bool(self.fixes_applied), self.fixes_applied


def process_file(file_path: Path, dry_run: bool = False, verbose: bool = False):
    """Process a single markdown file."""
    if file_path.suffix != ".md":
        return

    try:
        fixer = MarkdownFixer(file_path)
        modified, fixes = fixer.apply_fixes(dry_run)

        if modified:
            prefix = "[DRY RUN] " if dry_run else ""
            print(f"{prefix}✅ {file_path}: Applied {len(fixes)} fix(es)")
            if verbose:
                for fix in fixes:
                    print(f"   - {fix}")
        elif verbose:
            print(f"⏭️  {file_path}: No changes needed")

    except Exception as e:
        print(f"❌ {file_path}: Error - {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Auto-fix common markdown issues",
    )
    parser.add_argument("path", help="File or directory to fix")
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="Process directories recursively"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed information about fixes applied",
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

    print(f"Processing {len(files)} markdown file(s)...\n")

    for file_path in sorted(files):
        process_file(file_path, args.dry_run, args.verbose)


if __name__ == "__main__":
    main()
