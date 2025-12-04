---
name: quality-ci-integration
description: |
  Sets up and maintains CI/CD quality pipelines for GitHub Actions.
  Use when setting up CI, configuring quality gates, optimizing pipelines,
  or troubleshooting CI failures. Generates appropriate workflows based
  on repository tooling.
documentation_type: reference
---

This skill is automatically invoked when Claude works on CI/CD configuration.

When this skill is active, Claude will:

- Analyze repository to detect installed quality tools
- Generate GitHub Actions workflows with appropriate jobs
- Configure quality gates that block merge on failures
- Set up caching for fast CI runs
- Include prek/pre-commit hook execution
- Add MegaLinter for comprehensive analysis
- Configure PR status checks

Claude should invoke this skill whenever:

- Setting up GitHub Actions for a project
- Adding quality checks to CI pipeline
- Optimizing slow CI builds
- Troubleshooting CI failures
- User asks about CI configuration

## Available Scripts

This skill can invoke the following scripts:

- `uv run plugins/static-analysis/scripts/generate_ci_workflow.py` - Generate CI workflows

Run with `--help` for full options.

## Script Usage Examples

```bash
# Analyze repo and generate workflow
uv run scripts/generate_ci_workflow.py .

# Generate for specific CI platform
uv run scripts/generate_ci_workflow.py . --platform github

# Include Python version matrix
uv run scripts/generate_ci_workflow.py . --matrix 3.11,3.12,3.13

# Generate with caching enabled
uv run scripts/generate_ci_workflow.py . --cache

# Preview without creating files
uv run scripts/generate_ci_workflow.py . --dry-run

# Output to specific location
uv run scripts/generate_ci_workflow.py . --output .github/workflows/quality.yml
```

## Generated Workflow Structure

The script generates a workflow with these jobs based on detected tools:

### prek/pre-commit Job

```yaml
prek:
  name: Pre-commit Hooks
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run prek
      uses: j178/prek-action@v1
```

### Python Quality Job (if Python detected)

```yaml
python-quality:
  name: Python Quality
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - name: Install uv
      uses: astral-sh/setup-uv@v4
    - name: Run ruff
      run: uvx ruff check .
    - name: Run ruff format check
      run: uvx ruff format --check .
```

### Test Job (if pytest detected)

```yaml
test:
  name: Tests
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
    - name: Install dependencies
      run: uv sync
    - name: Run tests
      run: uv run pytest --cov
```

### MegaLinter Job

```yaml
megalinter:
  name: MegaLinter
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    - name: MegaLinter
      uses: oxsecurity/megalinter@v7
```

## Tool Detection

The script detects these tools in your repository:

| File | Tool Detected | CI Job Added |
|------|---------------|--------------|
| `pyproject.toml` | Python project | python-quality |
| `ruff.toml` / `[tool.ruff]` | Ruff | ruff check/format |
| `pytest.ini` / `[tool.pytest]` | Pytest | test job |
| `.pre-commit-config.yaml` | pre-commit | prek job |
| `prek.yaml` | prek | prek job |
| `package.json` | Node.js | node-quality |
| `biome.json` | Biome | biome check |
| `.mega-linter.yml` | MegaLinter | megalinter job |

## Caching Configuration

With `--cache`, the script adds:

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/uv
      ~/.cache/pip
      .venv
    key: ${{ runner.os }}-python-${{ hashFiles('**/pyproject.toml') }}
```

## Quality Gates

The generated workflow can serve as a required status check:

1. Go to repo Settings > Branches
2. Add branch protection rule for `main`
3. Enable "Require status checks to pass"
4. Select the quality jobs as required
