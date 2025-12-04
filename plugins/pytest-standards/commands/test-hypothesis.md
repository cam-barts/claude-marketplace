---
description: Suggest Hypothesis property-based tests
documentation_type: how-to
---

Analyze codebase and suggest opportunities for property-based testing with Hypothesis.

This command will:

1. Identify functions suitable for property-based testing:
    - Pure functions with clear mathematical properties
    - Data transformations
    - Functions with invariants
    - Serialization/deserialization
2. Suggest appropriate Hypothesis strategies
3. Provide example test implementations
4. Show how to use `@given` decorator

Property-based testing finds edge cases you'd miss with example-based tests.
