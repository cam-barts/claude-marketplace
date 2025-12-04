---
description: Run all tests with coverage and ensure they pass
documentation_type: how-to
---

Run the complete test suite with coverage reporting and enforce zero-failure policy.

This command will:

1. Run all tests with `pytest -v`
2. Generate coverage report with `pytest --cov`
3. Show missing lines with `--cov-report=term-missing`
4. Identify failing tests
5. Report coverage metrics
6. **Fail if any tests don't pass**
7. **Fail if coverage dropped**

Use this command to ensure test suite health before committing changes.
