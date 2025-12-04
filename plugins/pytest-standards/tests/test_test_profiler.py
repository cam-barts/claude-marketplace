"""Tests for test_profiler.py script."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestOutputParsing:
    """Tests for parsing pytest duration output."""

    def test_parse_duration_output(self) -> None:
        """Test parsing pytest duration output."""
        output = """
============================= slowest 5 durations ==============================
1.23s call     tests/test_slow.py::test_slow
0.45s call     tests/test_medium.py::test_medium
0.12s call     tests/test_fast.py::test_fast
0.05s setup    tests/test_fast.py::test_fast
0.01s teardown tests/test_slow.py::test_slow

============================== 3 passed in 1.86s ===============================
"""
        from test_profiler import parse_pytest_output

        report = parse_pytest_output(output)
        assert len(report.tests) >= 3
        assert report.total_duration == pytest.approx(1.86, 0.1)

    def test_identify_slow_tests(self) -> None:
        """Test identifying slow tests."""
        output = """
2.50s call     tests/test_slow.py::test_very_slow
0.10s call     tests/test_fast.py::test_fast

============================== 2 passed in 2.60s ===============================
"""
        from test_profiler import parse_pytest_output

        report = parse_pytest_output(output)
        slow = report.tests_above_threshold(1.0)

        assert len(slow) == 1
        assert "test_very_slow" in slow[0].name


class TestRecommendations:
    """Tests for performance recommendations."""

    def test_recommend_parallelization(self) -> None:
        """Test parallelization recommendations."""
        from test_profiler import ProfileReport, TestTiming, suggest_parallel_config

        report = ProfileReport(
            tests=[
                TestTiming(name="test1", file_path="test.py", duration=5.0),
                TestTiming(name="test2", file_path="test.py", duration=5.0),
                TestTiming(name="test3", file_path="test.py", duration=5.0),
            ],
            total_duration=60.0,
            total_tests=10,
        )

        config = suggest_parallel_config(report)
        assert "workers" in config
        assert config["workers"] >= 2
        assert config["estimated_time"] < config["current_time"]

    def test_analyze_bottlenecks(self) -> None:
        """Test bottleneck analysis."""
        from test_profiler import ProfileReport, TestTiming, analyze_bottlenecks

        report = ProfileReport(
            tests=[
                TestTiming(name="test_slow", file_path="test.py", duration=15.0),
                TestTiming(name="test_fast", file_path="test.py", duration=0.1),
            ],
            total_duration=15.1,
            total_tests=2,
        )

        recommendations = analyze_bottlenecks(report)
        assert len(recommendations) >= 1
        # Should recommend addressing the slow test
        assert any("slow" in r.lower() or ">10s" in r for r in recommendations)


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from test_profiler import main

        old_argv = sys.argv
        try:
            sys.argv = ["test_profiler.py", "/nonexistent/tests"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
