---
name: quality-metrics
description: |
  Tracks and reports code quality metrics over time.
  Use when reviewing overall code quality, preparing quality reports,
  setting quality gates, or tracking technical debt.
  Calculates complexity, maintainability, and other metrics.
documentation_type: reference
---

This skill is automatically invoked when Claude analyzes code quality metrics.

When this skill is active, Claude will:

- Calculate cyclomatic complexity for functions and classes
- Compute maintainability index scores
- Count lines of code by type (code, comments, blank)
- Track metrics over time when history is available
- Generate quality reports and dashboards
- Set and monitor quality gates
- Compare quality across branches/releases

Claude should invoke this skill whenever:

- Reviewing overall code quality
- Preparing quality reports for stakeholders
- Setting up quality gates for CI/CD
- Tracking technical debt
- Comparing code quality between releases

## Available Scripts

This skill can invoke the following scripts:

- `uv run plugins/static-analysis/scripts/quality_metrics.py` - Calculate code quality metrics

Run with `--help` for full options.

## Script Usage Examples

```bash
# Analyze a Python project
uv run scripts/quality_metrics.py src/

# Calculate specific metrics
uv run scripts/quality_metrics.py src/ --metrics complexity,loc

# Set quality thresholds
uv run scripts/quality_metrics.py src/ --threshold complexity:10

# Track history over time
uv run scripts/quality_metrics.py src/ --history metrics_history.json

# Fail if quality gates not met
uv run scripts/quality_metrics.py src/ --fail-gates --threshold complexity:15

# Output as JSON
uv run scripts/quality_metrics.py src/ --output json > metrics.json
```

## Metrics Explained

### Cyclomatic Complexity

Measures the number of linearly independent paths through code.

| Score | Risk Level | Recommendation |
|-------|------------|----------------|
| 1-5 | Low | Simple, well-structured code |
| 6-10 | Moderate | Consider simplification |
| 11-20 | High | Refactor to reduce complexity |
| 21+ | Very High | Must refactor, high bug risk |

**Calculation**: Count decision points (if, for, while, case, catch, and, or) + 1

### Maintainability Index

Composite metric indicating how maintainable code is (0-100 scale).

| Score | Rating | Meaning |
|-------|--------|---------|
| 85-100 | Excellent | Highly maintainable |
| 65-84 | Good | Reasonably maintainable |
| 40-64 | Moderate | Difficult to maintain |
| 0-39 | Poor | Very difficult to maintain |

**Formula**: Based on Halstead Volume, Cyclomatic Complexity, and Lines of Code

### Lines of Code Metrics

- **SLOC**: Source Lines of Code (excluding blanks/comments)
- **LLOC**: Logical Lines of Code (statements)
- **Comments**: Number of comment lines
- **Blank**: Number of blank lines
- **Comment Ratio**: Comments / SLOC (aim for 10-30%)

### Code Smells

Patterns that indicate potential problems:

- **Long Method**: Functions > 50 lines
- **Large Class**: Classes > 300 lines
- **Too Many Parameters**: Functions with > 5 parameters
- **Deep Nesting**: Code nested > 4 levels
- **Long Parameter List**: > 4 parameters

## Quality Gates

Set thresholds to enforce quality:

```bash
# Block if any function has complexity > 15
uv run scripts/quality_metrics.py src/ --threshold max_complexity:15 --fail-gates

# Block if average complexity > 5
uv run scripts/quality_metrics.py src/ --threshold avg_complexity:5 --fail-gates

# Block if maintainability < 65
uv run scripts/quality_metrics.py src/ --threshold min_maintainability:65 --fail-gates

# Multiple gates
uv run scripts/quality_metrics.py src/ \
  --threshold max_complexity:15 \
  --threshold avg_complexity:5 \
  --threshold min_maintainability:65 \
  --fail-gates
```

## Report Structure

```text
CODE QUALITY METRICS
====================

Project: myproject
Files Analyzed: 45
Total Lines: 12,450

COMPLEXITY
==========
Average Complexity: 4.2 (Good)
Max Complexity: 18 (High - needs attention)

Most Complex Functions:
  18  src/parser.py::parse_expression
  15  src/compiler.py::optimize_ast
  12  src/evaluator.py::evaluate_node

MAINTAINABILITY
===============
Average MI: 72.5 (Good)
Lowest MI: 45.2 (src/legacy.py)

FILES NEEDING ATTENTION
=======================
  src/parser.py - High complexity (18)
  src/legacy.py - Low maintainability (45.2)

CODE SMELLS
===========
  Long Method: 3 functions > 50 lines
  Deep Nesting: 2 functions with depth > 4
  Too Many Parameters: 1 function with 8 params

QUALITY GATES
=============
✓ avg_complexity <= 5 (actual: 4.2)
✗ max_complexity <= 15 (actual: 18)
✓ min_maintainability >= 65 (actual: 72.5)

Result: FAILED (1 gate failed)
```

## Tracking Over Time

Use `--history` to track metrics across runs:

```bash
# First run - creates history
uv run scripts/quality_metrics.py src/ --history .metrics/history.json

# Subsequent runs - appends to history
uv run scripts/quality_metrics.py src/ --history .metrics/history.json

# View trends
uv run scripts/quality_metrics.py src/ --history .metrics/history.json --show-trends
```

History enables:

- Detect quality regression
- Track improvement over time
- Generate trend reports
- Alert on degradation
