# Cam's Claude Code Marketplace

Personal collection of opinionated, quality-enforcing plugins for Claude Code.
These plugins are designed to maintain high standards and never accept "good enough" - they enforce best practices until all issues are resolved.

## Philosophy

These plugins share a common philosophy:

- **Zero tolerance for unresolved issues** - No warnings, no unaddressed problems
- **Explicit over implicit** - All suppressions and ignores must be documented
- **Automation over manual work** - Use tools to fix issues, never iterate manually
- **Proactive enforcement** - Catch issues early, fail fast, fix faster
- **Best practices by default** - Opinionated standards based on industry leaders

## Installation

Install this marketplace in Claude Code:

```bash
/plugin install cam-marketplace@github:cam-barts/claude-marketplace
```

Or install individual plugins:

```text
/plugin install documentation-standards@cam-marketplace
/plugin install pytest-standards@cam-marketplace
/plugin install static-analysis@cam-marketplace
```

## Plugins

### documentation-standards

Enforces documentation quality using rumdl, vale, and Diataxis documentation framework. Proactively recommends documentation when code changes occur.

**Key Features:**

- Zero-error documentation enforcement
- Diataxis documentation type frontmatter (tutorial/how-to/reference/explanation)
- Vale prose linting
- rumdl for consistent formatting
- Proactive documentation recommendations
- Attribution enforcement for external sources

**Commands:**

- `/docs-check` - Validate all documentation
- `/docs-fix` - Auto-fix documentation issues
- `/docs-validate` - Verify Diataxis frontmatter
- `/docs-recommend` - Get documentation recommendations
- `/docs-attribution` - Check and add attribution

**Agent:** `docs-enforcer` - Never satisfied until all documentation is error-free

**Version:** 0.1.0 (pre-release)

---

### pytest-standards

Enforces opinionated pytest testing standards based on Thea Flowers' testing philosophy and Real Python best practices. Promotes property-based testing with Hypothesis and never accepts failing tests or reduced coverage.

**Key Features:**

- Zero-failure test enforcement
- Opinionated pytest best practices (assert results, prefer real objects, clear naming)
- Property-based testing with Hypothesis
- Coverage maintenance and improvement
- Test-driven development workflow
- Proactive test suggestions for new code

**Commands:**

- `/test-run` - Run all tests with coverage
- `/test-fix` - Fix failing tests
- `/test-review` - Review test quality
- `/test-coverage` - Analyze coverage
- `/test-hypothesis` - Add property-based tests

**Agent:** `test-enforcer` - Never satisfied until all tests pass and coverage is maintained

**Version:** 0.1.0 (pre-release)

---

### static-analysis

Enforces code quality through prek pre-commit hooks and MegaLinter. Actively prevents manual file iteration by recommending automated tools. Never satisfied until all issues are resolved or explicitly suppressed with reasoning.

**Key Features:**

- Manual iteration prevention (recommends formatters, linters, refactoring tools)
- prek pre-commit hooks (faster, lighter alternative to pre-commit)
- MegaLinter integration for tool discovery
- GitHub Actions quality gates
- Explicit issue resolution (fix/suppress/configure/remove)
- Autofix prioritization

**Commands:**

- `/quality-check` - Run all quality tools
- `/quality-setup` - Set up prek and MegaLinter
- `/quality-fix` - Fix quality issues with automation
- `/quality-discover` - Discover quality issues with MegaLinter

**Agent:** `quality-enforcer` - Intervenes when manual iteration detected, recommends automation

**Version:** 0.1.0 (pre-release)

## Plugin Philosophy Details

### documentation-standards

- **"Error-free or nothing"** - No documentation warnings tolerated
- **"Type everything"** - All docs must declare Diataxis type
- **"Explain suppressions"** - Any disabled rules must have documented reasoning
- **"Attribute everything"** - External sources must be properly credited

### pytest-standards

- **"Assert outcomes, not steps"** - Test the result, not the implementation
- **"Real over mocked"** - Prefer real objects and integrations
- **"Property-based by default"** - Use Hypothesis for robust testing
- **"Coverage never decreases"** - Maintain or improve, never regress

### static-analysis

- **"Automate everything"** - Never manually iterate when a tool exists
- **"Discover, then enforce"** - Use MegaLinter to find valuable linters
- **"Fail fast, fix faster"** - Catch issues in pre-commit and CI/CD
- **"Explicit over implicit"** - All ignored issues need documented reasoning

## Best Practices Compliance

All plugins in this marketplace follow Claude Code best practices:

- ✅ **Agents**: Action-oriented descriptions with "MUST BE USED" and "PROACTIVELY"
- ✅ **Agents**: Explicit tools lists for security
- ✅ **Agents**: Single responsibility focus
- ✅ **Skills**: Specific trigger keywords with name field
- ✅ **Hooks**: Appropriate notification types, secure bash commands
- ✅ **Commands**: Clear descriptions with usage examples
- ✅ **Documentation**: Comprehensive READMEs with attribution sections

## Development

This marketplace is versioned at 0.1.0 (pre-release) until pushed to GitHub. All plugins share this version number.

### Project Structure

```text
cam_claude_marketplace/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   ├── documentation-standards/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── .mcp.json
│   │   ├── agents/
│   │   ├── commands/
│   │   ├── skills/
│   │   ├── hooks/
│   │   ├── configs/
│   │   └── README.md
│   ├── pytest-standards/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── agents/
│   │   ├── commands/
│   │   ├── skills/
│   │   ├── hooks/
│   │   ├── configs/
│   │   └── README.md
│   └── static-analysis/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── agents/
│       ├── commands/
│       ├── skills/
│       ├── hooks/
│       ├── configs/
│       └── README.md
├── README.md
└── TODO.md
```

## Attribution

This marketplace and its plugins were inspired by and built upon numerous open-source projects and resources:

### Core Inspirations

- **Claude Code**: Plugin architecture and best practices - <https://code.claude.com/docs>
- **Anthropic**: Claude AI platform

### Plugin-Specific Credits

See individual plugin READMEs for detailed attribution:

- `plugins/documentation-standards/README.md` - Diataxis, Vale, rumdl credits
- `plugins/pytest-standards/README.md` - Thea Flowers, Real Python, Hypothesis, pytest credits
- `plugins/static-analysis/README.md` - prek, MegaLinter, pre-commit credits

## License

This marketplace and all plugins are provided as-is for personal and educational use. Individual components may be subject to their respective licenses as documented in attribution sections.

## Contributing

This is a personal marketplace. Feel free to fork and adapt for your own use.

## Support

For issues or questions:

- Create an issue in the GitHub repository
- Consult individual plugin READMEs for specific documentation
- Review Claude Code documentation at <https://code.claude.com/docs>
