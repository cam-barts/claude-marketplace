#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
# ]
# ///
"""
Parse and analyze pytest output to identify failures and suggest fixes.

Parses:
- Standard pytest terminal output
- JUnit XML reports
- JSON reports (pytest-json-report)

Provides:
- Failure summaries grouped by type
- Flaky test detection
- Slow test identification
- Actionable fix suggestions

Usage:
    uv run parse_pytest_output.py [OPTIONS] INPUT

Examples
--------
    pytest tests/ 2>&1 | uv run parse_pytest_output.py -
    uv run parse_pytest_output.py test_output.txt
    uv run parse_pytest_output.py --format junit report.xml
    uv run parse_pytest_output.py output.txt --slow-threshold 2.0
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


class TestResult(Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    XFAILED = "xfailed"
    XPASSED = "xpassed"


@dataclass
class TestCase:
    """Information about a single test case."""

    name: str
    file_path: str
    class_name: str | None = None
    result: TestResult = TestResult.PASSED
    duration: float = 0.0
    error_type: str | None = None
    error_message: str | None = None
    traceback: str | None = None
    stdout: str | None = None
    stderr: str | None = None


@dataclass
class ParsedReport:
    """Parsed test report."""

    tests: list[TestCase] = field(default_factory=list)
    total_duration: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> list[TestCase]:
        return [t for t in self.tests if t.result == TestResult.PASSED]

    @property
    def failed(self) -> list[TestCase]:
        return [t for t in self.tests if t.result == TestResult.FAILED]

    @property
    def errors(self) -> list[TestCase]:
        return [t for t in self.tests if t.result == TestResult.ERROR]

    @property
    def skipped(self) -> list[TestCase]:
        return [t for t in self.tests if t.result == TestResult.SKIPPED]


def parse_pytest_terminal(content: str) -> ParsedReport:
    """Parse standard pytest terminal output."""
    report = ParsedReport()

    # Extract test results from short summary
    # Pattern: test_file.py::test_name PASSED/FAILED/ERROR
    result_pattern = re.compile(
        r"^([\w/\\_.-]+\.py)(?:::(\w+))?(?:::(\w+))?\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)",
        re.MULTILINE,
    )

    for match in result_pattern.finditer(content):
        file_path = match.group(1)
        class_name = match.group(2) if match.group(3) else None
        test_name = match.group(3) or match.group(2) or "unknown"
        result_str = match.group(4)

        result_map = {
            "PASSED": TestResult.PASSED,
            "FAILED": TestResult.FAILED,
            "ERROR": TestResult.ERROR,
            "SKIPPED": TestResult.SKIPPED,
            "XFAIL": TestResult.XFAILED,
            "XPASS": TestResult.XPASSED,
        }

        report.tests.append(
            TestCase(
                name=test_name,
                file_path=file_path,
                class_name=class_name,
                result=result_map.get(result_str, TestResult.PASSED),
            ),
        )

    # Extract failure details
    # Pattern: FAILED test_file.py::test_name - ErrorType: message
    failure_pattern = re.compile(
        r"FAILED\s+([\w/\\_.-]+\.py)(?:::(\w+))?(?:::(\w+))?\s*-\s*(\w+):\s*(.+)",
        re.MULTILINE,
    )

    for match in failure_pattern.finditer(content):
        file_path = match.group(1)
        test_name = match.group(3) or match.group(2) or "unknown"
        error_type = match.group(4)
        error_message = match.group(5)

        # Find matching test case and update it
        for test in report.tests:
            if test.file_path == file_path and test.name == test_name:
                test.error_type = error_type
                test.error_message = error_message
                break

    # Extract detailed failure sections
    failure_section_pattern = re.compile(
        r"_{10,}\s+([\w/\\_.-]+\.py)(?:::(\w+))?(?:::(\w+))?\s+_{10,}\s*\n(.*?)(?=_{10,}|\Z)",
        re.DOTALL,
    )

    for match in failure_section_pattern.finditer(content):
        file_path = match.group(1)
        test_name = match.group(3) or match.group(2) or "unknown"
        traceback = match.group(4).strip()

        # Extract error type from traceback
        error_match = re.search(
            r"^E\s+(\w+Error|\w+Exception):\s*(.+)$", traceback, re.MULTILINE
        )

        for test in report.tests:
            if test.file_path == file_path and test.name == test_name:
                test.traceback = traceback
                if error_match:
                    test.error_type = error_match.group(1)
                    test.error_message = error_match.group(2)
                break

    # Extract duration from summary line
    # Pattern: === 10 passed, 2 failed in 5.23s ===
    duration_pattern = re.compile(r"in\s+([\d.]+)s?\s*={3,}")
    duration_match = duration_pattern.search(content)
    if duration_match:
        report.total_duration = float(duration_match.group(1))

    # Extract individual test durations if available (pytest -v --durations=0)
    duration_line_pattern = re.compile(
        r"([\d.]+)s\s+(call|setup|teardown)?\s*([\w/\\_.-]+\.py)(?:::(\w+))?(?:::(\w+))?",
    )

    for match in duration_line_pattern.finditer(content):
        duration = float(match.group(1))
        file_path = match.group(3)
        test_name = match.group(5) or match.group(4) or "unknown"

        for test in report.tests:
            if test.file_path == file_path and test.name == test_name:
                test.duration = max(test.duration, duration)
                break

    # Extract warnings
    warning_pattern = re.compile(
        r"warnings summary.*?(?:={10,}|$)", re.DOTALL | re.IGNORECASE
    )
    warning_match = warning_pattern.search(content)
    if warning_match:
        warning_lines = warning_match.group(0).split("\n")
        for line in warning_lines:
            line = line.strip()
            if (
                line
                and not line.startswith("=")
                and "warnings summary" not in line.lower()
            ):
                report.warnings.append(line)

    return report


def parse_junit_xml(content: str) -> ParsedReport:
    """Parse JUnit XML format."""
    report = ParsedReport()

    try:
        # XML is from trusted pytest JUnit output, not untrusted user input
        root = ET.fromstring(content)  # noqa: S314
    except ET.ParseError as e:
        console.print(f"[red]Error parsing XML:[/red] {e}", file=sys.stderr)
        return report

    # Handle both testsuite and testsuites root elements
    testsuites = root.findall(".//testsuite")
    if not testsuites and root.tag == "testsuite":
        testsuites = [root]

    for testsuite in testsuites:
        for testcase in testsuite.findall("testcase"):
            name = testcase.get("name", "unknown")
            classname = testcase.get("classname", "")
            file_path = testcase.get("file", classname.replace(".", "/") + ".py")
            duration = float(testcase.get("time", 0))

            # Determine result
            result = TestResult.PASSED
            error_type = None
            error_message = None
            traceback = None

            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped = testcase.find("skipped")

            if failure is not None:
                result = TestResult.FAILED
                error_type = failure.get("type", "AssertionError")
                error_message = failure.get("message", "")
                traceback = failure.text

            elif error is not None:
                result = TestResult.ERROR
                error_type = error.get("type", "Error")
                error_message = error.get("message", "")
                traceback = error.text

            elif skipped is not None:
                result = TestResult.SKIPPED
                error_message = skipped.get("message", "")

            # Get stdout/stderr
            stdout_elem = testcase.find("system-out")
            stderr_elem = testcase.find("system-err")

            report.tests.append(
                TestCase(
                    name=name,
                    file_path=file_path,
                    class_name=classname if classname else None,
                    result=result,
                    duration=duration,
                    error_type=error_type,
                    error_message=error_message,
                    traceback=traceback,
                    stdout=stdout_elem.text if stdout_elem is not None else None,
                    stderr=stderr_elem.text if stderr_elem is not None else None,
                ),
            )

        # Get total duration
        report.total_duration = float(testsuite.get("time", 0))

    return report


def suggest_fix(test: TestCase) -> str:
    """Suggest a fix based on error type."""
    if not test.error_type:
        return "Review test output for details"

    suggestions = {
        "AssertionError": "Check expected vs actual values. Verify test data.",
        "AttributeError": "Object missing attribute. Check mock config or type.",
        "TypeError": "Wrong argument type or count. Check function signature.",
        "KeyError": "Dictionary key not found. Verify data structure.",
        "ValueError": "Invalid value. Check input validation and formats.",
        "ImportError": "Module not found. Check PYTHONPATH and dependencies.",
        "ModuleNotFoundError": "Module not found. Install package or fix import.",
        "FileNotFoundError": "File not found. Check file paths and fixtures.",
        "PermissionError": "Permission denied. Check file permissions.",
        "ConnectionError": "Network failed. Mock external services.",
        "TimeoutError": "Operation timed out. Increase timeout or mock.",
        "RuntimeError": "Runtime error. Review stack trace for cause.",
        "FixtureLookupError": "Fixture not found. Check conftest.py.",
    }

    for error_type, suggestion in suggestions.items():
        if error_type in test.error_type:
            return suggestion

    return "Review stack trace and error message for details"


def group_failures_by_type(tests: list[TestCase]) -> dict[str, list[TestCase]]:
    """Group failed tests by error type."""
    groups: dict[str, list[TestCase]] = {}
    for test in tests:
        error_type = test.error_type or "Unknown"
        if error_type not in groups:
            groups[error_type] = []
        groups[error_type].append(test)
    return groups


def detect_flaky_patterns(tests: list[TestCase]) -> list[str]:
    """Detect patterns that suggest flaky tests."""
    patterns = []

    for test in tests:
        if test.result != TestResult.FAILED:
            continue

        traceback = (test.traceback or "").lower()
        error_msg = (test.error_message or "").lower()
        combined = traceback + " " + error_msg

        # Check for timing-related issues
        if any(
            word in combined
            for word in ["sleep", "timeout", "time.time", "asyncio.wait"]
        ):
            patterns.append(f"{test.file_path}::{test.name} - Timing-dependent test")

        # Check for randomness
        if any(word in combined for word in ["random", "uuid", "shuffle"]):
            patterns.append(f"{test.file_path}::{test.name} - Uses random values")

        # Check for network/external calls
        if any(
            word in combined for word in ["requests", "http", "socket", "connection"]
        ):
            patterns.append(f"{test.file_path}::{test.name} - External network call")

        # Check for file system operations
        if any(word in combined for word in ["open(", "write(", "read(", "/tmp"]):
            patterns.append(f"{test.file_path}::{test.name} - File system operations")

    return patterns


def print_report(
    report: ParsedReport,
    slow_threshold: float = 1.0,
    verbose: bool = False,
) -> None:
    """Print the parsed report."""
    # Summary table
    table = Table(title="Test Results Summary")
    table.add_column("Status", style="cyan")
    table.add_column("Count", style="green")

    total = len(report.tests)
    table.add_row("Total", str(total))
    table.add_row("[green]Passed[/green]", str(len(report.passed)))
    table.add_row("[red]Failed[/red]", str(len(report.failed)))
    table.add_row("[red]Errors[/red]", str(len(report.errors)))
    table.add_row("[yellow]Skipped[/yellow]", str(len(report.skipped)))
    if report.total_duration:
        table.add_row("Duration", f"{report.total_duration:.2f}s")

    console.print(table)

    # Failures by type
    all_failures = report.failed + report.errors
    if all_failures:
        console.print("\n[bold red]Failures by Type[/bold red]")
        groups = group_failures_by_type(all_failures)

        for error_type, tests in sorted(groups.items(), key=lambda x: -len(x[1])):
            console.print(f"\n[red]{error_type}[/red] ({len(tests)})")
            for test in tests[:5]:  # Show first 5
                location = f"{test.file_path}::{test.name}"
                console.print(f"  • {location}")
                if test.error_message and verbose:
                    msg = (
                        test.error_message[:100] + "..."
                        if len(test.error_message) > 100
                        else test.error_message
                    )
                    console.print(f"    [dim]{msg}[/dim]")

            if len(tests) > 5:
                console.print(f"  ... and {len(tests) - 5} more")

    # Slow tests
    slow_tests = [t for t in report.tests if t.duration >= slow_threshold]
    if slow_tests:
        console.print(f"\n[bold yellow]Slow Tests (>{slow_threshold}s)[/bold yellow]")
        for test in sorted(slow_tests, key=lambda t: -t.duration)[:10]:
            console.print(f"  {test.duration:6.2f}s  {test.file_path}::{test.name}")

    # Flaky patterns
    flaky_patterns = detect_flaky_patterns(report.tests)
    if flaky_patterns:
        console.print("\n[bold yellow]Potential Flaky Test Patterns[/bold yellow]")
        for pattern in flaky_patterns[:10]:
            console.print(f"  ⚠ {pattern}")

    # Suggestions
    if all_failures:
        console.print("\n[bold blue]Suggested Actions[/bold blue]")
        seen_suggestions: set[str] = set()
        for i, test in enumerate(all_failures[:5], 1):
            suggestion = suggest_fix(test)
            if suggestion not in seen_suggestions:
                console.print(f"  {i}. {test.file_path}::{test.name}")
                console.print(f"     → {suggestion}")
                seen_suggestions.add(suggestion)

    # Warnings
    if report.warnings and verbose:
        console.print("\n[bold yellow]Warnings[/bold yellow]")
        for warning in report.warnings[:10]:
            console.print(f"  {warning}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        type=str,
        help="Input file path, or '-' for stdin",
    )
    parser.add_argument(
        "--format",
        choices=["auto", "text", "junit"],
        default="auto",
        help="Input format (default: auto-detect)",
    )
    parser.add_argument(
        "--slow-threshold",
        type=float,
        default=1.0,
        help="Threshold in seconds for slow tests (default: 1.0)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    # Read input
    if args.input == "-":
        content = sys.stdin.read()
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            console.print(
                f"[red]Error:[/red] File '{args.input}' not found", file=sys.stderr
            )
            return 1
        content = input_path.read_text(encoding="utf-8")

    # Detect format
    input_format = args.format
    if input_format == "auto":
        if content.strip().startswith("<?xml") or content.strip().startswith("<"):
            input_format = "junit"
        else:
            input_format = "text"

    # Parse
    if input_format == "junit":
        report = parse_junit_xml(content)
    else:
        report = parse_pytest_terminal(content)

    # Output
    if args.output == "json":
        result: dict[str, Any] = {
            "summary": {
                "total": len(report.tests),
                "passed": len(report.passed),
                "failed": len(report.failed),
                "errors": len(report.errors),
                "skipped": len(report.skipped),
                "duration": report.total_duration,
            },
            "failures": [
                {
                    "name": t.name,
                    "file": t.file_path,
                    "error_type": t.error_type,
                    "error_message": t.error_message,
                    "duration": t.duration,
                    "suggestion": suggest_fix(t),
                }
                for t in report.failed + report.errors
            ],
            "slow_tests": [
                {"name": t.name, "file": t.file_path, "duration": t.duration}
                for t in sorted(report.tests, key=lambda t: -t.duration)
                if t.duration >= args.slow_threshold
            ],
            "flaky_patterns": detect_flaky_patterns(report.tests),
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(report, args.slow_threshold, args.verbose)

    # Return non-zero if there are failures
    return 1 if report.failed or report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
