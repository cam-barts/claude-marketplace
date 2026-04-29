---
documentation_type: reference
---

# Documentation Standards Scripts

Python scripts for documentation tasks that benefit from cross-file or async work.

## Scripts

### `validate_links.py`

Validates internal and external links across the docs tree; async HTTP with caching; detects orphan files. Worth running over Edit/Grep because of the I/O.

### `sync_docstrings.py`

Compares Python docstrings (Google/NumPy/Sphinx) against external docs and reports drift. Multi-style AST diff across files.

## Requirements

- Python 3.8+
- [uv](https://docs.astral.sh/uv/) — scripts are self-installing via PEP 723 inline metadata

## Usage

```bash
chmod +x scripts/*.py
./scripts/validate_links.py docs/ --recursive
```

Run any script with `--help` for full options.

For routine markdown lint/fix, use `rumdl` and `vale` directly — Claude can drive those without a wrapper.
