---
name: test-writing
description: |
  Autonomous pytest test writing following modern best practices.
  Use when writing tests, test files, pytest fixtures, or test functions.
  Enforces naming conventions, fixture patterns, and assertion quality.
  Promotes property-based testing with Hypothesis.
documentation_type: reference
---

This skill is automatically invoked when Claude writes or modifies tests.

When this skill is active, Claude will:

- Follow pytest naming conventions (test_* for files and functions)
- Use Arrange-Act-Assert pattern
- Prefer real objects over mocks
- Use `mock.create_autospec()` when mocking is necessary
- Consider Hypothesis for property-based tests
- Write clear, focused assertions on outcomes
- Create appropriate fixtures in conftest.py when needed
- Use parametrization to reduce duplication

Claude should invoke this skill whenever:

- Creating new test files
- Writing test functions
- Creating pytest fixtures
- Refactoring tests
- User requests test improvements

## Available Scripts

This skill can invoke the following scripts:

- `uv run plugins/pytest-standards/scripts/generate_test_scaffold.py` - Generate test scaffolding from source code
- `uv run plugins/pytest-standards/scripts/analyze_test_smells.py` - Detect test anti-patterns and smells

Run with `--help` for full options.

## Script Usage Examples

```bash
# Generate test scaffolding for a module
uv run scripts/generate_test_scaffold.py src/module.py

# Generate with Hypothesis strategies
uv run scripts/generate_test_scaffold.py src/module.py --hypothesis

# Analyze tests for smells
uv run scripts/analyze_test_smells.py tests/

# Show only severe test smells
uv run scripts/analyze_test_smells.py tests/ --severity high
```

## Test Patterns

### Arrange-Act-Assert (AAA)

```python
def test_user_creation():
    # Arrange
    email = "user@example.com"

    # Act
    user = User.create(email=email)

    # Assert
    assert user.email == email
    assert user.is_active is True
```

### Property-Based Testing with Hypothesis

```python
from hypothesis import given, strategies as st

@given(st.integers(), st.integers())
def test_addition_commutative(a, b):
    assert add(a, b) == add(b, a)
```

### Parametrization

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("World", "WORLD"),
    ("", ""),
])
def test_uppercase(input, expected):
    assert uppercase(input) == expected
```

## Fixture Complexity Analysis

This skill monitors fixture health and complexity:

### Analyze Fixture Dependencies

```bash
uv run plugins/pytest-standards/scripts/analyze_fixtures.py tests/
```

Detects fixture issues:

- **Deep nesting:** Fixtures with depth > 3 are flagged
- **Circular dependencies:** Fixtures that depend on each other
- **Scope mismatches:** Function-scoped fixtures using session-scoped resources
- **Unused fixtures:** Fixtures defined but never used

### Fixture Best Practices

**Appropriate Scope:**

```python
# Session scope for expensive setup
@pytest.fixture(scope="session")
def database():
    db = create_database()
    yield db
    db.cleanup()

# Function scope for isolation
@pytest.fixture
def user(database):
    return database.create_user()
```

**Avoid Deep Nesting:**

```python
# Bad: Deep fixture chain
@pytest.fixture
def a(): ...
@pytest.fixture
def b(a): ...
@pytest.fixture
def c(b): ...
@pytest.fixture
def d(c): ...  # Depth 4 - too deep!

# Good: Flatten dependencies
@pytest.fixture
def test_context():
    # Create all needed resources in one fixture
    return TestContext(a=..., b=..., c=...)
```

### Generate Fixture Visualization

```bash
# Output DOT graph for visualization
uv run plugins/pytest-standards/scripts/analyze_fixtures.py tests/ --graph > fixtures.dot
dot -Tpng fixtures.dot -o fixtures.png
```

## Test Smell Detection

The skill automatically detects common anti-patterns:

| Smell | Description | Fix |
|-------|-------------|-----|
| ASSERTION_ROULETTE | Too many assertions | Split into focused tests |
| EAGER_TEST | Tests multiple behaviors | One behavior per test |
| MYSTERY_GUEST | Hidden dependencies | Make dependencies explicit |
| MOCK_OVERLOAD | Excessive mocking | Use real objects when possible |
| DEAD_TEST | Test never fails | Add meaningful assertions |

Run detection:

```bash
uv run plugins/pytest-standards/scripts/analyze_test_smells.py tests/ --severity warning
```

## Hypothesis Strategy Generation

Generate Hypothesis strategies from type hints:

```bash
uv run plugins/pytest-standards/scripts/hypothesis_strategy_generator.py src/module.py --format code
```

This generates test templates with appropriate strategies based on function signatures.
