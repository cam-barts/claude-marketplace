---
name: test-writing
description: |
  Use when writing new pytest tests or auditing fixture health and test smells.
  Covers fixture graph analysis and anti-pattern detection. Author scaffolding and Hypothesis strategies inline from source context.
documentation_type: reference
---

Write and improve pytest test suites. Scaffolds and Hypothesis strategies are best authored inline from the source — reach for the scripts below when the work needs cross-file AST/CST analysis.

## Scripts

- `uv run plugins/pytest-standards/scripts/analyze_fixtures.py` — map fixture dependency graph; flag cycles, deep nesting, scope mismatches, unused fixtures
- `uv run plugins/pytest-standards/scripts/analyze_test_smells.py` — detect anti-patterns: assertion roulette, eager tests, mock overload, magic numbers, dead tests

Run any script with `--help` for full options.

## Conventions
- Naming: `test_<verb>_<what>_when_<condition>` (e.g., `test_parse_raises_when_empty`)
- Fixture scope: `function` by default; `session` only for expensive shared resources — document the reason in the fixture docstring
- Tests mirror source structure: `plugins/foo/scripts/bar.py` → `plugins/foo/tests/test_bar.py`
- Add `@given` Hypothesis tests for any function accepting primitive inputs or collections
