"""Tests for discover_linters.py script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestLanguageDetection:
    """Tests for detecting project languages."""

    def test_detect_python_project(self, tmp_path: Path) -> None:
        """Test detecting a Python project."""
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        from discover_linters import detect_languages

        languages = detect_languages(tmp_path)
        assert "python" in languages

    def test_detect_javascript_project(self, tmp_path: Path) -> None:
        """Test detecting a JavaScript project."""
        (tmp_path / "index.js").write_text("console.log('hello')")
        (tmp_path / "package.json").write_text('{"name": "test"}')

        from discover_linters import detect_languages

        languages = detect_languages(tmp_path)
        assert "javascript" in languages

    def test_detect_multi_language(self, tmp_path: Path) -> None:
        """Test detecting multiple languages."""
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "index.ts").write_text("console.log('hello')")
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'")

        from discover_linters import detect_languages

        languages = detect_languages(tmp_path)
        assert len(languages) >= 2


class TestLinterRecommendations:
    """Tests for linter recommendations."""

    def test_recommend_python_linters(self, tmp_path: Path) -> None:
        """Test recommending linters for Python."""
        (tmp_path / "main.py").write_text("print('hello')")

        from discover_linters import recommend_linters

        recommendations = recommend_linters(tmp_path)
        python_linters = [r for r in recommendations if r.language == "python"]

        assert len(python_linters) >= 1
        linter_names = [r.name for r in python_linters]
        assert "ruff" in linter_names or "pylint" in linter_names

    def test_recommend_with_priority(self, tmp_path: Path) -> None:
        """Test linter recommendations include priority."""
        (tmp_path / "main.py").write_text("print('hello')")

        from discover_linters import recommend_linters

        recommendations = recommend_linters(tmp_path)
        # Recommendations should have priority ordering
        assert all(hasattr(r, "priority") for r in recommendations)


class TestExistingToolDetection:
    """Tests for detecting existing linter configurations."""

    def test_detect_ruff_config(self, project_with_configs: Path) -> None:
        """Test detecting existing ruff configuration."""
        from discover_linters import detect_existing_tools

        tools = detect_existing_tools(project_with_configs)
        tool_names = [t.name for t in tools]
        assert "ruff" in tool_names

    def test_detect_precommit_hooks(self, project_with_configs: Path) -> None:
        """Test detecting pre-commit hooks."""
        from discover_linters import detect_existing_tools

        tools = detect_existing_tools(project_with_configs)
        # Should find tools from pre-commit config
        tool_names = [t.name for t in tools]
        assert "ruff" in tool_names or "black" in tool_names


class TestConfigGeneration:
    """Tests for generating linter configurations."""

    def test_generate_ruff_config(self, tmp_path: Path) -> None:
        """Test generating ruff configuration."""
        from discover_linters import generate_config

        config = generate_config("ruff", tmp_path)
        assert "line-length" in config or "select" in config

    def test_generate_minimal_config(self, tmp_path: Path) -> None:
        """Test generating minimal starter config."""
        from discover_linters import generate_config

        config = generate_config("ruff", tmp_path, minimal=True)
        # Minimal config should be short
        assert len(config) < 500


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from discover_linters import main

        old_argv = sys.argv
        try:
            sys.argv = ["discover_linters.py", "/nonexistent/path"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
