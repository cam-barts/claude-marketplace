---
documentation_type: explanation
---

# Documentation Standards Plugin

Enforces comprehensive documentation standards using rumdl, vale, and Diataxis documentation types.

## Features

### Documentation Quality & Validation

- **Diataxis MCP Server**: Access to the official Diataxis framework via gitmcp.io
    - Quality standards and best practices for each documentation type
    - Intelligent validation beyond just checking frontmatter
    - Context-aware feedback: "This tutorial needs hands-on practice" vs generic errors
    - Reference 32 files including quality.rst, type-specific guidelines, and theory
- **Markdown Linting**: Validates all markdown files using rumdl (high-performance Rust linter)
- **Prose Quality**: Checks writing quality using vale (RedHat, write-good, alex, Readability styles)
- **Diataxis Compliance**: Ensures all documentation has proper `documentation_type` frontmatter
- **Zensical Compatible**: Ensures documentation works with zensical
- **Auto-fixing**: Automatically corrects issues where possible
- **Zero-Error Enforcement**: Agent won't stop until all issues are resolved

### Proactive Documentation Recommendations

- **Code Change Monitoring**: Automatic notifications when code files are modified
- **Smart Recommendations**: Analyzes code changes and suggests specific documentation actions
    - New functions/classes → Reference documentation
    - API changes → Update how-to guides
    - Bug fixes → Update troubleshooting docs
    - Deprecated code → Remove or update related docs
- **Gap Detection**: Identifies missing documentation for new features
- **Outdated Doc Detection**: Finds documentation referencing changed/removed code
- **Proactive Skill**: Claude automatically considers documentation needs when writing code

### Attribution Enforcement

- **Automatic Attribution Checking**: Identifies when external sources should be credited
- **Required Elements**: Source URL, author, license, and usage description
- **Format Enforcement**: Consistent "Attribution & Credits" sections
- **Best Practices**: Be generous with credit, be specific about usage, respect licenses
- **Zero Tolerance**: Documentation not complete until proper attribution provided

## Installation

Add to your marketplace and install:

```bash
/plugin install documentation-standards@cam-marketplace
```

## Commands

### `/docs-check`

Check all documentation for standards compliance without making changes. Uses rumdl for formatting and vale for prose quality.

### `/docs-fix`

Automatically fix documentation issues where possible. Uses `rumdl check --fix` for auto-correction.

### `/docs-recommend`

Analyze code changes and recommend documentation updates. Detects new functions, API changes, deprecated code, and suggests specific documentation actions (add/update/remove) with appropriate documentation types.

### `/docs-attribution`

Check and add proper attribution for external sources. Ensures all borrowed content, inspirations, and external resources are properly credited with source, author, license, and usage information.

### `/docs-validate`

Comprehensive validation with zero-error enforcement. Invokes the docs-enforcer agent with full rumdl, vale validation, and attribution checking.

## Agent

**docs-enforcer**: Specialized agent for documentation work that:

- Uses Diataxis MCP server for quality validation and intelligent feedback
- Validates all markdown files
- Ensures proper frontmatter with `documentation_type`
- Validates content actually matches its declared type (tutorials teach, how-tos solve problems, etc.)
- Verifies all code blocks have language identifiers
- Checks link structure and header hierarchy
- Runs rumdl and vale
- Fixes issues automatically
- Never satisfied until all errors are resolved

## Skills

### `documentation-work`

Automatically invoked when Claude works on documentation tasks. Ensures validation, quality checking, and standards compliance.

### `documentation-recommendations`

Automatically invoked when Claude makes code changes. Proactively suggests documentation updates, identifies gaps, and ensures documentation stays in sync with the codebase.

## Diataxis Documentation Types

All markdown files must include a `documentation_type` frontmatter field with one of:

- `tutorial` - Learning-oriented lessons that take the reader by the hand (hands-on, practical, for beginners)
- `how-to` - Goal-oriented directions that guide through a specific task (problem-solving, for experienced users)
- `reference` - Information-oriented technical descriptions of the system (accurate, complete, comprehensive)
- `explanation` - Understanding-oriented discussions that clarify topics (clarifying, contextual, theoretical)

Example:

```markdown
---
documentation_type: how-to
---

# How to Configure the Plugin

...
```

### Quality Validation

The plugin uses the **Diataxis MCP server** (via gitmcp.io) to access the official framework and validate:

- Does a tutorial actually teach through hands-on practice?
- Does a how-to guide solve a specific problem for experienced users?
- Is a reference comprehensive and technically accurate?
- Does an explanation provide understanding and context?

This goes beyond just checking that the frontmatter field exists—it validates content quality against Diataxis principles.

## Configuration

The plugin includes default configurations for:

- **rumdl**: ATX headings, 120 char lines, 4-space indent, fenced code blocks (configured via `pyproject.toml`)
- **vale**: RedHat, write-good, alex, Readability, Openly styles

Projects can override these by including their own `pyproject.toml` with `[tool.rumdl]` section or `.vale.ini` files.

## Hooks

The plugin automatically validates and monitors:

### Documentation Validation

1. **Pre-write**: Checks for documentation_type frontmatter
2. **Post-write**: Runs rumdl on saved files
3. **Post-write**: Runs vale for prose quality

### Code Change Monitoring

1. **Post-write/edit**: Reminds about documentation when code files are modified
2. **Post-write**: Detects new functions/classes and suggests reference documentation
3. **Post-write/edit**: Warns about documentation updates when API files change

## Requirements

For full functionality, install:

```bash
# Core tools
uv tool install rumdl  # or: pip install rumdl, brew install rumdl
uv tool install vale   # or download from https://vale.sh
```

The hooks gracefully skip checks if tools aren't installed.

## MCP Servers

The plugin includes an MCP server that is automatically configured:

### diataxis (Quality Validation)

- **URL**: <https://gitmcp.io/evildmp/diataxis-documentation-framework>
- **Via**: gitmcp.io remote MCP server
- **Content**: Official Diataxis framework (32 files)
- **Purpose**: Access quality standards, guidelines, and best practices
- **Files**: quality.rst, tutorials.rst, how-to-guides.rst, reference.rst, explanation.rst, and more
- **Requirement**: None - remote server, no installation needed

This server is configured in `.mcp.json` and activates automatically when the plugin is enabled.

## Best Practices Compliance

This plugin follows all [Claude Code best practices](https://code.claude.com/docs):

### Agent

- ✅ Action-oriented description with "MUST BE USED" and "PROACTIVELY" keywords
- ✅ Explicit `tools` list for security and focus (only necessary tools)
- ✅ Single responsibility principle (documentation enforcement)
- ✅ Structured instructions with step-by-step workflow
- ✅ Clear evaluation criteria and checklists

### Skills

- ✅ Specific, discoverable descriptions with trigger keywords
- ✅ Focused capabilities (one skill per capability)
- ✅ Clear invocation triggers for automatic use
- ✅ Distinct trigger terms to avoid conflicts

### Hooks

- ✅ Appropriate hook types (validation vs notification)
- ✅ Secure bash commands with quoted variables
- ✅ Input validation and safe path handling
- ✅ Command existence checks before execution
- ✅ Proper error handling with exit codes

### Plugin Structure

- ✅ Correct directory organization
- ✅ Semantic versioning
- ✅ Comprehensive documentation
- ✅ Team collaboration ready

## Attribution & Credits

This plugin was inspired by and built upon the following resources:

### Diataxis Documentation Framework

- **Source**: <https://github.com/evildmp/diataxis-documentation-framework>
- **Author**: Daniele Procida
- **License**: CC-BY-SA 4.0
- **Usage**: Official Diataxis framework accessed via gitmcp.io for quality standards, guidelines, and documentation type validation

### gitmcp.io

- **Website**: <https://gitmcp.io>
- **Usage**: Remote MCP server infrastructure for accessing the Diataxis framework

### Vale

- **Source**: <https://github.com/errata-ai/vale>
- **Website**: <https://vale.sh>
- **Usage**: Default vale.ini configuration adapted from user's personal configuration at `~/.config/vale/vale.ini`

### rumdl

- **Source**: <https://github.com/rvben/rumdl>
- **Author**: rvben
- **License**: MIT
- **Usage**: High-performance Rust markdown linter with pyproject.toml configuration

### Claude Code Documentation

- **Source**: <https://code.claude.com/docs>
- **Usage**: Plugin architecture, best practices, and component design patterns

All configurations and implementations follow the licenses and terms of their respective sources.
