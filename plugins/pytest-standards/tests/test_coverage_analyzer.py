"""Tests for coverage_analyzer.py script."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestCoverageReportParsing:
    """Tests for parsing coverage reports."""

    def test_parse_json_report(self, tmp_path: Path) -> None:
        """Test parsing a coverage JSON report."""
        report = {
            "meta": {"timestamp": "2024-01-01"},
            "files": {
                "src/module.py": {
                    "executed_lines": [1, 2, 3, 4, 5],
                    "missing_lines": [6, 7],
                    "summary": {
                        "covered_lines": 5,
                        "num_statements": 7,
                        "percent_covered": 71.4,
                    },
                },
            },
            "totals": {
                "covered_lines": 5,
                "num_statements": 7,
                "percent_covered": 71.4,
            },
        }

        report_file = tmp_path / "coverage.json"
        report_file.write_text(json.dumps(report))

        from coverage_analyzer import parse_coverage_json

        result = parse_coverage_json(report_file)
        assert len(result.files) == 1
        assert result.total_coverage == pytest.approx(71.4, 0.1)


class TestFilePrioritization:
    """Tests for file prioritization."""

    def test_prioritize_by_coverage(self, tmp_path: Path) -> None:
        """Test that files are prioritized by coverage."""
        report = {
            "meta": {},
            "files": {
                "high_coverage.py": {
                    "executed_lines": list(range(90)),
                    "missing_lines": list(range(90, 100)),
                    "summary": {
                        "covered_lines": 90,
                        "num_statements": 100,
                        "percent_covered": 90,
                    },
                },
                "low_coverage.py": {
                    "executed_lines": list(range(30)),
                    "missing_lines": list(range(30, 100)),
                    "summary": {
                        "covered_lines": 30,
                        "num_statements": 100,
                        "percent_covered": 30,
                    },
                },
            },
            "totals": {
                "covered_lines": 120,
                "num_statements": 200,
                "percent_covered": 60,
            },
        }

        report_file = tmp_path / "coverage.json"
        report_file.write_text(json.dumps(report))

        from coverage_analyzer import parse_coverage_json, prioritize_files

        parsed = parse_coverage_json(report_file)
        prioritized = prioritize_files(parsed.files)

        # Low coverage file should be first (higher priority)
        assert prioritized[0].name == "low_coverage.py"


class TestThresholds:
    """Tests for coverage thresholds."""

    def test_files_below_threshold(self, tmp_path: Path) -> None:
        """Test finding files below threshold."""
        report = {
            "meta": {},
            "files": {
                "above.py": {
                    "executed_lines": list(range(90)),
                    "missing_lines": list(range(90, 100)),
                    "summary": {
                        "covered_lines": 90,
                        "num_statements": 100,
                        "percent_covered": 90,
                    },
                },
                "below.py": {
                    "executed_lines": list(range(70)),
                    "missing_lines": list(range(70, 100)),
                    "summary": {
                        "covered_lines": 70,
                        "num_statements": 100,
                        "percent_covered": 70,
                    },
                },
            },
            "totals": {"percent_covered": 80},
        }

        report_file = tmp_path / "coverage.json"
        report_file.write_text(json.dumps(report))

        from coverage_analyzer import files_below_threshold, parse_coverage_json

        parsed = parse_coverage_json(report_file)
        below = files_below_threshold(parsed.files, threshold=80)

        assert len(below) == 1
        assert below[0].name == "below.py"


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_file(self) -> None:
        """Test main with nonexistent file."""
        import sys

        from coverage_analyzer import main

        old_argv = sys.argv
        try:
            sys.argv = ["coverage_analyzer.py", "/nonexistent/coverage.json"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
