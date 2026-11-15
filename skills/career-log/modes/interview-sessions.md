# interview: one run across several sessions

How an [interview.md](interview.md) run holds together when it outgrows one session: the user splits it into sessions (one per phase or per part, such as the pack or the talk) and forks side sessions to ask questions without disturbing the main one. Read this file when a session of the run starts or forks another session, when it was started or forked by one, or when it is about to end before the run does.

## The prep file is the run's state

The prep file (`prep-<stage>.md`, [interview.md](interview.md)) is the only place one session hands state to another; chat is not. Each session of the run starts by reading it and running `prep-status`, and goes on from what that prints.

- **Each decision lands at once.** A decision the user makes in any session is a row of the prep file's `## Decisions`, with its source `(user, YYYY-MM-DD)`, written and committed (`python3 -I <root>/tools/sync.py commit "interview(<company>): <stage> decision" -- <prep file>`) before the next question, so that no decision lives only in chat. The session that owns the prep file writes it; any other session hands the row to that owner at once (*One writer per file*). This holds for a decision that overturns an earlier one too: edit that row's value and note the change in its *backup / note* cell.
- **Before a session ends or is compacted**, when the user says they will compact it, leave it, or start another: run `prep-status`, write every decision made in chat that the prep file lacks, set each item's state and where, and commit. Then say so in one line.
- **A finding that changes a recommendation** (a story judged too weak for its question, a fact that turned out wrong) is a Decisions row when the user agreed to it, or a note in the item's *where* file when they have not decided yet, so that no other session recommends what this one ruled out.

## Which checkout

Every session of the run works in the Log's own checkout, on its default branch, where `sync.py commit` commits and pushes. Start each new session there, without a worktree. A session that finds itself in a worktree or on another branch (`sync.py commit` prints a `branch:` line and a `next: stop:` line) follows that line and writes nothing more until the user says how to go on.

## One writer per file

`sync.py commit` commits whole files, so a session that commits a file another session also edited takes that session's changes with it. Each file of the run has one writer at a time, and claims hold to it: the writer is the session that claimed the file ([SKILL.md](../SKILL.md#rules-for-every-mode) › *Commits*).

- The session that starts or forks another names, in the brief, the files the new session owns, and releases each one it holds before giving the brief: `python3 -I <root>/tools/sync.py release --session <session> -- <file>...`. The new session claims them before its first edit; the rest stay with the sessions that own them. The prep file goes with the run's current phase: a session that hands that phase to a new one names the prep file among its files and leaves it alone until the new session ends; a session working beside it (the talk while another builds the pack) hands its decision rows to the prep file's owner as each lands.
- A session that owns a file edits it, commits it itself, and, when it reports to the session that owns the prep file, names the commit (its short hash and subject).
- A session that owns no file (a fork that only asks or advises) writes nothing to the run's files; a fork that needs to change one is given it first, by its owner (who releases it) or the user, and then claims and commits it as above. The line that gives a fork a file also tells it to run the *Trigger check* without `--session` first and to use the key it prints. It ends with the exact rows or lines to add, each with the file and section it goes under, and the user takes them back to the owner, or the session sends them itself when it has tools to message the other session.
- A fork's question that shows a gap in what the user knows (a term or concept they asked about while practising) is one row in the practice log: the owner of the practice log adds it with `python3 -I <root>/tools/application.py practice-add <folder> --stage <stage> --item <the item or sub-item, such as areas/<topic>> --kind question --verdict shaky --weak "<what they asked>" --root <root>`, from the line the fork hands back.
- Before committing, run `git -C <root> status --short`: a changed file this session does not own is left out of the commit. When a claim or commit refuses a file this session must write (`owned:` or `held:`), follow its `next:` line.

## Brief for a new session

When a session starts or forks another for the run, write its brief from this template, fill each line, and give it to the user as one block to paste as the new session's first message (or send it with the session tools when this session has them):

```
Interview run: <company>, <stage>; interview on <date>.
Goal: <what this session does, such as the behavioural leads or the talk's first half>.
Not in this session: <what it leaves to another session, such as rehearsal, or learning the material>.
Read first: <folder>/prep-<stage>.md (run prep-status), then <the pack, notes or pages it works from>.
You own: <each file's path from the Log's root>. Every other file is read-only here; for one of them, hand the rows to add back to the owner.
Checkout: <the Log's root>, default branch, no worktree.
Session: run the Trigger check without --session and use the key it prints; claim the files under You own: before your first edit.
Conversation language: <the config conversation_language: value>. Rehearsal language: <the language the user will answer in>.
Mode start: <the prep file's mode start: value>.
Each decision goes into the prep file's ## Decisions and is committed before the next question.
Ends the run: <yes: run Next up as interview-sessions.md says | no: end by updating the prep file, committing, releasing your claims with python3 -I <root>/tools/sync.py end --session <your session key>, and giving a start prompt for the next session, with no Next up block>.
```

The conversation language is the value on the *Trigger check*'s `config conversation_language:` line, without a trailing ` (default)` (`empty, the language the user writes in` copies as is). The rehearsal language is that of the practice answers and the talk ([SKILL.md](../SKILL.md#rules-for-every-mode) › *Languages*). The mode start is the one in the prep file's header, not the new session's own: it is what the run's one Next up block counts commits from. When the header says `mode start: ?`, the session that owns the prep file first writes into it the `mode start:` value its own first *Trigger check* printed. *Ends the run* is `yes` only for the session that will run the run's last phase. Fill every slot with this run's values: `<the Log's root>` and `<root>` are both the path on your *Trigger check*'s `root:` line, and *You own:* gives each file its path from the Log's root, as *Read first:* does. The one slot left as written is `<your session key>`, for the new session to fill with the key its own *Trigger check* prints. The brief is ready to give when the only `<…>` left in it is `<your session key>`. The brief's *Goal* and *Not in this session* lines bound the new session: it stops at them, even where `prep-status` points to a later phase.

## How each session ends

- **Next up once.** Only the session that finishes the run's last phase (Close the loop, or the phase where the user stops the run) runs Next up, with the prep file's mode start: `python3 -I <root>/tools/check.py done interview --session <session> --since <the prep file's mode start: value>`. Every other session, and every fork, ends without the Next up block, however much of the run it did: it updates the prep file (as above), commits, releases its claims with `python3 -I <root>/tools/sync.py end --session <session>`, and ends with a start prompt for the next session, the brief above filled in, or, for a fork, the lines it hands back.
- A session that handles one task while the run goes on (a recruiter email, a question) ends the same way: no Next up block.

## New recruiter mail

New mail from the recruiter goes to a session that has the application folder loaded: the one that owns the prep file, or a new session that reads the prep file first. It saves the mail into the folder's `recruiter/` as Intake does (`application.py intake`), adds a row for anything the mail asks for, and updates the logistics as the Plan phase says.
