#!/usr/bin/env bash
# PreToolUse hook: warn if a markdown file is being written without Diataxis
# documentation_type frontmatter. Receives Claude Code hook input as JSON on stdin.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')

[ -z "$file" ] && exit 0
case "$file" in *.md) ;; *) exit 0 ;; esac
[ -f "$file" ] || exit 0

if ! grep -q "^---" "$file" 2>/dev/null || ! grep -q "documentation_type:" "$file" 2>/dev/null; then
  printf '{"decision":"warn","message":"Markdown file should have frontmatter with documentation_type field (tutorial/how-to/reference/explanation)"}\n'
fi
