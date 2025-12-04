"""Tests for dependency_analyzer.py script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestDependencyExtraction:
    """Tests for extracting dependencies from project files."""

    def test_extract_from_requirements(self, tmp_path: Path) -> None:
        """Test extracting dependencies from requirements.txt."""
        (tmp_path / "requirements.txt").write_text("""
requests==2.28.0
flask>=2.0.0
django~=3.2.0
numpy
""")

        from dependency_analyzer import extract_dependencies

        deps = extract_dependencies(tmp_path)
        dep_names = [d.name for d in deps]

        assert "requests" in dep_names
        assert "flask" in dep_names
        assert "django" in dep_names

    def test_extract_from_pyproject(self, tmp_path: Path) -> None:
        """Test extracting dependencies from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("""
[project]
name = "sample"
dependencies = [
    "requests>=2.28.0",
    "click>=8.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
]
""")

        from dependency_analyzer import extract_dependencies

        deps = extract_dependencies(tmp_path)
        dep_names = [d.name for d in deps]

        assert "requests" in dep_names
        assert "click" in dep_names


class TestVersionAnalysis:
    """Tests for analyzing dependency versions."""

    def test_detect_outdated_version(self, project_with_requirements: Path) -> None:
        """Test detecting outdated dependency versions."""
        from dependency_analyzer import check_outdated

        report = check_outdated(project_with_requirements)
        # May find outdated packages depending on current versions
        assert hasattr(report, "outdated")

    def test_detect_pinned_versions(self, tmp_path: Path) -> None:
        """Test detecting overly pinned versions."""
        (tmp_path / "requirements.txt").write_text("""
requests==2.28.0
flask==2.0.0
""")

        from dependency_analyzer import analyze_version_constraints

        report = analyze_version_constraints(tmp_path)
        # Should detect exact pins
        pinned = [d for d in report.dependencies if d.is_pinned]
        assert len(pinned) >= 2


class TestSecurityAnalysis:
    """Tests for security vulnerability analysis."""

    def test_check_known_vulnerabilities(self, tmp_path: Path) -> None:
        """Test checking for known vulnerabilities."""
        (tmp_path / "requirements.txt").write_text("""
requests==2.28.0
""")

        from dependency_analyzer import check_vulnerabilities

        report = check_vulnerabilities(tmp_path)
        # Should return a vulnerability report (may or may not have issues)
        assert hasattr(report, "vulnerabilities")

    def test_report_severity_levels(self, tmp_path: Path) -> None:
        """Test that vulnerabilities include severity levels."""
        (tmp_path / "requirements.txt").write_text("""
requests>=2.0.0
""")

        from dependency_analyzer import check_vulnerabilities

        report = check_vulnerabilities(tmp_path)
        # If vulnerabilities exist, they should have severity
        if report.vulnerabilities:
            assert all(hasattr(v, "severity") for v in report.vulnerabilities)


class TestDependencyGraph:
    """Tests for dependency graph analysis."""

    def test_detect_circular_dependencies(self, tmp_path: Path) -> None:
        """Test detecting circular dependencies."""
        # Note: this tests the detection capability, not actual circular deps
        (tmp_path / "requirements.txt").write_text("""
package-a>=1.0.0
package-b>=1.0.0
""")

        from dependency_analyzer import analyze_dependency_graph

        report = analyze_dependency_graph(tmp_path)
        assert hasattr(report, "circular_dependencies")

    def test_identify_heavy_dependencies(self, tmp_path: Path) -> None:
        """Test identifying dependencies with many transitive deps."""
        (tmp_path / "requirements.txt").write_text("""
django>=4.0.0
""")

        from dependency_analyzer import analyze_dependency_graph

        report = analyze_dependency_graph(tmp_path)
        # Should identify dependency weight/size
        assert hasattr(report, "heavy_dependencies") or hasattr(
            report, "dependency_counts"
        )


class TestLicenseAnalysis:
    """Tests for license analysis."""

    def test_detect_dependency_licenses(self, tmp_path: Path) -> None:
        """Test detecting dependency licenses."""
        (tmp_path / "requirements.txt").write_text("""
requests>=2.28.0
""")

        from dependency_analyzer import analyze_licenses

        report = analyze_licenses(tmp_path)
        assert hasattr(report, "licenses")

    def test_flag_incompatible_licenses(self, tmp_path: Path) -> None:
        """Test flagging potentially incompatible licenses."""
        (tmp_path / "requirements.txt").write_text("""
gpl-package>=1.0.0
mit-package>=1.0.0
""")

        from dependency_analyzer import analyze_licenses

        report = analyze_licenses(tmp_path)
        assert hasattr(report, "warnings") or hasattr(report, "conflicts")


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from dependency_analyzer import main

        old_argv = sys.argv
        try:
            sys.argv = ["dependency_analyzer.py", "/nonexistent/path"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
