---
description: Install or update the optional companion plugins the team's agents borrow skills from
---
Install or update the team's companion plugins. Setup (`/startup-team:start-team`) already installs
every companion and leaves it on; this command adds or updates them later, by my choice. Companions
are on by default (owner); the activator never switches one off. I turn one off myself with
`claude plugin disable <name>@<marketplace> --scope local` (its files stay in the plugin cache and
agents read them from there by path) and back on with `claude plugin enable ...`. They are listed in this plugin's marketplace
(`startup-team`), each linked to its author's original repository, and described in `ROSTER.md`
beside the `team-workflow` skill. `$ARGUMENTS` may be `status`, `update`, or a list of plugin names
(`agent-skills`, `antislop`, `taste-skill`, `ui-ux-pro-max`, `frontend-design`, `design`,
`humanizer`, `ponytail`).

1. Run `claude plugin list` and say, for each companion, whether it is installed, from which
   marketplace, at which version and scope, and whether it is enabled. With `status`, stop here.
2. With no argument, ask me which ones to install, one question, the not-yet-installed ones as
   options. With names, use those. A companion I already have from its author's own marketplace
   counts as installed: leave it as it is.
3. Install each chosen one with `claude plugin install <name>@startup-team --scope local`, unless I
   name another scope, and leave it enabled (companions are on by default, owner); an already-enabled copy from any marketplace is left as it is and reported. With `update`, first run `claude plugin marketplace update startup-team`,
   then `claude plugin update <name>@<the marketplace it was installed from> --scope <its scope>`
   for each installed companion, and tell me each version before and after.
4. A companion may bring its own hooks, settings or setup questions. Apply none of them without my
   1, and remind me that the team's rules win over every companion (`ROSTER.md`, "Precedence").
5. After an update, check that the skills and agents `ROSTER.md` names for that companion still
   exist in it, and list any that do not.

Install nothing I did not choose. Never use `npx`, an install script or a manual copy for these.
