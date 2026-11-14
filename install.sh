#!/usr/bin/env sh
# Install startup-team into the current project folder, then ask the setup question.
# Runs only two commands: `claude plugin marketplace add` (skipped when already added) and
# `claude plugin install startup-team@startup-team --scope local`. Writes nothing else.
# Usage, from the project folder: sh install.sh [--dry-run]
set -u

MARKETPLACE="mypanda7/startup-team"
PLUGIN="startup-team@startup-team"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

run() {
  if [ "$DRY" -eq 1 ]; then
    echo "[dry-run] $*"
    return 0
  fi
  "$@"
}

if [ "$DRY" -eq 0 ] && ! command -v claude >/dev/null 2>&1; then
  echo "install failed: the claude command was not found. Install Claude Code first." >&2
  exit 1
fi

if [ "$DRY" -eq 0 ] && claude plugin marketplace list 2>/dev/null | grep -q "$MARKETPLACE"; then
  echo "Marketplace $MARKETPLACE is already added."
else
  run claude plugin marketplace add "$MARKETPLACE" || {
    echo "install failed: could not add the marketplace $MARKETPLACE." >&2
    exit 1
  }
fi

run claude plugin install "$PLUGIN" --scope local || {
  echo "install failed: could not install $PLUGIN in this folder." >&2
  exit 1
}

echo "startup-team installed successfully."
echo "Create the AI Tech Lead session and its six sub sessions (Business Analyst, Designer, Developer, QA Engineer, DevOps, Security) and turn on the companion plugins? 1 = yes, 0 = no."
echo "Claude, if you ran this: ask the owner that question now. On 1, on the owner's turn, follow commands/start-team.md from the installed plugin folder (see claude plugin list); in the terminal CLI, say the sessions need the desktop app."
echo "On 0, nothing more: the plugin asks again in the next session."
