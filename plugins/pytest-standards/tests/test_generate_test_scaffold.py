"""Tests for generate_test_scaffold.py script."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestFunctionExtraction:
    """Tests for extracting function signatures."""

    def test_extract_simple_function(self, tmp_path: Path) -> None:
        """Test extracting a simple function."""
        source = tmp_path / "module.py"
        source.write_text("""
def add(a: int, b: int) -> int:
    return a + b
""")

        from generate_test_scaffold import extract_functions

        functions = extract_functions(source)
        assert len(functions) == 1
        assert functions[0].name == "add"
        assert "a" in functions[0].params
        assert "b" in functions[0].params

    def test_skip_private_functions(self, tmp_path: Path) -> None:
        """Test that private functions are skipped."""
        source = tmp_path / "module.py"
        source.write_text("""
def public_func():
    pass

def _private_func():
    pass

def __dunder_func__():
    pass
""")

        from generate_test_scaffold import extract_functions

        functions = extract_functions(source)
        # Only public_func and __dunder_func__ (dunder is not private)
        names = [f.name for f in functions]
        assert "public_func" in names
        assert "_private_func" not in names


class TestStrategyGeneration:
    """Tests for Hypothesis strategy generation."""

    def test_basic_type_strategies(self) -> None:
        """Test strategy generation for basic types."""
        from generate_test_scaffold import type_to_strategy

        assert "st.integers()" in type_to_strategy("int")
        assert "st.text()" in type_to_strategy("str")
        assert "st.booleans()" in type_to_strategy("bool")
        assert "st.floats" in type_to_strategy("float")

    def test_list_strategy(self) -> None:
        """Test strategy generation for List types."""
        from generate_test_scaffold import type_to_strategy

        result = type_to_strategy("List[int]")
        assert "st.lists" in result
        assert "st.integers()" in result

    def test_optional_strategy(self) -> None:
        """Test strategy generation for Optional types."""
        from generate_test_scaffold import type_to_strategy

        result = type_to_strategy("Optional[str]")
        assert "st.none()" in result
        assert "st.text()" in result


class TestTestGeneration:
    """Tests for test code generation."""

    def test_generate_test_function(self, tmp_path: Path) -> None:
        """Test generating a test function."""
        source = tmp_path / "module.py"
        source.write_text("""
def greet(name: str) -> str:
    return f"Hello, {name}!"
""")

        from generate_test_scaffold import extract_functions, generate_test

        functions = extract_functions(source)
        test = generate_test(functions[0])

        assert "def test_greet" in test.test_code
        assert "name" in test.test_code
        assert "@given" in test.test_code


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_file(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test main function with nonexistent file."""
        import sys

        from generate_test_scaffold import main

        old_argv = sys.argv
        try:
            sys.argv = ["generate_test_scaffold.py", "/nonexistent/path.py"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
