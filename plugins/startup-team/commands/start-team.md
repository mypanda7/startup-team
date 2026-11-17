---
description: Start the AI Tech Lead session (and AI Team Optimization where the project names a team repo clone); run inside it, finish the setup; sub sessions start when a task first needs them (or name them, or `all`)
---
Set up the team's standing sessions: the AI Tech Lead, a session of its own, and its sub sessions
(Business Analyst, Designer, Developer, QA Engineer, DevOps, Security), which sit under it in the
sidebar. Sub sessions start on demand: with no argument, case B starts none, and each one starts the
first time a task needs it (`team-workflow` skill, "Sessions"). `$ARGUMENTS` may name sub sessions
to start now (`business-analyst`, `designer`, `developer`, `qa`, `devops`, `security`), or `all`
for all six. The argument
`gateway`, run in the Tech Lead, runs only step 12 and asks its question again.
Where the project's CLAUDE.md names `TEAM REPO CLONE: <path>`, case A also starts "AI Team
Optimization", a second session of its own beside the AI Tech Lead (never under it), where the
owner improves the team itself.
Team lines the project's CLAUDE.md may hold, each the owner's standing yes (`team-workflow` skill):
`TEAM REPO CLONE: <path>`, `Setup changes: automatic, straight to main`, `Remote Control clears:
allowed`, `Setup repair: allowed` ("Setup repair") and `Sub sessions: bypass` (step 13).

The desktop app nests a session under the session that started it, and allows `start_session`
only on a turn the owner typed. So setup takes two runs of this command: run in any other
session, it starts only the AI Tech Lead (case A); run in the AI Tech Lead on a turn the owner
typed there, it finishes the setup and starts the named sub sessions under it (case B). Follow these steps in order.

1. If you have no `start_session` tool (the terminal CLI), say in one line that standing sessions
   need the desktop app and that the team keeps using its sub-agents. Stop.
2. Call `get_session` with `self` for this session's id and title, then `list_sessions` once (all
   sessions, not only linked ones). Read `<project folder>/.handoff/team-sessions.json` if it
   exists (the registry, below).
3. A role has a session when:
   - Registry first: the registry names a session id for the role, and `list_sessions` shows a
     non-archived session with that id whose `cwd` is the project's folder (compared ignoring case,
     slash direction and a trailing slash; a worktree or subfolder does not count). That is the
     role's session whatever its title is now, so a renamed session is still found.
   - Otherwise, by title: a non-archived session whose `cwd` is the project's folder (as above) and
     whose title IS the role's title, ignoring case and spaces ("Designer", "QA Engineer", ...);
     for the Tech Lead, a title that ends with "Tech Lead", so "AI Tech Lead" matches. A title
     that only contains the word does not match. A session whose title starts with `[run]` is a
     role session and never counts. A session with the role's title that runs in a worktree or
     another folder does not count: name it in your report so I can archive it.
4. The case: this session is the Tech Lead when its id is the registry's `tech-lead` entry, or else
   its title ends with "Tech Lead" (ignoring case and spaces). Then go to case B (step 6).
   Otherwise, case A (step 5).
5. **Case A: this session is not the Tech Lead.** Start no sub session here.
   - Create `<project folder>/.handoff/team-setup-started` holding one line, today's date, so the
     sessions started from now on never get the setup notice.
   - The Tech Lead, by step 3. More than one matches: list them and ask me which one leads (I
     archive the others); start and message none meanwhile. Exactly one: reuse it, never start a
     second one, and send it, by session id, the lines `[startup-team:tech-lead]`,
     `PLUGIN FOLDER: <absolute path of this plugin's folder>`, the `FIRST:` line below when
     `.handoff/team-setup-done` does not exist, and `REQUEST: <my pending request, verbatim>` when there is one.
   - None: start it with ONE `start_session` call: initiation `user_asked`, title `AI Tech Lead`,
     name `tech-lead`, model from the table (unless the project's CLAUDE.md names another),
     context `fresh`, `use_worktree: false` (never a worktree: it would not be found by step 3,
     nor see the project's `.handoff/`). Prompt: `[startup-team:tech-lead]`, the full text of
     `sessions/tech-lead-session.md` (the `sessions` and `agents` folders sit beside the
     `commands` folder), `PLUGIN FOLDER: <absolute path of this plugin's folder>`, the line
     `FIRST: the setup is not finished yet; ask the owner to type a reply here once (no dialog), then
     run start-team from the plugin folder on that typed turn`, and `REQUEST: <my pending request, verbatim>` when there is
     one. Background: at least 80 characters on which project folder it serves and that it leads
     the team.
   - Team Optimization, only when the project's CLAUDE.md names `TEAM REPO CLONE:`: find it by
     step 3 (registry `optimization` entry, else the title "AI Team Optimization"). More than one:
     list them and ask me which one to keep; start none meanwhile. Exactly one: reuse it, never a
     second one. None: start it on this same turn with ONE `start_session` call, by the same rules
     as the AI Tech Lead (initiation `user_asked`, context `fresh`, `use_worktree: false`, the
     project's folder): title `AI Team Optimization`, name `optimization`, model from the table.
     Prompt: `[startup-team:optimization]`, the full text of `sessions/optimization-session.md` and
     `PLUGIN FOLDER: <absolute path of this plugin's folder>`. Background: at least 80 characters
     on which project folder it serves and that it improves the team itself. Without the
     `TEAM REPO CLONE:` line, skip this bullet.
   - If this session has a tool that moves a session it started to the top level of the sidebar
     (in the desktop app: `detach_session`), use it on the AI Tech Lead and on AI Team
     Optimization, so each is a session of its own. Without one, leave them where they are.
   - Write the registry's `tech-lead` entry, and `optimization` when it was found or started
     (step 9 shows the format), keeping every other entry.
   - Tell me in one line: when the setup is not finished (no `team-setup-done`), open AI Tech Lead
     (link it) and type a reply there once to finish it; when it is, that the team already exists,
     with the AI Tech Lead linked. Link AI Team Optimization too when it was
     found or started. Do not write `team-setup-done`. Stop.
6. **Case B: this session is the Tech Lead.** If this turn was started by another session's
   message, not typed by me, say in one line that the app refuses session starts on such a turn and
   ask me to reply here once. Stop. Otherwise create `.handoff/team-setup-started` if it is
   missing, read `sessions/tech-lead-session.md` and keep it, with the `team-workflow` skill, as
   your standing method.
7. The named sub sessions are those `$ARGUMENTS` names, all six for `all`, and none with no
   argument. For each named sub session, in the table's order: one match by step 3, use it as it is, whoever
   started it. More than one: list them and ask me which one to use; never guess, and start none
   for that role meanwhile.
8. Note whether `<project folder>/.handoff/team-setup-done` already exists (then this run is an
   on-demand start, and steps 10 to 12 are skipped). Create it if missing, holding one line,
   today's date, before any `start_session` call, so the setup offer (the `setup-offer` hook) stops
   and new sub sessions' hooks stay quiet. Then start each named sub session that has none with ONE
   `start_session` call, so it sits under this session:
   - initiation `user_asked`, the title and name from the table
   - context `fresh`, `use_worktree: false`, never a worktree, whatever else I said
   - the model from the table, unless the project's CLAUDE.md names another
   - prompt: the line `[startup-team:<name>]` so the team gate stays quiet, then the full text of
     the brief, then, when the table names an agent file, a last line
     `AGENT FILE: <absolute path of that file>`
   - background: at least 80 characters saying which project folder it serves and which role it
     holds in the team
9. Write the registry `<project folder>/.handoff/team-sessions.json`: every role found or started,
   this session as `tech-lead`, keyed by name, each with its session id and title, for example
   `{"tech-lead": {"id": "<session id>", "title": "AI Tech Lead"}, "developer": {...}}`. Keep the
   entries of roles this run did not name, `optimization` among them. Every "find a session" rule of the team reads it first.
10. Companions: for each companion plugin this plugin's marketplace lists (`ROSTER.md` beside the
    `team-workflow` skill names them), run `claude plugin list` once. A copy it shows installed for
    this project, from any marketplace, wins and stays the one in use: do not install the team's
    copy beside it, and leave an installed `<name>@startup-team` as it is (no reinstall). A copy
    only named in the project's CLAUDE.md but not installed does not count. Otherwise run
    `claude plugin install <name>@startup-team --scope local`, then
    `claude plugin disable <name>@startup-team --scope local`: companions are off by default. Their
    files stay in the plugin cache and agents read them from there by path when a task needs one.
    An already-enabled copy from any marketplace is left as it is and reported as enabled.
    Apply none of a companion's own hooks, settings or setup questions.
11. Code graph (optional). A failure anywhere in this step never fails the setup; report it in one
    line and go on. Skip it when `.handoff/graph-setup-declined` exists, or when
    `.claude/skills/graphify/` and `graphify-out/graph.json` already exist: then only rebuild the
    graph as in 11.4 and report it in one line. When `.handoff/graph-setup-pending` exists, do not
    ask again: resume at 11.2.
    1. Find the command: `graphify` on PATH; else `graphify` in the user Python scripts folder
       (`python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user' if __import__('os').name == 'nt' else 'posix_user'))"`);
       else `python -m graphify --help` exits 0. Not found: ask me once whether to install it
       (`python -m pip install --user graphifyy`, the PyPI package `graphifyy`, for this user only);
       install only on my yes; on no, write `.handoff/graph-setup-declined` and go on.
       Then ask me once, as the only question: "Set up a code graph (graphify) for this project?
       The full install adds a graphify section to the project's CLAUDE.md, a `.claude/CLAUDE.md`,
       a `/graphify` skill and three hooks in `.claude/settings.json` that run on searches and file
       reads." If this session has, or can load, a question dialog, ask it there with "Set it up"
       (= 1) and "Not now" (= 0); a dialog I dismiss counts as "Not now"; else ask it as text ending
       "1 = yes, 0 = no." On "Not now", write `.handoff/graph-setup-declined` and go on. My yes here
       is the approval for those CLAUDE.md and hook changes, also in a project whose CLAUDE.md asks
       for the owner's approval for them: quote my answer in the report.
    2. The hooks call `graphify` by its bare name, so check it resolves in a fresh shell
       (`cmd /c where graphify` on Windows, `sh -lc "command -v graphify"` elsewhere). If it does
       not: do NOT install. Tell me the folder to add to my PATH (the scripts folder of 11.1; I
       change PATH myself), build the graph with the full path as in 11.4 meanwhile, write
       `.handoff/graph-setup-pending` and stop this step: it finishes the next time this command
       runs here.
    3. Install, in the project folder: `graphify install --project --platform claude`.
    4. Build the graph code-only with every model backend off: `graphify extract . --code-only`
       (local AST, no LLM), run with the model key and base-URL variables (ANTHROPIC_*, OPENAI_*,
       GEMINI_API_KEY, GOOGLE_API_KEY and the like) unset for that one command. Never `extract`
       without `--code-only`, never `label`, never a docs pass without my 1.
    5. Add `graphify-out/` to the project's `.gitignore` unless `git check-ignore -q graphify-out`
       already passes.
    6. Run each hook command once by hand with a harmless input, e.g.
       `echo '{"tool_name":"Grep","tool_input":{"pattern":"x"},"hook_event_name":"PreToolUse"}' | graphify hook-guard search`,
       the same with `"tool_name":"Read"` for `graphify hook-guard read`, and
       `echo '{"source":"compact","hook_event_name":"SessionStart"}' | graphify hook-guard compact`.
       Each must exit 0. If one does not, remove graphify's three entries (the commands starting
       `graphify hook-guard`) from `.claude/settings.json` again and say so.
    7. Report in one line: installed or pending, the graph's node and edge count, ignored, hooks
       ok or removed, and my quoted yes. Delete `.handoff/graph-setup-pending` if it exists.
12. Outside models (optional). A
    failure anywhere in this step never fails the setup; report it in one line and go on.
    Skip it when `.handoff/gateway-setup-declined` exists (unless `$ARGUMENTS` is `gateway`), or
    when the project's CLAUDE.md already has a `# Gateway (outside models)` section: then only run
    the `health` command of 12.1 against its base URL and report the result in one line. When
    `.handoff/gateway-setup-pending` exists, do not ask again: resume at 12.1.
    Otherwise ask me once, as the only question: "Set up FreeLLMAPI so the team can hand text work
    to free models?" If this session has, or can load, a question dialog, ask it there with two
    options, "Set it up" (= 1) and "Not now" (= 0); a dialog I dismiss counts as "Not now". Only if
    the dialog can't be shown, ask it as text ending "1 = yes, 0 = no." On "Not now", write
    `.handoff/gateway-setup-declined` (one line, today's date) and go on: this project is not asked
    again; `/startup-team:start-team gateway` asks again. On "Set it up", the sub-steps below, in
    order, each reported in one line. `<plugin folder>` is this plugin's absolute folder.
    1. Find a running local router, only at these two addresses, in this order:
       `python <plugin folder>/skills/team-workflow/scripts/gateway.py --base-url http://127.0.0.1:31415 --key-env FREELLMAPI_API_KEY health`,
       then the same with `http://127.0.0.1:3001`. `ok <n>` at either: that address is the base URL,
       go to 12.4. Report `auth`, `down <reason>` and `refused: ...` as they are. If both say
       `down`, go to 12.2. If either says the key variable is unset (it refuses before contacting
       anything, so a router may or may not be running), or `auth`, go to 12.3.
    2. No router answers: tell me where to get FreeLLMAPI (https://github.com/tashfeenahmed/freellmapi,
       its Releases page or its desktop app), and that I install it and add my provider keys in
       its dashboard myself: the team never installs it and never handles a key. Write
       `.handoff/gateway-setup-pending` (one line, today's date). Stop this step; it resumes at
       12.1 the next time this command runs here.
    3. The key is missing or refused: ask me to copy the unified key from FreeLLMAPI's dashboard and
       save it as a user environment variable named `FREELLMAPI_API_KEY`, never pasting it into the
       chat, then to restart the session. If FreeLLMAPI may not be installed yet, add the pointer of
       12.2. Write `.handoff/gateway-setup-pending` and stop this step, as in 12.2.
    4. Masking needs the project's private words. If `.handoff/private-words.txt` is missing or
       lists no word (blank lines and `#` lines don't count), ask me for them in one question: the
       project and company names, domains, hosts, account names and people's names. Write my
       answer to it, one per line. Check that `.handoff/` is git-ignored
       (`git check-ignore -q .handoff/`) and tell me in one line if it is not.
    5. Show me the exact text of a `# Gateway (outside models)` section for the project's
       CLAUDE.md, and write it only on my yes (on a no, stop this step and write the pending
       marker):
       ```
       # Gateway (outside models)
       - Base URL: <the address found in 12.1>. Key variable: FREELLMAPI_API_KEY (the name only;
         the key is never written, pasted or printed).
       - Commands, with the plugin at <plugin folder>: `python <plugin folder>/skills/team-workflow/scripts/gateway.py
         --base-url <base URL> --key-env FREELLMAPI_API_KEY health | launch --brief <file> --out
         <file> --terms <file> --job <type> | pick --job <type> | review <id> pass|fail | scores |
         list | log <id>` (plus `mask` / `unmask` to check locally).
       - Every brief is masked before it leaves: the words in .handoff/private-words.txt, emails,
         secret-shaped text and the terms the anonymizer agent lists. The real values come back
         only in the answer. A task whose point is a secret or personal value is never sent.
       - Stays here, never delegated: code for auth, permissions, payments and database changes;
         reading or writing files, running commands or tests, pushes, deploys, approvals and
         questions to the owner.
       - Every answer is checked here against the request and this file's rules before it is used.
       ```
    6. Run the `health` command again with the base URL; then ONE trial launch: write
       `.handoff/gateway/trial-brief.txt` holding "Rewrite in plain words: The meeting has been moved
       to a later time." and run `launch --brief .handoff/gateway/trial-brief.txt --out
       .handoff/gateway/trial-answer-<date>.txt`. Report ok or failed and the ledger id. On ok,
       delete `.handoff/gateway-setup-pending` if it exists.
13. Sub-session permissions (run also on an on-demand start). When the project's CLAUDE.md already
    has the line `Sub sessions: bypass`, switch each sub session this run started to
    `bypassPermissions` with `set_session_permission_mode` and go on. Otherwise, skip this step when
    no sub session is in the registry. Read the app settings with `get_settings` (read-only; never
    change `bypass_permissions_mode`). Not opted in: tell me in one line to opt in under the app's
    Settings, and go on. Opted in: ask me once "Switch the sub sessions to bypass permissions?" (the
    question dialog, options "Switch" = 1 and "Not now" = 0; as text ending "1 = yes, 0 = no." only
    if no dialog can be shown). On my yes, typed in this session: add the line `Sub sessions:
    bypass` to the project's CLAUDE.md, then switch every sub session in the registry to
    `bypassPermissions`. Main sessions (AI Tech Lead, AI Team Optimization) keep their mode; any
    change there asks me first, every time. Why: auto mode cannot pass the Remote Control switch
    before a clear, so each pre-task clear would otherwise wait for my click.
14. Tell me in one line which sub sessions were found and which were started (with no argument:
    none, and each one starts the first time a task needs it), and name any role
    still missing because its start failed or was refused, with the app's reason: running this
    command again here starts just that one. Then any worktree or duplicate sessions from step 3;
    then which companions were installed (disabled) and which kept (with their state), and that I
    turn one on with `claude plugin enable <name>@<marketplace> --scope local` (`disable` turns it
    off).

| Session | Title | Name | Model | Brief | Agent file |
|---|---|---|---|---|---|
| Tech Lead | AI Tech Lead | `tech-lead` | opus | `sessions/tech-lead-session.md` | none |
| Team Optimization | AI Team Optimization | `optimization` | opus | `sessions/optimization-session.md` | none |
| Business Analyst | Business Analyst | `business-analyst` | sonnet | `sessions/business-analyst-session.md` | none |
| Designer | Designer | `designer` | sonnet | `sessions/designer-session.md` | `agents/designer.md` |
| Developer | Developer | `developer` | opus | `sessions/developer-session.md` | `agents/executor.md` |
| QA Engineer | QA Engineer | `qa` | sonnet | `sessions/qa-session.md` | `agents/qa.md` |
| DevOps | DevOps | `devops` | opus | `sessions/devops-session.md` | `agents/devops.md` |
| Security | Security | `security` | opus | `sessions/security-session.md` | none |

This command starts no session beyond the AI Tech Lead and AI Team Optimization (case A) and the
Tech Lead's named sub sessions (case B). Case B never starts AI Team Optimization.
