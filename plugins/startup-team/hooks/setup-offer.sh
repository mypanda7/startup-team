#!/usr/bin/env bash
# UserPromptSubmit hook: offer to set up the team once per session until it is set up.
# Finds a Python and hands over to setup-offer.py. Always exits 0 so a prompt is never blocked.
dir="$(cd "$(dirname "$0")" && pwd)"
for py in python python3 py; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import sys" >/dev/null 2>&1; then
    "$py" "$dir/setup-offer.py" "$@" || true
    exit 0
  fi
done
exit 0
