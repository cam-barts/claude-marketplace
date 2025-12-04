---
documentation_type: reference
---

# Documentation Standards Scripts

Python scripts for automated documentation quality enforcement and fixing.

## Scripts

### 1. `add_doc_type.py`

Add or update `documentation_type` frontmatter in markdown files.

**Features:**

- Auto-categorizes files based on path/name
- Interactive mode for manual selection
- Dry-run support
- Batch processing

**Usage:**

```bash
# Add specific type to a file
./add_doc_type.py README.md explanation

# Auto-categorize all files in a directory
./add_doc_type.py docs/ --auto --recursive

# Interactive mode
./add_doc_type.py . --interactive --recursive

# Dry run to preview changes
./add_doc_type.py docs/ --auto -r --dry-run
```

**Auto-categorization rules:**

- `README.md` → `explanation`
- `TODO.md` → `reference`
- Files in `commands/` → `how-to`
- Files in `agents/` or `skills/` → `reference`
- Files with "tutorial" or "guide" in name → `tutorial`
- Files with "how" in name → `how-to`
- Files with "api", "spec", or "reference" → `reference`
- Default → `explanation`

### 2. `add_code_languages.py`

Add language identifiers to code blocks without them.

**Features:**

- Smart language detection based on content and context
- Detects 10+ languages (bash, python, javascript, json, yaml, etc.)
- Handles special cases (shebangs, command prompts, file trees)
- Preserves existing code block content

**Usage:**

```bash
# Fix a single file
./add_code_languages.py README.md

# Fix all files recursively
./add_code_languages.py docs/ --recursive

# Dry run with verbose output
./add_code_languages.py . -r --dry-run --verbose
```

**Language detection:**

- Checks for shebangs (`#!/usr/bin/env python`)
- Detects command-line patterns (`$`, `npm`, `pip`, `git`)
- Analyzes syntax (JSON braces, YAML colons, function keywords)
- Uses surrounding context (nearby text mentioning language)
- Falls back to `text` for ambiguous cases

### 3. `validate_markdown.py`

Comprehensive markdown validation that respects code block boundaries.

**Features:**

- Validates frontmatter and documentation_type
- Checks code block structure and language identifiers
- Validates header hierarchy (H1 → H2 → H3, no skipping)
- Checks relative links (broken link detection)
- Validates list formatting
- JSON output support for CI/CD integration

**Usage:**

```bash
# Validate a single file
./validate_markdown.py README.md

# Validate directory recursively
./validate_markdown.py docs/ --recursive

# Filter by severity
./validate_markdown.py . -r --severity error

# JSON output for CI/CD
./validate_markdown.py . -r --json > report.json
```

**Exit codes:**

- `0` - No errors (warnings/info may exist)
- `1` - Errors found

**Severity levels:**

- `error` - Must be fixed (missing frontmatter, broken links, unclosed code blocks)
- `warning` - Should be fixed (missing language identifiers, header hierarchy issues)
- `info` - Nice to fix (formatting suggestions, link text improvements)

### 4. `fix_markdown.py`

Auto-fix common markdown issues in one command.

**Features:**

- Combines all fixes from other scripts
- Adds frontmatter with auto-categorization
- Fixes code block issues (missing languages, incorrect closures)
- Removes trailing whitespace
- Ensures single newline at end of file
- Detailed reporting of fixes applied

**Usage:**

```bash
# Fix a single file
./fix_markdown.py README.md

# Fix all files recursively
./fix_markdown.py docs/ --recursive

# Dry run to preview fixes
./fix_markdown.py . -r --dry-run

# Verbose output showing all fixes
./fix_markdown.py . -r --verbose
```

**Fixes applied:**

1. Missing frontmatter → Adds with auto-categorized documentation_type
2. Missing documentation_type → Adds to existing frontmatter
3. Code blocks without language → Detects and adds language identifier
4. Incorrect code block closures → Fixes (e.g., ` ```bash` → ` ``` `)
5. Trailing whitespace → Removes from all lines
6. Missing/multiple EOF newlines → Ensures single newline

## Integration with Plugin Commands

These scripts can be used in the plugin's slash commands:

**`/docs-fix` can call:**

```bash
uv run scripts/fix_markdown.py . --recursive
```

**`/docs-check` can call:**

```bash
uv run scripts/validate_markdown.py . --recursive --severity error
```

**`/docs-validate` can call:**

```bash
uv run scripts/validate_markdown.py . --recursive --json
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Documentation Quality

on: [push, pull_request]

jobs:
  validate-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Validate markdown
        run: |
          uv run plugins/documentation-standards/scripts/validate_markdown.py . -r --severity error
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: markdown-validation
        name: Validate Markdown
        entry: uv run plugins/documentation-standards/scripts/validate_markdown.py
        language: system
        files: \.md$
        args: [--severity, error]
```

```toml
# .prek.toml
[[hooks]]
name = "markdown-validation"
entry = "uv run plugins/documentation-standards/scripts/validate_markdown.py . -r --severity error"
language = "system"
files = "\.md$"
```

## Requirements

- Python 3.8+
- [uv](https://docs.astral.sh/uv/) (for self-installing scripts)
- No external dependencies (uses only standard library)

## Installation

### Install uv (one-time setup)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pipx (not recommended, prefer native install)
pipx install uv
```

### Using the Scripts

All scripts are **self-installing** using uv. Just make them executable and run them directly:

```bash
# Make executable (one-time)
chmod +x scripts/*.py

# Run directly - uv handles everything automatically
./scripts/fix_markdown.py . --recursive
```

**First run:** uv creates a virtual environment and installs dependencies (none in this case, but the infrastructure is there for future additions).

**Subsequent runs:** uv reuses the existing environment and verifies dependencies.

### Alternative: Traditional Python

If you don't have uv installed, you can still run scripts with regular Python:

```bash
python scripts/fix_markdown.py . --recursive
```

## Best Practices

1. **Always run with `--dry-run` first** to preview changes
2. **Use version control** before running bulk fixes
3. **Validate after fixing** to ensure no issues remain:

   ```bash
   ./fix_markdown.py . -r && ./validate_markdown.py . -r
   ```

4. **Customize auto-categorization** by editing the rules in the scripts
5. **Use `--verbose` for debugging** when fixes don't work as expected

## Troubleshooting

**Issue:** Script reports false positives for headers in code blocks

**Solution:** The validation script properly handles this. If using basic regex validation elsewhere, use `validate_markdown.py` which respects code block boundaries.

**Issue:** Language detection is incorrect

**Solution:** Edit the `detect_language()` function in the script to add more patterns or adjust priority.

**Issue:** Auto-categorization puts files in wrong type

**Solution:** Edit the `categorize_file()` function to add more rules or change defaults.

## Contributing

To add new validation rules or fixes:

1. Add validation logic to `MarkdownValidator` class in `validate_markdown.py`
2. Add fix logic to `MarkdownFixer` class in `fix_markdown.py`
3. Update this README with the new feature
4. Test with `--dry-run` on various markdown files

## License

Same as parent plugin (documentation-standards).
