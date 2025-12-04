---
name: test-coverage
description: |
  Ensures test coverage is maintained and improved.
  Use when running tests, checking coverage, or adding new code.
  Automatically suggests tests for uncovered code paths.
  Never allows coverage to drop.
documentation_type: reference
---

This skill is automatically invoked when Claude works on code that affects test coverage.

When this skill is active, Claude will:

- Run pytest with coverage before and after changes
- Identify uncovered code paths
- Suggest specific tests for uncovered lines
- Ensure coverage doesn't drop
- Add tests proactively when adding new code

Claude should invoke this skill whenever:

- Adding new functions or methods
- Modifying existing code
- User requests coverage improvements
- Running tests
- Coverage drops below previous level

## Available Scripts

This skill can invoke the following scripts:

- `uv run plugins/pytest-standards/scripts/coverage_analyzer.py` - Analyze coverage reports with complexity weighting

Run with `--help` for full options.

## Script Usage Examples

```bash
# Analyze coverage from JSON report
uv run scripts/coverage_analyzer.py .coverage.json

# Show only files below 80% coverage
uv run scripts/coverage_analyzer.py .coverage.json --threshold 80

# Weight coverage by complexity
uv run scripts/coverage_analyzer.py .coverage.json --weight-by-complexity

# Output as JSON for CI integration
uv run scripts/coverage_analyzer.py .coverage.json --output json
```

## Coverage Workflow

### Generate Coverage Report

```bash
# Run tests with coverage
pytest --cov=src --cov-report=json --cov-report=term-missing

# Generate detailed HTML report
pytest --cov=src --cov-report=html
```

### Analyze Gaps

```bash
# Find uncovered complex code (high priority)
uv run scripts/coverage_analyzer.py .coverage.json --weight-by-complexity --threshold 70

# Get prioritized list of files needing tests
uv run scripts/coverage_analyzer.py .coverage.json --output json | jq '.priority_files'
```

### CI Integration

```yaml
# In GitHub Actions
- name: Check coverage
  run: |
    pytest --cov=src --cov-report=json
    uv run scripts/coverage_analyzer.py .coverage.json --threshold 80 --fail-under
```

## Best Practices

1. **Run coverage before and after changes** to ensure no regression
2. **Focus on complex code first** - use `--weight-by-complexity`
3. **Set thresholds per-module** for granular control
4. **Exclude generated code** from coverage requirements

## Branch Coverage

Line coverage alone can miss untested conditional paths. Branch coverage ensures all decision points are tested.

### Enable Branch Coverage

```bash
# Run with branch coverage
pytest --cov=src --cov-branch --cov-report=term-missing

# In pyproject.toml
[tool.coverage.run]
branch = true
```

### Understanding Branch Coverage

```python
def process(value, flag):
    if flag:           # Branch point 1
        result = value * 2
    else:
        result = value

    if result > 10:    # Branch point 2
        return "high"
    return "low"
```

For full branch coverage, tests must cover:

- `flag=True` AND `flag=False`
- `result > 10` AND `result <= 10`

### Analyze Branch Coverage

```bash
# Coverage analyzer shows branch information
uv run scripts/coverage_analyzer.py coverage.json --branch

# Output includes:
# - Missing branches per file
# - Branch coverage percentage
# - Suggested test cases for uncovered branches
```

### Prioritize by Complexity

Focus testing effort on complex conditional logic:

```bash
# High-complexity uncovered code is highest priority
uv run scripts/coverage_analyzer.py coverage.json --weight-by-complexity --branch

# This ranks files by:
# 1. Number of untested branches
# 2. Cyclomatic complexity of untested code
# 3. Overall coverage percentage
```

## Mutation Testing Concepts

Coverage doesn't guarantee test quality. Consider these patterns:

### Weak Tests

```python
def test_add():
    result = add(2, 3)
    assert result  # Passes even if add() returns True!
```

### Strong Tests

```python
def test_add():
    result = add(2, 3)
    assert result == 5  # Specific assertion
```

### Detecting Weak Tests

Look for tests that:

- Assert truthiness instead of values
- Never check edge cases
- Mock too many dependencies
- Have no assertions at all

The `analyze_test_smells.py` script can detect some of these patterns.
