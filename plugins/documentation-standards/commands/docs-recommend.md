---
description: Analyze code changes and recommend documentation updates
documentation_type: how-to
---

Analyze recent code changes and provide intelligent recommendations for documentation updates.

This command will:

## Analysis

1. **Detect code changes** using git diff or recent file modifications
2. **Identify change types**:
    - New functions/classes/modules → Suggest reference documentation
    - API changes → Suggest updating how-to guides and tutorials
    - Bug fixes → Suggest updating troubleshooting documentation
    - New features → Suggest tutorials and how-to guides
    - Deprecated code → Suggest removing or updating related documentation
    - Configuration changes → Suggest updating reference docs

3. **Cross-reference with existing documentation**:
    - Find documentation that mentions changed code
    - Identify gaps where documentation should exist but doesn't
    - Detect outdated examples or instructions

## Recommendations

The command will suggest:

- **Add new documentation** - "New function `processData()` added. Consider adding reference documentation."
- **Update existing docs** - "API changed in `auth.py`. Update how-to guides that reference authentication."
- **Remove deprecated docs** - "Function `oldLogin()` removed. Remove or update related documentation."
- **Specify documentation type** - Recommend tutorial vs how-to vs reference vs explanation based on change context

## Usage Examples

```bash
# Analyze recent changes (last commit)
/docs-recommend

# Analyze specific files
/docs-recommend src/api.py

# Analyze changes between commits
/docs-recommend --since HEAD~5
```

## Output

For each recommendation, you'll get:

- What changed in the code
- What documentation action is needed (add/update/remove)
- Suggested documentation type (tutorial/how-to/reference/explanation)
- Specific files or sections to update
- Reasoning for the recommendation

Use this command after making code changes to ensure documentation stays in sync with your codebase.
