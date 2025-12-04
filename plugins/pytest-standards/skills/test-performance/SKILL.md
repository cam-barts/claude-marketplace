---
name: test-performance
description: |
  Optimizes test suite execution time and identifies slow tests.
  Use when test suite is slow, CI/CD times are increasing,
  need to parallelize tests, or optimizing fixture performance.
documentation_type: reference
---

This skill is automatically invoked when Claude works on test performance.

When this skill is active, Claude will:

- Profile test execution times
- Identify slow tests and suggest optimizations
- Configure pytest-xdist for parallelization
- Optimize fixture scope for performance
- Suggest test splitting strategies for CI
- Detect I/O and network bottlenecks in tests

Claude should invoke this skill whenever:

- Test suite is running slowly
- CI/CD pipeline times are increasing
- Need to set up parallel test execution
- Optimizing fixture setup/teardown
- User complains about slow tests

## Available Scripts

This skill can invoke the following scripts:

- `uv run plugins/pytest-standards/scripts/test_profiler.py` - Profile test execution

Run with `--help` for full options.

## Script Usage Examples

```bash
# Profile all tests (runs pytest with timing)
uv run scripts/test_profiler.py tests/

# Show only slow tests (>1 second)
uv run scripts/test_profiler.py tests/ --threshold 1.0

# Show top 20 slowest tests
uv run scripts/test_profiler.py tests/ --top 20

# Include fixture timing breakdown
uv run scripts/test_profiler.py tests/ --fixtures

# Suggest parallel configuration
uv run scripts/test_profiler.py tests/ --suggest-parallel

# Output as JSON
uv run scripts/test_profiler.py tests/ --output json
```

## Common Performance Issues

### 1. Slow Fixture Setup

**Problem**: Fixtures running expensive setup for each test.

**Solution**: Use appropriate fixture scope:

```python
# Bad: Creates database for every test
@pytest.fixture
def db():
    return create_database()  # Slow!

# Good: Share database across module
@pytest.fixture(scope="module")
def db():
    db = create_database()
    yield db
    db.cleanup()
```

### 2. Unnecessary I/O

**Problem**: Tests reading/writing files unnecessarily.

**Solution**: Use in-memory alternatives or `tmp_path`:

```python
# Bad: Writes to real filesystem
def test_save():
    save_to_file("/tmp/test.txt", data)

# Good: Use pytest's tmp_path fixture
def test_save(tmp_path):
    save_to_file(tmp_path / "test.txt", data)
```

### 3. Network Calls

**Problem**: Tests making real HTTP requests.

**Solution**: Mock external services:

```python
# Bad: Real network call
def test_api():
    response = requests.get("https://api.example.com")

# Good: Mock the call
def test_api(mocker):
    mocker.patch("requests.get", return_value=MockResponse())
    response = requests.get("https://api.example.com")
```

### 4. Database Operations

**Problem**: Real database operations in tests.

**Solution**: Use in-memory databases or transactions:

```python
# Use SQLite in-memory for tests
@pytest.fixture(scope="session")
def db_engine():
    return create_engine("sqlite:///:memory:")

# Or use transaction rollback
@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    yield Session(bind=connection)
    transaction.rollback()
```

### 5. Sleep Statements

**Problem**: Tests using `time.sleep()`.

**Solution**: Mock time or use async:

```python
# Bad: Actually waits
def test_timeout():
    time.sleep(5)
    assert something()

# Good: Mock the sleep
def test_timeout(mocker):
    mocker.patch("time.sleep")
    assert something()
```

## Parallelization with pytest-xdist

### Basic Parallel Execution

```bash
# Run on all available CPUs
pytest -n auto

# Run on 4 workers
pytest -n 4

# Distribute by file (default)
pytest -n auto --dist loadfile

# Distribute by test
pytest -n auto --dist load
```

### Configuration in pytest.ini

```ini
[pytest]
addopts = -n auto --dist loadfile
```

### Test Isolation for Parallel

Tests must be isolated to run in parallel:

```python
# Bad: Shared state
class TestCounter:
    counter = 0  # Shared between workers!

    def test_increment(self):
        TestCounter.counter += 1

# Good: Isolated state
class TestCounter:
    def test_increment(self):
        counter = Counter()  # Each test has own instance
        counter.increment()
```

### Grouping Tests

Use markers to control parallelization:

```python
# Mark tests that can't run in parallel
@pytest.mark.serial
def test_global_state():
    pass

# In conftest.py
def pytest_collection_modifyitems(items):
    for item in items:
        if "serial" in item.keywords:
            item.add_marker(pytest.mark.xdist_group("serial"))
```

## CI/CD Optimization

### Test Splitting

For CI, split tests across jobs:

```yaml
# GitHub Actions matrix
jobs:
  test:
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - run: pytest --splits 4 --group ${{ matrix.shard }}
```

Using pytest-split:

```bash
# Install
uv add pytest-split

# Run specific shard
pytest --splits 4 --group 1
```

### Caching

Cache expensive setup:

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/uv
      .pytest_cache
    key: pytest-${{ hashFiles('**/pyproject.toml') }}
```

### Fail Fast

Stop on first failure during development:

```bash
pytest -x  # Stop on first failure
pytest --maxfail=3  # Stop after 3 failures
```

## Profiling Report Structure

```text
TEST PERFORMANCE REPORT
=======================

Total Tests: 150
Total Duration: 45.2s
Average per Test: 0.30s

SLOWEST TESTS
=============
  12.34s  tests/test_integration.py::test_full_workflow
   5.67s  tests/test_api.py::test_bulk_upload
   3.21s  tests/test_db.py::test_complex_query
   2.45s  tests/test_export.py::test_large_export
   1.89s  tests/test_import.py::test_csv_import

FIXTURE TIMING
==============
  setup:
    8.50s  db_session (session scope)
    2.30s  test_client (function scope)
    1.20s  mock_api (function scope)

  teardown:
    0.50s  db_session

RECOMMENDATIONS
===============
1. Consider moving 'test_client' to module scope
2. Mock the external API in test_bulk_upload
3. Use pytest-xdist to parallelize: pytest -n 4
4. Split integration tests into separate CI job

PARALLEL CONFIGURATION
======================
Suggested pytest.ini:

[pytest]
addopts = -n 4 --dist loadfile

Estimated parallel time: ~15s (3x speedup)
```
