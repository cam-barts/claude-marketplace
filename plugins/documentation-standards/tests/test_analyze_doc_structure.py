"""Tests for analyze_doc_structure.py script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestDiataxisClassification:
    """Tests for Diataxis documentation classification."""

    def test_classify_tutorial(self, tmp_path: Path) -> None:
        """Test classifying a tutorial document."""
        doc = tmp_path / "tutorial.md"
        doc.write_text("""---
documentation_type: tutorial
---

# Getting Started

In this tutorial, you will learn how to...

## Step 1: Install

First, install the package...

## Step 2: Configure

Next, configure your settings...
""")

        from analyze_doc_structure import classify_document

        doc_type = classify_document(doc)
        assert doc_type == "tutorial"

    def test_classify_reference(self, tmp_path: Path) -> None:
        """Test classifying a reference document."""
        doc = tmp_path / "api.md"
        doc.write_text("""---
documentation_type: reference
---

# API Reference

## Functions

### `get_user(id: int) -> User`

Returns a user by ID.

**Parameters:**
- `id`: The user ID

**Returns:** User object
""")

        from analyze_doc_structure import classify_document

        doc_type = classify_document(doc)
        assert doc_type == "reference"

    def test_infer_type_from_content(self, tmp_path: Path) -> None:
        """Test inferring type from content when no frontmatter."""
        doc = tmp_path / "howto.md"
        doc.write_text("""
# How to Configure SSL

This guide shows how to configure SSL for your application.

## Prerequisites

You will need:
- A certificate
- A key file

## Steps

1. Generate a certificate
2. Configure the server
3. Test the connection
""")

        from analyze_doc_structure import infer_type_from_content

        # Without frontmatter, should infer from content
        doc_type = infer_type_from_content(doc.read_text())
        assert doc_type == "how-to"


class TestGapAnalysis:
    """Tests for documentation gap analysis."""

    def test_identify_missing_types(self, tmp_path: Path) -> None:
        """Test identifying missing documentation types."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create only tutorials
        for i in range(3):
            doc = docs_dir / f"tutorial{i}.md"
            doc.write_text(f"---\ndocumentation_type: tutorial\n---\n# Tutorial {i}")

        from analyze_doc_structure import analyze_structure

        report = analyze_structure(docs_dir)

        # Should identify missing how-to, reference, explanation
        assert "how-to" in report.missing_types or len(report.missing_types) > 0

    def test_coverage_report(self, tmp_path: Path) -> None:
        """Test documentation coverage report."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        types = ["tutorial", "how-to", "reference", "explanation"]
        for doc_type in types:
            doc = docs_dir / f"{doc_type}.md"
            doc.write_text(f"---\ndocumentation_type: {doc_type}\n---\n# {doc_type}")

        from analyze_doc_structure import analyze_structure

        report = analyze_structure(docs_dir)

        # All types covered
        assert len(report.missing_types) == 0
        assert report.coverage == 100.0


class TestNavGeneration:
    """Tests for navigation generation."""

    def test_generate_zensical_nav(self, tmp_path: Path) -> None:
        """Test generating zensical navigation."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "index.md").write_text("# Home")
        (docs_dir / "guide.md").write_text("# Guide")

        subdir = docs_dir / "api"
        subdir.mkdir()
        (subdir / "reference.md").write_text("# API")

        from analyze_doc_structure import generate_zensical_nav

        nav = generate_zensical_nav(docs_dir)
        assert "nav" in nav
        assert len(nav["nav"]) >= 1


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from analyze_doc_structure import main

        old_argv = sys.argv
        try:
            sys.argv = ["analyze_doc_structure.py", "/nonexistent/path"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
