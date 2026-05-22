#!/usr/bin/env bash
# PostToolUse hook: nudge to run /docs-recommend when a code file is edited.
# Receives Claude Code hook input as JSON on stdin.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')

[ -z "$file" ] && exit 0
case "$file" in
  *.js|*.ts|*.jsx|*.tsx|*.py|*.java|*.go|*.rs|*.rb|*.php|*.c|*.cpp|*.h|*.hpp)
    echo "NOTICE: Code file modified. Consider running /docs-recommend to check if documentation needs updating."
    ;;
esac
