#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "rich>=13.0",
#     "bandit>=1.7",
# ]
# ///
"""
Run security-focused static analysis on Python code.

Analyzes:
- Security vulnerabilities using Bandit
- Hardcoded secrets and credentials
- SQL injection risks
- Command injection risks
- Insecure cryptographic practices

Features:
- Multiple severity levels
- SARIF output for GitHub integration
- Prioritized findings
- Actionable fix suggestions

Usage:
    uv run security_scanner.py [OPTIONS] PATH

Examples
--------
    uv run security_scanner.py src/
    uv run security_scanner.py src/ --severity medium
    uv run security_scanner.py src/ --output sarif > results.sarif
    uv run security_scanner.py src/ --fail-on high
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_bandit(cls, severity: str, confidence: str) -> Severity:
        """Map Bandit severity/confidence to our severity."""
        sev = severity.upper()
        conf = confidence.upper()

        if sev == "HIGH" and conf == "HIGH":
            return cls.CRITICAL
        if sev == "HIGH":
            return cls.HIGH
        if sev == "MEDIUM":
            return cls.MEDIUM
        return cls.LOW


@dataclass
class SecurityFinding:
    """A security issue found in code."""

    rule_id: str
    severity: Severity
    confidence: str
    file_path: str
    line_number: int
    line_range: list[int]
    code: str
    message: str
    cwe: str | None = None
    suggestion: str | None = None


@dataclass
class SecurityReport:
    """Complete security scan report."""

    findings: list[SecurityFinding] = field(default_factory=list)
    files_scanned: int = 0
    errors: list[str] = field(default_factory=list)

    def by_severity(self, severity: Severity) -> list[SecurityFinding]:
        return [f for f in self.findings if f.severity == severity]

    @property
    def critical_count(self) -> int:
        return len(self.by_severity(Severity.CRITICAL))

    @property
    def high_count(self) -> int:
        return len(self.by_severity(Severity.HIGH))

    @property
    def medium_count(self) -> int:
        return len(self.by_severity(Severity.MEDIUM))

    @property
    def low_count(self) -> int:
        return len(self.by_severity(Severity.LOW))


# Suggestions for common Bandit rules
RULE_SUGGESTIONS = {
    "B101": "Remove assert in production code or use proper error handling",
    "B102": "Use subprocess with shell=False and explicit argument lists",
    "B103": "Set secure file permissions (e.g., 0o600 for sensitive files)",
    "B104": "Bind to specific IP address, not 0.0.0.0",
    "B105": "Use environment variables or secure vault for passwords",
    "B106": "Use environment variables or secure vault for passwords",
    "B107": "Use environment variables or secure vault for passwords",
    "B108": "Use tempfile module for temporary files",
    "B110": "Handle exceptions explicitly, don't use bare except with pass",
    "B112": "Handle exceptions explicitly, don't use try-except-continue",
    "B201": "Avoid flask debug mode in production",
    "B301": "Use pickle only with trusted data, consider json instead",
    "B302": "Use defusedxml for parsing untrusted XML",
    "B303": "Use modern hash functions (sha256+), not md5/sha1",
    "B304": "Use modern ciphers (AES-GCM), not DES/Blowfish",
    "B305": "Use modern ciphers, not RC4",
    "B306": "Use tempfile.mkstemp() instead of tempfile.mktemp()",
    "B307": "Avoid eval(), use ast.literal_eval() for literals",
    "B308": "Use defusedxml.lxml instead of lxml",
    "B310": "Validate URLs before using urllib.urlopen",
    "B311": "Use secrets module instead of random for security",
    "B312": "Use defusedxml instead of xml.dom.minidom",
    "B313": "Use defusedxml instead of xml.etree",
    "B314": "Use defusedxml instead of xml.expatreader",
    "B315": "Use defusedxml instead of xml.sax",
    "B316": "Use defusedxml instead of xml.etree.ElementTree",
    "B317": "Use defusedxml instead of xml.dom.pulldom",
    "B318": "Use defusedxml instead of xml.dom.expatbuilder",
    "B319": "Use defusedxml instead of xml.dom.xmlbuilder",
    "B320": "Use defusedxml.lxml instead of lxml.etree",
    "B321": "Use SFTP instead of FTP",
    "B322": "Use input() is safe in Python 3, but validate the input",
    "B323": "Use ssl.create_default_context() for SSL connections",
    "B324": "Use hashlib with secure algorithms (sha256+)",
    "B501": "Verify SSL certificates in requests",
    "B502": "Use modern SSL/TLS versions",
    "B503": "Use modern SSL/TLS versions",
    "B504": "Use ssl.create_default_context()",
    "B505": "Use cryptography library with secure key sizes",
    "B506": "Use yaml.safe_load() instead of yaml.load()",
    "B507": "Verify SSH host keys",
    "B508": "Use SNMPv3 with authentication and encryption",
    "B509": "Use SNMPv3 with privacy",
    "B601": "Use parameterized queries to prevent SQL injection",
    "B602": "Use subprocess with shell=False",
    "B603": "Validate subprocess inputs",
    "B604": "Avoid shell=True in subprocess calls",
    "B605": "Avoid os.system, use subprocess instead",
    "B606": "Avoid os.popen, use subprocess instead",
    "B607": "Use full paths for executables in subprocess",
    "B608": "Use parameterized queries to prevent SQL injection",
    "B609": "Avoid wildcard injection in subprocess",
    "B610": "Use Django's ORM safely",
    "B611": "Use Django's ORM safely",
    "B701": "Use jinja2.select_autoescape() or autoescape=True",
    "B702": "Use mako with autoescape",
    "B703": "Use Django's autoescape",
}


def run_bandit(path: Path, severity: Severity) -> dict[str, Any]:
    """Run Bandit security scanner."""
    # Severity mapping for future use with bandit severity filtering
    _severity_map = {
        Severity.LOW: "low",
        Severity.MEDIUM: "medium",
        Severity.HIGH: "high",
        Severity.CRITICAL: "high",
    }

    cmd = [
        sys.executable,
        "-m",
        "bandit",
        "-r",
        str(path),
        "-f",
        "json",
        "-ll"
        if severity in (Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL)
        else "-l",
    ]

    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        # Bandit returns non-zero if it finds issues
        if result.stdout:
            return json.loads(result.stdout)
        return {"results": [], "errors": [], "metrics": {"_totals": {"loc": 0}}}
    except subprocess.TimeoutExpired:
        return {"results": [], "errors": ["Bandit timed out"], "metrics": {}}
    except json.JSONDecodeError:
        err_msg = "Failed to parse Bandit output"
        return {"results": [], "errors": [err_msg], "metrics": {}}
    except Exception as e:
        return {"results": [], "errors": [str(e)], "metrics": {}}


def scan_for_secrets(path: Path) -> list[SecurityFinding]:
    """Scan for hardcoded secrets and credentials."""
    findings: list[SecurityFinding] = []

    # Patterns for potential secrets
    secret_patterns = [
        (
            r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']([^"\']{10,})["\']',
            "Potential API key",
        ),
        (
            r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\']([^"\']{6,})["\']',
            "Potential hardcoded password",
        ),
        (r'(?i)(token)\s*[=:]\s*["\']([^"\']{10,})["\']', "Potential hardcoded token"),
        (
            r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[=:]\s*["\']([A-Z0-9]{16,})["\']',
            "AWS Access Key ID",
        ),
        (
            r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[=:]\s*["\']([^"\']{30,})["\']',
            "AWS Secret Key",
        ),
        (
            r"(?i)bearer\s+[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+",
            "JWT Token",
        ),
        (r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----", "Private Key"),
        (
            r'(?i)(database[_-]?url|db[_-]?url)\s*[=:]\s*["\']([^"\']+://[^"\']+)["\']',
            "Database URL with credentials",
        ),
    ]

    files = [path] if path.is_file() else list(path.rglob("*.py"))

    skip_dirs = [".venv", "venv", "__pycache__", ".git"]
    for file_path in files:
        if any(skip in str(file_path) for skip in skip_dirs):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                # Skip comments
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue

                for pattern, description in secret_patterns:
                    if re.search(pattern, line):
                        findings.append(
                            SecurityFinding(
                                rule_id="SECRET001",
                                severity=Severity.HIGH,
                                confidence="MEDIUM",
                                file_path=str(file_path),
                                line_number=line_num,
                                line_range=[line_num],
                                code=line.strip()[:100],
                                message=description,
                                suggestion=(
                                    "Use environment variables or a secrets manager"
                                ),
                            ),
                        )
                        break  # One finding per line

        except Exception:
            pass

    return findings


def parse_bandit_results(bandit_output: dict[str, Any]) -> SecurityReport:
    """Parse Bandit JSON output into SecurityReport."""
    report = SecurityReport()

    # Get metrics
    metrics = bandit_output.get("metrics", {})
    totals = metrics.get("_totals", {})
    report.files_scanned = totals.get("loc", 0) // 50  # Rough estimate

    # Parse results
    for result in bandit_output.get("results", []):
        severity = Severity.from_bandit(
            result.get("issue_severity", "LOW"),
            result.get("issue_confidence", "LOW"),
        )

        rule_id = result.get("test_id", "UNKNOWN")

        finding = SecurityFinding(
            rule_id=rule_id,
            severity=severity,
            confidence=result.get("issue_confidence", "LOW"),
            file_path=result.get("filename", ""),
            line_number=result.get("line_number", 0),
            line_range=result.get("line_range", []),
            code=result.get("code", "").strip(),
            message=result.get("issue_text", ""),
            cwe=(
                result.get("issue_cwe", {}).get("id")
                if result.get("issue_cwe")
                else None
            ),
            suggestion=RULE_SUGGESTIONS.get(rule_id),
        )
        report.findings.append(finding)

    # Parse errors
    for error in bandit_output.get("errors", []):
        report.errors.append(str(error))

    return report


def generate_sarif(report: SecurityReport) -> dict[str, Any]:
    """Generate SARIF format output for GitHub."""
    sarif: dict[str, Any] = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "security_scanner",
                        "version": "1.0.0",
                        "rules": [],
                    },
                },
                "results": [],
            },
        ],
    }

    # Collect unique rules
    rules: dict[str, dict[str, Any]] = {}
    for finding in report.findings:
        if finding.rule_id not in rules:
            rules[finding.rule_id] = {
                "id": finding.rule_id,
                "name": finding.rule_id,
                "shortDescription": {"text": finding.message[:100]},
                "defaultConfiguration": {
                    "level": (
                        "error"
                        if finding.severity in (Severity.HIGH, Severity.CRITICAL)
                        else "warning"
                    ),
                },
            }

    sarif["runs"][0]["tool"]["driver"]["rules"] = list(rules.values())

    # Add results
    for finding in report.findings:
        level_map = {
            Severity.CRITICAL: "error",
            Severity.HIGH: "error",
            Severity.MEDIUM: "warning",
            Severity.LOW: "note",
        }

        result = {
            "ruleId": finding.rule_id,
            "level": level_map[finding.severity],
            "message": {"text": finding.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.file_path},
                        "region": {"startLine": finding.line_number},
                    },
                },
            ],
        }
        sarif["runs"][0]["results"].append(result)

    return sarif


def print_report(report: SecurityReport, verbose: bool = False) -> None:
    """Print the security scan report."""
    # Summary
    console.print(Panel("[bold]Security Scan Results[/bold]"))

    summary_table = Table(title="Summary")
    summary_table.add_column("Severity", style="cyan")
    summary_table.add_column("Count", justify="right")

    if report.critical_count > 0:
        summary_table.add_row(
            "[red bold]CRITICAL[/red bold]", str(report.critical_count)
        )
    if report.high_count > 0:
        summary_table.add_row("[red]HIGH[/red]", str(report.high_count))
    if report.medium_count > 0:
        summary_table.add_row("[yellow]MEDIUM[/yellow]", str(report.medium_count))
    if report.low_count > 0:
        summary_table.add_row("[blue]LOW[/blue]", str(report.low_count))

    summary_table.add_row("Total", str(len(report.findings)))

    console.print(summary_table)

    if not report.findings:
        console.print("\n[bold green]No security issues found![/bold green]")
        return

    # Group by severity
    for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
        findings = report.by_severity(severity)
        if not findings:
            continue

        color = {
            Severity.CRITICAL: "red bold",
            Severity.HIGH: "red",
            Severity.MEDIUM: "yellow",
            Severity.LOW: "blue",
        }[severity]

        console.print(f"\n[{color}]{severity.value.upper()} Severity[/{color}]")

        for finding in findings[:10]:  # Limit output
            msg = f"\n  [{color}]{finding.rule_id}[/{color}]: {finding.message}"
            console.print(msg)
            console.print(f"  [dim]{finding.file_path}:{finding.line_number}[/dim]")

            if verbose and finding.code:
                console.print(f"  [dim]Code: {finding.code[:80]}...[/dim]")

            if finding.suggestion:
                console.print(f"  [green]→ {finding.suggestion}[/green]")

            if finding.cwe:
                console.print(f"  [dim]CWE-{finding.cwe}[/dim]")

        if len(findings) > 10:
            remaining = len(findings) - 10
            console.print(f"\n  ... and {remaining} more {severity.value} issues")

    # Errors
    if report.errors:
        console.print("\n[yellow]Warnings:[/yellow]")
        for error in report.errors:
            console.print(f"  {error}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="File or directory to scan")
    parser.add_argument(
        "--severity",
        choices=["low", "medium", "high"],
        default="low",
        help="Minimum severity to report (default: low)",
    )
    parser.add_argument(
        "--fail-on",
        choices=["low", "medium", "high", "critical"],
        help="Exit with error if issues at or above this severity",
    )
    parser.add_argument(
        "--include-secrets",
        action="store_true",
        default=True,
        help="Scan for hardcoded secrets (default: True)",
    )
    parser.add_argument(
        "--no-secrets",
        action="store_false",
        dest="include_secrets",
        help="Skip secret scanning",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output",
        choices=["text", "json", "sarif"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    if not args.path.exists():
        console.print(
            f"[red]Error:[/red] Path '{args.path}' does not exist", file=sys.stderr
        )
        return 1

    min_severity = Severity(args.severity)

    # Run Bandit
    console.print(f"[dim]Scanning {args.path}...[/dim]")
    bandit_output = run_bandit(args.path, min_severity)
    report = parse_bandit_results(bandit_output)

    # Add secret scanning
    if args.include_secrets:
        secret_findings = scan_for_secrets(args.path)
        report.findings.extend(secret_findings)

    # Filter by minimum severity
    severity_order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    min_index = severity_order.index(min_severity)
    report.findings = [
        f for f in report.findings if severity_order.index(f.severity) >= min_index
    ]

    # Output
    if args.output == "json":
        result = {
            "summary": {
                "critical": report.critical_count,
                "high": report.high_count,
                "medium": report.medium_count,
                "low": report.low_count,
                "total": len(report.findings),
            },
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity.value,
                    "file": f.file_path,
                    "line": f.line_number,
                    "message": f.message,
                    "suggestion": f.suggestion,
                    "cwe": f.cwe,
                }
                for f in report.findings
            ],
            "errors": report.errors,
        }
        print(json.dumps(result, indent=2))

    elif args.output == "sarif":
        sarif = generate_sarif(report)
        print(json.dumps(sarif, indent=2))

    else:
        print_report(report, args.verbose)

    # Check fail threshold
    if args.fail_on:
        fail_severity = Severity(args.fail_on)
        fail_index = severity_order.index(fail_severity)

        for finding in report.findings:
            if severity_order.index(finding.severity) >= fail_index:
                return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
