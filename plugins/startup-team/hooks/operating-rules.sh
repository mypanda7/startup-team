#!/usr/bin/env bash
# UserPromptSubmit hook: re-surface the project's own operating rules.
# Finds a Python and hands over to operating-rules.py. Always exits 0 so nothing is ever blocked.
dir="$(cd "$(dirname "$0")" && pwd)"
for py in python python3 py; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import sys" >/dev/null 2>&1; then
    "$py" "$dir/operating-rules.py" "$@" || true
    exit 0
  fi
done
exit 0
