---
description: Set up quality tools for the repository
documentation_type: how-to
---

Analyze repository and set up appropriate quality tools.

This command will:

1. Analyze repository (languages, frameworks, existing tools)
2. Run MegaLinter to discover valuable linters
3. Set up `.pre-commit-config.yaml` with prek hooks (preferring Rust tools: ruff, biome, uv)
4. Configure GitHub Actions quality workflow
5. Install prek hooks
6. Run initial quality check
7. Document configuration choices and Rust tool selections

Establishes comprehensive quality enforcement from scratch.
