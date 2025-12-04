---
name: quality-refactoring
description: |
  Guides safe, automated refactoring operations across codebases.
  Use when renaming symbols, extracting functions/classes, moving code
  between modules, or applying design patterns. Ensures refactoring
  preserves behavior.
documentation_type: reference
---

This skill is automatically invoked when Claude performs refactoring operations.

When this skill is active, Claude will:

- Analyze symbol usage across the codebase before changes
- Generate refactoring plans with all affected files
- Validate refactoring preserves API surface
- Support rename, move, and extract operations
- Create rollback instructions
- Verify changes with test suites

Claude should invoke this skill whenever:

- Renaming functions, classes, or variables across files
- Extracting code into new functions or classes
- Moving code between modules
- Applying design patterns
- Large-scale code reorganization

## Available Scripts

This skill can invoke the following scripts:

- `uv run plugins/static-analysis/scripts/refactoring_planner.py` - Plan refactoring operations

Run with `--help` for full options.

## Script Usage Examples

```bash
# Plan a rename operation
uv run scripts/refactoring_planner.py rename old_name new_name src/

# Find all usages of a symbol
uv run scripts/refactoring_planner.py find MyClass src/

# Plan moving a function to another module
uv run scripts/refactoring_planner.py move src/old.py:func src/new.py

# Preview changes without applying
uv run scripts/refactoring_planner.py rename old_name new_name src/ --dry-run

# Generate rollback script
uv run scripts/refactoring_planner.py rename old_name new_name src/ --rollback
```

## Refactoring Operations

### Rename

Safely rename symbols across the codebase:

```bash
# Rename a function
uv run scripts/refactoring_planner.py rename get_user fetch_user src/

# Rename a class
uv run scripts/refactoring_planner.py rename UserManager UserService src/

# Rename with type filter
uv run scripts/refactoring_planner.py rename Config Settings src/ --type class
```

**What gets updated:**

- Function/class definitions
- All call sites and references
- Import statements
- Type annotations
- Docstrings and comments (optional)
- Test files

### Move

Move code between modules:

```bash
# Move a function
uv run scripts/refactoring_planner.py move src/utils.py:helper src/helpers.py

# Move a class
uv run scripts/refactoring_planner.py move src/models.py:User src/entities/user.py
```

**What gets updated:**

- Source file (removes definition)
- Target file (adds definition)
- All import statements
- Relative imports adjusted

### Extract

Extract code into new functions or classes:

```bash
# Extract function (interactive)
uv run scripts/refactoring_planner.py extract function src/module.py:10-25

# Extract class
uv run scripts/refactoring_planner.py extract class src/module.py:MyClass.method
```

## Safety Checks

Before applying refactoring:

### 1. Usage Analysis

```text
USAGE ANALYSIS: get_user
========================

Definitions:
  src/services/user.py:45  def get_user(id: int) -> User:

References (23 total):
  src/api/routes.py:12     user = get_user(user_id)
  src/api/routes.py:34     return get_user(request.user_id)
  src/services/auth.py:8   from .user import get_user
  tests/test_user.py:15    result = get_user(1)
  ...

Indirect References:
  src/api/__init__.py:5    from .routes import *  # Re-exports get_user
```

### 2. Impact Assessment

```text
IMPACT ASSESSMENT
=================

Files to modify: 8
  - src/services/user.py (definition)
  - src/api/routes.py (2 references)
  - src/services/auth.py (import)
  - src/api/__init__.py (re-export)
  - tests/test_user.py (3 references)
  - tests/test_api.py (1 reference)
  - docs/api.md (documentation)

Risk Level: LOW
  - All references are direct (no dynamic access)
  - No string-based references found
  - Test coverage exists for affected code
```

### 3. Pre-flight Checks

```text
PRE-FLIGHT CHECKS
=================

✓ No syntax errors in affected files
✓ All tests pass before refactoring
✓ No uncommitted changes in affected files
✓ Target name 'fetch_user' not already in use
✓ No circular import risk detected

Ready to proceed with refactoring.
```

## Rollback Support

Every refactoring generates rollback instructions:

```bash
# Generate rollback script
uv run scripts/refactoring_planner.py rename old new src/ --rollback > rollback.sh

# Contents of rollback.sh:
#!/bin/bash
# Rollback: rename old -> new
# Generated: 2024-01-15T10:30:00

git checkout HEAD -- src/services/user.py
git checkout HEAD -- src/api/routes.py
git checkout HEAD -- tests/test_user.py
# ... etc
```

Or with git:

```bash
# Before refactoring, create a savepoint
git stash push -m "before-refactoring"

# If something goes wrong
git stash pop
```

## Best Practices

### 1. Always Run Tests First

```bash
# Verify tests pass before refactoring
pytest tests/

# Then refactor
uv run scripts/refactoring_planner.py rename old new src/

# Verify tests still pass
pytest tests/
```

### 2. Small, Incremental Changes

Instead of one large refactoring:

```bash
# Bad: Rename and restructure in one go
uv run scripts/refactoring_planner.py move-and-rename ...

# Good: Step by step
uv run scripts/refactoring_planner.py rename old_name new_name src/
git commit -m "Rename old_name to new_name"

uv run scripts/refactoring_planner.py move src/old.py:new_name src/new.py
git commit -m "Move new_name to src/new.py"
```

### 3. Review the Plan

Always use `--dry-run` first:

```bash
# Preview changes
uv run scripts/refactoring_planner.py rename old new src/ --dry-run

# Review the plan, then apply
uv run scripts/refactoring_planner.py rename old new src/
```

### 4. Handle Edge Cases

Watch for:

- **Dynamic access**: `getattr(obj, "method_name")`
- **String references**: `"method_name"` in configs
- **Reflection**: Code that inspects names at runtime
- **External dependencies**: Code in other repos that imports this

## Integration with Other Tools

### With rope (Python)

```python
# Using rope for more sophisticated refactoring
from rope.base.project import Project
from rope.refactor.rename import Rename

project = Project('.')
resource = project.get_resource('src/module.py')
renamer = Rename(project, resource, offset)
changes = renamer.get_changes('new_name')
project.do(changes)
```

### With jscodeshift (JavaScript)

```bash
# Using jscodeshift for JS/TS refactoring
npx jscodeshift -t transform.js src/
```

### With IDE Integration

Most refactoring is better done in IDEs:

- **PyCharm**: Right-click → Refactor
- **VS Code**: F2 for rename, extract with selection
- **IntelliJ**: Refactor menu

Use the script for:

- Batch operations
- CI/CD validation
- Documentation of changes
