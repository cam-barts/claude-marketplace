#!/usr/bin/env bash
# PostToolUse hook: nudge to run /test-run or /test-coverage when a Python file
# is edited. Receives Claude Code hook input as JSON on stdin.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')

[ -z "$file" ] && exit 0

basename=$(basename "$file")
case "$basename" in
  test_*.py|*_test.py)
    echo "NOTICE: Test file modified. Run /test-run to verify all tests still pass."
    ;;
  *.py)
    echo "NOTICE: Source code modified. Consider running /test-coverage to check if coverage dropped and /test-run to ensure tests pass."
    ;;
esac
