---
name: documentation-recommendations
description: |
  Proactively recommends documentation updates when code changes occur.
  Use when writing code, adding functions, modifying APIs, refactoring, or implementing features.
  Suggests adding reference docs, tutorials, how-to guides based on code changes.
  Detects missing, outdated, or deprecated documentation.
documentation_type: reference
---

This skill is automatically invoked when Claude makes code changes or analyzes a codebase.

When this skill is active, Claude will:

- Monitor code changes for documentation impacts
- Proactively suggest documentation updates without being asked
- Identify gaps between code and documentation
- Recommend specific documentation types based on the change
- Ensure documentation stays in sync with the codebase

Claude should invoke this skill whenever:

- Writing or modifying code files
- Adding new functions, classes, or modules
- Changing API endpoints or interfaces
- Deprecating or removing code
- Fixing bugs that affect user-facing behavior
- Modifying configuration options
- Completing a feature implementation
- User requests code analysis or refactoring

## Recommendation Strategy

### New Code

- **New functions/classes** → Suggest reference documentation with examples
- **New features** → Suggest tutorial (for learning) and how-to (for tasks)
- **New API endpoints** → Suggest reference docs and how-to guides

### Changed Code

- **API changes** → Identify docs that reference the API, suggest updates
- **Behavior changes** → Update how-to guides and tutorials
- **Configuration changes** → Update reference documentation

### Removed Code

- **Deprecated functions** → Flag documentation for removal or update
- **Removed features** → Suggest removing related documentation or adding migration guide

## Proactive Behavior

This skill makes Claude proactive about documentation:

- After writing new code: "I've added a new authentication function. Should I create reference documentation for it?"
- After modifying an API: "The login endpoint has changed. I'll update the API documentation and how-to guides."
- After fixing a bug: "This bug fix affects the authentication flow. I should update the troubleshooting docs."

The skill ensures documentation is treated as a first-class concern, not an afterthought.

## Documentation Scripts

When recommendations are acted upon, use the plugin's scripts to ensure quality:

### After Creating New Documentation

```bash
# Add appropriate documentation_type frontmatter
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/add_doc_type.py new-doc.md <type>
# Where <type> is: tutorial, how-to, reference, or explanation

# Fix common issues automatically
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/fix_markdown.py new-doc.md

# Validate before considering complete
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/validate_markdown.py new-doc.md --severity error
```

### Bulk Documentation Updates

When code changes affect multiple docs:

```bash
# Auto-categorize all docs and fix issues
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/fix_markdown.py docs/ --recursive

# Validate all documentation
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/validate_markdown.py docs/ -r --severity error
```

### Quick Checks

Before recommending documentation changes, verify current state:

```bash
# Check what documentation exists
find . -name "*.md" -type f

# Validate existing docs
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/validate_markdown.py . -r --json
```

## Integration with Recommendations

When making documentation recommendations:

1. **Be specific** about documentation type needed (tutorial/how-to/reference/explanation)
2. **Suggest file location** following Diataxis organization
3. **Offer to create** the documentation if user agrees
4. **Use scripts** to ensure quality when creating/updating docs
5. **Validate** before marking recommendation as complete

Example workflow:

```text
User adds new API endpoint
  → Recommend: "I'll add reference documentation for this endpoint"
  → Create: docs/api/reference/auth-endpoint.md
  → Add frontmatter: documentation_type: reference
  → Run fix_markdown.py to clean up
  → Run validate_markdown.py to ensure no errors
  → Complete: Documentation meets standards
```

## Docstring Analysis

This skill can analyze Python docstrings and compare them with external documentation:

### Sync Docstrings with Documentation

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/sync_docstrings.py src/ docs/api/
```

Compares code docstrings with external docs:

- Parses Google, NumPy, and Sphinx docstring styles
- Detects out-of-sync function descriptions
- Identifies missing parameter documentation
- Finds documented functions that no longer exist in code

### Docstring Analysis Workflow

When this skill detects documentation gaps:

1. **Scan source code** for functions with docstrings
2. **Compare with documentation** to find discrepancies
3. **Report mismatches:**
    - Functions documented in code but not in docs
    - Parameters missing from documentation
    - Documentation for removed functions
4. **Suggest updates** to bring docs in sync

Example:

```bash
# Check for sync issues
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/sync_docstrings.py src/ docs/ --output json

# Output shows:
{
  "issues": [
    {"function": "authenticate", "type": "param_mismatch",
     "details": "Parameters not documented: timeout, retry_count"}
  ]
}
```

### Proactive Docstring Recommendations

When Claude modifies a function with a docstring:

- Check if external documentation exists for this function
- Compare docstring with external docs
- Recommend updates if they're out of sync
- Offer to update documentation automatically

This ensures docstrings and documentation stay synchronized as code evolves.
