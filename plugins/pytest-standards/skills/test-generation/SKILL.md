---
name: test-generation
description: |
  Generates test scaffolding and suggests test cases for Python code.
  Use when creating tests for new code, adding tests to untested code,
  generating Hypothesis strategies, or creating test fixtures.
  Follows pytest naming conventions and modern testing best practices.
documentation_type: reference
---

This skill is automatically invoked when Claude needs to generate tests for code.

When this skill is active, Claude will:

- Generate test file scaffolding matching naming conventions (test_*.py)
- Create test function stubs for all public functions
- Generate appropriate imports based on the source module
- Add Hypothesis strategy decorators for typed functions when appropriate
- Generate parametrized test cases for edge cases
- Create conftest.py fixtures from common patterns
- Follow Arrange-Act-Assert pattern in generated tests

Claude should invoke this skill whenever:

- Creating tests for new source code
- Adding tests to existing untested code
- User asks to generate test scaffolding
- User wants Hypothesis property-based tests
- User needs fixture generation

## Available Scripts

This skill can invoke the following scripts:

- `uv run plugins/pytest-standards/scripts/generate_test_scaffold.py` - Generate test scaffolding

Run with `--help` for full options.

## Script Usage Examples

```bash
# Generate test file for a single source file
uv run scripts/generate_test_scaffold.py src/mymodule.py

# Generate tests for a directory
uv run scripts/generate_test_scaffold.py src/ --output tests/

# Generate with Hypothesis strategies
uv run scripts/generate_test_scaffold.py src/mymodule.py --hypothesis

# Preview what would be generated
uv run scripts/generate_test_scaffold.py src/mymodule.py --dry-run

# Generate class-based tests
uv run scripts/generate_test_scaffold.py src/mymodule.py --style class
```

## Generated Test Structure

For a source file like `src/calculator.py`:

```python
# src/calculator.py
def add(a: int, b: int) -> int:
    return a + b

def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

The script generates `tests/test_calculator.py`:

```python
"""Tests for calculator module."""
import pytest
from hypothesis import given, strategies as st

from src.calculator import add, divide


class TestAdd:
    """Tests for add function."""

    def test_add_basic(self):
        """Test basic addition."""
        # Arrange
        a, b = 1, 2
        # Act
        result = add(a, b)
        # Assert
        assert result == 3

    @given(a=st.integers(), b=st.integers())
    def test_add_commutative(self, a: int, b: int):
        """Property: addition is commutative."""
        assert add(a, b) == add(b, a)


class TestDivide:
    """Tests for divide function."""

    def test_divide_basic(self):
        """Test basic division."""
        # Arrange
        a, b = 10.0, 2.0
        # Act
        result = divide(a, b)
        # Assert
        assert result == 5.0

    def test_divide_by_zero_raises(self):
        """Test that division by zero raises ValueError."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(1.0, 0.0)
```

## Hypothesis Strategy Generation

For typed functions, the script generates appropriate Hypothesis strategies:

| Python Type | Hypothesis Strategy |
|-------------|---------------------|
| `int` | `st.integers()` |
| `float` | `st.floats(allow_nan=False)` |
| `str` | `st.text()` |
| `bool` | `st.booleans()` |
| `list[T]` | `st.lists(st.T())` |
| `dict[K, V]` | `st.dictionaries(st.K(), st.V())` |
| `Optional[T]` | `st.none() \| st.T()` |
| Custom classes | `st.builds(ClassName)` |
| Dataclasses | `st.builds()` with field strategies |

## Fixture Generation

When common patterns are detected, the script suggests fixtures for `conftest.py`:

```python
# conftest.py
import pytest

@pytest.fixture
def sample_user():
    """Provide a sample user for testing."""
    return User(name="test", email="test@example.com")

@pytest.fixture
def db_session(tmp_path):
    """Provide a temporary database session."""
    db_path = tmp_path / "test.db"
    session = create_session(db_path)
    yield session
    session.close()
```
