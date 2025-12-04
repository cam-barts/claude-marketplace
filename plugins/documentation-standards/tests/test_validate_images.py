"""Tests for validate_images.py script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestImageExtraction:
    """Tests for extracting image references from markdown."""

    def test_extract_markdown_images(self, tmp_path: Path) -> None:
        """Test extracting markdown-style image references."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
# Test Document

![Alt text](images/photo.png)

Some text here.

![Another image](../assets/diagram.svg)
""")

        from validate_images import extract_images

        images = extract_images(md_file)
        assert len(images) == 2
        assert any("photo.png" in img.path for img in images)
        assert any("diagram.svg" in img.path for img in images)

    def test_extract_html_images(self, tmp_path: Path) -> None:
        """Test extracting HTML-style image references."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
# Test Document

<img src="images/logo.png" alt="Logo" />

<img src="assets/banner.jpg" alt="Banner" width="800" />
""")

        from validate_images import extract_images

        images = extract_images(md_file)
        assert len(images) == 2


class TestAltTextValidation:
    """Tests for alt text validation."""

    def test_missing_alt_text(self, tmp_path: Path) -> None:
        """Test detecting missing alt text."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
![](images/photo.png)
""")

        from validate_images import validate_images

        report = validate_images(md_file.parent)
        assert len(report.missing_alt_text) >= 1

    def test_valid_alt_text(self, tmp_path: Path) -> None:
        """Test images with valid alt text."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
![A descriptive alt text](images/photo.png)
""")

        from validate_images import validate_images

        report = validate_images(md_file.parent)
        assert len(report.missing_alt_text) == 0


class TestBrokenImageDetection:
    """Tests for detecting broken image references."""

    def test_detect_missing_image(self, tmp_path: Path) -> None:
        """Test detecting missing image file."""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""
![Alt text](images/nonexistent.png)
""")

        from validate_images import validate_images

        report = validate_images(md_file.parent)
        assert len(report.broken_images) >= 1

    def test_valid_image_reference(self, tmp_path: Path) -> None:
        """Test valid image reference."""
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        (images_dir / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        md_file = tmp_path / "doc.md"
        md_file.write_text("""
![Alt text](images/photo.png)
""")

        from validate_images import validate_images

        report = validate_images(md_file.parent)
        assert len(report.broken_images) == 0


class TestFileSizeValidation:
    """Tests for image file size validation."""

    def test_detect_large_image(self, tmp_path: Path) -> None:
        """Test detecting oversized images."""
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        # Create a 2MB file (over typical limit)
        large_file = images_dir / "large.png"
        large_file.write_bytes(b"\x89PNG" + b"\x00" * (2 * 1024 * 1024))

        md_file = tmp_path / "doc.md"
        md_file.write_text("""
![Large image](images/large.png)
""")

        from validate_images import validate_images

        report = validate_images(md_file.parent, max_size_kb=1024)
        assert len(report.oversized_images) >= 1


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from validate_images import main

        old_argv = sys.argv
        try:
            sys.argv = ["validate_images.py", "/nonexistent/path"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
