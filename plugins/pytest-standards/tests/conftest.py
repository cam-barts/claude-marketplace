"""Pytest configuration for pytest-standards tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts directory to path so test files can import from scripts
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


@pytest.fixture
def sample_python_file(tmp_path: Path) -> Path:
    """Create a sample Python file for testing."""
    file_path = tmp_path / "sample.py"
    file_path.write_text("""
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b


def multiply(x: float, y: float) -> float:
    \"\"\"Multiply two numbers.\"\"\"
    return x * y


class Calculator:
    \"\"\"A simple calculator.\"\"\"

    def divide(self, a: int, b: int) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
""")
    return file_path


@pytest.fixture
def sample_test_file(tmp_path: Path) -> Path:
    """Create a sample test file for testing."""
    file_path = tmp_path / "test_sample.py"
    file_path.write_text("""
import pytest


def test_add():
    assert 1 + 1 == 2


def test_with_fixture(tmp_path):
    assert tmp_path.exists()


@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (0, 0, 0),
])
def test_parametrized(a, b, expected):
    assert a + b == expected
""")
    return file_path
