#!/usr/bin/env bash
# PostToolUse hook: lint markdown files after Write/Edit with rumdl and vale.
# Receives Claude Code hook input as JSON on stdin.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')

[ -z "$file" ] && exit 0
case "$file" in *.md) ;; *) exit 0 ;; esac
[ -f "$file" ] || exit 0

if command -v rumdl >/dev/null 2>&1; then
  rumdl check "$file" 2>&1 || echo "NOTICE: rumdl found issues. Run /docs-fix to auto-correct."
fi

if command -v vale >/dev/null 2>&1; then
  config="${CLAUDE_PLUGIN_ROOT:-.}/configs/vale.ini"
  if [ -f .vale.ini ] || [ -f "$HOME/.vale.ini" ]; then
    vale "$file" 2>&1 || echo "NOTICE: vale found prose issues. Review suggestions."
  elif [ -f "$config" ]; then
    vale --config="$config" "$file" 2>&1 || echo "NOTICE: vale found prose issues. Review suggestions."
  else
    vale "$file" 2>&1 || echo "NOTICE: vale found prose issues. Review suggestions."
  fi
fi
