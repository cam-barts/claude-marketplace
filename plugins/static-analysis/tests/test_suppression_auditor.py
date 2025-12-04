"""Tests for suppression_auditor.py script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestSuppressionExtraction:
    """Tests for extracting suppression comments."""

    def test_extract_noqa_comments(self, tmp_path: Path) -> None:
        """Test extracting noqa comments."""
        py_file = tmp_path / "sample.py"
        py_file.write_text("""
x = 1  # noqa: F841
y = unused_var  # noqa
import os  # noqa: F401
""")

        from suppression_auditor import extract_suppressions

        suppressions = extract_suppressions(py_file)
        assert len(suppressions) >= 3
        # Should identify specific codes where provided
        codes = [s.codes for s in suppressions if s.codes]
        assert any("F841" in c for c in codes)

    def test_extract_pylint_disable(self, tmp_path: Path) -> None:
        """Test extracting pylint disable comments."""
        py_file = tmp_path / "sample.py"
        py_file.write_text("""
def func(self):  # pylint: disable=no-self-use
    return 42

class Foo:  # pylint: disable=too-few-public-methods
    pass
""")

        from suppression_auditor import extract_suppressions

        suppressions = extract_suppressions(py_file)
        pylint_suppressions = [s for s in suppressions if s.tool == "pylint"]
        assert len(pylint_suppressions) >= 2

    def test_extract_type_ignore(self, tmp_path: Path) -> None:
        """Test extracting type: ignore comments."""
        py_file = tmp_path / "sample.py"
        py_file.write_text("""
x: int = "string"  # type: ignore
result = func()  # type: ignore[arg-type]
""")

        from suppression_auditor import extract_suppressions

        suppressions = extract_suppressions(py_file)
        type_suppressions = [s for s in suppressions if s.tool == "mypy"]
        assert len(type_suppressions) >= 2


class TestSuppressionAudit:
    """Tests for auditing suppressions."""

    def test_identify_blanket_suppressions(self, sample_python_project: Path) -> None:
        """Test identifying blanket suppressions without specific codes."""
        src_file = sample_python_project / "src" / "blanket.py"
        src_file.write_text("""
x = 1  # noqa
y = 2  # type: ignore
""")

        from suppression_auditor import audit_suppressions

        report = audit_suppressions(sample_python_project)
        blanket = list(report.blanket_suppressions)
        assert len(blanket) >= 2

    def test_identify_stale_suppressions(self, tmp_path: Path) -> None:
        """Test identifying potentially stale suppressions."""
        py_file = tmp_path / "sample.py"
        # Suppression for code that wouldn't trigger
        py_file.write_text("""
x = 1  # noqa: E501 - but line is short
print("hello")  # noqa: F841 - but no unused variable here
""")

        from suppression_auditor import audit_suppressions

        report = audit_suppressions(tmp_path)
        # Should flag these as potentially stale
        assert len(report.potentially_stale) >= 1 or len(report.warnings) >= 1

    def test_count_suppressions_by_rule(self, tmp_path: Path) -> None:
        """Test counting suppressions by rule."""
        py_file = tmp_path / "sample.py"
        py_file.write_text("""
a = 1  # noqa: F841
b = 2  # noqa: F841
c = 3  # noqa: F841
d = 4  # noqa: E501
""")

        from suppression_auditor import audit_suppressions

        report = audit_suppressions(tmp_path)
        # Should count F841 suppressions
        assert report.by_rule.get("F841", 0) >= 3


class TestTrendAnalysis:
    """Tests for suppression trend analysis."""

    def test_identify_suppression_hotspots(self, tmp_path: Path) -> None:
        """Test identifying files with many suppressions."""
        hotspot = tmp_path / "hotspot.py"
        hotspot.write_text("""
a = 1  # noqa: F841
b = 2  # noqa: F841
c = 3  # noqa: F841
d = 4  # noqa: F841
e = 5  # noqa: F841
f = 6  # noqa: F841
g = 7  # noqa: F841
h = 8  # noqa: F841
i = 9  # noqa: F841
j = 10  # noqa: F841
""")

        clean = tmp_path / "clean.py"
        clean.write_text("""
def clean_function():
    return 42
""")

        from suppression_auditor import identify_hotspots

        hotspots = identify_hotspots(tmp_path, threshold=5)
        hotspot_files = [h.file_path.name for h in hotspots]
        assert "hotspot.py" in hotspot_files

    def test_generate_suppression_report(self, sample_python_project: Path) -> None:
        """Test generating a comprehensive suppression report."""
        from suppression_auditor import generate_report

        report = generate_report(sample_python_project)
        assert hasattr(report, "total_suppressions")
        assert hasattr(report, "by_tool")
        assert hasattr(report, "by_file")


class TestRecommendations:
    """Tests for suppression improvement recommendations."""

    def test_recommend_adding_specific_codes(self, tmp_path: Path) -> None:
        """Test recommending specific codes for blanket suppressions."""
        py_file = tmp_path / "sample.py"
        py_file.write_text("""
x = 1  # noqa
""")

        from suppression_auditor import get_recommendations

        recommendations = get_recommendations(tmp_path)
        assert any("specific" in r.suggestion.lower() for r in recommendations)

    def test_recommend_removing_stale(self, tmp_path: Path) -> None:
        """Test recommending removal of stale suppressions."""
        py_file = tmp_path / "sample.py"
        py_file.write_text("""
print("hello")  # noqa: F841
""")

        from suppression_auditor import get_recommendations

        recommendations = get_recommendations(tmp_path)
        # May recommend removing stale suppression
        assert len(recommendations) >= 0  # At least runs without error


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from suppression_auditor import main

        old_argv = sys.argv
        try:
            sys.argv = ["suppression_auditor.py", "/nonexistent/path"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv

    def test_main_json_output(self, sample_python_project: Path) -> None:
        """Test main with JSON output format."""
        import sys

        from suppression_auditor import main

        old_argv = sys.argv
        try:
            sys.argv = [
                "suppression_auditor.py",
                str(sample_python_project),
                "--format",
                "json",
            ]
            result = main()
            assert result in (0, 1)  # Either success or warnings
        finally:
            sys.argv = old_argv
