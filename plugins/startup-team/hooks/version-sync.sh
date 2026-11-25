#!/usr/bin/env bash
# UserPromptSubmit hook: align a running session with the installed startup-team version.
# Finds a Python and hands over to version-sync.py. Always exits 0 so a prompt is never blocked.
dir="$(cd "$(dirname "$0")" && pwd)"
for py in python python3 py; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import sys" >/dev/null 2>&1; then
    "$py" "$dir/version-sync.py" || true
    exit 0
  fi
done
exit 0
