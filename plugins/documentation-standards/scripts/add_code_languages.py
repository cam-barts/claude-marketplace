#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Add language identifiers to code blocks without them.

Usage:
    ./add_code_languages.py <file_or_directory>

Examples
--------
    ./add_code_languages.py README.md
    ./add_code_languages.py docs/ --recursive
    ./add_code_languages.py . -r --dry-run
"""

import argparse
import re
import sys
from pathlib import Path


def detect_language(
    code_block: str, context_before: str = "", context_after: str = ""
) -> str:
    """Detect programming language based on code content and context."""
    code_lower = code_block.lower().strip()
    context = (context_before + context_after).lower()

    # Check for shebang
    if code_block.strip().startswith("#!"):
        if "python" in code_block[:30]:
            return "python"
        if "bash" in code_block[:30] or "sh" in code_block[:30]:
            return "bash"
        if "node" in code_block[:30]:
            return "javascript"

    # Command line indicators
    if code_block.strip().startswith("$") or code_block.strip().startswith("> "):
        return "bash"

    # Common command patterns
    cmd_patterns = ["npm ", "pip ", "cargo ", "go ", "apt ", "brew ", "git "]
    if any(cmd in code_lower[:50] for cmd in cmd_patterns):
        return "bash"

    # JSON detection
    starts_json = code_block.strip().startswith(("{", "["))
    has_quotes = '"' in code_block or "'" in code_block
    is_json_pattern = re.search(r'["{]\s*"\w+"\s*:', code_block)
    if starts_json and has_quotes and is_json_pattern:
        return "json"

    # YAML detection
    yaml_pattern = re.search(r"^\w+:\s*$", code_block, re.MULTILINE)
    starts_yaml = code_block.strip().startswith("---")
    is_yaml_like = ":" in code_block and "{" not in code_block[:20]
    if (yaml_pattern or starts_yaml) and is_yaml_like:
        return "yaml"

    # Python detection
    python_kw = ["def ", "import ", "class ", "from ", "print("]
    if any(keyword in code_block for keyword in python_kw):
        return "python"
    if "pytest" in context or "python" in context:
        return "python"

    # JavaScript/TypeScript detection
    js_kw = ["function ", "const ", "let ", "var ", "=>", "console.log"]
    if any(keyword in code_block for keyword in js_kw):
        return "javascript"
    if "npm" in context or "node" in context or "javascript" in context:
        return "javascript"

    # Shell script patterns
    if re.search(r"^\s*[#$]", code_block, re.MULTILINE):
        return "bash"
    bash_cmds = ["echo ", "cd ", "ls ", "mkdir ", "cat ", "grep ", "find ", "chmod "]
    if any(cmd in code_lower for cmd in bash_cmds):
        return "bash"

    # Markdown (rare but possible in examples)
    if code_block.strip().startswith(("#", "##", "###")):
        return "markdown"

    # File tree / directory structure
    has_tree_chars = re.search(r"[├└│]", code_block)
    is_path_like = code_block.count("/") > 3 and "\n" in code_block
    if has_tree_chars or is_path_like:
        return "text"

    # SQL detection
    sql_kw = ["select ", "insert ", "update ", "delete ", "create table"]
    if any(keyword in code_lower for keyword in sql_kw):
        return "sql"

    # Dockerfile
    docker_kw = ["FROM ", "RUN ", "CMD ", "COPY ", "WORKDIR "]
    if any(keyword in code_block for keyword in docker_kw):
        return "dockerfile"

    # Default based on context
    if "bash" in context or "shell" in context or "command" in context:
        return "bash"
    if "code" in context or "example" in context:
        return "text"

    # Final fallback
    return "text"


def fix_code_blocks(file_path: Path, dry_run: bool = False) -> tuple[int, int]:
    """Add language identifiers to code blocks without them."""
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        modified = False
        modifications = []
        i = 0

        while i < len(lines):
            # Find code blocks without language identifier
            if re.match(r"^```\s*$", lines[i]):
                # Get context before
                context_before = "\n".join(lines[max(0, i - 3) : i])

                # Find end of code block and collect code
                j = i + 1
                code_lines = []
                while j < len(lines) and not lines[j].startswith("```"):
                    code_lines.append(lines[j])
                    j += 1

                if j >= len(lines):
                    # Unclosed code block
                    break

                # Get context after
                context_after = "\n".join(lines[j + 1 : min(len(lines), j + 4)])

                code_block = "\n".join(code_lines)
                lang = detect_language(code_block, context_before, context_after)

                # Update the line
                lines[i] = f"```{lang}"
                modified = True
                modifications.append((i + 1, lang))

                i = j + 1
            else:
                i += 1

        if modified and not dry_run:
            new_content = "\n".join(lines)
            file_path.write_text(new_content, encoding="utf-8")

        return len(modifications), len(modifications)

    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return 0, 0


def process_file(file_path: Path, dry_run: bool = False, verbose: bool = False):
    """Process a single markdown file."""
    if file_path.suffix != ".md":
        return

    fixed, total = fix_code_blocks(file_path, dry_run)

    if fixed > 0:
        prefix = "[DRY RUN] " if dry_run else ""
        print(f"{prefix}✅ {file_path}: Fixed {fixed} code block(s)")
    elif verbose:
        print(f"⏭️  {file_path}: No changes needed")


def main():
    parser = argparse.ArgumentParser(
        description="Add language identifiers to code blocks without them",
    )
    parser.add_argument("path", help="File or directory to process")
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
        help="Show all files processed, not just modified ones",
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

    if args.verbose:
        print(f"Processing {len(files)} markdown file(s)...\n")

    for file_path in sorted(files):
        process_file(file_path, args.dry_run, args.verbose)


if __name__ == "__main__":
    main()
