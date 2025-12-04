---
name: tool-discovery
description: |
  Discovers appropriate quality tools using MegaLinter analysis.
  Use when analyzing codebases, setting up new projects, or improving quality processes.
  Recommends prek hooks and GitHub Actions based on project needs.
documentation_type: reference
---

This skill is automatically invoked when Claude analyzes code quality needs.

When this skill is active, Claude will:

- Run MegaLinter to discover quality issues
- Identify high-value linters for the project
- Recommend appropriate prek pre-commit hooks
- Suggest GitHub Actions quality workflows
- Prioritize tools with autofix capabilities

Claude should invoke this skill whenever:

- Setting up quality tools for new project
- Improving existing quality processes
- User asks what linters to use
- Analyzing code quality needs
- Discovering quality issues

## Available Scripts

This skill can invoke the following scripts:

- `uv run plugins/static-analysis/scripts/discover_linters.py` - Discover appropriate linters
- `uv run plugins/static-analysis/scripts/detect_tool_conflicts.py` - Find redundant tools

Run with `--help` for full options.

## Linter Discovery

Analyze a repository and recommend appropriate linters:

```bash
# Discover linters for current repo
uv run scripts/discover_linters.py .

# Generate installation script
uv run scripts/discover_linters.py . --install

# Prioritize Rust-based tools (faster)
uv run scripts/discover_linters.py . --rust-first
```

### Output Example

```text
File Types Found:
  .py   → 150 files
  .js   →  45 files
  .md   →  20 files

Recommended Linters:
  ruff      ✓ Installed   [Rust]  Fast Python linter + formatter
  biome     ✗ Not installed [Rust]  Fast JS/TS linter + formatter
  mypy      ✓ Installed           Static type checker

Missing Linters:
  biome: npm install -D @biomejs/biome
```

## Tool Conflict Detection

Identify redundant or conflicting linting tools:

```bash
# Check for conflicts
uv run scripts/detect_tool_conflicts.py .

# Only check installed tools
uv run scripts/detect_tool_conflicts.py . --installed

# Generate migration commands
uv run scripts/detect_tool_conflicts.py . --migrate
```

### Common Conflicts

| Conflict | Resolution |
|----------|------------|
| black + ruff | Use `ruff format` (faster, same output) |
| flake8 + ruff | Use `ruff check` (includes flake8 rules) |
| isort + ruff | Use `ruff check --select I` (isort rules) |
| prettier + biome | Use biome (Rust, faster) |
| eslint + biome | Use biome for formatting, keep eslint for custom rules |
| markdownlint + rumdl | Use `rumdl` (Rust, 10x faster, pyproject.toml config) |

### Migration Example

```bash
# Detect conflicts
uv run scripts/detect_tool_conflicts.py . --migrate

# Output:
# Remove redundant tools
pip uninstall black flake8 isort

# Configure ruff to replace removed tools
# Add to ruff.toml:
# select = ["E", "F", "I", "W"]
```

## Tool Prioritization

This skill recommends tools in this order:

1. **Rust-based tools** - Fastest, lowest overhead (ruff, biome, dprint)
2. **All-in-one tools** - Reduce configuration complexity
3. **Specialized tools** - When all-in-one doesn't cover the need
4. **Legacy tools** - Only when no modern alternative exists

### Rust-First Philosophy

Modern Rust-based tools are significantly faster:

| Task | Traditional | Rust-based |
|------|-------------|------------|
| Python lint | flake8 ~10s | ruff ~0.1s |
| Python format | black ~5s | ruff ~0.1s |
| JS/TS lint | eslint ~15s | biome ~0.5s |
| Markdown lint | markdownlint ~2s | rumdl ~0.2s |

## Integration with MegaLinter

For comprehensive analysis, use MegaLinter:

```bash
# Run MegaLinter to discover all issues
docker run -v $(pwd):/tmp/lint oxsecurity/megalinter:v7

# Then use discover_linters.py to prioritize which tools to keep
uv run scripts/discover_linters.py . --rust-first
```

## Workflow

1. **Discover** what tools are appropriate: `discover_linters.py`
2. **Detect** conflicts with existing tools: `detect_tool_conflicts.py`
3. **Migrate** to recommended toolset: `--migrate`
4. **Configure** pre-commit hooks with prek
