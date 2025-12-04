---
description: Generate coverage report and identify gaps
documentation_type: how-to
---

Generate comprehensive coverage report and identify untested code.

This command will:

1. Run `pytest --cov --cov-report=term-missing`
2. Show coverage percentage per file
3. Identify specific uncovered lines
4. Suggest tests for uncovered code paths
5. Show coverage trend (increased/decreased/maintained)
6. **Warn if coverage dropped**

Use this to understand what code needs test coverage.
