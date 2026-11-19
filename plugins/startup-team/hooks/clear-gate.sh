#!/usr/bin/env bash
# PreToolUse/PostToolUse hook: a task message to a team session only after a clear (see clear-gate.py).
# Finds a Python and hands over to clear-gate.py. Always exits 0; a missing Python lets the call through.
dir="$(cd "$(dirname "$0")" && pwd)"
for py in python python3 py; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import sys" >/dev/null 2>&1; then
    "$py" "$dir/clear-gate.py" || true
    exit 0
  fi
done
exit 0
