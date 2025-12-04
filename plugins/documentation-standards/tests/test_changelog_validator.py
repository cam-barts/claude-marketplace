"""Tests for changelog_validator.py script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestChangelogParsing:
    """Tests for parsing changelog files."""

    def test_parse_valid_changelog(self, tmp_path: Path) -> None:
        """Test parsing a valid Keep a Changelog format."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("""
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- New feature X

## [1.0.0] - 2024-01-15

### Added
- Initial release

### Changed
- Updated dependencies

[Unreleased]: https://github.com/example/project/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/example/project/releases/tag/v1.0.0
""")

        from changelog_validator import parse_changelog

        parsed = parse_changelog(changelog)
        assert len(parsed.versions) >= 2
        assert "Unreleased" in [v.name for v in parsed.versions]
        assert "1.0.0" in [v.name for v in parsed.versions]

    def test_extract_sections(self, tmp_path: Path) -> None:
        """Test extracting change sections."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("""
## [1.0.0] - 2024-01-15

### Added
- Feature A
- Feature B

### Fixed
- Bug X

### Removed
- Deprecated API
""")

        from changelog_validator import parse_changelog

        parsed = parse_changelog(changelog)
        version = parsed.versions[0]

        assert "Added" in version.sections
        assert len(version.sections["Added"]) == 2
        assert "Fixed" in version.sections
        assert "Removed" in version.sections


class TestVersionValidation:
    """Tests for version format validation."""

    def test_valid_semver(self, tmp_path: Path) -> None:
        """Test validating semantic versioning."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("""
## [1.2.3] - 2024-01-15

### Added
- Something
""")

        from changelog_validator import validate_changelog

        report = validate_changelog(changelog)
        assert len(report.version_errors) == 0

    def test_invalid_version_format(self, tmp_path: Path) -> None:
        """Test detecting invalid version format."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("""
## [v1.2] - 2024-01-15

### Added
- Something
""")

        from changelog_validator import validate_changelog

        report = validate_changelog(changelog)
        # Should detect non-standard version format
        assert len(report.version_errors) >= 1 or len(report.warnings) >= 1


class TestDateValidation:
    """Tests for date format validation."""

    def test_valid_date_format(self, tmp_path: Path) -> None:
        """Test validating ISO date format."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("""
## [1.0.0] - 2024-01-15

### Added
- Something
""")

        from changelog_validator import validate_changelog

        report = validate_changelog(changelog)
        assert len(report.date_errors) == 0

    def test_invalid_date_format(self, tmp_path: Path) -> None:
        """Test detecting invalid date format."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("""
## [1.0.0] - January 15, 2024

### Added
- Something
""")

        from changelog_validator import validate_changelog

        report = validate_changelog(changelog)
        assert len(report.date_errors) >= 1


class TestLinkValidation:
    """Tests for version link validation."""

    def test_missing_version_links(self, tmp_path: Path) -> None:
        """Test detecting missing version comparison links."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("""
## [Unreleased]

### Added
- Feature

## [1.0.0] - 2024-01-15

### Added
- Initial release
""")

        from changelog_validator import validate_changelog

        report = validate_changelog(changelog)
        # Should detect missing link definitions
        assert len(report.link_errors) >= 1 or len(report.warnings) >= 1

    def test_valid_links(self, tmp_path: Path) -> None:
        """Test validating proper version links."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("""
## [Unreleased]

### Added
- Feature

## [1.0.0] - 2024-01-15

### Added
- Initial release

[Unreleased]: https://github.com/example/project/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/example/project/releases/tag/v1.0.0
""")

        from changelog_validator import validate_changelog

        report = validate_changelog(changelog)
        assert len(report.link_errors) == 0


class TestSectionValidation:
    """Tests for section type validation."""

    def test_valid_sections(self, tmp_path: Path) -> None:
        """Test validating standard section types."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("""
## [1.0.0] - 2024-01-15

### Added
- Feature

### Changed
- Update

### Deprecated
- Old API

### Removed
- Legacy code

### Fixed
- Bug

### Security
- Vulnerability fix
""")

        from changelog_validator import validate_changelog

        report = validate_changelog(changelog)
        assert len(report.section_errors) == 0

    def test_invalid_section_type(self, tmp_path: Path) -> None:
        """Test detecting non-standard section types."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("""
## [1.0.0] - 2024-01-15

### New Stuff
- Something

### Bug Fixes
- Fix
""")

        from changelog_validator import validate_changelog

        report = validate_changelog(changelog)
        # Should detect non-standard sections
        assert len(report.section_errors) >= 1 or len(report.warnings) >= 1


class TestCLI:
    """Tests for CLI functionality."""

    def test_main_with_nonexistent_path(self) -> None:
        """Test main with nonexistent path."""
        import sys

        from changelog_validator import main

        old_argv = sys.argv
        try:
            sys.argv = ["changelog_validator.py", "/nonexistent/path"]
            result = main()
            assert result == 1
        finally:
            sys.argv = old_argv
