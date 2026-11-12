#!/usr/bin/env bash
# SessionStart, UserPromptSubmit and Stop hook: point at the project's notes (mode in $1).
# Finds a Python and hands over to notes.py. Always exits 0 so nothing is ever blocked.
dir="$(cd "$(dirname "$0")" && pwd)"
for py in python python3 py; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import sys" >/dev/null 2>&1; then
    "$py" "$dir/notes.py" "$@" || true
    exit 0
  fi
done
exit 0
