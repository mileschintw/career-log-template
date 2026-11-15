#!/usr/bin/env python3
"""Every git step that changes the Log or its remote: pull, commit and push, settle what an earlier
session left (SKILL.md › Commits).

  python3 -I <root>/tools/sync.py pull [--root <root>]            (Windows: py -3 -I ...)
  python3 -I <root>/tools/sync.py commit [--root <root>] [--no-push] [--session <key>] <subject> -- <path>...
  python3 -I <root>/tools/sync.py push [--root <root>]
  python3 -I <root>/tools/sync.py status [--root <root>] [-- <path>...]
  python3 -I <root>/tools/sync.py settle commit [--root <root>] [--no-push] [--session <key>] [--subject <subject>] [-- <path>...]
  python3 -I <root>/tools/sync.py settle discard [--root <root>] [--session <key>] [--sources-checked] [-- <path>...]
  python3 -I <root>/tools/sync.py claim [--root <root>] --session <key> -- <path>...
  python3 -I <root>/tools/sync.py release [--root <root>] --session <key> -- <path>...
  python3 -I <root>/tools/sync.py end [--root <root>] --session <key>

<root> is the Log's root, by default the folder above this script's. The Log's own files are
logfiles.LOG_PATHS (AGENTS.md › Changes); Engine files and the ignored inbox are never settled.

pull: at every mode's start (SKILL.md › Trigger check). With uncommitted Log changes it prints
`pull: skipped (uncommitted Log changes)`: a bulk change waiting for the user's yes stays as it is.
Otherwise `git pull --ff-only`: `pull: up to date`, `pull: ok (<n> new commit(s))`, or `pull: no
remote` with no origin. When origin cannot be reached (no network, a host that does not resolve
or answer) it prints `pull: offline (origin unreachable, working on the local copy)` and ends with
`sync: ok`. An unattended run (CAREER_LOG_UNATTENDED) pulls even with uncommitted Log changes,
which it leaves as they are (scan.md › Schedule), so that its own commit is not pushed from
behind. When the pull fails any other way (it would not fast-forward, the remote refuses the
login), it prints `pull: refused`, git's message indented, and a `next: stop:` line (exit 1).

commit: refuses without a repo-local identity (`git config --local user.email`, SETUP.md step 3),
and on any branch except the default one (when origin says which) and the scan draft branches
(`scan/<name>`); that `next: stop:` line also tells a session in another worktree of this Log not
to push its head to the default branch instead. Then it adds each path by name (a folder adds what
is under it; a deleted file is committed as deleted), commits those paths only, whatever else is
staged, as <subject>, and pushes the branch to origin.
Done when `git status --short -- <path>...` prints nothing and, once pushed, `origin/<branch>..HEAD`
counts 0. It
prints `committed: [<branch> <sha>] <subject>` (or `commit: nothing to commit` when the paths
match HEAD; it still pushes), `pushed: origin/<branch>` (or `push: no remote`), and `sync: ok`.
Sessions (ADR 0014): <key> is the session key tools/check.py printed on its `session:` line at this
session's first Trigger check (logfiles.SESSIONS/<key>/ holds its baseline and claims). Before adding
anything, commit holds each changed Log file among the paths (or under a folder among them) that
another session has claimed, with a `held: <path> (session <other key>)` line, and each one in this
session's baseline (uncommitted when it started, so not its own) with a `held: <path> (uncommitted
when this session started)` line; then a `next: stop:` line, the only place the user is asked whether
another session is still going (on their word that it has ended, `end --session <its key>` releases
its claims), commits nothing and exits 1. Otherwise it claims each changed file it commits and each
file path it names, which stay this session's until it releases them. While another session holds
claims, a commit without --session stops with a `session: none given` line and a `next: stop:` line
naming the flag. --run <run key> (the `run:` key of scan.py run) stands for the session that run
recorded (scan.py run --session), for one release; a run that recorded none stands for no session.
A path neither on disk nor known to git (an optional file the mode names that does not exist) is
left out, with a `skipped: <path>` line; when every path is, it is a usage error. The subject is
the mode's message, or a `commit: <subject>` line another tool printed. --no-push commits and
stops there (`push: held (--no-push)`), for the upgrade mode, whose push waits for the user's yes;
the clean check still runs.

Two sessions in one Log: a git add, commit, restore or rebase that finds `.git/index.lock` (another
session's git step holds the index) tries again, LOCK_TRIES times LOCK_WAIT seconds apart, before it
stops. A push origin refuses as non-fast-forward (another clone pushed first) runs `git pull --rebase
--autostash` once, printing `push: rebased on origin/<branch>`, and pushes again; each uncommitted
file keeps its time on disk. A rebase that fails is undone (`git rebase
--abort`) and the push stops as a refused one does.

push: pushes the commits already on HEAD and not on origin (those a mode that commits nothing left,
SKILL.md › Commits), adding and committing nothing. It refuses on the branches commit refuses, but
needs no identity. It prints `pushed: origin/<branch>` (or `push: no remote`) and `sync: ok`. Done
when it ends with `sync: ok`: with a remote, `origin/<branch>..HEAD` then counts 0.

status: the bulk change as the user reviews it: one `log change: <XY> <path>` line per Log file
(of the paths given, when given) `git status --short` lists (XY as git prints it, `??` for a new
file), then `git diff --stat HEAD` over the same files, and `log changes: none` when there is
nothing.

settle commit: commits every Log change (or only the paths given) as `commit` does, with the subject
`log: changes left uncommitted (<files>)` (the file names, comma-separated, or `<n> files` for more
than three), or --subject for a bulk change's yes; --no-push and --session (or --run) as for commit.
It is how a baseline file is settled, on the user's yes: it holds a file another session has claimed,
not one in this session's baseline, and claims nothing.
settle discard: puts every Log change (or only the paths given) back as HEAD has it, unless a session
(other than --session's) has claimed one: then it holds them as commit does and changes nothing. A changed or
deleted file is restored (`restored: <path>`), a new one deleted (`deleted: <path>`). A new file
under sources/ may be an original an import moved out of sources/inbox/, the user's only copy: while
any is in the set, it changes nothing, prints `new source: <path>` for each and a `next: now,
first:` line, and exits 1. Move each such original back into sources/inbox/ under its old name,
then run it again with --sources-checked to delete the rest. Done when `status` prints `log
changes: none` (for the paths given, when given).

claim: claims each path (a Log file, or a folder of the Log) for the session, before its first edit:
`claimed: <path>` each (`(already)` when it held it). All or none: a path another session has claimed
gets an `owned: <path> (session <other key>)` line and one in this session's baseline a `baseline:
<path> (uncommitted when this session started)` line, then the `next: stop:` line commit's `held:`
lines get; nothing is claimed (exit 1). A claim lasts until the session's Next up (tools/check.py
done --session), its end, or its release. release: hands paths on (a brief's *You own:* line):
`released: <path>`, or `not claimed: <path> (by session <key>)`. end: releases every claim of the
session, printing `released:` lines and `session: <key> ended (...)`: run by a session that closes
without Next up, or for another session on the user's word that it has ended. Neither deletes the
session's record: an idle session keeps its key. Time never releases a claim.

Every run ends with `sync: ok` (exit 0), or with a `next:` line the agent follows (exit 1). Exit 2
on a bad argument. -h or --help prints this text and exits 0. Standard library only, Python 3.11+.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I leaves this folder off sys.path
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles

USAGE = ("usage: sync.py pull | commit [--no-push] [--session <key>] <subject> -- <path>..."
         " | push | status [-- <path>...]"
         " | settle commit [--no-push] [--session <key>] [--subject <subject>] [-- <path>...]"
         " | settle discard [--session <key>] [--sources-checked] [-- <path>...]"
         " | claim --session <key> -- <path>... | release --session <key> -- <path>... | end --session <key>"
         "   (each takes --root <root>; --run <run key> stands for --session for one release)")
SOURCES = "sources/"
UNATTENDED = bool(os.environ.get("CAREER_LOG_UNATTENDED"))
LOCK_TRIES = 10   # another session's git step holds .git/index.lock: try again, LOCK_WAIT seconds apart
LOCK_WAIT = 0.5


class Stop(Exception):
    """A state the agent must take to the user: its lines are printed, then the run exits 1."""

    def __init__(self, *lines):
        super().__init__(lines[-1])
        self.lines = list(lines)


def indented(text):
    return ["  " + line for line in text.strip().splitlines() if line.strip()]


def log_changes(root, paths=None):
    """[(XY, path)] for each Log file (of paths, when given) git lists as changed or new; a staged
    rename is its two paths, the old one deleted (`D `) and the new one added (`A `)."""
    spec = logfiles.LOG_PATHS
    if paths:
        spec = [p for p in paths] + [":(exclude)%s" % p for p in logfiles.NOT_LOG]
    out = logfiles.git(root, "status", "--porcelain", "-z", "--no-renames", "--untracked-files=all", "--",
                       *spec)
    files = [(e[:2], e[3:]) for e in out.split("\0") if len(e) > 3]
    if paths:   # only the Log's own files, whatever was asked for
        logs = set(logfiles.LOG_FILES)
        files = [(s, p) for s, p in files
                 if p in logs or p.split("/")[0] in logfiles.LOG_FOLDERS and not p.startswith(logfiles.INBOX + "/")]
    return files


def git_locked(root, *args, timeout=60):
    """git_run, tried again while another git step holds .git/index.lock (a second session in this Log)."""
    for _ in range(LOCK_TRIES - 1):
        p = logfiles.git_run(root, *args, timeout=timeout)
        if p.returncode == 0 or "index.lock" not in p.stderr:
            return p
        time.sleep(LOCK_WAIT)
    return logfiles.git_run(root, *args, timeout=timeout)


def has_remote(root):
    return logfiles.git_run(root, "remote", "get-url", "origin").returncode == 0


def head(root):
    p = logfiles.git_run(root, "rev-parse", "--verify", "--quiet", "HEAD")
    return p.stdout.strip() if p.returncode == 0 else None


# ---- pull ----

# the cause lines libcurl and ssh print, which git does not translate; anything else stops
UNREACHABLE = ("Could not resolve host", "Failed to connect to", "Connection refused", "Connection timed out",
               "Operation timed out", "Network is unreachable", "No route to host",
               "Temporary failure in name resolution")
REFUSED = ("Permission denied", "Authentication failed", "terminal prompts disabled", "Repository not found",
           "error: 403")


def unreachable(message):
    """Whether git's message says the remote could not be reached at all (not that it refused)."""
    return any(s in message for s in UNREACHABLE) and not any(s in message for s in REFUSED)


def pull(root):
    if log_changes(root) and not UNATTENDED:
        return ["pull: skipped (uncommitted Log changes)"]
    if not has_remote(root):
        return ["pull: no remote"]
    before = head(root)
    p = logfiles.git_run(root, "pull", "--ff-only", timeout=180)
    if p.returncode != 0 and unreachable(p.stderr):
        return ["pull: offline (origin unreachable, working on the local copy)"]
    if p.returncode != 0:
        raise Stop("pull: refused", *indented(p.stderr or p.stdout),
                   "next: stop: show the user git's message above and ask how to go on; pull again"
                   " (this command) once it is settled.")
    after = head(root)
    if before == after:
        return ["pull: up to date"]
    n = logfiles.git(root, "rev-list", "--count", "%s..%s" % (before, after)).strip() if before else "?"
    return ["pull: ok (%s new commit(s))" % n]


# ---- commit ----

def branch(root):
    """(current branch, default branch); the default is set from the remote when origin/HEAD is unset."""
    current = logfiles.git_run(root, "symbolic-ref", "--short", "-q", "HEAD").stdout.strip()
    default = logfiles.default_branch(root)
    if default is None and has_remote(root):
        default = logfiles.set_default_branch(root)
    return current, default


def log_branch(root):
    """(current, default) when HEAD is on a branch Log commits go to: the default one, or a scan draft branch."""
    current, default = branch(root)
    if not current or (default and current != default and not current.startswith("scan/")):
        raise Stop("branch: %s (default: %s)" % (current or "detached HEAD", default or "unknown"),
                   "next: stop: a Log commit goes to the default branch (SKILL.md › Commits): show the"
                   " user this line and ask how to go on. A session in another worktree of this Log never"
                   " pushes its head to the default branch to get round this: the user saves the change"
                   " from a session on the main checkout.")
    return current, default


def known(root, path):
    """Whether git knows path: on disk, in the index or in HEAD (a deleted file)."""
    if os.path.exists(os.path.join(root, path)):
        return True
    return bool(logfiles.git_run(root, "ls-files", "--", path).stdout.strip()
                or logfiles.git_run(root, "ls-tree", "-r", "--name-only", "HEAD", "--", path).stdout.strip())


def known_session(root, session):
    """Stop when a session key names no record in this Log."""
    if logfiles.read_session(root, session) is None:
        raise Stop("session: %s unknown (no record of it in %s/)" % (session, logfiles.SESSIONS),
                   "next: stop: use the key this session's first Trigger check printed on its `session:` line; when"
                   " that is this key, run the Trigger check again with --session %s, which makes its record again,"
                   " then this command. Nothing was changed." % session)


def held(root, paths, session=None, settling=False):
    """Stop when a changed Log file among paths (or under a folder among them), or a file path named, is claimed by
    another session, or, unless settling (`settle commit`, on the user's yes), a changed one is in this session's
    baseline; with no session, stop whenever any session holds claims. Otherwise claim, for session, each changed
    file and each named file (not when settling); the changed files."""
    logfiles.uncommitted(root)   # a baseline entry whose file matches HEAD lapses first
    if session:
        known_session(root, session)
    with logfiles.session_lock(root):
        records = logfiles.sessions(root)
        changed = [p for _, p in log_changes(root, paths)]
        if session is None:
            holding = sorted(k for k, r in records.items() if r["claims"])
            if holding:
                raise Stop("session: none given (%s %s claims in this Log)"
                           % (", ".join("session " + k for k in holding), "holds" if len(holding) == 1 else "hold"),
                           "next: stop: while another session holds claims, a commit names its own session: run this"
                           " command again with --session <key>, <key> the one this session's first Trigger check"
                           " printed on its `session:` line. Nothing was committed.")
            return changed
        mine = records[session]
        named = [p for p in paths if not os.path.isdir(os.path.join(root, p))]   # a file claimed before its first edit is unchanged
        theirs = [(p, k) for p, k in ((p, logfiles.holder(records, p, but=session))
                                      for p in dict.fromkeys(changed + named)) if k]
        base = [] if settling else [p for p in changed if p in mine["baseline"] and p not in dict(theirs)]
        if theirs or base:
            raise Stop(*(["held: %s (session %s)" % t for t in theirs]
                         + ["held: %s (uncommitted when this session started)" % p for p in base]
                         + [stop_line(theirs, base, session)]))
        if not settling:
            mine["claims"] = list(dict.fromkeys(mine["claims"] + changed + named))
            logfiles.write_session(root, session, mine)
        return changed


def stop_line(theirs, base, session):
    """The `next: stop:` line under `held:` (or `owned:`) lines: the only place the user is asked whether another
    session is still going (ADR 0014)."""
    parts = ["next: stop: nothing was changed."]
    if theirs:
        keys = sorted({k for _, k in theirs})
        parts.append("%s %s claimed by session %s: hand the rows to that session to write, or ask the user whether"
                     " session %s is still going; when they say it has ended, `sync.py end --session %s` releases"
                     " its claims, then run this command again."
                     % (", ".join(dict.fromkeys(p for p, _ in theirs)), "is" if len(theirs) == 1 else "are",
                        ", ".join(keys), " or ".join(keys), keys[0] if len(keys) == 1 else "<its key>"))
    if base:
        parts.append("%s had uncommitted changes when this session started, which are not this session's: settle"
                     " %s first as the Trigger check's `next:` line says, on the user's yes (`sync.py settle commit"
                     " --session %s -- <file>`, or `settle discard`), then run this command again."
                     % (", ".join(base), "it" if len(base) == 1 else "them", session))
    parts.append("Or leave the held files out, naming the others after `--`.")
    return " ".join(parts)


def claim(root, session, paths):
    """`claim`: claim each path for session (all or none): refused when another session claimed it (`owned:`) or
    it is in this session's baseline and not yet settled."""
    logfiles.uncommitted(root)   # a settled baseline entry lapses first
    known_session(root, session)
    with logfiles.session_lock(root):
        records = logfiles.sessions(root)
        mine = records[session]
        theirs = [(p, k) for p, k in ((p, logfiles.holder(records, p, but=session)) for p in paths) if k]
        base = [p for p in paths if p in mine["baseline"] and p not in dict(theirs)]
        if theirs or base:
            raise Stop(*(["owned: %s (session %s)" % t for t in theirs]
                         + ["baseline: %s (uncommitted when this session started)" % p for p in base]
                         + [stop_line(theirs, base, session)]))
        out = ["claimed: %s%s" % (p, " (already)" if p in mine["claims"] else "") for p in paths]
        mine["claims"] = list(dict.fromkeys(mine["claims"] + paths))
        logfiles.write_session(root, session, mine)
    return out


def release(root, session, paths=None):
    """`release` (paths) and `end` (None: every claim): the released claims' lines."""
    known_session(root, session)
    gone = logfiles.release_claims(root, session, paths)
    out = ["released: %s" % p for p in gone]
    out += ["not claimed: %s (by session %s)" % (p, session) for p in paths or [] if p not in gone]
    if paths is None:
        out.append("session: %s ended (%s)" % (session, "%d claim(s) released" % len(gone) if gone else "it held no claim"))
    return out


def commit(root, subject, paths, push_too=True, session=None, settling=False):
    held(root, paths, session, settling)
    name, email = logfiles.local_identity(root)
    if not email:
        raise Stop("identity: none (no repo-local git identity)",
                   "next: stop: no repo-local git identity, and the global one may belong to someone"
                   " else: run SETUP.md step 3 with the user, then run this command again.")
    current, default = log_branch(root)
    out = []
    # a path whose deletion is already staged is in neither the tree nor the index: git add refuses it
    adding = [p for p in paths if os.path.exists(os.path.join(root, p))
              or logfiles.git_run(root, "ls-files", "--", p).stdout.strip()]
    staged = git_locked(root, "add", "-A", "--", *adding) if adding else None
    if staged and staged.returncode != 0:
        raise Stop("commit: refused (git add)", *indented(staged.stderr),
                   "next: stop: show the user git's message above and ask how to go on.")
    if logfiles.git_run(root, "diff", "--cached", "--quiet", "HEAD", "--", *paths).returncode == 0:
        out.append("commit: nothing to commit (%s as HEAD has them)" % ", ".join(paths))
    else:
        p = git_locked(root, "commit", "-q", "-m", subject, "--only", "--", *paths)
        if p.returncode != 0:
            raise Stop("commit: refused", *indented(p.stderr or p.stdout),
                       "next: stop: show the user git's message above and ask how to go on.")
        sha = logfiles.git(root, "rev-parse", "--short", "HEAD").strip()
        out.append("committed: [%s %s] %s" % (current, sha, subject))
        logfiles.uncommitted(root)   # each baseline entry this commit settled lapses now, before a later edit
    try:
        out += push(root, current, default) if push_too else ["push: held (--no-push)"]
    except Stop as e:   # the commit line stays in the output: the commit is made
        e.lines[:0] = out
        raise
    left = logfiles.git(root, "status", "--short", "--", *paths)
    if left.strip():
        raise Stop(*(out + ["status: not clean"] + indented(left)
                     + ["next: stop: these paths still differ from the commit: show the user this"
                        " output and ask how to go on."]))
    return out


def push(root, current, default, made=True):
    """Push HEAD to origin/<current>; made: a commit was just made (commit, settle commit), not only push."""
    if not has_remote(root):
        return ["push: no remote (the commit stays in this clone)" if made else "push: no remote (the commits stay in this clone)"]
    args = ["push", "origin", "HEAD:refs/heads/%s" % current]
    if current != default:
        args[1:1] = ["-u"]
    p = logfiles.git_run(root, *args, timeout=180)
    out = []
    if p.returncode != 0 and ("non-fast-forward" in p.stderr or "fetch first" in p.stderr):
        # another clone pushed first: put this branch's commits on top of origin's once, then push again
        # --autostash puts back the uncommitted files with a new time on disk; keep each one's own time
        times = {f: os.stat(os.path.join(root, f)) for f in logfiles.git(root, "diff", "--name-only", "-z", "HEAD").split("\0")
                 if f and os.path.isfile(os.path.join(root, f))}
        r = git_locked(root, "pull", "--rebase", "--autostash", "origin", current, timeout=180)
        if r.returncode == 0:
            out.append("push: rebased on origin/%s" % current)
            p = logfiles.git_run(root, *args, timeout=180)
        else:
            gitdir = logfiles.git(root, "rev-parse", "--absolute-git-dir").strip()
            if any(os.path.isdir(os.path.join(gitdir, d)) for d in ("rebase-merge", "rebase-apply")):
                logfiles.git_run(root, "rebase", "--abort")
            p = r
        for f, st in times.items():
            try:
                os.utime(os.path.join(root, f), ns=(st.st_atime_ns, st.st_mtime_ns))
            except OSError:
                pass
    if p.returncode != 0:
        raise Stop(*out, "push: refused (the commit is made, not pushed)" if made else "push: refused (nothing pushed)",
                   *indented(p.stderr or p.stdout),
                   "next: stop: show the user git's message above and ask how to go on. Never"
                   " force-push: other clones pull with --ff-only.")
    ahead = logfiles.git(root, "rev-list", "--count", "origin/%s..HEAD" % current).strip()
    if ahead != "0":
        raise Stop("push: %s commit(s) still not on origin/%s" % (ahead, current),
                   "next: stop: show the user this line and ask how to go on.")
    return out + ["pushed: origin/%s" % current]


# ---- status and settle ----

def status(root, paths=None):
    files = log_changes(root, paths)
    if not files:
        return ["log changes: none"]
    out = ["log changes: uncommitted (%d file(s))" % len(files)]
    out += ["log change: %s %s" % (s, p) for s, p in files]
    if head(root):
        stat = logfiles.git(root, "diff", "--stat", "HEAD", "--", *[p for _, p in files])
        out += [line.rstrip() for line in stat.splitlines() if line.strip()]
    new = sum(1 for s, _ in files if s == "??")
    if new:
        out.append("(%d new file(s) above are not in the stat: git diff leaves untracked files out)" % new)
    return out


def left_subject(paths):
    names = [os.path.basename(p.rstrip("/")) for p in paths]
    return "log: changes left uncommitted (%s)" % (", ".join(names) if len(names) <= 3 else "%d files" % len(names))


def settle_commit(root, subject, paths, push_too=True, session=None):
    files = [p for _, p in log_changes(root, paths)]
    if not files:
        return ["log changes: none"]
    return commit(root, subject or left_subject(files), files, push_too, session, settling=True)


def settle_discard(root, paths, sources_checked, session=None):
    logfiles.uncommitted(root)   # a baseline entry whose file matches HEAD lapses first
    if session:
        known_session(root, session)
    with logfiles.session_lock(root):   # no session claims a file between the check and the restore
        out = put_back(root, paths, sources_checked, session)
    logfiles.uncommitted(root)   # each baseline entry put back lapses now, before a later edit
    left = log_changes(root, paths)
    if left:
        raise Stop(*(out + ["log change: %s %s" % f for f in left]
                     + ["next: stop: these Log changes are still there: show the user this output and"
                        " ask how to go on."]))
    return out


def put_back(root, paths, sources_checked, session):
    """settle discard's restore and delete, under the session lock; its lines."""
    files = log_changes(root, paths)
    if not files:
        return ["log changes: none"]
    records = logfiles.sessions(root)
    theirs = [(p, k) for p, k in ((p, logfiles.holder(records, p, but=session)) for _, p in files) if k]
    if theirs:   # another session's work: never put back here
        raise Stop(*(["held: %s (session %s)" % t for t in theirs] + [stop_line(theirs, [], session)]))
    new = [p for s, p in files if s == "??" or "A" in s]   # " A": added with intent to add (add -N)
    sources = [p for p in new if p.startswith(SOURCES)]
    if sources and not sources_checked:
        raise Stop(*(["new source: %s" % p for p in sources]
                     + ["next: now, first: a new file under sources/ may be an original an import moved"
                        " out of sources/inbox/, the user's only copy. Move each such original back into"
                        " sources/inbox/ under its old name (when this session did not make that move,"
                        " ask the user about each file above), then run this command again with"
                        " --sources-checked. Nothing was changed."]))
    out = []
    old = [p for _, p in files if p not in new]
    if old:
        p = git_locked(root, "restore", "--source=HEAD", "--staged", "--worktree", "--", *old)
        if p.returncode != 0:
            raise logfiles.LogError("git restore failed: %s" % p.stderr.strip())
        out += ["restored: %s" % p for p in old]
    for p in new:
        logfiles.git_run(root, "rm", "-q", "--cached", "--", p)
        try:
            os.remove(os.path.join(root, p))
        except FileNotFoundError:
            pass
        out.append("deleted: %s" % p)
    return out


# ---- command line ----

def split_paths(args):
    """(the arguments before `--`, the paths after it, with / separators); paths None without `--`."""
    if "--" not in args:
        return args, None
    i = args.index("--")
    return args[:i], [p.replace("\\", "/") for p in args[i + 1:]]


def session_flags(args, flags=("--session", "--run")):
    """({flag: key} for --session and --run, the other arguments) from the arguments before `--`; None on a bad
    key, a flag given twice, or both flags."""
    keys, words, it = {}, [], iter(args)
    for a in it:
        if a in flags:
            value = next(it, None)
            if a in keys or not logfiles.SESSION_KEY.match(value or ""):
                return None
            keys[a] = value
        else:
            words.append(a)
    return (keys, words) if len(keys) < 2 else None


def commit_flags(root, args):
    """(--no-push given, the session the commit runs under (logfiles.commit_session), the other arguments) from the
    arguments before `--`; None on a bad flag."""
    parsed = session_flags(args)
    if parsed is None:
        return None
    keys, words = parsed
    hold = "--no-push" in words
    return hold, logfiles.commit_session(root, keys.get("--session"), keys.get("--run")), [w for w in words if w != "--no-push"]


def file_paths(paths):
    """The Log paths given to claim or release: / separators, no leading `./`; None when one is no Log path."""
    out = [p[2:] if p.startswith("./") else p for p in paths]
    return out if out and all(logfiles.is_log_path(p) for p in out) else None


def run(root, args):
    if not os.path.isdir(os.path.join(root, ".git")) and not os.path.isfile(os.path.join(root, ".git")):
        raise logfiles.LogError("%s is not a git repository's root" % root)
    cmd, rest = args[0], args[1:]
    if cmd == "pull" and not rest:
        return pull(root)
    if cmd == "push" and not rest:
        return push(root, *log_branch(root), made=False)
    if cmd == "status":
        before, paths = split_paths(rest)
        return status(root, paths) if not before and paths != [] else None
    if cmd in ("claim", "release", "end"):
        before, paths = split_paths(rest)
        parsed = session_flags(before, ("--session",))
        if parsed is None or parsed[1] or "--session" not in parsed[0]:
            return None
        session = parsed[0]["--session"]
        if cmd == "end":
            return release(root, session) if paths is None else None
        paths = file_paths(paths or [])
        if paths is None:
            return None
        return claim(root, session, paths) if cmd == "claim" else release(root, session, paths)
    if cmd == "commit":
        before, paths = split_paths(rest)
        flags = commit_flags(root, before)
        if flags is None:
            return None
        hold, session, before = flags
        if len(before) != 1 or not before[0].strip() or not paths:
            return None
        missing = [p for p in paths if not known(root, p)]
        if len(missing) == len(paths):
            raise ValueError("no such file, and none git knows: %s" % ", ".join(missing))
        kept = [p for p in paths if p not in missing]
        return ["skipped: %s (no such file, and none git knows)" % p for p in missing] + commit(root, before[0], kept, not hold, session)
    if cmd == "settle" and rest[:1] in (["commit"], ["discard"]):
        before, paths = split_paths(rest[1:])
        if paths == []:
            return None
        if rest[0] == "commit":
            flags = commit_flags(root, before)
            if flags is None:
                return None
            hold, session, before = flags
            subject = None
            if before[:1] == ["--subject"] and len(before) == 2 and before[1].strip():
                subject, before = before[1], []
            return settle_commit(root, subject, paths, not hold, session) if not before else None
        parsed = session_flags(before, ("--session",))
        if parsed and parsed[1] in ([], ["--sources-checked"]):
            return settle_discard(root, paths, bool(parsed[1]), parsed[0].get("--session"))
    return None


def main(argv):
    logfiles.utf8_stdout()
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.rstrip())
        return 0
    try:
        root, args = logfiles.split_root(argv[1:], __file__)
    except logfiles.LogError as e:
        print("%s: %s" % (USAGE, e))
        return 2
    if not args:
        print(USAGE)
        return 2
    try:
        out = run(root, args)
    except ValueError as e:
        print("%s: %s" % (USAGE, e))
        return 2
    except Stop as e:
        print("\n".join(e.lines))
        return 1
    except logfiles.LogError as e:
        print("FAIL: %s" % e)
        print("next: stop: show the user this line and ask how to go on.")
        return 1
    if out is None:
        print(USAGE)
        return 2
    print("\n".join(out + ["sync: ok"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
