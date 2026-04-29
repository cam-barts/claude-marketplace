---
name: test-analysis
description: |
  Use when diagnosing failing tests, analyzing coverage gaps, or profiling slow test suites.
  Parses pytest output, reports coverage by complexity, and identifies slow tests and fixtures.
documentation_type: reference
---

Analyze test suite health: failures, coverage, and performance.

## Scripts

- `uv run plugins/pytest-standards/scripts/coverage_analyzer.py` — parse coverage.py JSON, weight line/branch coverage by cyclomatic complexity, rank test targets

Run any script with `--help` for full options.

## Thresholds
- Coverage gate: 80% line coverage minimum — fail the suite if it drops below this
- Slow test budget: flag any test exceeding 5 seconds; investigate before merging
- Branch coverage tracked but not gated
