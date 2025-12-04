"""Pytest configuration for static-analysis tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts directory to path so test files can import from scripts
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


@pytest.fixture
def sample_python_project(tmp_path: Path) -> Path:
    """Create a sample Python project structure."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create pyproject.toml
    (project_dir / "pyproject.toml").write_text("""
[project]
name = "sample-project"
version = "0.1.0"

[tool.ruff]
line-length = 88

[tool.black]
line-length = 88
""")

    # Create source files
    src_dir = project_dir / "src"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text("")
    (src_dir / "main.py").write_text('''
"""Main module."""

def main():
    x = 1  # noqa: F841
    print("Hello")


class Example:
    def method(self):  # pylint: disable=no-self-use
        return 42
''')

    # Create test files
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "test_main.py").write_text('''
"""Tests for main module."""

import pytest


def test_example():
    assert True
''')

    return project_dir


@pytest.fixture
def project_with_requirements(tmp_path: Path) -> Path:
    """Create a project with requirements.txt."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    (project_dir / "requirements.txt").write_text("""
requests==2.28.0
flask==2.0.0
django==3.2.0
""")

    (project_dir / "pyproject.toml").write_text("""
[project]
name = "sample"
version = "0.1.0"
dependencies = [
    "requests>=2.28.0",
    "flask>=2.0.0",
]
""")

    return project_dir


@pytest.fixture
def project_with_configs(tmp_path: Path) -> Path:
    """Create a project with various linter configs."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Ruff config
    (project_dir / "ruff.toml").write_text("""
line-length = 88
select = ["E", "F", "W"]
""")

    # Flake8 config
    (project_dir / ".flake8").write_text("""
[flake8]
max-line-length = 88
extend-ignore = E203
""")

    # Pre-commit config
    (project_dir / ".pre-commit-config.yaml").write_text("""
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
""")

    return project_dir
