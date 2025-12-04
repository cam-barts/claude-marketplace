---
description: Fix quality issues automatically where possible
documentation_type: how-to
---

Invoke quality-enforcer agent to fix all quality issues.

This command will:

1. Run all quality tools to identify issues
2. Check if Rust-based automation exists for each issue type (prefer ruff, biome, uv)
3. Apply automated fixes using Rust tools where possible
4. Fix remaining issues manually
5. Explicitly ignore unfixable issues with reasoning
6. Re-run to verify all issues resolved or documented
7. STOP if about to manually iterate - find Rust-based automation first

Agent won't stop until all issues are resolved or explicitly ignored with clear reasoning.
