---
name: documentation-work
description: |
  Use when writing, fixing, validating, or planning documentation.
  Covers link validation, docstring drift, Diataxis frontmatter, and changelog conventions.
documentation_type: reference
---

Create, fix, and validate documentation. Use built-in tools (Edit, Grep, `rumdl`, `vale`) for routine markdown lint/fix; reach for the scripts below when the work needs cross-file analysis or async I/O.

## Scripts

- `uv run plugins/documentation-standards/scripts/validate_links.py` — async validation of internal and external links with caching; detects orphan files
- `uv run plugins/documentation-standards/scripts/sync_docstrings.py` — compare Python docstrings (Google/NumPy/Sphinx) with external docs; report drift

Run any script with `--help` for full options.

## Conventions
- Vale style: `write-good` only — run `vale --minAlertLevel=warning .`
- Markdown lint/fix: prefer `rumdl` for routine checks
- All docs must have `documentation_type` frontmatter set to the correct Diataxis type (tutorial, how-to, reference, explanation)
- Distribution target: ~60% reference, ~20% how-to, ~20% tutorial+explanation
- Changelog: Keep-a-Changelog format; sections Added/Changed/Deprecated/Removed/Fixed/Security; `## [Unreleased]` stays at top and is dated on release; semver versioning
