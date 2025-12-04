---
name: test-debugging
description: |
  Helps diagnose and fix failing tests in pytest.
  Use when tests fail unexpectedly, tests are flaky, test output is confusing,
  or need to understand test failures. Parses pytest output and suggests fixes.
documentation_type: reference
---

This skill is automatically invoked when Claude needs to debug failing tests.

When this skill is active, Claude will:

- Parse and explain pytest output clearly
- Identify root causes of test failures
- Detect flaky test patterns (tests that fail intermittently)
- Group failures by type and common cause
- Suggest debugging strategies (pdb, logging, isolation)
- Recommend test isolation improvements
- Track test duration to identify slow tests

Claude should invoke this skill whenever:

- Tests fail unexpectedly
- Test output is confusing or verbose
- User reports flaky tests
- Need to understand why tests are failing
- Debugging test infrastructure issues

## Available Scripts

This skill can invoke the following scripts:

- `uv run plugins/pytest-standards/scripts/parse_pytest_output.py` - Parse and analyze pytest output

Run with `--help` for full options.

## Script Usage Examples

```bash
# Parse pytest output from a file
uv run scripts/parse_pytest_output.py test_output.txt

# Parse from stdin (pipe pytest output)
pytest tests/ 2>&1 | uv run scripts/parse_pytest_output.py -

# Parse JUnit XML format
uv run scripts/parse_pytest_output.py --format junit report.xml

# Identify slow tests
uv run scripts/parse_pytest_output.py test_output.txt --slow-threshold 1.0

# Output as JSON for further processing
uv run scripts/parse_pytest_output.py test_output.txt --output json
```

## Understanding Test Failures

### Common Failure Patterns

#### AssertionError

- Most common failure type
- Check expected vs actual values
- Verify test data and fixtures are correct

#### ImportError / ModuleNotFoundError

- Missing dependencies
- Incorrect PYTHONPATH
- Circular imports

#### AttributeError

- Object doesn't have expected attribute
- Mock not configured correctly
- Wrong object type

#### TypeError

- Wrong number of arguments
- Wrong argument types
- API changed

#### Fixture Errors

- Fixture not found (check conftest.py location)
- Fixture scope mismatch
- Fixture dependency cycle

### Flaky Test Indicators

Tests are likely flaky if they:

- Pass/fail inconsistently across runs
- Depend on timing or sleep()
- Use shared state or global variables
- Access external services without mocking
- Depend on test execution order

### Debugging Strategies

#### 1. Isolate the failure

```bash
# Run single test
pytest tests/test_module.py::test_function -v

# Run with last failed
pytest --lf

# Run failed first
pytest --ff
```

#### 2. Add debugging output

```bash
# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb
```

#### 3. Check test isolation

```bash
# Run in random order
pytest --random-order

# Run each test in subprocess
pytest --forked
```

## Failure Report Structure

The script generates reports with:

```text
FAILURE SUMMARY
===============
Total: 50 tests
Passed: 45
Failed: 3
Errors: 2
Skipped: 0

FAILURES BY TYPE
================
AssertionError: 2
  - test_api.py::test_response_format
  - test_api.py::test_status_code

AttributeError: 1
  - test_models.py::test_user_creation

ERRORS
======
ImportError: 1
  - test_utils.py (collection error)

Fixture Error: 1
  - test_db.py::test_query (fixture 'db_session' not found)

SLOW TESTS (>1.0s)
==================
  2.34s test_integration.py::test_full_workflow
  1.56s test_api.py::test_bulk_upload

SUGGESTED ACTIONS
=================
1. Fix ImportError in test_utils.py - check imports
2. Add 'db_session' fixture to conftest.py
3. Review assertion in test_response_format
```
