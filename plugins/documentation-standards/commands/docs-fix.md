---
description: Auto-fix documentation issues where possible
documentation_type: how-to
---

Automatically fix documentation issues that can be corrected programmatically.

This command will:

1. Run rumdl with `--fix` to auto-correct formatting issues
2. Add missing `documentation_type` frontmatter to files (will ask which type to use)
3. Fix common markdown structure problems
4. Report issues that require manual intervention

After running this command, use `/docs-check` to verify all issues are resolved.

Note: Some vale suggestions and complex formatting issues may still require manual fixes.
