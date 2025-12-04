---
documentation_type: explanation
---

# Static Analysis Plugin

Enforces code quality through automated static analysis tools, prek pre-commit hooks, and MegaLinter. **Prefers Rust-based tools for 10-100x speed improvements.** Discovers quality standards, prevents manual file iteration, and ensures all issues are resolved or explicitly ignored.

## Philosophy

This plugin is **opinionated** about automation, speed, and explicit decision-making:

- **"Automate everything"** - Never manually iterate when a tool exists
- **"Rust over Python"** - Prefer Rust-based tools (ruff, biome, uv) for massive speed gains
- **"Understand, then enforce"** - Discover standards before adding new ones
- **"Fail fast, fix faster"** - Catch issues in pre-commit and CI/CD
- **"Explicit over implicit"** - All ignored issues must have documented reasoning
- **Zero tolerance for unaddressed issues** - Fix, suppress with reason, or configure out with justification

## Features

### Rust-First Tool Selection

- **Python**: `ruff` (replaces black, flake8, isort, pyupgrade, autoflake) - 10-100x faster
- **JavaScript/TypeScript**: `biome` (replaces eslint + prettier) - 10-20x faster
- **Package management**: `uv`/`uvx` (replaces pip, pipx, poetry, pyenv) - 10-100x faster
- **File operations**: `fd`, `ripgrep`, `bat`, `eza`, `dust`
- **Formatting**: `dprint` (multi-language, 20-60x faster than prettier)
- **Spell checking**: `typos-cli` (fast Rust spell checker)

### Automated Quality Enforcement

- **prek pre-commit hooks**: Faster, dependency-free pre-commit alternative (Rust-based)
- **MegaLinter integration**: Discover and run 50+ linters automatically
- **GitHub Actions**: CI/CD quality gates
- **Tool discovery**: Analyzes repo and recommends appropriate Rust-based linters
- **Autofix prioritization**: Prefers Rust tools with automatic fixing

### Manual Iteration Prevention

- **Detects when Claude plans to iterate** over multiple similar files
- **Intervenes and recommends Rust automation**: formatters, linters with --fix, refactoring tools
- **Examples caught**:
    - Python formatting → Use `ruff format` (not `black`)
    - Python linting → Use `ruff check --fix` (not `flake8`, `pylint`)
    - JS/TS formatting → Use `biome format` or `dprint fmt` (not `prettier`)
    - JS/TS linting → Use `biome lint` (not `eslint`)
    - Import sorting → Use `ruff --select I` (not `isort`)
    - Package install → Use `uvx` (not `pipx`)

### Explicit Issue Resolution

- **Fixed**: Correct the problem
- **Suppressed**: Disable with inline comment explaining why
- **Configured out**: Adjust tool config with documented reasoning
- **Tool removed**: Remove tool with justification
- **Never acceptable**: Unaddressed warnings or silent ignoring

## Installation

```bash
/plugin install static-analysis@cam-marketplace
```

## Commands

### `/quality-check`

Run all configured quality tools and report issues. Fails if unaddressed issues exist.

### `/quality-setup`

Analyze repository and set up appropriate quality tools (prek, MegaLinter, GitHub Actions).

### `/quality-fix`

Fix all quality issues using automation where possible. Prevents manual iteration by finding appropriate tools first.

### `/quality-discover`

Use MegaLinter to discover quality issues and recommend tools for the project.

## Agent

**quality-enforcer**: Specialized agent for code quality that:

- Discovers existing quality standards
- Sets up prek pre-commit hooks
- Configures GitHub Actions quality gates
- Uses MegaLinter to discover valuable linters
- **Prevents manual file iteration** by recommending automation
- Ensures all issues resolved or explicitly ignored
- Never satisfied until quality standards met

## Skills

### `quality-enforcement`

Automatically invoked when working on code. Runs static analysis, prevents manual iteration, recommends automation tools.

### `tool-discovery`

Automatically invoked when analyzing quality needs. Uses MegaLinter to discover and recommend appropriate tools.

## Hooks

1. **prevent-manual-iteration**: Warns when similar changes planned for multiple files
2. **prek-reminder**: Suggests running quality checks when code is modified

## Quality Standards

### Manual Iteration Prevention

**Before iterating over files, ASK:**

- Is there a Rust-based formatter? (ruff format, biome, dprint, rustfmt)
- Is there a Rust linter with --fix? (ruff check, biome lint)
- Is there a Rust refactoring tool? (Fallback to language-specific tools if needed)

**Intervention pattern:**

1. STOP - Notice iteration plan
2. THINK - What Rust tool can automate this?
3. RECOMMEND - Suggest specific Rust-based tool with config
4. EXECUTE - Set up and run tool once

### Rust Tool Priority Matrix

| Task | First Choice (Rust) | Fallback | Speed Gain |
|------|---------------------|----------|------------|
| Python lint | `ruff check --fix` | pylint, flake8 | 10-100x |
| Python format | `ruff format` | black | 10-100x |
| Python imports | `ruff --select I` | isort | 10-100x |
| JS/TS lint | `biome lint` | eslint | 10-20x |
| JS/TS format | `biome format` | prettier | 10-20x |
| Multi-format | `dprint fmt` | prettier | 20-60x |
| Package install | `uvx` | pipx | 10-100x |
| File search | `fd` | find | 10x+ |
| Content search | `ripgrep` | grep | 10x+ |
| Spell check | `typos-cli` | cspell | 10x+ |

### Issue Resolution

✅ **ACCEPTABLE**:

```python
# pylint: disable=broad-except
# Reason: Third-party API raises various exception types
try:
    external_call()
except Exception as e:
    log(e)
```

❌ **UNACCEPTABLE**:

- Silently ignoring warnings
- Disabling without explanation
- "Fix later" mentality

## prek Setup

**Why prek over pre-commit:**

- 3-10x faster with 50% less disk space
- Single binary, no Python required
- Better toolchain sharing
- Enhanced commands (--directory, --last-commit)
- Monorepo support
- Built-in Rust implementations

**Basic setup:**

```text
# Install
curl -fsSL https://prek.j178.dev/install.sh | sh

# Install hooks
prek install

# Run
prek run --all-files
```

## MegaLinter Discovery

**How to use:**

```text
# Run locally
docker run --rm -v $(pwd):/tmp/lint oxsecurity/megalinter:latest

# Analyze report
# High findings = valuable linter
# Autofix available = prioritize
# Zero findings = may not need
```

## Configuration Templates

The plugin includes templates for:

- `.pre-commit-config.yaml` - prek/pre-commit configuration
- `.mega-linter.yml` - MegaLinter configuration
- `quality-workflow.yml` - GitHub Actions quality workflow

## Workflow

1. **Analyze** repository (languages, existing tools)
2. **Discover** issues with MegaLinter
3. **Setup** prek hooks and GitHub Actions
4. **Run** all quality tools
5. **Check** for automation before manual fixes
6. **Resolve** all issues (fix/suppress/configure)
7. **Verify** all issues addressed
8. **Document** all configuration choices

## Best Practices Compliance

This plugin follows Claude Code best practices:

### Agent

- ✅ Action-oriented description with "MUST BE USED" and "PROACTIVELY"
- ✅ Explicit tools list for security
- ✅ Single responsibility (quality enforcement)
- ✅ Structured workflow

### Skills

- ✅ Specific trigger keywords
- ✅ Focused capabilities
- ✅ Clear invocation triggers

### Hooks

- ✅ Appropriate notification types
- ✅ Secure bash commands
- ✅ Safe path handling

## Attribution & Credits

This plugin was inspired by and built upon the following resources:

### Core Infrastructure

#### prek

- **Source**: <https://github.com/j178/prek>
- **Website**: <https://prek.j178.dev/>
- **Author**: j178
- **License**: MIT
- **Usage**: Core pre-commit hook management, configuration patterns, and best practices for fast, dependency-free quality enforcement

#### MegaLinter

- **Source**: <https://github.com/oxsecurity/megalinter>
- **Website**: <https://megalinter.io/>
- **Organization**: OX Security
- **License**: GNU Affero General Public License v3.0
- **Usage**: Linter discovery, quality analysis patterns, and comprehensive static analysis tool integration

#### pre-commit

- **Source**: <https://github.com/pre-commit/pre-commit>
- **Website**: <https://pre-commit.com/>
- **License**: MIT
- **Usage**: Configuration format compatibility (prek maintains compatibility with pre-commit configs)

### Rust-Based Tools (Recommended)

#### Ruff

- **Source**: <https://github.com/astral-sh/ruff>
- **Website**: <https://astral.sh/ruff>
- **Organization**: Astral Software Inc.
- **License**: MIT
- **Usage**: Python linting and formatting (replaces black, flake8, isort, pyupgrade, autoflake, pydocstyle)

#### uv

- **Source**: <https://github.com/astral-sh/uv>
- **Website**: <https://docs.astral.sh/uv/>
- **Organization**: Astral Software Inc.
- **License**: Apache-2.0 / MIT
- **Usage**: Python package management (replaces pip, pipx, poetry, pyenv, virtualenv)

#### Biome

- **Source**: <https://github.com/biomejs/biome>
- **Website**: <https://biomejs.dev/>
- **Organization**: Biome
- **License**: MIT / Apache-2.0
- **Usage**: JavaScript/TypeScript linting and formatting (replaces eslint + prettier)

#### dprint

- **Source**: <https://github.com/dprint/dprint>
- **Website**: <https://dprint.dev/>
- **Author**: David Sherret
- **License**: MIT
- **Usage**: Multi-language code formatting (replaces prettier for many formats)

#### ripgrep

- **Source**: <https://github.com/BurntSushi/ripgrep>
- **Author**: Andrew Gallant (BurntSushi)
- **License**: MIT / Unlicense
- **Usage**: Fast file content searching (replaces grep)

#### fd

- **Source**: <https://github.com/sharkdp/fd>
- **Author**: David Peter (sharkdp)
- **License**: MIT / Apache-2.0
- **Usage**: Fast file finding (replaces find)

#### typos

- **Source**: <https://github.com/crate-ci/typos>
- **Organization**: crate-ci
- **License**: MIT / Apache-2.0
- **Usage**: Fast spell checking for code

### Documentation

#### Claude Code Documentation

- **Source**: <https://code.claude.com/docs>
- **Usage**: Plugin architecture, best practices, and component design patterns

All configurations and implementations follow the licenses and terms of their respective sources. This plugin's philosophy of preferring Rust-based tools is informed by performance benchmarks and community adoption of these modern alternatives.
