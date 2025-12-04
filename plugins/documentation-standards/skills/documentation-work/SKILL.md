---
name: documentation-work
description: |
  Autonomous documentation quality enforcement using rumdl, vale, and Diataxis standards.
  Use when working with markdown files, documentation, README files, guides, or .md files.
  Validates frontmatter, prose quality, code blocks, and ensures Diataxis compliance.
documentation_type: reference
---

This skill is automatically invoked when Claude is working on documentation tasks.

When this skill is active, Claude will:

- Validate all markdown files for standards compliance
- Ensure proper Diataxis `documentation_type` frontmatter
- Run rumdl and vale on all documentation
- Fix issues automatically where possible using plugin scripts
- Never mark documentation work complete until all errors are resolved

Claude should invoke this skill whenever:

- Creating new markdown documentation
- Editing existing documentation
- Reviewing pull requests with documentation changes
- User requests documentation improvements or fixes
- Any task involves writing or modifying .md files

This skill uses the same standards as the docs-enforcer agent and ensures consistent, high-quality documentation across all work.

## Available Scripts

The plugin provides self-installing Python scripts (using uv) for automated documentation quality:

### 1. Quick Fix Everything

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/fix_markdown.py . --recursive
```

Auto-fixes common issues:

- Adds missing frontmatter with auto-categorized documentation_type
- Adds language identifiers to code blocks
- Fixes incorrect code block closures
- Removes trailing whitespace
- Ensures proper EOF newline

### 2. Validate Documentation

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/validate_markdown.py . --recursive --severity error
```

Comprehensive validation (code-block aware):

- Checks frontmatter and documentation_type
- Validates code block structure
- Checks header hierarchy (respects code blocks)
- Validates relative links
- Exit code 1 if errors found (perfect for verification)

### 3. Add/Update Frontmatter

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/add_doc_type.py . --auto --recursive
```

Automatically categorizes and adds documentation_type:

- READMEs → explanation
- Commands → how-to
- Agents/Skills → reference
- TODOs → reference

### 4. Add Code Block Languages

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/add_code_languages.py . --recursive
```

Smart language detection for code blocks (10+ languages).

## Workflow

When working on documentation:

1. **Before starting:** Run validation to see current state
2. **While editing:** Follow Diataxis standards, add frontmatter
3. **After editing:** Run fix_markdown.py to auto-correct issues
4. **Before completion:** Run validation with `--severity error` to ensure zero errors

## Best Practices

- **Always use `--dry-run` first** when testing scripts on new documentation
- **Use validation script** instead of manual checks (respects code block boundaries)
- **Fix issues automatically** before manual intervention (saves time)
- **Verify after fixing:** `fix_markdown.py && validate_markdown.py`

### 5. Validate Links

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/validate_links.py docs/ --recursive
```

Checks all internal and external links:

- Validates relative link targets exist
- Checks external URLs (with caching)
- Reports broken anchors
- Async for fast validation

### 6. Analyze Documentation Structure

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/analyze_doc_structure.py docs/
```

Analyzes docs against Diataxis framework:

- Categorizes each document
- Identifies gaps in coverage
- Generates zensical.yml navigation
- Suggests missing documentation types

### 7. Validate Images

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/validate_images.py docs/ --check-alt --find-unused
```

Comprehensive image validation:

- Verifies all referenced images exist
- Checks for missing alt text (accessibility)
- Warns about oversized images (>500KB default)
- Detects unused images in assets folder
- Validates image format compatibility

### 8. Extract and Validate Code Examples

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/extract_code_examples.py docs/ --validate-syntax
```

Ensures code examples are correct:

- Extracts fenced code blocks from markdown
- Validates Python syntax
- Checks for deprecated API usage
- Can output examples to files for testing

### 9. Validate Changelog

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/changelog_validator.py CHANGELOG.md --suggest
```

Keep a Changelog compliance:

- Validates format and version ordering
- Checks for missing release dates
- Suggests entries from recent git commits
- Validates semver compliance

## Extended Workflow

For comprehensive documentation quality:

1. **Content validation:** `validate_markdown.py` - Frontmatter, structure
2. **Link validation:** `validate_links.py` - Internal and external links
3. **Image validation:** `validate_images.py` - References and accessibility
4. **Code validation:** `extract_code_examples.py` - Syntax correctness
5. **Structure analysis:** `analyze_doc_structure.py` - Diataxis coverage
