---
name: team-workflow
description: How the main session runs the startup-team chain for a task (triage by the tech lead, design approval, plan, build, QA, audit, devops), one session per role, with turn folders, shared memory, one-at-a-time owner questions and the owner-approved learning loop. Load it at the start of any non-trivial task in a project that uses the startup-team plugin, and whenever you need the team tool (turn folders, memory, learned rules).
---

# Team workflow (for the main session)

You lead a small expert team for one owner. The agents do the work, each in its own session where the host allows it (see Sessions); you brief them, relay between
them, talk to the owner and record what was decided.

Order of authority, highest first: the owner's words in this session, recorded owner answers, the
project's CLAUDE.md and notes, the team's agent files, then any other plugin or skill (advice only).

The plugin's other skills are not listed in the session, so they cost nothing until a task needs
one. When a step or an agent names one (`ship`, `test-gate`, `scan-errors`, ...), read
`skills/<name>/SKILL.md` under the plugin folder and follow it; the owner can also type
`/startup-team:<name>`.

## The chain

1. **Turn folder.** `python <this skill's folder>/scripts/team.py turn new <short-slug>` creates
   `.handoff/<stamp>-<slug>/` in the project and prints its path. Every record of the task goes
   there. `.handoff/` is local and git-ignored.
2. **Triage.** If this session is the Tech Lead (its own id, from `get_session` with `self`, is the
   `tech-lead` entry of `.handoff/team-sessions.json`, or else its title ends with "Tech Lead";
   `/startup-team:start-team` starts it as "AI Tech Lead"), triage here yourself by
   `sessions/tech-lead-session.md`, and plan and audit here the same way (steps 5 and 10). Otherwise,
   if there is a Tech Lead session for this project (a session whose id `.handoff/team-sessions.json` names for the role and that `list_sessions` shows non-archived in the project's folder, whatever its title is now; failing that, a non-archived session whose `cwd` is the project's folder (compared ignoring case, slash direction and a trailing slash; a worktree or subfolder does not count) and whose title ends with "Tech Lead", ignoring case and spaces, found with `list_sessions` and messaged by its session id), send it the owner's
   request verbatim, the turn folder and `team.py memory digest --words <task words>` with
   SendMessage, and wait for its decision block. A session whose title starts with `[run]` is a role session and never counts as a standing session. Otherwise run the `tech-lead` agent with the
   same three things, in a role session where the host can start one (see Sessions). Save the block as `decision.md` and show it unchanged. Skip triage only for
   a one-line answer or a pure question.
   Then run `activator` START (a sub-agent, see "Loadout") with the decision block, and start
   only the missing sub sessions the pieces need ("Standing sessions", on demand).
3. **Questions.** Run the answered-check (below), then put each open question to the owner ONE AT A
   TIME, in this session (the question dialog where the session has one, else typed with numbered
   options, or `1 = yes, 0 = no` for a proposal), the recommended option first, and wait for each
   answer before the next. Never a batch and never through another session: every session and sub
   session asks the owner its own questions in its own session the same way, and an agent or
   sub-agent returns its questions to the session that ran it, which asks them. A main session never asks the owner a sub session's question: one that reaches it in a sub
   session's report or message (an UNCLEAR, an open question) goes back to that sub session with one
   line, "ask the owner this in your session", and the sub session asks it, one at a time.
   No question travels out of the session that owns it. A session with an open owner question asks
   it in its own session with the question dialog (AskUserQuestion) where it has one, one at a
   time; its closing message and its wrap-up recap (what the app passes to the session that started
   it) never hold the question, its options or its recommendation, only "<role> has an open question
   for the owner in this session.", and the same holds for anything it sends a parent or another
   session. A main session (Tech Lead, optimization) that receives a report or note carrying a
   question never restates it, its options or a recommendation, never asks the owner for the
   answer, never answers it for the owner and never forwards an answer: at most one line, "<session>
   has an open question in its own session." An agent's question blocks (OPEN QUESTIONS, QUESTIONS,
   UNCLEAR) are only for the session that ran it, which asks them itself the same way. A question
   the owner has answered in one session is never asked again in another: a session that receives
   the answer quoted verbatim, with the question it answered, acts on it. A role agent with a
   standing session in `.handoff/team-sessions.json` (designer, qa, security, devops) runs only in
   that session. Another session that gets work for that role (a request the owner typed, a slash
   command, a piece) does not run the agent: it sends that session the owner's words verbatim, the
   file paths and any answers already given (verbatim, with their questions), then says only
   "<Role> has the request." That role session asks the questions. No registry entry for the
   role: the current session runs the agent as before.
   Record each answer
   at once: `team.py memory add --kind owner-answer --source main --turn <turn> --evidence <id>
   --text "<id> <question> -> <answer verbatim>"`, and append it to `answers.md`.
4. **Design.** Any UI change (in the Designer sub session when the project has one, see Sessions): `designer` PROPOSE, its questions to the owner, the proposal, the
   owner's 1, then `designer` BRIEF. Nothing is built before the 1.
5. **Plan.** Any API, data model, auth or job piece: `architect` (the Tech Lead session when the
   project has one, see Sessions). Its questions go to the owner; its plan is the executor's brief.
6. **Build.** One piece per `executor` run, with the model the decision block names. One local
   commit per piece. A BLOCKED piece waits for its answer; it is never built on an assumption.
   With no git identity set, commit as the previous commit's author (`git -c user.name="$(git log
   -1 --format=%an)" -c user.email="$(git log -1 --format=%ae)" commit ...`); never write git config.
7. **Check it yourself.** After a piece that changes a screen, look at it in a real browser at the
   project's breakpoints, check the console, and save `browser-pass.md` in the turn folder.
8. **QA.** `qa` (the QA Engineer sub session when the project has one), once the pieces of the turn are built (or per piece when the decision block says
   so), with the request, the answers, the design brief or plan and the results. It writes
   `qa-<piece>.md`. QA makes sure nothing is missed: every acceptance point, edge case, and for auth / data / redirect /
   upload pieces the abuse cases (security probes), plus the checks the brief names; its record says what it covered
   and what it could not. BUGS go back to the tech lead as fix tasks; an UNCLEAR is asked of the owner by the QA session
   itself (or by the session that ran the `qa` agent).
9. **Deviation sweep.** Every DEVIATION that touches an owner answer goes to the owner before the audit.
10. **Audit.** `auditor` (the Tech Lead session when the project has one, see Sessions), with the request, the decision block, the answers, the briefs, the results and the QA records. FAIL
   items go back to the tech lead. W items go to the owner as one list of 1/0 proposals. One audit per task: the
   auditor checks the task was completed as assigned (each brief's DONE WHEN, VERIFY WITH and DO NOT, the owner's
   words, the records, and that the stated commits and files exist). It re-runs only the VERIFY commands the briefs
   name, never QA's tests, probes or browser passes; a coverage gap goes back to QA as "QA missed X". No separate
   same-hands audit beside it and no second independent auditor run on the same task. Where the project has a
   gateway, the requirement check (does the output match what the brief assigned) goes to it first (`pick --job
   audit`, then `launch` with a masked brief: the assignment and the output summary); the auditor reviews the answer
   against the files, records `review <id> pass|fail` and writes the verdict itself. The verdict, the VERIFY re-runs,
   file reading and anything secret stay local; with no reachable gateway the auditor checks it itself and says so.
11. **Ship.** `devops` (the DevOps sub session when the project has one) PROPOSE for any push, merge, deploy or server change. The owner approves each.
12. **Close.** Record outcomes (below), mark open items done, collect the tech lead's LEARN
    proposals (learning loop, step 1), and when nothing is running and
    nothing approved is left unbuilt, tell the owner once, in one line. Run `team.py conversations
    build`, add one row to the summary's table and update its "Where things stand" ("Conversation
    summary"). Where the project tracks `.handoff/` in git, make the records commit ("Step 12,
    records commit") and, beside it, the project setup commit ("Setup in git"). Then run `activator`
    CLOSE. Replies to the owner stay short: the result first, no
    repeated background.

## Step details
These add to the numbered steps above.

- **Fast lane.** A request that starts with `quick:` skips triage. QA and the auditor still run.
- **Step 2, triage.** The tech lead reads the project's routing digest instead of the whole
  CLAUDE.md when the project has one (see "Project setup files"). Save the decision block before
  any piece starts.
- **Step 2, delegated pieces.** If the block has DELEGATE pieces and the project's CLAUDE.md names
  a gateway to cheaper outside models, run `dispatcher` in DISPATCH mode with the block and save
  its report as `board.md` in the turn folder. Send each FOR TECH-LEAD entry to the tech lead. A
  retry past the first is a 1/0 for the owner. With no gateway, there are no DELEGATE pieces.
- **Step 3, questions.** Send a question marked `AFTER: Q<n>` only once Q<n> is answered, in its
  final wording. To reach the owner on a channel outside the app that the project's CLAUDE.md
  names, the `messenger` agent carries one question at a time; give it the ANSWERED-CHECK line.
- **Step 5, plan.** The architect works in two passes: questions first (to the owner, one at a
  time), then `plan-<piece>.md`, which ends in GREEN LIGHT NEEDED. Nothing is built before the
  owner's 1 on the plan. The executor's brief names the plan's path.
- **Step 6, build.** Run pieces in the block's order; pieces marked `PARALLEL: yes` whose TOUCHES
  share nothing may run side by side when they do not write source. The brief carries OWNER,
  FILES and CHANGE, READ FIRST, READ ONLY IF NEEDED, STATE YOU BUILD ON, RULES, VERIFY and COMMIT,
  plus the path of the project's preflight sheet when it has one. Decide a piece's tests with the
  `feature-tests` skill. To prove a branch before its pull request, use `dev-feature-test`.
  A video piece goes to the `video` agent.
- **Step 8, QA.** QA follows the `testing-rules` skill; for QA of changes already merged, `e2e-qa`;
  for throwaway accounts on a test environment, `test-accounts`. Step 8 is piece QA: what the
  task's pieces touch. Full QA (the whole product, a regression run, a security sweep) is never
  folded into it: it is a separate task, triaged on its own, that starts with a written
  `test-plan.md` in its turn folder (scope, areas, cases, environments, what cannot be tested)
  before any test runs, reusing `e2e-qa`, `testing-rules` and `app-audit` where they fit. Its
  audit checks the run against that plan.
- **Step 10, audit.** Also pass `board.md` when anything was delegated (say "nothing delegated"
  otherwise), `browser-pass.md` when a screen changed, and after a devops run its
  `devops-<what>.md` and `devops-log.md`. On `PRE-AUDIT CHECK FAILED`, fix the records it names
  and run it again.
- **Step 11, ship.** Use the skill that fits: `ship` (one finished branch), `wrap` (end of
  session), `hotfix`, `release-train`, `deploy` (manual deploy or automatic-deploy control).
  `test-gate` runs before any merge; `release-notes`, `announcement` and `ship-log` after. Each
  push, merge, tag and deploy is its own `devops` proposal; pass the owner's 1 on verbatim with the
  step ids it covers. A devops run that changed something is followed by the `auditor`.
- **Step 12, close.** Apply the tech lead's MEMORY lines: `team.py memory done <id>` for DONE,
  `memory add` for KEEP, and for STALE a new entry whose text names the id it replaces.
- **Step 12, records commit.** Only where the project tracks `.handoff/` in git (`git ls-files --
  .handoff` lists files), and only by the main session, after the checkpoint, the summary and
  `team.py conversations build`: stage `.handoff/` alone (`git add -- .handoff`, never `-f`: the
  gateway maps stay git-ignored), run `team.py records check-commit`, and on `staged records ok`
  make ONE local commit `Team records: <task>`. The check stops on a staged name outside
  `.handoff/`, a gateway map, `.private`, `.env` or local settings file, or a secret shape in the
  staged diff: then commit nothing, unstage (`git restore --staged -- .handoff`) and tell the owner.
  Nothing outside `.handoff/` is ever in this commit; push only on the owner's command. It and the
  project setup commit ("Setup in git") are the only commits a main session makes itself. Where `.handoff/` is not tracked, `team.py` keeps it in
  `.git/info/exclude` and there is no records commit.
- **Step 12, clears.** The host re-sends a session's whole history with every message, so every
  history stays near empty and context comes from the summary, checkpoints and records. The clear
  tool takes `self` and acts when the turn ends, so say and write everything first. The host may ask
  the owner to approve a clear outside auto or bypass mode, and drops a `self` clear when the owner
  speaks first.
  - Before any clear (`self`, on `RESET:`, past the Threshold, one the owner asks for, or a session
    this one started), check that nothing is ongoing: no open task-list step, no background
    command, Monitor or timer of that session running, no piece out with a sub session, no owner
    question or approval open, and for another session `get_session` shows it not running.
    Anything ongoing: skip the clear and say so in one line. A Threshold or owner-asked clear then
    happens once it is done; a skipped before-new-task `RESET:` clear never happens later (the task is sent anyway).
  - No session clears itself when a piece or task closes, and nothing is sent at close to clear
    another (except past the Threshold). A session is cleared just before another session sends
    it any message that starts its turn: a task (a brief, a triage request), a re-test, a
    follow-up, a `RULE:` or `HEADS-UP:` notice. `RESET:` and `WAKE` themselves never trigger it.
    Agents and sub-agents keep no history: their record file is their history, and they end when
    they return.
  - Before sending a session any message that starts its turn (called the task below):
    1. Check that it holds nothing pending (the check before any clear, above), and also: no piece
       out, no FAIL awaiting a re-test, no Developer fix round open, and no owner question or
       approval it holds.
    2. Something pending: send the task without clearing. Nothing pending: run
       `team.py conversations build` (so its chat lands in the history files first), clear it, then
       send the task. A session this one started: clear it with the clear tool (Remote Control
       below). Any other: send `[startup-team:<its name>]` + `RESET: before new task from <own name>`,
       wait until its turn has ended (a background command of about a minute, then `get_session`
       shows it not running; a message that arrives before its turn ends cancels its clear), then
       send the task.
  - On `RESET: before new task from <name>` or `RESET: threshold from <name>` (never triaged, never
    a piece): first the check before any clear, above. Anything ongoing: skip the clear and say so
    in one line; the task is sent anyway (none follows a threshold `RESET:`), and no later
    self-clear follows. Nothing ongoing: write your checkpoint; if your Remote
    Control is on, add `REMOTE CONTROL: on again` to it and turn Remote Control off (Remote Control
    below); then clear `self` as the turn's last call, replying nothing.
  - Limit: a message the owner types into a main session cannot be preceded by a clear, so a main
    session is cleared only by the other main session: before it sends it a task, or past the
    Threshold with `RESET: threshold from <own name>`. Never while it is building, testing, in a
    fix round or holding live work.
  - Remote Control. Applies only where the project's CLAUDE.md has the line `Remote Control clears:
    allowed` (the owner's standing yes); without it, Remote Control is a refused clear. The host
    refuses to clear a session while Remote Control is on, refuses to turn it on again until the
    cleared session has run a turn, and a clear cancels the timers that session set, so a session
    cannot wake itself. Before a clear, read the target's state with `get_session`:
    `remoteControlState` `off`: clear as usual. `connecting` or `unavailable`, or
    `startedViaRemoteControl` true (its switch is locked): a refused clear. `on`:
    - Clearing `self` (on `RESET:`): add the line `REMOTE CONTROL: on again` to your checkpoint,
      turn Remote Control off for `self` and clear as the turn's last call. The task the sender
      sends next wakes you.
    - On your first turn after a clear, whatever message started it (a task, `WAKE` or anything
      else), when your checkpoint has `REMOTE CONTROL: on again`, turn Remote Control on for `self`
      before anything else and delete the line.
    - A clear that is refused or dropped after Remote Control was turned off: turn it on again at
      once and delete the line. A session whose Remote Control was on always ends up on again.
    - Clearing a session you started: turn its Remote Control off, clear it, send it the task (or,
      for a clear the owner asked for with no task, `[startup-team:<its name>]` + `WAKE`), and turn
      its Remote Control on again once that session's next turn has ended, whether or not the clear
      went through; then check with `get_session` that it is on. `WAKE` (never triaged, never a piece)
      needs only the first-turn step above and no reply.
    - A Remote Control or clear call that is refused because a hook changed its input is repeated
      once with exactly the input the refusal quotes.
  - A refused clear (pinned, queued work, owner declined, a locked or unavailable Remote Control
    switch, or Remote Control without the CLAUDE.md line): the target says so in its reply (or the
    sender sees it in the tool result), the task is sent anyway, and the main session tells the
    owner once, in one line, which session and why; never change those settings. Without a clear
    tool, skip it.
- **Step 12, early compress.** On the owner's yes only, the project's tracked `.claude/settings.json`
  gets `"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "30"}` (created or merged, every other key kept;
  never `settings.local.json`), so every session compresses its history at about 30% full. The
  skip check looks in both files. It applies on each session's next start. Never set it without the owner's yes.
  `start-team` asks it once in its step "Early compress" (skipped when the line is already set).

## Checkpoints
Long histories are re-read on every turn, so sessions stay short and the detail stays in files.
- **Checkpoint file.** `.handoff/checkpoints/<session name>.md`, written by the session itself, at
  most 30 lines. Its first line names the role and the brief path; then the task and piece in hand, what is done (with commits), what is next,
  open questions, and the paths of the records that hold the detail.
- **Threshold.** At each task close the main session checks every standing sub session's message
  count: `list_events` prints "showing N of M messages", and M is the count. Past the project's
  `CLEAR AT: <n> messages` CLAUDE.md line (default 100), clear that session as soon as the check
  before any clear ("Step 12, clears") passes: a session you started with the clear tool, any
  other with `RESET:`. Never while it is building, testing, in a fix round or holding live work.
  Then tell the owner in one line which sessions were cleared and which were skipped (pending).
  A main session also reads the OTHER main session's count (its id in `.handoff/team-sessions.json`;
  `list_events` cannot read the calling session itself). Past `CLEAR AT`, with `get_session`
  showing it not running and its checkpoint showing no open piece, question or approval, send it
  `[startup-team:<its name>]` + `RESET: threshold from <own name>`; it runs the `RESET:` flow
  ("Step 12, clears", Remote Control included) and the next message wakes it. Pending: skip it, say
  so in one line, and try again at the next task close.
- **Pointer brief.** The message that starts a piece is the brief, under `[startup-team:<name>]`:
  the role, the brief path, the agent file path, the checkpoint path,
  `.handoff/conversations/SUMMARY.md`, the record paths, "find more with `team.py records find
  <words>`", and at most five lines of summary. No separate re-brief follows a clear. Agents and
  sub-agents get paths too, never pasted history or transcripts; skills have no history of their own.
- **After a clear.** When the session's id is a role in `.handoff/team-sessions.json`, the
  session-start output names the role (when the host skips SessionStart, the first prompt's hook
  output does, also for a message from another session): the session reads that role's brief under
  the plugin folder, then its checkpoint. The checkpoint's first line names the role and brief
  path as the backstop.
- **Looking things up.** A session that needs older detail runs `team.py records find <words>
  [--kind k] [--last n]` (paths, kinds and titles only; `records index` rebuilds
  `.handoff/records-index.jsonl`) and opens only the files it names, instead of asking for a
  recap. Code files are found with the code graph when the project has one ("Code graph").

## Conversation summary
`.handoff/conversations/SUMMARY.md` is the hand-kept map of past work: one row per task (when, asked
for, outcome, chat file, records) and "Where things stand". `team.py conversations build` writes the
sub files from the project's session transcripts, one per session and day
(`<session>-<YYYYMMDD>.md`: what the owner typed and each turn's final reply, redacted), and creates
the summary from a template only when it is missing; it never changes it otherwise.
- A session that needs past context reads the summary first, when it exists, and never loads past
  transcripts or whole turn folders. It opens a sub file only when the task needs it, and Greps
  before reading a whole one.
- On its first turn after a clear or a restart, a session starts its visible reply with a short
  block `Read from summary:` (at most 5 lines: the last task, its state, anything open), taken from
  the summary and its checkpoint, then carries on.
- At each task's close (step 12) the main session rebuilds the sub files, adds one row and updates
  "Where things stand". Keep the summary under about 60 lines.

## Loadout
`activator` (a cheap sub-agent, `agents/activator.md`) keeps each session lean with `team.py
loadout`: `inventory` (plugins for this project, on or off, rough listing tokens, CLAUDE.md size,
standing sessions), `plan --needs a,b` (changes nothing), `on|off <plugin>` (this project, local
scope only, logged to `.handoff/loadout/log.jsonl`) and `selftest`. It runs at task start and close,
never on every message. It refuses the team's own plugin, a plugin on the CLAUDE.md `ALWAYS ON:`
line, and switching off a plugin with hooks or MCP servers without the owner's yes. It only
switches and names sessions: it never starts, clears or messages one, never uninstalls or deletes,
and never edits hooks, settings files or CLAUDE.md. A switch takes effect in a new or cleared
session; starting a session needs a turn the owner typed. The token counts are rough (characters
/ 4).

## Operations skills
Outside the build chain, the plugin has skills for running a product, read by path as said at the
top: `scan-errors` (cluster an error log into a triage report), `scan-tickets` (investigate support
tickets), `reply-tickets` (draft a ticket reply), `triage-log` (the ledger of triage outcomes),
`scrum-master` (notes into cards and epics; standup, review, retro), `start-epic` (build an epic's
cards one by one), `app-audit` (crawl every route as several roles: access grid, request cost),
`optimize-image` (shrink images), `repeated-judgment` (one cheap judgement over many items) and
`multi-model-supervisor` (supervise work on outside models). Each says near its top what the
project's CLAUDE.md must name for it to work. A fix that comes out of a scan or an audit is a new
task for the chain, starting at triage. Anything a skill sends, posts or deletes outside the local
working copy needs the owner's 1.

## Project setup files
The plugin works with none of these. Each makes it cheaper or sharper, and each is a fill-in
template in `templates/` beside this skill that a project copies into its own repository:

| Template | Copy to (or the path the project's CLAUDE.md names) | Read by |
|---|---|---|
| `routing-digest.md` | `.claude/routing-digest.md` | tech lead, in place of the whole CLAUDE.md |
| `audit-digest.md` | `.claude/audit-digest.md` | auditor, for the project's standing rules |
| `preflight-frontend.md` | `.claude/preflight-frontend.md` | executor, before a frontend piece |
| `preflight-backend.md` | `.claude/preflight-backend.md` | executor, before a backend piece |
| `operating-rules.md` | `.claude/operating-rules.md` | the rules and notes hooks, every prompt |

Without `.claude/operating-rules.md` the rules and notes hooks print nothing.

## Sessions
Two kinds of session can work for the team in a host that can start sessions. Standing sessions are
long-lived, one per role, and serve every task in the project. Role sessions are opened per run of a
role and end with it. A role whose standing session exists for the project gets no role session.

### Standing sessions
`/startup-team:start-team`, run in the session where the owner answers the setup offer, starts
only a session of its own titled "AI Tech Lead", where the owner carries on; there the AI Tech
Lead is the main session (by `sessions/tech-lead-session.md`, section "When you are the main
session"). After one reply from the owner there, the AI Tech Lead runs `start-team` itself to
finish the setup; it starts no sub session then. Each sub session (Business Analyst, Designer,
Developer, QA Engineer, DevOps and Security, from the briefs in `sessions/`) starts under it the
first time a task needs it. It writes `.handoff/team-sessions.json`, each role's
session id and title, and every rule below that finds a session reads that registry first, so a
renamed session is still found. When another session has an open question for the owner, only say "<that session> has an open question", in one line; never repeat the question or its options. Only a turn the owner started may call `start_session` (the app refuses it on
a turn another session's message started), so the AI Tech Lead is started by the session where the
owner answered the setup offer, and the sub sessions by the AI Tech Lead on a turn the owner typed
there, always with `use_worktree: false`, in the project's folder.
Where the project's CLAUDE.md has the line `Sub sessions: bypass` (the owner's yes, recorded by
`start-team`, "Sub-session permissions"), a sub session started later is switched to
`bypassPermissions` with `set_session_permission_mode` right after it starts. On "not available"
(the app's opt-in is off), tell the owner in one line to opt in under the app's Settings, and go on.
Main sessions (AI Tech Lead, AI Team Optimization) keep their mode; any change there asks the owner
first, every time.

**On demand.** After triage, on a turn the owner typed, the main session starts only the missing
sub sessions the task's pieces need (the `activator`'s list, or the decision block's routes), by
the `start-team` rules (found first by registry, then by title; never a second one;
`use_worktree: false`; the project's folder; registry updated), then sends the work. The AI Tech
Lead does this with `/startup-team:start-team <names>`. When a role is first needed on a turn
another session's message started, that run goes to a role session where one can be started, else
a sub-agent (Business Analyst: the main session does that analysis itself), and the
standing session is started on the owner's next typed turn only if the task still needs it. Never
start a session just in case. A sub session that already exists is used, never duplicated. They work only in the desktop app, where a
session can start another with `start_session`, list sessions with `list_sessions` and talk to any
of them with `SendMessage` by session id. In the terminal CLI those tools do not exist, so the
sub-agents and the main session stay the fallback. Only the Developer session writes source; every
other standing session only reads it.

Where the project's CLAUDE.md names `TEAM REPO CLONE: <path>`, the same setup run also starts
"AI Team Optimization" (`optimization`, by `sessions/optimization-session.md`), a second session of
its own beside the AI Tech Lead, never under it, recorded in the registry under `optimization`. It
is the owner's main chat for improving the team itself: it triages, plans and audits its own team
work, messages the sub sessions directly with no relay through the Tech Lead, and sends the Tech
Lead one `HEADS-UP:` line before it uses the Developer or the QA Engineer. Product work stays with
the AI Tech Lead. Without that line it is not started, and the setup is as above.

A project may still keep a separate Tech Lead session (the owner chooses when `start-team` finds
one); the rest of this section is about that case where it names the Tech Lead session. When this
session is the Tech Lead, there is no relay, and triage, plan and audit are done here.

Find the Tech Lead session like this: a session whose id `.handoff/team-sessions.json` names for the role and that `list_sessions` shows non-archived in the project's folder, whatever its title is now; failing that, a non-archived session whose `cwd` is the project's folder (compared ignoring case, slash direction and a trailing slash; a worktree or subfolder does not count) and whose title is the role's title, ignoring case and spaces (for the Tech Lead, a title that ends with "Tech Lead", so "AI Tech Lead" matches; a title that only contains the word does not), found with `list_sessions` and messaged by its session id.
A session whose title starts with `[run]` is a role session and never counts as a standing session.
Whoever started it, it is used, and a second one is never started. If more than one session matches, list them and ask the owner which one to use; never guess, and start none meanwhile.

**Message each session directly.** The Tech Lead session leads the sub sessions, but you talk to
each one yourself. Find a sub session by the same rule as the Tech Lead session, with its own title
("Business Analyst", "Designer", "QA Engineer", "DevOps", "Security"), and send it its work with
`SendMessage` by session id, under a first line `[startup-team:<name>]` (`business-analyst`,
`designer`, `developer`, `qa`, `devops` or `security`). It replies to you.
- **Tech Lead** (`tech-lead`): triage, plan and audit. For triage, send the owner's request
  verbatim, the turn folder and the memory digest; it replies with the decision block. For the
  architect's work, make the second line `PLAN: <piece> step 1` (or `step 2`, with the answers) and
  send what the architect would get; it writes `plan-<piece>.md`. For the auditor's work, make the
  second line `AUDIT` and send what the auditor would get; it writes `audit.md`. Its verdict starts
  with a `SAME HANDS` line. That is the task's one audit: no independent `auditor` run follows it.
- **Business Analyst** (`business-analyst`): a request to analyse (requirements, acceptance points,
  business rules). It asks the owner its own questions in its own session, one at a time, and replies
  with its findings and each answer verbatim as `<id> = <answer>`. It never asks another session's
  questions. It is only ever a sub session: there is no Business Analyst agent or role session.
- **Designer** (`designer`): a design step with its mode (PROPOSE, BRIEF or REVIEW). The reply
  names its record files.
- **Developer** (`developer`): step 6, one HERE piece at a time, with the executor's brief. It
  makes one local commit and replies with the result file, the commit and the VERIFY results, or
  `STATUS: BLOCKED`. Send the next piece only after it says nothing is building.
- **QA Engineer** (`qa`): step 8, only once the pieces are committed and no `executor` (or
  Developer session) is building. The QA record lands in the turn folder.
- **DevOps** (`devops`): ANALYSE and PROPOSE requests. When the owner approves a proposal, send
  the 1 on in the owner's words, verbatim; nothing runs without that.
- **Security** (`security`): a security check. Its fixes come back as proposals for the owner,
  never as changes.

**Backup: relay through the Tech Lead session.** Use it only when the direct way fails: you cannot
find the sub session (none matches, or more than one does and the owner has not chosen), or the
message to it is refused or gets no reply after one follow-up. Then send the Tech Lead session a
message whose first line is `[startup-team:tech-lead]` and whose second line is `FOR: <name>`,
followed by exactly what you would have sent. The Tech Lead session passes the message on unchanged and sends the reply back unchanged under `FROM: <name>`.
Say in `sessions.md` that the relay was used and why. A reply of `NO SESSION: <name>` means the sub
session does not exist (or more than one matches): tell the owner that `/startup-team:start-team`
starts it, and meanwhile run that role in a role session (below), or as a
sub-agent in the fallback; for `business-analyst`, do the analysis here.
Without a Tech Lead session there is no relay: a sub session you can find is still used directly,
and any other role runs in a role session (below).

### Role sessions: one per role run
The owner has asked for every role to run in its own session, so each can be opened, steered and
stopped on its own. Installing this plugin is that standing request: do not ask again per task.

**When.** If this session has a tool that starts a separate session (in the Claude desktop app:
`start_session`, with initiation `user_asked`), every run of `tech-lead`, `designer`, `architect`,
`executor`, `qa`, `auditor`, `devops` and `security` goes into its own session instead of a
sub-agent, except a role that has a standing session for the project: its runs go to that standing
session by message, and no new one is started. So `tech-lead`, `designer`, `qa`, `devops` and `security` runs go to their
standing session when one exists, and `executor` runs go to the Developer session when one
exists; otherwise they open a role session like the others. `architect` and `auditor` runs go to the
Tech Lead session when one exists, and otherwise open a role session.
`skill-sub` and `activator` stay sub-agents: their answers are short and are needed at once.
Fall back to sub-agents, for the whole task, when there is no such tool, when a start is refused,
or when the owner says "here" or "no sessions". In that fallback the main session also asks the
owner's questions itself, one at a time.

**The brief.** Start each one fresh (not a fork), with the model the decision block names and the
title `[run] <role>: <turn slug> <piece>`. The first line of the brief is exactly
`[startup-team:<role>]` so the team gate stays quiet in that session. Then:
- "You are the startup-team `<role>`. Read `<absolute path>/agents/<role>.md` and follow it as your
  instructions for this session. Do not triage, do not start sessions or agents of your own, and do
  not put questions to the owner: write them in your output file."
- Everything a sub-agent would get: the request verbatim, the mode, the piece, the decision block,
  the answers, the memory digest and the LEARNED lines for that role.
- The absolute path of the turn folder, the file to write there, and "end with one line naming it".

**Where.** Role sessions share this project's checkout (no worktree of their own): `.handoff/` is
git-ignored, so a separate worktree would not see the turn folder, and the executor's commit has
to land on the current branch. So only ONE session that writes source runs at a time (one
`executor` piece, then the next). Sessions that only read source or run it (`tech-lead`,
`designer`, `architect`, `qa`, `auditor`, `devops` ANALYSE, `security`) may run side by side, but
never `qa` or `auditor` while an `executor` is still building. The same holds for a standing
session: send nothing for `qa` while an `executor` or the Developer session is building, and never
run an `executor` role session while the Developer session is building.

**Getting the result.** The host tells you when a role session ends its turn. Do not poll. Its note
is a report, not the result: read the file it wrote in the turn folder and carry on from that. A
follow-up for the same role and piece (an answer to its question, a fix round) goes to the session
that already has the context, not to a new one. Add one line per session to `sessions.md` in the
turn folder: role, piece, session id, outcome.

**Each session asks its own questions.** A role session asks the owner its own questions in its
own session, as in step 3: one at a time, waiting for each answer, never a batch and never through
another session; it puts each answer verbatim in its reply, and the main session records it. The
1/0 proposals and every approval for the main session's steps are put to the owner here, as before. If the owner steers a role session directly, read
its output file again before the next step.

## Answered-check (before any question goes out)
For each question, search `.handoff/*/answers.md`, `team.py memory query <topic>`, the project's
memory notes, CLAUDE.md and this conversation. Already answered: drop the question and apply the
answer. Write `ANSWERED-CHECK: <what was searched> -> <result>` above the questions you do send.
Never ask the owner to confirm something they already said. Never send the same question twice.

## Rules every agent and sub-agent follows
Every agent in `agents/` and every sub-agent it runs keeps these, beside its own file's rules:
- Delegation loop (in a project whose CLAUDE.md has a gateway section): `pick --job` -> `launch
  --job` -> your check -> `review pass|fail`. The anonymizer and the activator never delegate;
  the messenger follows the gateway section in its own file.
- A question for the owner goes back to the session that ran you; that session asks it in its own
  session, one at a time. Never through another session, never a batch. Your questions are yours
  to ask: never hand them to another session to ask. A main session never asks the owner a sub session's question: one that reaches it in a sub
  session's report or message (an UNCLEAR, an open question) goes back to that sub session with one
  line, "ask the owner this in your session", and the sub session asks it, one at a time.
- Your question blocks (OPEN QUESTIONS, QUESTIONS, UNCLEAR) go only to the session that ran you,
  which asks them itself in its own session (question dialog, one at a time). No question, option
  or recommendation goes into a session's closing message, wrap-up recap or anything passed to a
  parent or another session, and a main session never restates one (step 3).
- Context comes from the paths in your brief and the conversation summary, never pasted history.
- Scope is the request: nothing beyond it.
- Never a secret, key or the contents of the private-words file in any output.
- Nothing about the project goes into the team repo. No push, deploy or install.
- A session passes the `RULE:` notices it has received into the brief of every agent it runs.

## Sub-agent requests
When an agent returns a `SUBAGENT REQUESTS` or `SPECIALIST REQUESTS` block, run each request with
`skill-sub` (or the named specialist), save the answer as `subagent-S<n>.md` in the turn folder and
resume the same parent. At most 2 per parent run; more needs the owner's 1. The brief you give
`skill-sub` is PARENT / SKILL / INSTRUCTION / SCOPE / QUESTION, the last four verbatim from the
request. The executor returns its block inside `STATUS: BLOCKED`.

Which skill an agent may ask for is in `ROSTER.md` beside this file: the companion plugins, the
roster per agent, the auditor's specialists, and the rule that the team's rules win over every
borrowed skill. Read it when you load this skill and put an agent's roster line into its brief.
A skill that is not installed comes back `SKILL NOT FOUND`; the agent carries on without it.

## Shared memory
`team.py memory add | query | digest | done` keeps one append-only file per project at
`.handoff/memory/agent-memory.jsonl`. Kinds: `owner-answer`, `fact`, `open-item`, `pointer`,
`learned`, `setup-change` (see "Setup changes"). Everything except an owner answer needs `--evidence` (a path, a command or a turn id).
Pass the digest into every brief. Text that looks like a secret is refused: never store one.

After each piece, record how the model choice went so the tech lead picks better next time:
`team.py memory add --kind learned --for tech-lead --tags model-selection,<shape> --evidence
<turn>/result-<piece>.md --text "<shape> on <agent@model>: green first try | green after N fixes | FAIL"`.

## Learning loop (how the team gets better across projects)
The team repository improves from what projects learn, and only generic rules ever travel there.

1. **Notice.** Day-to-day notes (`learned` memory entries, audit findings, model outcomes) stay in
   the project. At the close of every turn, ask the tech lead whether any failure or good outcome
   has now been seen at least twice. Those become `LEARN:` proposals.
2. **Propose.** `team.py learn propose --agent <agent | all> --source <who> --evidence <turn>
   --text "<the rule, in generic words>"`. The tool refuses the text if it holds a secret, an email,
   an IP or web address, a local path, the project's own name, or any word in the project's
   `.handoff/private-words.txt`. That file must exist before the first proposal: list the project's
   name, domains, hosts, brand terms and people in it, one per line.
3. **Decide.** Put the rule to the owner as a 1/0 proposal, in its final wording.
   `team.py learn decide <id> 1|0`.
4. **Apply.** `team.py learn apply <id> --repo <clone of the team repository>` checks the text
   again, adds the line to `LEARNED.md` and raises the plugin's patch version, so every project
   receives it on its next `claude plugin update`. Commit those two files on a branch `learn/<id>`
   with a generic message. The owner merges it. Never push it yourself unless the owner says so.
5. **Use.** When you load this skill, read `LEARNED.md` beside it and put the lines for an agent
   (and the `all` lines) into that agent's brief.

Only the rule's one line leaves the project. Its evidence, the turn folder, the memory file and the
proposal log stay in the project's `.handoff/`. Nothing about one project, its owner, its users, its
hosts or its secrets ever goes into the team repository, in a file or in a commit message.

## Code graph (optional: graphify)
A project set up with `/startup-team:start-team` may have a code graph (`graphify-out/graph.json`,
built by the graphify tool, an optional tool and not a plugin). When it exists:
- Ask it first, before grepping or reading whole files: `graphify query "<question>"`,
  `graphify path "<A>" "<B>"`, `graphify explain "<X>"` (exit 0 with an answer, 3 when a name is
  ambiguous, 4 when nothing matches). Name files from it; fall back to Grep/Glob when it has no
  answer.
- Rebuild it after a piece that changed code: `graphify update .` or
  `graphify extract . --code-only` (code only, offline, no model backend).
- The graph output is local: never committed, never deployed or served, never sent through the
  gateway unmasked. Code only, always; a docs or semantic pass needs the owner's 1.

## Gateway (optional: delegated pieces on outside models)
`scripts/gateway.py` beside this skill sends a delegated piece to an OpenAI-compatible endpoint
and keeps a ledger in `.handoff/gateway/ledger.jsonl`. A project switches it on by naming, in its
CLAUDE.md, the base URL, the NAME of the environment variable that holds the key (the key itself
never appears in the project, a brief, a record or a reply), and these commands:
- `gateway.py --base-url <url> --key-env <NAME> health`: `ok <n models>`, `down <reason>` or `auth`.
- `gateway.py ... launch --brief <file> --out <file> [--job <type>] [--terms <file>] [--model <name>]`:
  masks, sends, restores, and prints a task id; the ledger row keeps the job type.
- `gateway.py ... review <id> pass|fail [--note <text>]`, `scores [--job <type>] [--last n]` and
  `pick --job <type>`: record your verdict on an answer, show pass rate and median tokens per job
  and model (with `--last n`, over each job and model's last n reviews only), and print the model
  to use for a job (see "Delegation first"). They send nothing.
- `gateway.py ... mask --brief <file> --out <file> [--terms <file>]` and
  `gateway.py ... unmask --map <task id | file> --in <file> --out <file>`: check the masking locally;
  they send nothing.
- `gateway.py ... list [--last n]` and `gateway.py ... log <id>`: the ledger, never the key or the
  full brief. `gateway.py selftest` checks the guards without any network.
- Options before or after the command: `--timeout <s>` (default 120); `launch --max-brief-kb n`
  (default 200).
Guards refuse before anything is sent (exit 2): a host that is not local unless the project's
CLAUDE.md names it (`--allow-host`); a key variable that is unset, empty or holds whitespace or
control characters; a `.handoff/private-words.txt` that is missing or lists no word, or a brief
holding one of its words or an email address; an empty, non-UTF-8 or oversized brief; an `--out`
that exists or whose folder does not. Redirects are never followed, no proxy is used, and the key
is scrubbed from error text and from the answer. Odd replies fail cleanly (exit 1, class worker).
The guard's limits: it can't see a word split, spaced out or disguised (look-alike letters,
invisible characters); it misses unusual email forms ("name at domain", full-width @); and
`--allow-host` is a convention, not enforced. The brief writer stays responsible for what is sent.
Masking, always on for `launch` (there is no way to send unmasked text): every line of
`.handoff/private-words.txt` (case-insensitive, also inside longer words and across line breaks),
every email address (Unicode letters included, e.g. an accented name or domain), every
secret-shaped string (a private-key header; any name holding secret, password, passwd, token or
key followed by `=` or `:` and a value, such as `SECRET_KEY=`, `apikey=`, `api-key:`; a `Bearer`
token; a URL with `user:password@`; the prefixes `sk-`, `ghp_`, `gho_`, `github_pat_`, `xoxb-`,
`xoxp-`, `AIza`, `AKIA`; a long token-like string) and every line of `--terms` is replaced by an
opaque placeholder such as `⟦a7f3-1⟧`: a random tag per task and a number, one per value. The
type is kept only in the map and the ledger counts, so a placeholder holds no word a list could
hold. The guards then run on the MASKED text, skipping placeholders, so a hit refuses with nothing
sent. The `--model` value is checked the same way (private words, emails, secret shapes) and is
never masked: a hit refuses. The map (placeholder -> real value) is kept only in
`.handoff/gateway/maps/<task id>.json`, never sent or printed. The answer gets the real values
back before `--out` is written; only an exact bracketed placeholder is restored, and a bare
look-alike, an unknown placeholder or a lone bracket is left as it is and listed in the ledger's
`unrestored`. Maps are deleted after 7 days of not being used: each `launch` and `unmask` updates
the last-used time of the map it uses, and each `launch` deletes the maps unused for longer (the
ledger records how many, never their contents); `launch --keep-maps-days N` changes the 7.

Setup: `/startup-team:start-team` (in the Tech Lead) asks once whether to set up the outside
models. On yes it looks for FreeLLMAPI, the default router, on 127.0.0.1:31415 then :3001, guides
the owner to install it and save the key variable themselves, collects the private words, and
writes the project's `# Gateway (outside models)` CLAUDE.md section on the owner's yes. Any other
OpenAI-compatible endpoint works by editing that section; `gateway.py` itself names no router.

### Delegation first (only in a project whose CLAUDE.md has a gateway section)
When the project's CLAUDE.md names the gateway's base URL, key variable and commands, this rule
applies to every main session, sub session, role session, agent, sub-agent, skill and command of
the team: each of them may delegate, and each checks what comes back against the requirement (the
brief, the owner's words, the project's rules) before using it. Questions to the owner and their
answers are never sent. Without that section nothing here changes.
- Your main task, in every main and sub session: DELEGATE and REVIEW. Hand each text-producing
  part of your work to the outside models: drafts of code, copy, plans, test lists, reviews,
  summaries, briefs. Then CHECK each answer against the request and the project's rules, fix or
  redo it yourself when it fails, and PUT THE PARTS TOGETHER. You stay responsible for the result.
- The loop, per part: `gateway.py ... pick --job <type>` prints the model to use, then
  `launch --job <type> --model <picked> ...`, then your check, then ALWAYS
  `review <id> pass|fail [--note <why>]`, also on a fail and before you redo it. Job types:
  `code-draft`, `copy`, `plan`, `test-list`, `review`, `summary`, `brief`, `general`; free text
  only when none fits. `pick` takes, among models with at least 3 reviewed answers for that job,
  the highest pass rate, ties to the fewer tokens; about one pick in five tries a less-tested
  model, and with no data it says `auto` (the router chooses, and the ledger records who answered).
- Write each brief self-contained, since the model sees nothing else: the task, the exact input,
  the rules that apply, the output format.
- Everything identifying is masked before it leaves. Run the `anonymizer` agent on the brief (as a
  sub-agent where the session can; otherwise list the terms yourself, one per line): it lists the
  names, ids, addresses, hosts and other identifying strings the fixed lists won't catch. Pass
  that list with `--terms`, then `launch`; the script masks it, the private words, emails and
  secrets, and restores the real values in the answer. Check any `unrestored` placeholder.
- Limits: a term nobody listed is sent as it is, and distinctive wording (a slogan, a rare
  feature) can still hint at the project. The lists and the anonymizer are a net, not a guarantee.
- Not delegable: reading or writing files, running commands or tests, browsers, pushes, deploys,
  approvals, questions to the owner, and a task whose point is the secret or personal value itself
  (for example "is this password strong").
- A refused or failed launch, or an answer that fails your check twice: do that part yourself and
  say so in your result. The ledger records each launch; add the one-line `model-selection`
  memory entry as for any piece.
- Continuous improvement: at each task close, AI Team Optimization (or the Tech Lead where the
  registry has no `optimization` entry) runs `gateway.py ... scores`. When a job's best model
  changed, it adds ONE line: `team.py memory add --kind learned --for tech-lead --tags
  model-selection,<job> --evidence .handoff/gateway/ledger.jsonl --text "<job>: <model> now best
  (<pass rate>, median <n> tokens)"`. A job whose pass rate over its last 10 reviews
  (`gateway.py ... scores --last 10`) is below 60% is raised to the owner in one line.
- Record line. Every result file, QA record and audit record carries, in its header, one line:
  `GATEWAY: <launch id> <job> pass|fail, ...` for each part sent, or `GATEWAY: none: <reason>`.
  Allowed reasons only: (1) not delegable (see the list above, and code for auth, permissions,
  money or migrations used as is), (2) the gateway refused or was unreachable (give the error
  class), (3) the answer failed the check twice. Size or speed is never a reason: "small",
  "quick", "trivial" or "only a few lines" do not count.
- The auditor fails a record with no `GATEWAY:` line, a reason outside the allowed list, or a
  launch id with no `review` verdict. A launch that failed with no answer (for example a 502 or a
  timeout) is recorded as `<launch id> failed <error class>` and needs no review verdict; the
  auditor accepts this form.
- Main sessions draft their briefs, rule wording and owner-facing summaries through the gateway
  (job `brief`, `copy` or `summary`), check and edit each answer, and use it only after `review`.
- Every existing gate stays: design approval, the plan's green light, QA, the audit, the owner's 1.
- A piece sent whole to the outside models (route DELEGATE) still goes through the `dispatcher`.

Sessions stay on Claude, and every result is reviewed here before it is used; one that fails
review is redone here. Code for auth, permissions, money or migrations is still written and
checked here: an outside draft of it is never used as it is.

## Setup changes (opt-in: straight to the team repo's main)
A setup change is an owner instruction about how the team itself is set up or works: session
names, which sessions start, how sessions talk to each other, rules every session follows. Product
work and project facts (the project's code, copy, design, hosting, data, owner answers about the
product) are never setup changes, and stay in the project.

It applies only when the project's CLAUDE.md has the line `Setup changes: automatic, straight to
main` and names the team repository clone with `TEAM REPO CLONE: <path>`. Every other project uses
the learning loop above, with the owner's 1/0 for each rule.

Flow, per change:
1. **Record.** The Tech Lead (or AI Team Optimization, with `--source optimization`) records it: `team.py memory add --kind setup-change --source tech-lead
   --evidence <turn> --text "<owner's words> -> <the generic rule>"`.
   Then the session that recorded it sends every standing session in `.handoff/team-sessions.json`
   (except itself) a short notice with `SendMessage`: first line `[startup-team:<name>]`, second
   line `RULE: <the rule in one line>`, so running sessions follow it before the plugin update
   reaches them, each after the pre-send check ("Step 12, clears"). A `RULE:` notice is never
   triaged and never a piece; the receiver follows the rule from then on and replies nothing.
2. **Build.** The Developer builds it in the clone named by `TEAM REPO CLONE:`, in generic words
   only, as ONE commit on `main` that also raises the plugin's patch version. The build brief
   carries the line `MEMORY: M####` naming the step-1 setup-change record (more than one allowed,
   comma separated).
3. **QA, then audit.** The audit includes the privacy check: `git show <commit>` (diff and message)
   holds none of the words in the project's `.handoff/private-words.txt` (which must exist) and none
   of what `team.py learn propose` refuses in added lines: a secret, an email, an IP address, a
   local path, the project's name or its web addresses.
4. **Push.** DevOps runs `git pull --ff-only`, then `git push origin <sha>:refs/heads/main` (the
   exact commit, never the moving tip), with no per-change 1 (the CLAUDE.md line is the owner's
   standing approval). Fast-forward only, never a force-push; check with `git ls-remote` after. Then
   it tells the owner in one line, with the commit link. When the project's CLAUDE.md has the line
   `Pushes: only on the owner's command`, this standing push is off: DevOps holds every push (any
   repo) until the owner's own push word, typed to DevOps or quoted verbatim by a main session (a
   quoted word is final: DevOps pushes on it and never asks the owner again). A push
   word the owner types in AI Team Optimization covers the team repository only, never the project.
5. **Rollback.** A bad change is undone with `git revert` on `main`, through the same flow.
A failed QA, audit or privacy check, or a pull that is not a fast-forward, stops the push and goes
to the owner.

**Setup in git.** Every setup customization goes to git. Generic ones (sessions, sub sessions,
agents, sub-agents, skills, commands, hooks, scripts, rules) are defined in the team repo, never
only on one machine. Project ones (CLAUDE.md lines, `.claude/settings.json`, `.htaccess`,
`.handoff/` records minus secrets) get a local commit in the project at every task close, beside the
records commit, holding only the files the task changed (staged by path). Secrets never.

## Setup repair
Applies only where the project's CLAUDE.md has the line `Setup repair: allowed` (the owner's
standing yes). A session that finds a piece of the team setup missing (a standing session the
registry names, a registry entry, a checkpoint, the `.handoff/team-setup-done` marker, the gateway
or team lines in the project's CLAUDE.md, the early-compress environment line, the team plugin
install) recreates it from its last owner-approved version (git history, the `start-team` steps,
the records) and tells the owner in one line what it recreated. Never product code, copy or data;
never a key or secret, and never the contents of `.handoff/private-words.txt` (ask the owner); no
software or plugin the owner has not approved before. A session is still started only on a turn the
owner typed (see Sessions). Without the line: tell the owner what is missing and ask.

## What stays in the project
Brand and design rules, the stack, hosting and deploy steps, standing owner decisions and the
project's own agents live in the project's CLAUDE.md and folders. Where the project's rules and
this file disagree, the project wins.
