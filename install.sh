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

# "Already added" means a marketplace NAMED startup-team, whatever its source; never re-add or replace it.
# Matched over the whole output joined to one line, so JSON layout and key order don't matter.
LIST=""
[ "$DRY" -eq 0 ] && LIST="$(claude plugin marketplace list --json 2>/dev/null | tr '\n\r' '  ')"
if printf '%s\n' "$LIST" | grep -Eq '"name"[[:space:]]*:[[:space:]]*"startup-team"'; then
  if printf '%s\n' "$LIST" | grep -Fq "$MARKETPLACE"; then
    echo "Marketplace startup-team is already added ($MARKETPLACE)."
  else
    echo "Marketplace startup-team is already added from another source; using that source."
  fi
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
echo "Claude, if you ran this: ask the owner that question now, with clickable options if you can (in Claude Code: AskUserQuestion) - \"Set up now\" (= 1) and \"Not now\" (= 0) - else as text ending 1 = yes, 0 = no. On 1, on the owner's turn, follow commands/start-team.md from the installed plugin folder (see claude plugin list); in the terminal CLI, say the sessions need the desktop app."
echo "On 0 (Not now), nothing more: the plugin asks again in the next session."
