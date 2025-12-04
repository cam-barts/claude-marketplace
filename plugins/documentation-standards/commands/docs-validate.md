---
description: Comprehensive documentation validation with zero-error enforcement
documentation_type: how-to
---

Perform comprehensive documentation validation and DO NOT stop until all issues are resolved.

This command invokes the **docs-enforcer** agent with strict enforcement:

- All rumdl errors must be fixed
- All vale issues must be addressed
- All files must have valid `documentation_type` frontmatter
- All project-specific documentation tools must pass
- Zero errors tolerated

Use this command when you want to ensure documentation is production-ready and meets all standards before publishing or committing.

The agent will iterate through fixes until everything passes or requires your manual intervention.
