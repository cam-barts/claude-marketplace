---
description: Fix failing tests and improve coverage
documentation_type: how-to
---

Invoke the test-enforcer agent to fix all failing tests and improve coverage.

This command will:

1. Run tests to identify failures
2. Analyze failure root causes
3. Fix failing tests
4. Identify coverage gaps
5. Add tests for uncovered code
6. Re-run until all tests pass
7. Ensure coverage maintained or improved

The agent will NOT stop until all tests pass and coverage is maintained.
