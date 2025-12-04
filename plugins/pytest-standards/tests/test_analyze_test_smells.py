"""Tests for analyze_test_smells.py script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestSmellDetection:
    """Tests for detecting test smells."""

    def test_detect_assertion_roulette(self, tmp_path: Path) -> None:
        """Test detection of assertion roulette smell."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("""
def test_many_assertions():
    assert 1 == 1
    assert 2 == 2
    assert 3 == 3
    assert 4 == 4
    assert 5 == 5
    assert 6 == 6
""")

        from analyze_test_smells import analyze_file

        smells = analyze_file(test_file)
        smell_types = [s.smell_type for s in smells]
        assert "ASSERTION_ROULETTE" in smell_types

    def test_detect_no_assertions(self, tmp_path: Path) -> None:
        """Test detection of tests without assertions."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("""
def test_no_assert():
    x = 1 + 1
    y = x * 2
""")

        from analyze_test_smells import analyze_file

        smells = analyze_file(test_file)
        smell_types = [s.smell_type for s in smells]
        assert "DEAD_TEST" in smell_types

    def test_detect_mock_overload(self, tmp_path: Path) -> None:
        """Test detection of excessive mocking."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text(
            """
from unittest import mock

def test_too_many_mocks():
    with mock.patch('a'), mock.patch('b'), mock.patch('c'), \\
            mock.patch('d'), mock.patch('e'):
        assert True
"""
        )

        from analyze_test_smells import analyze_file

        smells = analyze_file(test_file)
        smell_types = [s.smell_type for s in smells]
        assert "MOCK_OVERLOAD" in smell_types

    def test_clean_test_no_smells(self, tmp_path: Path) -> None:
        """Test that clean tests have no smells."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("""
def test_clean():
    # Arrange
    value = 5

    # Act
    result = value * 2

    # Assert
    assert result == 10
""")

        from analyze_test_smells import analyze_file

        smells = analyze_file(test_file)
        # Should have no high-severity smells
        high_smells = [s for s in smells if s.severity == "high"]
        assert len(high_smells) == 0


class TestReportGeneration:
    """Tests for report generation."""

    def test_analyze_directory(self, tmp_path: Path) -> None:
        """Test analyzing a directory of tests."""
        (tmp_path / "tests").mkdir()
        test_file = tmp_path / "tests" / "test_example.py"
        test_file.write_text("""
def test_example():
    assert True
""")

        from analyze_test_smells import analyze_tests

        report = analyze_tests(tmp_path / "tests")
        assert report.total_tests >= 1


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from analyze_test_smells import main

        old_argv = sys.argv
        try:
            sys.argv = ["analyze_test_smells.py", "/nonexistent/path"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
