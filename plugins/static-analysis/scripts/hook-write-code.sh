#!/usr/bin/env bash
# PostToolUse hook: nudge to run /quality-check when a code file is edited.
# Receives Claude Code hook input as JSON on stdin.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')

[ -z "$file" ] && exit 0
case "$file" in
  *.py|*.js|*.ts|*.jsx|*.tsx|*.java|*.go|*.rs|*.rb|*.php|*.c|*.cpp|*.h|*.hpp)
    echo "NOTICE: Code modified. Run /quality-check to ensure quality standards are met before committing."
    ;;
esac
