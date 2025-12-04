"""Tests for validate_links.py script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestLinkExtraction:
    """Tests for extracting links from markdown."""

    def test_extract_markdown_links(self, tmp_path: Path) -> None:
        """Test extracting markdown-style links."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
# Test Document

Check out [this link](other.md) and [another](../readme.md).
""")

        from validate_links import extract_links

        links = extract_links(md_file)
        assert len(links) == 2
        assert any("other.md" in link.url for link in links)

    def test_extract_reference_links(self, tmp_path: Path) -> None:
        """Test extracting reference-style links."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
# Test Document

See [the docs][1] for more info.

[1]: ./docs/guide.md
""")

        from validate_links import extract_links

        links = extract_links(md_file)
        assert len(links) >= 1

    def test_skip_external_links(self, tmp_path: Path) -> None:
        """Test that external links are identified."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
Check [Google](https://google.com) and [local](./local.md).
""")

        from validate_links import extract_links

        links = extract_links(md_file)
        external = [link for link in links if link.is_external]
        internal = [link for link in links if not link.is_external]

        assert len(external) == 1
        assert len(internal) == 1


class TestLinkValidation:
    """Tests for validating links."""

    def test_valid_internal_link(self, tmp_path: Path) -> None:
        """Test validating a valid internal link."""
        (tmp_path / "target.md").write_text("# Target")

        md_file = tmp_path / "doc.md"
        md_file.write_text("[Link](target.md)")

        from validate_links import validate_links

        report = validate_links(md_file.parent)
        assert len(report.broken_links) == 0

    def test_broken_internal_link(self, tmp_path: Path) -> None:
        """Test detecting a broken internal link."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("[Link](nonexistent.md)")

        from validate_links import validate_links

        report = validate_links(md_file.parent)
        assert len(report.broken_links) == 1

    def test_orphaned_files(self, tmp_path: Path) -> None:
        """Test detecting orphaned files."""
        (tmp_path / "linked.md").write_text("# Linked")
        (tmp_path / "orphan.md").write_text("# Orphan")

        md_file = tmp_path / "index.md"
        md_file.write_text("[Link](linked.md)")

        from validate_links import validate_links

        report = validate_links(md_file.parent, find_orphans=True)
        orphan_names = [p.name for p in report.orphaned_files]
        assert "orphan.md" in orphan_names


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from validate_links import main

        old_argv = sys.argv
        try:
            sys.argv = ["validate_links.py", "/nonexistent/path"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
