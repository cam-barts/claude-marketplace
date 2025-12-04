"""Tests for detect_tool_conflicts.py script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestRedundantToolDetection:
    """Tests for detecting redundant tools."""

    def test_detect_black_ruff_redundancy(self, tmp_path: Path) -> None:
        """Test detecting black as redundant with ruff format."""
        (tmp_path / "pyproject.toml").write_text("""
[tool.ruff]
line-length = 88

[tool.ruff.format]
quote-style = "double"

[tool.black]
line-length = 88
""")

        from detect_tool_conflicts import detect_conflicts

        report = detect_conflicts(tmp_path)
        # Should detect black is redundant when ruff format is used
        redundant_names = [r.tool for r in report.redundant]
        assert "black" in redundant_names or len(report.warnings) >= 1

    def test_detect_flake8_ruff_redundancy(self, tmp_path: Path) -> None:
        """Test detecting flake8 as redundant with ruff."""
        (tmp_path / "pyproject.toml").write_text("""
[tool.ruff]
select = ["E", "F", "W"]
""")
        (tmp_path / ".flake8").write_text("""
[flake8]
max-line-length = 88
""")

        from detect_tool_conflicts import detect_conflicts

        report = detect_conflicts(tmp_path)
        redundant_names = [r.tool for r in report.redundant]
        assert "flake8" in redundant_names or len(report.warnings) >= 1


class TestConfigConflictDetection:
    """Tests for detecting configuration conflicts."""

    def test_detect_line_length_conflict(self, tmp_path: Path) -> None:
        """Test detecting conflicting line length settings."""
        (tmp_path / "pyproject.toml").write_text("""
[tool.ruff]
line-length = 88

[tool.black]
line-length = 100
""")

        from detect_tool_conflicts import detect_conflicts

        report = detect_conflicts(tmp_path)
        assert len(report.config_conflicts) >= 1

    def test_detect_quote_style_conflict(self, tmp_path: Path) -> None:
        """Test detecting conflicting quote style settings."""
        (tmp_path / "pyproject.toml").write_text("""
[tool.ruff.format]
quote-style = "single"

[tool.black]
skip-string-normalization = false
""")

        from detect_tool_conflicts import detect_conflicts

        report = detect_conflicts(tmp_path)
        # May detect potential conflict or warning
        assert len(report.config_conflicts) >= 1 or len(report.warnings) >= 1


class TestRuleOverlapDetection:
    """Tests for detecting overlapping rules."""

    def test_detect_overlapping_checks(self, tmp_path: Path) -> None:
        """Test detecting overlapping linter rules."""
        (tmp_path / "pyproject.toml").write_text("""
[tool.ruff]
select = ["E", "F", "W", "I"]

[tool.pylint.messages_control]
enable = ["E0001", "W0611"]
""")
        (tmp_path / ".flake8").write_text("""
[flake8]
select = E,F,W
""")

        from detect_tool_conflicts import detect_conflicts

        report = detect_conflicts(tmp_path)
        # Should detect overlapping rules
        assert len(report.overlapping_rules) >= 1 or len(report.warnings) >= 1


class TestMigrationSuggestions:
    """Tests for tool migration suggestions."""

    def test_suggest_ruff_migration(self, tmp_path: Path) -> None:
        """Test suggesting migration to ruff."""
        (tmp_path / ".flake8").write_text("""
[flake8]
max-line-length = 88
extend-ignore = E203, E501
""")
        (tmp_path / "pyproject.toml").write_text("""
[tool.black]
line-length = 88
""")

        from detect_tool_conflicts import suggest_migrations

        suggestions = suggest_migrations(tmp_path)
        # Should suggest migrating to ruff
        assert any("ruff" in s.target.lower() for s in suggestions)

    def test_generate_migration_config(self, tmp_path: Path) -> None:
        """Test generating migration configuration."""
        (tmp_path / ".flake8").write_text("""
[flake8]
max-line-length = 88
extend-ignore = E203
""")

        from detect_tool_conflicts import generate_migration_config

        config = generate_migration_config(tmp_path, target="ruff")
        assert "line-length" in config
        assert "ignore" in config or "extend-ignore" in config


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from detect_tool_conflicts import main

        old_argv = sys.argv
        try:
            sys.argv = ["detect_tool_conflicts.py", "/nonexistent/path"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
