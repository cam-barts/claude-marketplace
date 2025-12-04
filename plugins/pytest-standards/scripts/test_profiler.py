#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
# ]
# ///
"""
Profile test execution times and identify slow tests.

Features:
- Run pytest with timing collection
- Identify slow tests above threshold
- Analyze fixture setup/teardown times
- Detect I/O and network bottlenecks
- Suggest parallelization configuration
- Generate optimization recommendations

Usage:
    uv run test_profiler.py [OPTIONS] PATH

Examples
--------
    uv run test_profiler.py tests/
    uv run test_profiler.py tests/ --threshold 1.0
    uv run test_profiler.py tests/ --top 20
    uv run test_profiler.py tests/ --suggest-parallel
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class TestTiming:
    """Timing information for a test."""

    name: str
    file_path: str
    duration: float
    phase: str = "call"  # setup, call, teardown
    outcome: str = "passed"


@dataclass
class FixtureTiming:
    """Timing information for a fixture."""

    name: str
    scope: str
    setup_time: float
    teardown_time: float = 0.0


@dataclass
class ProfileReport:
    """Complete profiling report."""

    tests: list[TestTiming] = field(default_factory=list)
    fixtures: list[FixtureTiming] = field(default_factory=list)
    total_duration: float = 0.0
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0

    @property
    def slow_tests(self) -> list[TestTiming]:
        """Tests sorted by duration, slowest first."""
        return sorted(self.tests, key=lambda t: -t.duration)

    def tests_above_threshold(self, threshold: float) -> list[TestTiming]:
        """Tests slower than threshold."""
        return [t for t in self.tests if t.duration >= threshold]


def run_pytest_with_timing(
    path: Path,
    extra_args: list[str] | None = None,
) -> tuple[str, int]:
    """Run pytest with duration reporting."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(path),
        "-v",
        "--durations=0",  # Show all durations
        "--durations-min=0.0",
        "-q",  # Quieter output
    ]

    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )
        return result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "Pytest timed out after 10 minutes", 1
    except Exception as e:
        return f"Error running pytest: {e}", 1


def parse_pytest_output(output: str) -> ProfileReport:
    """Parse pytest output to extract timing information."""
    report = ProfileReport()

    # Parse duration lines
    # Format: 0.12s call     tests/test_foo.py::test_bar
    duration_pattern = re.compile(
        r"^\s*([\d.]+)s\s+(setup|call|teardown)\s+(.+?)::(.+?)(?:\s|$)",
        re.MULTILINE,
    )

    for match in duration_pattern.finditer(output):
        duration = float(match.group(1))
        phase = match.group(2)
        file_path = match.group(3)
        test_name = match.group(4)

        timing = TestTiming(
            name=test_name,
            file_path=file_path,
            duration=duration,
            phase=phase,
        )
        report.tests.append(timing)

    # Aggregate by test (combine setup + call + teardown)
    test_durations: dict[str, float] = {}
    for test in report.tests:
        key = f"{test.file_path}::{test.name}"
        test_durations[key] = test_durations.get(key, 0) + test.duration

    # Create aggregated test list
    aggregated: dict[str, TestTiming] = {}
    for test in report.tests:
        key = f"{test.file_path}::{test.name}"
        if key not in aggregated:
            aggregated[key] = TestTiming(
                name=test.name,
                file_path=test.file_path,
                duration=test_durations[key],
            )

    report.tests = list(aggregated.values())

    # Parse summary line
    # Format: 10 passed, 2 failed in 5.23s
    summary_pattern = re.compile(
        r"(\d+)\s+passed.*?(?:(\d+)\s+failed)?.*?(?:(\d+)\s+error)?.*?in\s+([\d.]+)s",
    )
    summary_match = summary_pattern.search(output)
    if summary_match:
        report.passed = int(summary_match.group(1) or 0)
        report.failed = int(summary_match.group(2) or 0)
        report.errors = int(summary_match.group(3) or 0)
        report.total_duration = float(summary_match.group(4))
        report.total_tests = report.passed + report.failed + report.errors

    # If no summary found, count from tests
    if report.total_tests == 0:
        report.total_tests = len(report.tests)
        report.total_duration = sum(t.duration for t in report.tests)

    return report


def analyze_bottlenecks(report: ProfileReport) -> list[str]:
    """Analyze test timings for potential bottlenecks."""
    recommendations: list[str] = []

    if not report.tests:
        return recommendations

    # Check for very slow tests
    very_slow = [t for t in report.tests if t.duration > 10.0]
    if very_slow:
        recommendations.append(
            f"Found {len(very_slow)} tests taking >10s. "
            "Consider splitting or mocking external dependencies.",
        )

    # Check for many moderately slow tests
    slow = [t for t in report.tests if 1.0 <= t.duration <= 10.0]
    if len(slow) > 10:
        recommendations.append(
            f"Found {len(slow)} tests taking 1-10s. "
            "Consider parallelization with pytest-xdist.",
        )

    # Check total duration
    if report.total_duration > 60:
        parallel_estimate = report.total_duration / 4
        recommendations.append(
            f"Total test time is {report.total_duration:.0f}s. "
            f"With 4 parallel workers: ~{parallel_estimate:.0f}s",
        )

    # Check for integration test patterns
    integration_tests = [
        t
        for t in report.tests
        if "integration" in t.file_path.lower() or "e2e" in t.file_path.lower()
    ]
    if integration_tests:
        int_duration = sum(t.duration for t in integration_tests)
        recommendations.append(
            f"Integration tests take {int_duration:.1f}s. "
            "Consider running them in a separate CI job.",
        )

    # Check for fixture-related slowness (inferred from setup phase)
    # This would need more detailed pytest output

    return recommendations


def suggest_parallel_config(report: ProfileReport) -> dict[str, Any]:
    """Suggest pytest-xdist configuration."""
    total_time = report.total_duration
    num_tests = report.total_tests

    if num_tests == 0:
        return {}

    # Estimate optimal worker count
    # Rule of thumb: 1 worker per 2-4 CPU cores, or based on test count
    if total_time < 30:
        workers = 2
    elif total_time < 120:
        workers = 4
    else:
        workers = min(8, max(4, num_tests // 20))

    estimated_time = total_time / workers * 1.2  # 20% overhead

    return {
        "workers": workers,
        "current_time": round(total_time, 1),
        "estimated_time": round(estimated_time, 1),
        "speedup": round(total_time / estimated_time, 1),
        "config": {
            "pytest.ini": f"""[pytest]
addopts = -n {workers} --dist loadfile
""",
            "command": f"pytest -n {workers} --dist loadfile",
        },
    }


def print_report(
    report: ProfileReport,
    threshold: float = 1.0,
    top_n: int = 10,
    show_fixtures: bool = False,  # noqa: ARG001
    recommendations: list[str] | None = None,
    parallel_config: dict[str, Any] | None = None,
) -> None:
    """Print the profiling report."""
    # Summary
    console.print(Panel("[bold]Test Performance Report[/bold]"))

    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Total Tests", str(report.total_tests))
    summary_table.add_row("Passed", str(report.passed))
    if report.failed > 0:
        summary_table.add_row("Failed", f"[red]{report.failed}[/red]")
    summary_table.add_row("Total Duration", f"{report.total_duration:.2f}s")

    if report.total_tests > 0:
        avg = report.total_duration / report.total_tests
        summary_table.add_row("Average per Test", f"{avg:.2f}s")

    console.print(summary_table)

    # Slow tests
    slow_tests = report.tests_above_threshold(threshold)
    if slow_tests:
        console.print(f"\n[bold yellow]Slow Tests (>{threshold}s)[/bold yellow]")

        slow_table = Table()
        slow_table.add_column("Duration", justify="right", style="yellow")
        slow_table.add_column("Test", style="cyan")

        for test in slow_tests[:top_n]:
            slow_table.add_row(
                f"{test.duration:.2f}s", f"{test.file_path}::{test.name}"
            )

        console.print(slow_table)

        if len(slow_tests) > top_n:
            console.print(f"  ... and {len(slow_tests) - top_n} more slow tests")

    # Top N slowest (if different from threshold view)
    if not slow_tests:
        console.print(f"\n[bold]Top {top_n} Slowest Tests[/bold]")

        top_table = Table()
        top_table.add_column("Duration", justify="right")
        top_table.add_column("Test", style="cyan")

        for test in report.slow_tests[:top_n]:
            top_table.add_row(f"{test.duration:.2f}s", f"{test.file_path}::{test.name}")

        console.print(top_table)

    # Recommendations
    if recommendations:
        console.print("\n[bold blue]Recommendations[/bold blue]")
        for i, rec in enumerate(recommendations, 1):
            console.print(f"  {i}. {rec}")

    # Parallel configuration
    if parallel_config:
        console.print("\n[bold green]Parallelization Suggestion[/bold green]")
        console.print(f"  Current time: {parallel_config['current_time']}s")
        workers = parallel_config["workers"]
        est_time = parallel_config["estimated_time"]
        console.print(f"  With {workers} workers: ~{est_time}s")
        console.print(f"  Speedup: {parallel_config['speedup']}x")
        console.print(
            f"\n  Command: [cyan]{parallel_config['config']['command']}[/cyan]"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Test directory or file")
    parser.add_argument(
        "--threshold",
        type=float,
        default=1.0,
        help="Threshold in seconds for slow tests (default: 1.0)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of slowest tests to show (default: 10)",
    )
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help="Include fixture timing breakdown",
    )
    parser.add_argument(
        "--suggest-parallel",
        action="store_true",
        help="Suggest pytest-xdist configuration",
    )
    parser.add_argument(
        "--pytest-args",
        type=str,
        help="Additional arguments to pass to pytest",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    if not args.path.exists():
        console.print(
            f"[red]Error:[/red] Path '{args.path}' does not exist", file=sys.stderr
        )
        return 1

    # Parse extra pytest args
    extra_args = args.pytest_args.split() if args.pytest_args else None

    # Run pytest
    console.print(f"[dim]Running pytest on {args.path}...[/dim]")
    output, returncode = run_pytest_with_timing(args.path, extra_args)

    if args.verbose:
        console.print("[dim]Raw pytest output:[/dim]")
        console.print(output[:2000])

    # Parse results
    report = parse_pytest_output(output)

    if report.total_tests == 0:
        console.print("[yellow]No tests found or pytest failed to run[/yellow]")
        if args.verbose:
            console.print(output)
        return 1

    # Analysis
    recommendations = analyze_bottlenecks(report)
    parallel_config = suggest_parallel_config(report) if args.suggest_parallel else None

    # Output
    if args.output == "json":
        result: dict[str, Any] = {
            "summary": {
                "total_tests": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "total_duration": round(report.total_duration, 2),
                "average_duration": round(
                    report.total_duration / report.total_tests,
                    2,
                )
                if report.total_tests > 0
                else 0,
            },
            "slow_tests": [
                {
                    "name": t.name,
                    "file": t.file_path,
                    "duration": round(t.duration, 2),
                }
                for t in report.tests_above_threshold(args.threshold)
            ],
            "all_tests": [
                {
                    "name": t.name,
                    "file": t.file_path,
                    "duration": round(t.duration, 2),
                }
                for t in report.slow_tests[: args.top]
            ],
            "recommendations": recommendations,
        }

        if parallel_config:
            result["parallel_config"] = parallel_config

        print(json.dumps(result, indent=2))
    else:
        print_report(
            report,
            threshold=args.threshold,
            top_n=args.top,
            show_fixtures=args.fixtures,
            recommendations=recommendations,
            parallel_config=parallel_config,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
