---
name: quality-enforcement
description: |
  Automatic quality enforcement using static analysis and linting tools.
  Use when writing code, fixing issues, or setting up quality tools.
  Prevents manual file iteration by recommending automation.
  Ensures prek hooks run and quality standards met.
documentation_type: reference
---

This skill is automatically invoked when Claude works on code quality.

When this skill is active, Claude will:

- Run static analysis tools before committing
- Prevent manual iteration over multiple similar files
- Recommend appropriate automation tools (formatters, linters)
- Ensure all issues resolved or explicitly ignored with reasoning
- Set up prek pre-commit hooks when missing
- Never satisfied until quality checks pass

Claude should invoke this skill whenever:

- Writing or modifying code
- Fixing linting or formatting issues
- About to iterate over multiple files for similar changes
- Setting up or configuring quality tools
- User requests quality improvements

## Available Scripts

This skill can invoke the following scripts:

- `uv run plugins/static-analysis/scripts/quality_metrics.py` - Calculate code quality metrics
- `uv run plugins/static-analysis/scripts/security_scanner.py` - Scan for security issues
- `uv run plugins/static-analysis/scripts/generate_ci_workflow.py` - Generate CI/CD quality workflows
- `uv run plugins/static-analysis/scripts/refactoring_planner.py` - Plan safe refactoring operations

Run with `--help` for full options.

## Script Usage Examples

```bash
# Calculate quality metrics for a directory
uv run scripts/quality_metrics.py src/

# Set quality gates
uv run scripts/quality_metrics.py src/ --max-complexity 10 --min-maintainability 50

# Scan for security issues
uv run scripts/security_scanner.py src/ --output sarif > security.sarif

# Generate CI workflow
uv run scripts/generate_ci_workflow.py . --output .github/workflows/quality.yml

# Plan a rename operation
uv run scripts/refactoring_planner.py rename old_name new_name src/
```

## Quality Gates

Define minimum standards for code quality:

```bash
# Fail if complexity exceeds threshold
uv run scripts/quality_metrics.py src/ --max-complexity 15 --fail-on-violation

# Check maintainability index
uv run scripts/quality_metrics.py src/ --min-maintainability 40
```

## Security Scanning

Integrate security checks into your workflow:

```bash
# Run security scan
uv run scripts/security_scanner.py src/

# Output SARIF for GitHub Security tab
uv run scripts/security_scanner.py src/ --output sarif > results.sarif
```

## Best Practices

1. **Run quality checks before commits** - Use prek hooks
2. **Set reasonable thresholds** - Start lenient, tighten over time
3. **Track metrics over time** - Use `--history` to detect trends
4. **Integrate into CI** - Use generated workflows for consistency

## Security-Focused Analysis

This skill prioritizes security issues over style issues:

### Security Scanner Capabilities

```bash
# Full security scan
uv run scripts/security_scanner.py src/

# Scan with severity filter
uv run scripts/security_scanner.py src/ --severity high

# Output SARIF for GitHub Security integration
uv run scripts/security_scanner.py src/ --output sarif > security.sarif
```

### Security Checks Performed

| Check | Description |
|-------|-------------|
| Hardcoded secrets | API keys, passwords, tokens in code |
| SQL injection | Unsafe string formatting in queries |
| Command injection | Unsafe shell command construction |
| Path traversal | Unsanitized file path usage |
| Weak cryptography | MD5, SHA1, weak random generators |
| Unsafe deserialization | Pickle, eval, exec usage |

### Security Prioritization

When quality issues are found, address them in this order:

1. **Critical security** - Hardcoded secrets, injection vulnerabilities
2. **High security** - Weak crypto, unsafe deserialization
3. **Medium security** - Missing input validation
4. **Quality issues** - Complexity, style, maintainability

### Track Security Debt

```bash
# Security issues count as technical debt
uv run scripts/security_scanner.py src/ --output json | jq '.summary'

# Integrate with quality metrics
uv run scripts/quality_metrics.py src/ --include-security
```

## Dependency Security

Check dependencies for known vulnerabilities:

```bash
# Analyze dependencies
uv run scripts/dependency_analyzer.py . --check-security

# Generate update plan for vulnerable packages
uv run scripts/dependency_analyzer.py . --check-security --update-plan
```

## Suppression Audit

Track and audit linter suppressions:

```bash
# Find all noqa, pylint:disable, etc.
uv run scripts/suppression_auditor.py src/

# Require documented reasons for all suppressions
uv run scripts/suppression_auditor.py src/ --require-reason

# Generate suppression statistics
uv run scripts/suppression_auditor.py src/ --stats
```

This ensures suppressions are intentional and documented, not just silencing valid warnings.
