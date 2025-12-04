---
documentation_type: explanation
---

# pytest Standards Plugin

Enforces opinionated pytest testing standards based on modern best practices. Ensures all tests pass, maintains code coverage, and promotes property-based testing with Hypothesis.

## Philosophy

This plugin is **opinionated** and based on proven best practices:

- **"Assert results and outcome, not the steps needed to get there"** - Focus on final state, not implementation
- **"Prefer real objects over mocks"** - Use actual collaborators when possible
- **"Write tests which should pass for all inputs"** - Property-based testing with Hypothesis
- **Zero tolerance for failing tests** - Agent never satisfied until all tests pass
- **Coverage must not drop** - New code must be tested

## Features

### Test Quality Enforcement

- **Naming conventions**: test_module.py, test_function(), TestClass
- **Fixture best practices**: Appropriate use, not over/under-used
- **Mocking standards**: Always use `autospec`, prefer real objects
- **Assertion quality**: Outcomes over steps, avoid excessive mock assertions
- **Property-based testing**: Promotes Hypothesis for robust validation

### Coverage Management

- **Zero-drop policy**: Coverage must not decrease
- **Gap identification**: Shows specific uncovered lines
- **Proactive testing**: Suggests tests for new code
- **Trend tracking**: Reports coverage changes

### Test Organization

- **Arrange-Act-Assert pattern**: Clear test structure
- **One behavior per test**: Small, focused tests
- **Parametrization**: Reduces duplication
- **Marks for categorization**: unit, integration, slow, hypothesis

## Installation

```bash
/plugin install pytest-standards@cam-marketplace
```

## Commands

### `/test-run`

Run all tests with coverage and enforce zero-failure policy. Shows coverage report and fails if any tests don't pass or coverage dropped.

### `/test-fix`

Invoke the test-enforcer agent to fix all failing tests and improve coverage. Agent won't stop until all tests pass and coverage is maintained.

### `/test-review`

Review existing tests for adherence to best practices. Checks naming, fixtures, mocking, parametrization, and suggests improvements.

### `/test-coverage`

Generate comprehensive coverage report with missing lines. Warns if coverage dropped.

### `/test-hypothesis`

Analyze code and suggest opportunities for property-based testing with Hypothesis. Provides example implementations.

## Agent

**test-enforcer**: Specialized agent for testing that:

- Runs all tests and ensures they pass
- Maintains or improves code coverage
- Enforces pytest naming conventions
- Reviews fixture and mock usage
- Promotes property-based testing with Hypothesis
- Follows modern pytest best practices
- Never satisfied until tests pass and coverage maintained

## Skills

### `test-writing`

Automatically invoked when writing tests. Enforces naming conventions, fixture patterns, assertion quality, and promotes Hypothesis.

### `test-coverage`

Automatically invoked when code changes. Ensures coverage doesn't drop and suggests tests for uncovered code.

## Hooks

### Test Monitoring

1. **Test file modified**: Reminds to run tests
2. **Source code modified**: Suggests running coverage check
3. **New functions detected**: Suggests writing corresponding tests

## Testing Standards

### File Organization

```text
project/
├── src/
│   └── mymodule.py
└── tests/
    └── test_mymodule.py
```

### Naming Conventions

- **Files**: `test_<module>.py` for `<module>.py`
- **Functions**: `test_<function>()` for `<function>()`
- **Variations**: `test_<function>_<variation>()`
- **Classes**: `TestClassName` with `test_<method>()` methods

### Fixture Guidelines

✅ **DO**:

- Use for setup/teardown
- Use for dependency injection
- Place widely-used fixtures in `conftest.py`
- Name descriptively

❌ **DON'T**:

- Overuse for slight data variations
- Create obscure dependencies
- Use when factory functions suffice

### Mocking Rules

✅ **ALWAYS**:

- Use `mock.create_autospec()` or `mock.patch(autospec=True)`
- Maintain interface contracts
- Prefer real objects when possible

❌ **NEVER**:

- Use bare `Mock()` objects
- Over-assert on mock calls
- Mock when real object works

### Property-Based Testing with Hypothesis

Use Hypothesis for:

- Mathematical properties (commutativity, associativity)
- Data transformations (serialization, parsing)
- Invariants (list length after sort)
- Edge case discovery

Example:

```text
from hypothesis import given
import hypothesis.strategies as st

@given(st.lists(st.integers()))
def test_sort_preserves_length(lst):
    assert len(sorted(lst)) == len(lst)
```

## Configuration

The plugin includes default configurations:

- **pytest.ini**: Test discovery, output options, marks, coverage settings
- **.coveragerc**: Coverage reporting with exclude patterns

Projects can override by creating their own configuration files.

## Resources

- **Thea's Testing Style Guide**: <https://blog.thea.codes/my-python-testing-style-guide/>
- **Pytest Documentation**: <https://docs.pytest.org/>
- **Hypothesis Documentation**: <https://hypothesis.readthedocs.io/>
- **pytest-cov**: <https://pytest-cov.readthedocs.io/>

## Best Practices Compliance

This plugin follows Claude Code best practices:

### Agent

- ✅ Action-oriented description with "MUST BE USED" and "PROACTIVELY"
- ✅ Explicit tools list for security and focus
- ✅ Single responsibility (test enforcement)
- ✅ Structured workflow instructions

### Skills

- ✅ Specific trigger keywords (tests, pytest, coverage)
- ✅ Focused capabilities
- ✅ Clear invocation triggers

### Hooks

- ✅ Appropriate types (notification)
- ✅ Secure bash commands
- ✅ Safe path handling
- ✅ Command existence checks

### Plugin Structure

- ✅ Correct directory organization
- ✅ Semantic versioning (0.1.0 pre-release)
- ✅ Comprehensive documentation

## Attribution & Credits

This plugin was inspired by and built upon the following resources:

### Thea Flowers' Python Testing Style Guide

- **Source**: <https://blog.thea.codes/my-python-testing-style-guide/>
- **Author**: Stargirl Flowers (Thea Flowers)
- **Usage**: Core testing philosophy, fixture patterns, mocking guidelines, assertion philosophy, and naming conventions

### Real Python - Effective Python Testing With pytest

- **Source**: <https://realpython.com/pytest-python-testing/>
- **Author**: Real Python Team (Dane Hillard)
- **Usage**: pytest features (fixtures, marks, parametrization), best practices, plugin recommendations, and workflow patterns

### Hypothesis Documentation

- **Source**: <https://hypothesis.readthedocs.io/>
- **Project**: <https://github.com/HypothesisWorks/hypothesis>
- **License**: Mozilla Public License 2.0
- **Usage**: Property-based testing principles, strategies, and integration patterns with pytest

### pytest Documentation

- **Source**: <https://docs.pytest.org/>
- **Project**: <https://github.com/pytest-dev/pytest>
- **License**: MIT
- **Usage**: Testing framework features, configuration, and best practices

### pytest-cov

- **Source**: <https://pytest-cov.readthedocs.io/>
- **Project**: <https://github.com/pytest-dev/pytest-cov>
- **License**: MIT
- **Usage**: Coverage reporting configuration and integration

### Claude Code Documentation

- **Source**: <https://code.claude.com/docs>
- **Usage**: Plugin architecture, best practices, and component design patterns

All configurations and implementations follow the licenses and terms of their respective sources.
