---
name: documentation-migration
description: |
  Assists with documentation migrations and format conversions.
  Use when converting between formats (rst to md), migrating platforms,
  upgrading documentation tooling, or consolidating scattered documentation.
documentation_type: reference
---

This skill is automatically invoked when Claude works on documentation migration.

When this skill is active, Claude will:

- Convert between documentation formats (rst, md, adoc)
- Migrate from wiki to docs-as-code
- Consolidate scattered READMEs into unified documentation
- Preserve links and create redirects during migration
- Validate migration completeness
- Add required frontmatter during conversion

Claude should invoke this skill whenever:

- Converting between documentation formats
- Migrating from one documentation platform to another
- Upgrading documentation tooling (sphinx to zensical, etc.)
- Consolidating scattered documentation
- User asks about documentation migration

## Format Conversion Guidelines

### reStructuredText to Markdown

| RST | Markdown |
|-----|----------|
| `*italic*` | `*italic*` |
| `**bold**` | `**bold**` |

| `` ``code`` `` | `` `code` `` |
| `.. code-block:: python` | ` ```python ` |
| `.. note::` | `> **Note:**` |
| `.. warning::` | `> **Warning:**` |
| `:ref:`label`` | `[text](#anchor)` |
| `:doc:`path`` | `[text](path.md)` |
| `.. toctree::` | Navigation in zensical.yml |

### Common RST Directives

```rst
.. note::
   This is a note.

.. warning::
   This is a warning.

.. code-block:: python

   def example():
       pass

.. literalinclude:: ../src/example.py
   :language: python
   :lines: 1-10
```

Converts to:

````markdown
> **Note:** This is a note.

> **Warning:** This is a warning.

```python
def example():
    pass
```

```python
# See src/example.py lines 1-10
```
````

### Sphinx to Zensical

| Sphinx | Zensical |
|--------|----------|
| `conf.py` | `zensical.yml` |
| `index.rst` | `index.md` |
| `.. toctree::` | `nav:` in zensical.yml |
| `:ref:` | Markdown links |
| `.. automodule::` | docstrings plugins |
| Sphinx extensions | Zensical plugins |

## Migration Checklist

### Before Migration

1. **Inventory existing docs**
    - List all documentation files
    - Map internal links between docs
    - Identify external references
    - Note any custom extensions/plugins

2. **Plan URL structure**
    - Define new URL scheme
    - Create redirect mapping
    - Preserve SEO-important URLs

3. **Backup everything**
    - Version control current state
    - Document current build process

### During Migration

1. **Convert format**
    - Use automated tools where possible
    - Manual review of complex sections
    - Preserve all content

2. **Fix links**
    - Update internal links to new paths
    - Verify external links still work
    - Add anchors for deep links

3. **Add metadata**
    - Add frontmatter with documentation_type
    - Add titles and descriptions
    - Update navigation

### After Migration

1. **Validate**
    - Build documentation
    - Check all links
    - Review rendered output
    - Test search functionality

2. **Set up redirects**
    - Configure redirects for old URLs
    - Test redirect chains

3. **Update references**
    - Update links in README
    - Update CI/CD pipelines
    - Notify team of new URLs

## Consolidation Strategy

When consolidating scattered documentation:

### 1. Inventory Phase

```text
project/
├── README.md                 # Project overview
├── docs/
│   └── api.md               # API docs
├── src/
│   ├── module1/
│   │   └── README.md        # Module1 docs
│   └── module2/
│       └── README.md        # Module2 docs
└── CONTRIBUTING.md          # Contributor guide
```

### 2. Consolidation Plan

```text
docs/
├── index.md                 # From README.md
├── getting-started/
│   └── installation.md      # New
├── reference/
│   ├── api.md              # From docs/api.md
│   ├── module1.md          # From src/module1/README.md
│   └── module2.md          # From src/module2/README.md
├── contributing.md          # From CONTRIBUTING.md
└── zensical.yml
```

### 3. Redirect Map

```yaml
# redirects.yml
redirects:
  - from: /README.md
    to: /
  - from: /src/module1/README.md
    to: /reference/module1/
```

## Tools and Commands

### Pandoc (Universal Converter)

```bash
# RST to Markdown
pandoc input.rst -f rst -t markdown -o output.md

# Markdown to RST
pandoc input.md -f markdown -t rst -o output.rst

# With GitHub-flavored markdown
pandoc input.rst -f rst -t gfm -o output.md
```

### rst2md (Python)

```bash
# Install
uv add rst-to-myst

# Convert
rst2myst convert docs/**/*.rst
```

### Sphinx to Zensical

```bash
# Using pandoc for conversion
# Zensical uses similar markdown format, so convert rst to md first
pandoc input.rst -f rst -t gfm -o output.md
```

## Validation After Migration

Run these checks after migration:

1. **Link validation**

   ```bash
   uv run scripts/validate_links.py docs/
   ```

2. **Frontmatter check**

   ```bash
   uv run scripts/validate_markdown.py docs/
   ```

3. **Build test**

   ```bash
   zensical build --strict
   ```

4. **Structure analysis**

   ```bash
   uv run scripts/analyze_doc_structure.py docs/ --suggest
   ```
