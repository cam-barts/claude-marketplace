---
name: quality-enforcement
description: |
  Use when enforcing code quality, measuring metrics, or auditing dependencies.
  Covers complexity metrics, maintainability index, and dependency vulnerability auditing. Run security scanners (bandit) and suppression greps directly via Bash.
documentation_type: reference
---

Enforce and measure code quality.

## Scripts

- `uv run plugins/static-analysis/scripts/quality_metrics.py` — cyclomatic complexity, maintainability index, LOC, code smells, quality gates (radon-based)
- `uv run plugins/static-analysis/scripts/dependency_analyzer.py` — audit dependencies for vulnerabilities, outdated packages, duplicates (multi-source correlation)

For security scans, run `bandit -r <path>` directly. For suppression audits, grep for `noqa`, `type: ignore`, `pylint: disable` and verify each has a trailing explanation.

Run any script with `--help` for full options.

## Quality gates
- Coverage: 80% line coverage minimum
- Complexity: flag functions with cyclomatic complexity > 10
- Maintainability: flag modules below maintainability index 20

## Suppression policy
- Every `# noqa`, `# type: ignore`, or `# bandit: disable` must include a trailing explanation
- Undocumented suppressions are treated as failures
- Security scan scope: project source files only (exclude `tests/`, `scripts/`)
