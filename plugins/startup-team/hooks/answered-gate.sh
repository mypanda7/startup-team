#!/usr/bin/env bash
# PreToolUse/PostToolUse hook: no redundant build or green-light question (see answered-gate.py).
# Finds a Python and hands over to answered-gate.py. Always exits 0; a missing Python lets the call through.
dir="$(cd "$(dirname "$0")" && pwd)"
for py in python python3 py; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import sys" >/dev/null 2>&1; then
    "$py" "$dir/answered-gate.py" || true
    exit 0
  fi
done
exit 0
