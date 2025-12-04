"""Tests for sync_docstrings.py script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestDocstringExtraction:
    """Tests for extracting docstrings from Python files."""

    def test_extract_function_docstrings(self, tmp_path: Path) -> None:
        """Test extracting docstrings from functions."""
        py_file = tmp_path / "module.py"
        py_file.write_text('''
def example_function(x: int, y: int) -> int:
    """Add two numbers together.

    Args:
        x: First number
        y: Second number

    Returns:
        The sum of x and y
    """
    return x + y
''')

        from sync_docstrings import extract_docstrings

        docstrings = extract_docstrings(py_file)
        assert len(docstrings) >= 1
        assert "example_function" in docstrings
        assert "Add two numbers" in docstrings["example_function"]

    def test_extract_class_docstrings(self, tmp_path: Path) -> None:
        """Test extracting docstrings from classes."""
        py_file = tmp_path / "module.py"
        py_file.write_text('''
class MyClass:
    """A sample class for testing.

    Attributes:
        value: The stored value
    """

    def __init__(self, value: int):
        """Initialize with a value."""
        self.value = value
''')

        from sync_docstrings import extract_docstrings

        docstrings = extract_docstrings(py_file)
        assert "MyClass" in docstrings
        assert "sample class" in docstrings["MyClass"]


class TestDocComparisonAnalysis:
    """Tests for comparing docstrings with documentation."""

    def test_detect_missing_docs(self, tmp_path: Path) -> None:
        """Test detecting functions without corresponding docs."""
        py_file = tmp_path / "module.py"
        py_file.write_text('''
def documented_func():
    """This function is documented."""
    pass

def undocumented_func():
    """This function has no external docs."""
    pass
''')

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "api.md").write_text("""
# API Reference

## `documented_func()`

This function is documented in the external docs.
""")

        from sync_docstrings import compare_docs

        report = compare_docs(py_file, docs_dir)
        # undocumented_func should be missing from docs
        assert any("undocumented_func" in item for item in report.missing_from_docs)

    def test_detect_outdated_docs(self, tmp_path: Path) -> None:
        """Test detecting outdated documentation."""
        py_file = tmp_path / "module.py"
        py_file.write_text('''
def my_func(x: int, y: int) -> int:
    """Add two integers.

    Args:
        x: First value
        y: Second value
    """
    return x + y
''')

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "api.md").write_text("""
# API Reference

## `my_func(x)`

Adds a single number. (outdated - only shows one parameter)
""")

        from sync_docstrings import compare_docs

        report = compare_docs(py_file, docs_dir)
        # Should detect parameter mismatch
        assert len(report.outdated) >= 1 or len(report.mismatches) >= 1


class TestSyncSuggestions:
    """Tests for generating sync suggestions."""

    def test_suggest_doc_updates(self, tmp_path: Path) -> None:
        """Test suggesting documentation updates."""
        py_file = tmp_path / "module.py"
        py_file.write_text('''
def new_function():
    """A brand new function that needs docs."""
    pass
''')

        from sync_docstrings import suggest_updates

        suggestions = suggest_updates(py_file, docs_dir=None)
        assert len(suggestions) >= 1
        assert any("new_function" in s.function_name for s in suggestions)


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from sync_docstrings import main

        old_argv = sys.argv
        try:
            sys.argv = ["sync_docstrings.py", "/nonexistent/path"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
