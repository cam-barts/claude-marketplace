---
name: quality-tooling
description: |
  Use when configuring linters or detecting tool conflicts.
  Covers cross-config conflict detection across pyproject, ruff.toml, mypy.ini, and friends.
documentation_type: reference
---

Configure quality tooling. Pick linters from the approved set below — Claude already knows the file-type mapping.

## Scripts

- `uv run plugins/static-analysis/scripts/detect_tool_conflicts.py` — detect overlapping or redundant linters and conflicting settings across config files

Run with `--help` for full options.

## Approved tooling
- `ruff` — lint and format (replaces flake8, isort, black)
- `mypy` — static type checking
- `bandit` — security scanning
- `prek` — pre-commit hook runner

## CI/CD
- Pre-commit: prek hooks run on every commit
- Cloud CI: GitHub Actions — quality workflow in `.github/workflows/`
- Quality gates: lint clean, type clean, bandit clean, 80% line coverage
