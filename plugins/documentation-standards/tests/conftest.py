"""Pytest configuration for documentation-standards tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts directory to path so test files can import from scripts
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


@pytest.fixture
def sample_docs_dir(tmp_path: Path) -> Path:
    """Create a sample documentation directory."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    # Create index
    (docs_dir / "index.md").write_text("""---
documentation_type: explanation
---

# Documentation

Welcome to the docs.

- [Getting Started](./tutorial.md)
- [How-To Guides](./howto.md)
- [API Reference](./api/reference.md)
""")

    # Create tutorial
    (docs_dir / "tutorial.md").write_text("""---
documentation_type: tutorial
---

# Getting Started Tutorial

Learn how to use the library step by step.
""")

    # Create how-to
    (docs_dir / "howto.md").write_text("""---
documentation_type: how-to
---

# How-To Guides

Practical guides for common tasks.
""")

    # Create API reference
    api_dir = docs_dir / "api"
    api_dir.mkdir()
    (api_dir / "reference.md").write_text("""---
documentation_type: reference
---

# API Reference

## Functions

### `example_function()`

Does something useful.
""")

    return docs_dir


@pytest.fixture
def markdown_with_links(tmp_path: Path) -> Path:
    """Create markdown file with various link types."""
    md_file = tmp_path / "test.md"
    md_file.write_text("""# Test Document

## Internal Links

- [Relative link](./other.md)
- [Parent link](../parent.md)
- [Anchor link](#section)

## External Links

- [Google](https://google.com)
- [GitHub](https://github.com)

## Reference Links

Check [the docs][docs] for more.

[docs]: https://docs.example.com
""")
    return md_file
