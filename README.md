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
- **Lean tooling** - Scripts only where they meaningfully outperform an agent's built-in capabilities (cross-file AST/CST analysis, async I/O, multi-source correlation). Routine grep, edit, and CLI invocations are left to the agent

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
/plugin install silverbullet@cam-marketplace
/plugin install silverbullet-workflow@cam-marketplace
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

**Version:** 0.2.0 (pre-release)

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

**Version:** 0.2.0 (pre-release)

---

### static-analysis

Enforces code quality through prek pre-commit hooks, complexity metrics, and dependency auditing. Actively prevents manual file iteration by recommending automated tools. Never satisfied until all issues are resolved or explicitly suppressed with reasoning.

**Key Features:**

- Manual iteration prevention (recommends formatters, linters, refactoring tools)
- prek pre-commit hooks (faster, lighter alternative to pre-commit)
- Cross-config tool conflict detection (overlapping rules across pyproject, ruff.toml, mypy.ini)
- Quality metrics: cyclomatic complexity, maintainability index, LOC (radon-based)
- Dependency vulnerability auditing across pyproject + lockfiles
- Explicit issue resolution (fix/suppress/configure/remove)
- Autofix prioritization

**Commands:**

- `/quality-check` - Run all quality tools
- `/quality-setup` - Set up prek hooks and quality tooling
- `/quality-fix` - Fix quality issues with automation
- `/quality-discover` - Survey configured linters and detect tool conflicts

**Agent:** `quality-enforcer` - Intervenes when manual iteration detected, recommends automation

**Version:** 0.2.0 (pre-release)

---

### silverbullet

Skill bundle for working with Cam's SilverBullet knowledge base. Encodes paths, the server URL, and Lua function names — highly personal; useful as a reference for similar setups but not turnkey for others.

**Key Features:**

- Decision table for picking between `sb`, `zk`, and direct file edits
- `sb sync` workflow for pushing edits to the server
- Space Lua evaluation and SilverBullet object index queries
- `zk` search, link traversal, tag management, graph analysis

**Skill:** `silverbullet` - Triggers on SilverBullet, wikilinks, backlinks, `sb`/`zk` CLI usage, or references to the user's notes/wiki/knowledge base

**Version:** 0.2.0 (pre-release)

---

### silverbullet-workflow

Action-oriented playbook companion to `silverbullet`. Where the reference plugin says what the tools are, this one says what to do with them — Cam's daily CLI workflows for starting projects, pulling tasks, appending Captain's Log entries, searching the space, and getting set up on a fresh machine. Bundles the correct `done == false` task query (replaces the older `status == "open"` form that silently returned empty), the Project template scaffold rule, and the three Space Lua sharp edges that have cost the most time.

**Key Features:**

- First-time CLI setup detection — checks `sb`/`zk` on PATH, env vars, config, server reachability; surfaces install instructions when missing
- Slash commands for the daily-driver moves: `/sb-setup`, `/sb-tasks`, `/sb-new-project`, `/sb-search`, `/sb-log`, `/sb-garden`
- Encodes Cam's collaboration patterns from memory — templates as starting places, tasks vs bullets, `[assignee:]` convention, report-before-commit
- Reference docs for install, first-time setup, task patterns, project template structure, Space Lua pitfalls (expression-vs-statement, reserved `query` keyword, `net.proxyFetch` userdata)

**Commands:**

- `/sb-setup` - Verify CLI install + config; surface setup steps when anything is missing
- `/sb-tasks` - Pull open tasks for an assignee using the corrected `done == false` query
- `/sb-new-project` - Scaffold a new project doc from `Library/Personal/Templates/Project`
- `/sb-search` - Dispatch a search, picking `zk` or `sb query` based on the kind
- `/sb-log` - Append an entry to today's Captain's Log
- `/sb-garden` - Run a serendipity gardening round over the space

**Skills:** `silverbullet-workflow` - Triggers when the task involves the SB CLI in any of these flavors: starting a new project, pulling or annotating `[assignee:]` tasks, writing Captain's Log entries, searching the space, syncing edits, evaluating Space Lua, fixing aspiring wikilinks, or first-time CLI setup

`serendipity-gardening` - Cam's digital-gardening ritual: deal a wide random hand of notes from the Serendipity page's own pickers (or from the orphans nothing links to), hunt non-obvious connections between them, and propose the exact wikilinks. Writes an ephemeral scratch page per round and never edits content notes — Cam does the linking

**Version:** 0.3.1 (pre-release)

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
- **"Discover, then enforce"** - Survey existing linter config before adding new tooling
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
- ✅ **Scripts**: Trimmed to those that add value beyond what an agent does natively — AST/CST analysis, async I/O with caching, multi-source correlation. No CLI wrappers, no template generators, no regex passes the agent can do inline

## Development

This marketplace is versioned at 0.2.0 (pre-release) until pushed to GitHub. All plugins share this version number.

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
