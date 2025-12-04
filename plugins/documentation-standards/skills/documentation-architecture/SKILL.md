---
name: documentation-architecture
description: |
  Analyzes and maintains documentation structure using the Diataxis framework.
  Use when creating new documentation sections, reorganizing docs, setting up
  zensical/sphinx, or planning documentation for new projects.
documentation_type: reference
---

This skill is automatically invoked when Claude works on documentation structure.

When this skill is active, Claude will:

- Analyze existing documentation against Diataxis quadrants
- Identify gaps in documentation coverage (missing types)
- Report distribution of documentation types
- Suggest information architecture improvements
- Generate zensical.yml navigation structure
- Create documentation roadmaps based on project needs

Claude should invoke this skill whenever:

- Creating new documentation sections
- Reorganizing existing documentation
- Setting up zensical or sphinx configuration
- Planning documentation for new projects
- User asks about documentation structure

## Available Scripts

This skill can invoke the following scripts:

- `uv run plugins/documentation-standards/scripts/analyze_doc_structure.py` - Analyze documentation structure

Run with `--help` for full options.

## Script Usage Examples

```bash
# Analyze documentation structure
uv run scripts/analyze_doc_structure.py docs/

# Generate suggestions for improvements
uv run scripts/analyze_doc_structure.py docs/ --suggest

# Generate a documentation roadmap
uv run scripts/analyze_doc_structure.py docs/ --roadmap

# Output as JSON for processing
uv run scripts/analyze_doc_structure.py docs/ --output json

# Generate zensical navigation
uv run scripts/analyze_doc_structure.py docs/ --generate-nav
```

## Diataxis Framework

The script analyzes documentation using the four Diataxis types:

### Tutorials (Learning-oriented)

- **Purpose**: Learning a skill through doing
- **Form**: Lessons that take the reader through steps
- **Audience**: Newcomers, beginners
- **Keywords**: tutorial, getting started, learn, walkthrough, step by step

### How-To Guides (Task-oriented)

- **Purpose**: Solving a specific problem
- **Form**: Directions to achieve a goal
- **Audience**: Users with specific needs
- **Keywords**: how to, guide, configure, set up, install, deploy

### Reference (Information-oriented)

- **Purpose**: Providing technical description
- **Form**: Dry, accurate, complete information
- **Audience**: Users who need to look up details
- **Keywords**: reference, api, specification, configuration options

### Explanation (Understanding-oriented)

- **Purpose**: Explaining concepts and context
- **Form**: Discursive explanations
- **Audience**: Users wanting deeper understanding
- **Keywords**: explanation, architecture, design, concepts, about, why

## Ideal Distribution

For most projects, aim for:

```text
Tutorials:    15-25%  (at least 1-2 comprehensive tutorials)
How-To:       30-40%  (most user-facing documentation)
Reference:    20-30%  (complete API/config coverage)
Explanation:  15-25%  (architecture, design decisions)
```

## Report Structure

The script generates reports with:

```text
DOCUMENTATION ANALYSIS
======================

Files Analyzed: 24
Total Words: 45,230

DISTRIBUTION BY TYPE
====================
Type          Files    %     Words
─────────────────────────────────
Tutorial      2       8%    5,400
How-To        12     50%    22,000
Reference     7      29%    15,000
Explanation   3      13%    2,830

GAPS IDENTIFIED
===============
⚠ Low tutorial coverage (8%) - Recommended: 15-25%
  → Consider adding: Getting Started guide, First project walkthrough

⚠ Missing explanation for core concepts
  → Consider adding: Architecture overview, Design decisions

DOCUMENTATION HEALTH
====================
✓ Good how-to coverage
✓ Reference documentation complete
⚠ Needs more tutorials for onboarding
⚠ Missing changelog

SUGGESTED ROADMAP
=================
Priority 1: Add "Getting Started" tutorial
Priority 2: Write architecture explanation
Priority 3: Add troubleshooting how-to guide
```

## zensical.yml Generation

With `--generate-nav`, creates:

```yaml
nav:
  - Home: index.md
  - Tutorials:
    - Getting Started: tutorials/getting-started.md
    - Your First Project: tutorials/first-project.md
  - How-To Guides:
    - Installation: how-to/installation.md
    - Configuration: how-to/configuration.md
    - Deployment: how-to/deployment.md
  - Reference:
    - API: reference/api.md
    - Configuration Options: reference/config.md
    - CLI: reference/cli.md
  - Explanation:
    - Architecture: explanation/architecture.md
    - Design Decisions: explanation/design.md
```
