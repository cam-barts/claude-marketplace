"""Tests for parse_pytest_output.py script."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestOutputParsing:
    """Tests for parsing pytest output."""

    def test_parse_passed_test(self) -> None:
        """Test parsing passed test output."""
        output = """
============================= test session starts ==============================
collected 1 item

tests/test_example.py .                                                  [100%]

============================== 1 passed in 0.01s ===============================
"""
        from parse_pytest_output import parse_pytest_output

        result = parse_pytest_output(output)
        assert result.passed == 1
        assert result.failed == 0
        assert result.total == 1

    def test_parse_failed_test(self) -> None:
        """Test parsing failed test output."""
        output = """
============================= test session starts ==============================
collected 1 item

tests/test_example.py F                                                  [100%]

=================================== FAILURES ===================================
________________________________ test_example __________________________________

    def test_example():
>       assert 1 == 2
E       assert 1 == 2

tests/test_example.py:3: AssertionError
=========================== short test summary info ============================
FAILED tests/test_example.py::test_example - assert 1 == 2
============================== 1 failed in 0.01s ===============================
"""
        from parse_pytest_output import parse_pytest_output

        result = parse_pytest_output(output)
        assert result.passed == 0
        assert result.failed == 1
        assert len(result.failures) == 1
        assert "test_example" in result.failures[0].test_name

    def test_parse_mixed_results(self) -> None:
        """Test parsing mixed pass/fail output."""
        output = """
============================= test session starts ==============================
collected 3 items

tests/test_example.py .F.                                                [100%]

=================================== FAILURES ===================================
________________________________ test_fail _____________________________________

    def test_fail():
>       assert False

tests/test_example.py:5: AssertionError
=========================== short test summary info ============================
FAILED tests/test_example.py::test_fail
========================= 2 passed, 1 failed in 0.05s =========================
"""
        from parse_pytest_output import parse_pytest_output

        result = parse_pytest_output(output)
        assert result.passed == 2
        assert result.failed == 1


class TestFailureAnalysis:
    """Tests for failure analysis."""

    def test_extract_failure_location(self) -> None:
        """Test extracting failure location."""
        output = """
________________________________ test_example __________________________________

    def test_example():
>       assert 1 == 2
E       assert 1 == 2

tests/test_example.py:3: AssertionError
"""
        from parse_pytest_output import extract_failures

        failures = extract_failures(output)
        assert len(failures) >= 1
        failure = failures[0]
        assert "test_example.py" in failure.file_path
        assert failure.line_number == 3

    def test_suggest_fix_for_assertion(self) -> None:
        """Test fix suggestion for assertion error."""
        from parse_pytest_output import TestFailure, suggest_fix

        failure = TestFailure(
            test_name="test_example",
            file_path="tests/test_example.py",
            line_number=3,
            error_type="AssertionError",
            error_message="assert 1 == 2",
        )

        suggestion = suggest_fix(failure)
        assert suggestion is not None
        assert "expected" in suggestion.lower() or "assertion" in suggestion.lower()


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_reads_stdin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main can read from stdin."""
        import io
        import sys

        from parse_pytest_output import main

        test_input = "1 passed in 0.01s"
        monkeypatch.setattr("sys.stdin", io.StringIO(test_input))

        old_argv = sys.argv
        try:
            sys.argv = ["parse_pytest_output.py", "-"]
            # Should not raise
            result = main()
            assert result in (0, 1)
        finally:
            sys.argv = old_argv
