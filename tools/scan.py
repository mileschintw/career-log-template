#!/usr/bin/env python3
"""The mechanical steps of the scan mode (skills/career-log/modes/scan.md).

  python3 -I tools/scan.py name                       (Windows: py -3 -I tools/scan.py ...)
  python3 -I tools/scan.py prune [--dry-run]
  python3 -I tools/scan.py pending
  python3 -I tools/scan.py dedup <postings.jsonl> --out <kept.jsonl>
  python3 -I tools/scan.py screen <dir> --screen-budget <s> --fit-budget <f> [--sort]
  python3 -I tools/scan.py fitmap <url>
  python3 -I tools/scan.py report <rows.jsonl> [--name <name>] [--top <line>] [--body <file>] [--screen <dir>]
  python3 -I tools/scan.py status <url> <status> [--draft <cell>] [--reason <text>]
  python3 -I tools/scan.py cleanup [--dry-run]

Each takes --root <root>, the Log's root (default: the repo this script is in), and --date
YYYY-MM-DD, the day the run counts from (default: today), for tests. A relative path argument is
read from the Log's root. When `origin` exists, name, prune, report and cleanup first run `git fetch
--prune origin`, so a branch deleted from another clone counts as gone; a fetch that fails prints a
`fetch: failed` line and goes on with the branches as last fetched.

URLs: a posting's URL is kept as given (less trailing punctuation). Two URLs are the same posting when
their canonical forms (host without `www.`, port, path without its trailing slash, and the query less
TRACKING parameters; no scheme, no fragment) or their ATS job ids (`greenhouse:123`) match.

Files it reads and writes (SKILL.md › Layout):
- a scan report, `outputs/reports/<YYYY-MM-DD>-scan[-<n>].md` (REPORT_NAME), `-<n>` from 2 on for a
  later run the same day. Its first line is `# Scan <name>`, the next paragraph its top line (sources
  skipped), then `## Pending`, a table with the columns of PENDING_COLUMNS, one row per posting. The
  sections after it are the mode's, and `report --screen` writes two of them: `## Dropped at
  screen` (a table: URL, Company, Role, Reason, Screen key) and `## Screened, not fully fitted` (a
  table: Company, Role, URL, Tier, Rough, Screen key). `## Fit maps` holds one `### ` heading per
  posting fitted, with a `URL: <url>` line, an `Entries commit: <sha>` line, a `Screen: tier <t>,
  rough <touched>/<required>, key <key>` line (the tool adds it) and the requirement map;
- `outputs/reports/scan-declined.jsonl`: one `{"url", "date", "reason"}` object per line, newest
  first;
- draft branches `scan/<YYYY-MM-DD>[-<n>]`, named as the report they belong to. A Draft cell names a
  draft as `scan/<name>:scan-drafts/<folder>`, `.build/scan/<name>/drafts/<folder>` (no remote), or the
  application folder it was saved as;
- a run's folder `.build/scan/<name>/` (`<dir>` below), never committed: `prefiltered.jsonl` (the
  agent's), `screen-list.jsonl`, `not-screened.jsonl`, `postings/<folder>.md` (the captures, the URL
  on the first line), `screen/batch-<i>.todo` (capture paths, one per line), `screen/*.jsonl` (the
  Screen results), `fit.jsonl`, `screened.jsonl` and `dropped.jsonl`.

A Screen result is one JSON object per line: `url`, `gate` (`yes` or `no`), `reason` (on a no: the
constraint and the posting's words), `tier` (the role's rank in direction.md's Target roles, 1 the
first, or null for no tier), `rows` (one object per requirement or duty: `requirement`, `kind`
(`required`, `preferred` or `duty`), `entries` (the file names that touch it, or [])), and an optional
`check` (things to check, a list of strings). A result reused from a report has `touched` and
`required` in place of `rows`. Rough coverage is `<touched>/<required>`: the required and duty rows,
and of them the ones with an entry; when a posting marks no row required or duty, every row counts. The
Screen key is `<list>-<direction>`: the first 8 hex digits of the SHA-256 of `tools/entries.py list`'s
output (each line's `status` and `tokens` left out, so an edit that keeps the rest of an entry's line
keeps the key) and of direction.md's `## Constraints` and `## Target roles, ranked` sections. A result is reused while its
key is the current one.

- `name`: the next free report name today, as `report:`, `branch:`, `worktree:` and `drafts:` lines
  (the worktree and drafts paths under `.build/`), and `remote: yes|no` (whether `origin` exists). A
  name is taken by a scan report, a `scan/*` branch, local or on origin, or a `.build/scan/` folder.
- `prune`: deletes the declined lines and the `scan/*` branches (their worktrees, the local branch
  and the one on `origin`) dated more than PRUNE_DAYS days before --date. One `pruned:` line each.
- `pending`: `report: <path>` for the newest scan report (or `report: none`), then one
  `pending: <url> | <company> | <role> | <status> | <draft>` line per row whose status is in
  PENDING, or `pending: none`.
- `dedup`: reads one posting per line (`url`, `company`, `role`, optional `location`, any other
  fields kept), and drops the applied, declined and repeated ones. Applied means its URL or ATS job
  id is in an `outputs/applications/*/posting.md` or on an `applications.md` line. Failing that, when
  the posting or the record has no job id: an application folder whose name, less its date, is the
  company and then the role (as words), and whose posting text, when it has one, holds the city (the
  location's first part, when given); or an `applications.md` table row with a cell equal to the
  company and one equal to the role. Declined means its URL is in scan-declined.jsonl. A kept posting
  gains `"seen"`: the date of the earliest scan report that lists its URL, or null. Writes the kept
  ones to --out; prints one `dropped: <url> (<why>)` line each, then a `kept:` line with the counts.
- `screen`: refuses when --screen-budget is below --fit-budget. Without --sort, it takes the first
  --screen-budget postings of `<dir>/prefiltered.jsonl` into `screen-list.jsonl` (each with its
  `order`, its `folder`, `<YYYY-MM-DD>-<company>-<role>` from --date with `-2` and on for a repeat,
  and its `capture` path) and the rest into `not-screened.jsonl`; copies in a capture an earlier run
  left in `.build/scan/*/postings/` for the same URL; writes each result reused from a report to
  `screen/reused.jsonl`; and splits the others into `screen/batch-<i>.todo` files of up to BATCH
  capture paths. It prints a `key:` line, one `posting: <url> | capture <path> (have|copied|need) |
  screen (reused <report>|batch-<i>)` line each, and a `screen:` count line. With --sort, every
  posting of the list with a capture must have a result in `screen/*.jsonl` (else it refuses, naming
  the missing ones); one with neither goes to `unreadable.jsonl`. It puts the gate's noes in
  `dropped.jsonl`, sorts the rest by tier (no tier last), then
  rough coverage (the share, highest first; 0/0 counts as 0), then their order in the list, and
  writes the first --fit-budget to `fit.jsonl` and the others to `screened.jsonl`, each posting with
  `tier`, `touched`, `required`, `rough`, `key`, `check` and its `capture`. It prints one `fit: <url>
  | capture <path> (have|need)` line each, then the counts.
- `fitmap`: the newest `## Fit maps` subsection for the URL: `fit map: <report> (entries commit
  <sha>)`, then `fit map: reuse`, or `fit map: stale (<each entry changed since>)`; or `fit map: none`.
- `report`: writes the report --name names (`2026-10-22-2`; default: the next free one, as `name`
  gives it) with its title, the --top line (default `All sources read.`) and the `## Pending`
  table: the rows given (each object has PENDING_COLUMNS' keys: url, company, role, status, draft,
  fit_commit), then the pending rows of the newest report whose URL they lack, carried over. A row
  given whose URL has a pending row with a draft there keeps that row's status, draft and fit map
  commit. A draft whose branch is gone reads `pruned (<branch>)`, and its status `undecided`.
  --body appends a file's sections after the table. With --screen <dir>, the two Screen sections,
  from `dropped.jsonl` and `screened.jsonl`, go right after the body's `## Ranking` section (or after
  the table), and each `## Fit maps` subsection whose URL is in `fit.jsonl` gets this run's `Screen:` line.
- `status`: sets the status (one of STATUSES) of the URL's row in the newest report that lists it,
  and its Draft cell with --draft. `declined` also adds the URL to scan-declined.jsonl, with --reason,
  and for a URL in no Pending table (a posting screened, not fully fitted) does only that.
- `cleanup`: deletes each `scan/*` branch (worktree, local, origin) whose report exists and whose
  every draft, by its row in the newest report that lists it, is accepted or declined. A branch no
  report's row has ever named (drafting stopped before its Draft cells) is kept for prune, and so is
  one git cannot remove (a worktree with uncommitted changes). One `deleted:` or `kept:` line each.

Exit 0 on success, 1 when a step refuses (a report name taken, a URL in no report, a file that does
not parse), 2 on a bad argument. Standard library only, Python 3.11+.
"""
import argparse, datetime, glob, hashlib, json, os, re, shutil, subprocess, sys
from urllib.parse import parse_qsl, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPORTS = "outputs/reports"
DECLINED = REPORTS + "/scan-declined.jsonl"
REPORT_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-scan(?:-(\d+))?\.md$")
BRANCH_NAME = re.compile(r"^scan/(\d{4}-\d{2}-\d{2})(?:-(\d+))?$")
PRUNE_DAYS = 90
PENDING_COLUMNS = [("URL", "url"), ("Company", "company"), ("Role", "role"), ("Status", "status"),
                   ("Draft", "draft"), ("Fit map commit", "fit_commit")]
STATUSES = ("draft to review", "undecided", "accepted", "declined")
PENDING = ("draft to review", "undecided")
URL = re.compile(r"https?://[^\s<>()\[\]|\"'`]+")
TRAILING = ".,;:!?*_~"
# Query parameters that track a click (where it came from), never which posting it is; canonical()
# drops them and every utm_ one, and every other parameter, an unknown ATS's own id included, stays.
TRACKING = {"ref", "refs", "referrer", "source", "src", "gh_src", "lever-source", "lever-origin", "trk",
            "trkinfo", "trackingid", "refid", "gclid", "fbclid", "msclkid", "mc_cid", "mc_eid", "_hsenc",
            "_hsmi", "igshid", "campaign", "medium", "jobsource"}
BATCH = 10
SECTIONS = ("Constraints", "Target roles, ranked")


class ScanError(Exception):
    pass


# ---- URLs ----

def clean(url):
    """A URL as found in text, less the punctuation a sentence or Markdown put after it."""
    return url.strip().rstrip(TRAILING)


def urls(text):
    return [clean(u) for u in URL.findall(text)]


def canonical(url):
    """The form two URLs of one posting share: host without `www.`, a port other than the scheme's
    own, the path without its trailing slash, the query less TRACKING parameters; no scheme, no
    fragment."""
    s = urlsplit(clean(url))
    host = (s.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    try:
        port = s.port
    except ValueError:
        port = None
    if port and port != {"http": 80, "https": 443}.get(s.scheme.lower()):
        host += ":%d" % port
    path = re.sub(r"/+$", "", s.path) or ""
    query = sorted((k.lower(), v) for k, v in parse_qsl(s.query, keep_blank_values=True)
                   if k.lower() not in TRACKING and not k.lower().startswith("utm_"))
    return host + path + ("?" + "&".join("%s=%s" % kv for kv in query) if query else "")


def job_id(url):
    """An ATS's own id for the posting (`greenhouse:123`), or None."""
    s = urlsplit(url.strip())
    host, path = (s.hostname or "").lower(), s.path
    params = {k.lower(): v for k, v in parse_qsl(s.query)}
    if "gh_jid" in params:
        return "greenhouse:" + params["gh_jid"]
    m = re.search(r"greenhouse\.io$", host) and re.search(r"/jobs/(\d+)", path)
    if m:
        return "greenhouse:" + m.group(1)
    m = re.search(r"(?:^|\.)(lever\.co|ashbyhq\.com)$", host) and re.search(r"/([0-9a-f]{8}-[0-9a-f-]{27,})", path, re.I)
    if m:
        return "%s:%s" % (host.split(".")[-2], m.group(1).lower())
    m = host.endswith("myworkdayjobs.com") and re.search(r"_([A-Z]*-?\d[\w-]*)$", path.rstrip("/"))
    if m:
        return "workday:%s:%s" % (host.split(".")[0], m.group(1))
    m = host.endswith("smartrecruiters.com") and re.search(r"/(\d{6,})", path)
    if m:
        return "smartrecruiters:" + m.group(1)
    return None


def keys(url):
    if not clean(url):
        return set()
    k = {canonical(url)}
    jid = job_id(url)
    if jid:
        k.add(jid)
    return k


def norm(text):
    return " " + " ".join(re.sub(r"[^0-9a-z]+", " ", (text or "").lower()).split()) + " "


# ---- Reports ----

def read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def reports(root):
    """[(date, n, path)] of the scan reports, oldest first."""
    out = []
    for p in glob.glob(os.path.join(root, REPORTS, "*-scan*.md")):
        m = REPORT_NAME.match(os.path.basename(p))
        if m:
            out.append((m.group(1), int(m.group(2) or 1), p))
    return sorted(out)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def pending_table(text):
    """(start, end, rows): the line range of the `## Pending` table and its rows as dicts."""
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.strip() == "## Pending"), None)
    if start is None:
        return None, None, []
    i = start + 1
    while i < len(lines) and not lines[i].strip().startswith("|"):
        if lines[i].startswith("#"):
            return None, None, []
        i += 1
    first = i
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        c = cells(lines[i])
        if i >= first + 2 and len(c) == len(PENDING_COLUMNS):
            rows.append({key: value for (_, key), value in zip(PENDING_COLUMNS, c)} | {"_line": i})
        i += 1
    return first, i, rows


def table_lines(rows):
    out = ["| " + " | ".join(h for h, _ in PENDING_COLUMNS) + " |",
           "|" + "---|" * len(PENDING_COLUMNS)]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(k) or "-").replace("|", "/").replace("\n", " ")
                                     for _, k in PENDING_COLUMNS) + " |")
    return out


def newest_rows(root):
    """{canonical url: (report path, row)} from the newest report that lists each URL."""
    out = {}
    for _, _, p in reports(root):
        for r in pending_table(read(p))[2]:
            out[canonical(r["url"])] = (p, r)
    return out


# ---- git ----

def git(root, *args, check=False):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")   # an unattended run never waits on a credential prompt
    try:
        p = subprocess.run(["git", "-C", root] + list(args), capture_output=True, encoding="utf-8", errors="replace",
                           env=env, timeout=120)
    except subprocess.TimeoutExpired:
        raise ScanError("git %s: no answer in 120 s" % " ".join(args))
    if check and p.returncode != 0:
        raise ScanError("git %s: %s" % (" ".join(args), p.stderr.strip()))
    return p


def has_remote(root):
    return git(root, "remote", "get-url", "origin").returncode == 0


def fetch(root):
    """`git fetch --prune origin` when origin exists: [] on success or with no remote, else the
    `fetch: failed` line."""
    if not has_remote(root):
        return []
    try:
        p = git(root, "fetch", "-q", "--prune", "origin")
    except ScanError as e:   # a timeout
        return ["fetch: failed (%s); origin's branches as last fetched" % e]
    if p.returncode == 0:
        return []
    err = (p.stderr.strip().splitlines() or ["exit %d" % p.returncode])[-1]
    return ["fetch: failed (%s); origin's branches as last fetched" % err]


def scan_branches(root):
    """{branch name: (local?, on origin?)} for the scan/* branches git knows."""
    out = {}
    p = git(root, "for-each-ref", "--format=%(refname)", "refs/heads/scan/", "refs/remotes/origin/scan/")
    for ref in p.stdout.split():
        if ref.startswith("refs/heads/"):
            name = ref[len("refs/heads/"):]
            out[name] = (True, out.get(name, (False, False))[1])
        else:
            name = ref[len("refs/remotes/origin/"):]
            out[name] = (out.get(name, (False, False))[0], True)
    return {b: v for b, v in out.items() if BRANCH_NAME.match(b)}


def delete_branch(root, branch, where, dry_run, force=False):
    """Remove the branch's worktree (with uncommitted changes only when force), the local branch and the
    one on origin; one line each."""
    local, remote = where
    out = []
    p = git(root, "worktree", "list", "--porcelain")
    path = None
    for line in p.stdout.split("\n"):
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.strip() == "branch refs/heads/" + branch and path:
            out.append("worktree %s" % path)
            if not dry_run:
                git(root, "worktree", "remove", *(["--force"] if force else []), path, check=True)
    if local:
        out.append("local branch")
        if not dry_run:
            git(root, "branch", "-D", branch, check=True)
    if remote:
        out.append("origin's branch")
        if not dry_run:
            p = git(root, "push", "-q", "origin", "--delete", branch)
            if p.returncode != 0:
                if "remote ref does not exist" not in p.stderr:
                    raise ScanError("git push origin --delete %s: %s" % (branch, p.stderr.strip()))
                git(root, "update-ref", "-d", "refs/remotes/origin/" + branch)   # deleted from another clone
    return out


# ---- Commands ----

def next_name(root, date):
    taken = {(d, n) for d, n, _ in reports(root)}
    for b in scan_branches(root):
        m = BRANCH_NAME.match(b)
        taken.add((m.group(1), int(m.group(2) or 1)))
    for d in glob.glob(os.path.join(root, ".build", "scan", "*")):
        m = BRANCH_NAME.match("scan/" + os.path.basename(d))
        if m and os.path.isdir(d):
            taken.add((m.group(1), int(m.group(2) or 1)))
    n = 1
    while (date, n) in taken:
        n += 1
    return date + ("" if n == 1 else "-%d" % n)


def cmd_name(root, date):
    warn = fetch(root)
    name = next_name(root, date)
    return warn + ["report: %s/%s-scan%s.md" % (REPORTS, date, name[len(date):]),
            "branch: scan/" + name,
            "worktree: .build/worktrees/scan-" + name,
            "drafts: .build/scan/%s/drafts" % name,
            "remote: " + ("yes" if has_remote(root) else "no")]


def read_declined(root):
    p = os.path.join(root, DECLINED)
    if not os.path.exists(p):
        return []
    out = []
    for i, line in enumerate(read(p).split("\n"), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ScanError("%s line %d does not parse: %s" % (DECLINED, i, e))
    return out


def write_declined(root, items):
    p = os.path.join(root, DECLINED)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def cmd_prune(root, date, dry_run):
    cutoff = (datetime.date.fromisoformat(date) - datetime.timedelta(days=PRUNE_DAYS)).isoformat()
    warn = fetch(root)
    out = []
    items = read_declined(root)
    keep = [i for i in items if str(i.get("date", "")) >= cutoff]
    for i in items:
        if i not in keep:
            out.append("pruned: declined %s (%s)" % (i.get("url"), i.get("date")))
    if len(keep) != len(items) and not dry_run:
        write_declined(root, keep)
    for branch, where in sorted(scan_branches(root).items()):
        if BRANCH_NAME.match(branch).group(1) < cutoff:
            out.append("pruned: %s (%s)" % (branch, ", ".join(delete_branch(root, branch, where, dry_run, force=True))))
    out.append("prune: %d line(s) and branch(es) older than %s%s"
               % (len(out), cutoff, " (dry run: nothing deleted)" if dry_run else ""))
    return warn + out


def cmd_pending(root):
    rs = reports(root)
    if not rs:
        return ["report: none", "pending: none"]
    path = rs[-1][2]
    rows = [r for r in pending_table(read(path))[2] if r["status"] in PENDING]
    out = ["report: " + os.path.relpath(path, root).replace(os.sep, "/")]
    out += ["pending: %s | %s | %s | %s | %s" % (r["url"], r["company"], r["role"], r["status"], r["draft"])
            for r in rows] or ["pending: none"]
    return out


def url_keys(text):
    """(keys, has a job id) of every URL in the text."""
    k, jid = set(), False
    for u in urls(text):
        k |= keys(u)
        jid = jid or job_id(u) is not None
    return k, jid


def applied_records(root):
    """[(keys, has a job id, match, where)] for each application folder and each applications.md line;
    match(company, role, city) is the company-and-role fallback (normalised text in, bool out)."""
    out = []
    for d in sorted(glob.glob(os.path.join(root, "outputs", "applications", "*"))):
        if not os.path.isdir(d):
            continue
        posting = os.path.join(d, "posting.md")
        raw = read(posting) if os.path.exists(posting) else ""
        name = norm(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(d)))

        def match(company, role, city, name=name, text=norm(raw) if raw else ""):
            return name == company + role.lstrip() and (not text or not city.strip() or city in text)
        out.append(url_keys(raw) + (match, "outputs/applications/" + os.path.basename(d)))
    apps = os.path.join(root, "applications.md")
    if os.path.exists(apps):
        for i, line in enumerate(read(apps).split("\n"), 1):
            row = {norm(c) for c in cells(line)} if line.strip().startswith("|") else set()

            def match(company, role, city, row=row):
                return company in row and role in row
            out.append(url_keys(line) + (match, "applications.md:%d" % i))
    return out


def seen_dates(root):
    out = {}
    for date, _, p in reports(root):
        for u in urls(read(p)):
            out.setdefault(canonical(u), date)
    return out


def cmd_dedup(root, src, dst):
    postings = []
    for i, line in enumerate(read(src).split("\n"), 1):
        if line.strip():
            try:
                postings.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ScanError("%s line %d does not parse: %s" % (src, i, e))
    applied = applied_records(root)
    declined = {}
    for item in read_declined(root):
        for k in keys(str(item.get("url", ""))):
            declined.setdefault(k, item.get("date"))
    seen = seen_dates(root)
    kept, out, batch = [], [], set()
    for p in postings:
        url = str(p.get("url") or "")
        if not url:
            raise ScanError("%s: a posting without a url: %s" % (src, json.dumps(p, ensure_ascii=False)))
        k = keys(url)
        why = None
        for rk, _, _, where in applied:
            if k & rk:
                why = "applied: %s" % where
                break
        if not why:
            company, role = norm(p.get("company")), norm(p.get("role"))
            city = norm(str(p.get("location") or "").split(",")[0])
            has_id = job_id(url) is not None
            for _, rec_id, match, where in applied:
                if company.strip() and role.strip() and not (has_id and rec_id) and match(company, role, city):
                    why = "applied: %s, by company and role" % where
                    break
        if not why:
            hits = [declined[x] for x in k if x in declined]
            if hits:
                why = "declined %s" % hits[0]
        if not why and k & batch:
            why = "repeated in this batch"
        if why:
            out.append("dropped: %s (%s)" % (url, why))
            continue
        batch |= k
        p["seen"] = seen.get(canonical(url))
        kept.append(p)
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        for p in kept:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    listed = sum(1 for p in kept if p["seen"])
    out.append("kept: %d (%d new, %d listed before); dropped: %d; written to %s"
               % (len(kept), len(kept) - listed, listed, len(postings) - len(kept), dst))
    return out


def fit_maps(text):
    """[(url, sha, body)] of the `### ` subsections under `## Fit maps`."""
    m = re.search(r"^## Fit maps[ \t]*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    out = []
    for part in re.split(r"^### ", m.group(1), flags=re.M)[1:]:
        u = re.search(r"^URL:(.*)$", part, re.M)
        s = re.search(r"^Entries commit:\s*`?([0-9a-f]{4,40})`?", part, re.M)
        found = urls(u.group(1)) if u else []
        if found:
            out.append((found[0], s.group(1) if s else None, part))
    return out


def cmd_fitmap(root, url):
    want = keys(url)
    found = None
    for _, _, p in reports(root):
        for u, sha, body in fit_maps(read(p)):
            if keys(u) & want:
                found = (p, sha, body)
    if not found:
        return ["fit map: none"]
    p, sha, body = found
    rel = os.path.relpath(p, root).replace(os.sep, "/")
    out = ["fit map: %s (entries commit %s)" % (rel, sha or "missing")]
    if not sha or git(root, "cat-file", "-e", sha + "^{commit}").returncode != 0:
        return out + ["fit map: stale (its entries commit is missing or unknown)"]
    names = sorted(set(re.findall(r"\b(\d{4}-\d{2}-[A-Za-z0-9._-]+?\.md)\b", body)))
    changed = []
    for name in names:
        path = "entries/" + name
        p_ = git(root, "log", "--format=%h", sha + "..HEAD", "--", path)
        if p_.stdout.strip() or not os.path.exists(os.path.join(root, path)):
            changed.append(path)
    return out + (["fit map: stale (%s)" % ", ".join(changed)] if changed else ["fit map: reuse"])


# ---- Screen ----

DROPPED_COLUMNS = [("URL", "url"), ("Company", "company"), ("Role", "role"), ("Reason", "reason"), ("Screen key", "key")]
SCREENED_COLUMNS = [("Company", "company"), ("Role", "role"), ("URL", "url"), ("Tier", "tier"), ("Rough", "rough"),
                    ("Screen key", "key")]
SCREEN_LINE = re.compile(r"^Screen:\s*tier\s+(\S+),\s*rough\s+(\d+)/(\d+),\s*key\s+([0-9a-f]{8}-[0-9a-f]{8})\s*$", re.M)


def at_root(root, path):
    return path if os.path.isabs(path) else os.path.join(root, path)


def read_jsonl(path):
    out = []
    for i, line in enumerate(read(path).split("\n"), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ScanError("%s line %d does not parse: %s" % (path, i, e))
    return out


def write_jsonl(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def short_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def screen_key(root):
    """`<list>-<direction>`, as the docstring says."""
    tool = os.path.join(HERE, "entries.py")
    p = subprocess.run([sys.executable, "-I", tool, "list", root], capture_output=True, encoding="utf-8",
                       errors="replace")
    if p.returncode != 0:
        raise ScanError("tools/entries.py list: %s" % (p.stdout + p.stderr).strip())
    listing = "\n".join(re.sub(r"; status [^;]*; tokens \d+(?: \(over threshold\))?;", ";", line)
                        for line in p.stdout.splitlines())
    direction = os.path.join(root, "direction.md")
    text = read(direction).replace("\r\n", "\n") if os.path.exists(direction) else ""
    parts = []
    for name in SECTIONS:
        m = re.search(r"^## %s[ \t]*$(.*?)(?=^## |\Z)" % re.escape(name), text, re.M | re.S)
        parts.append(m.group(1).strip() if m else "")
    return short_hash(listing) + "-" + short_hash("\n\n".join(parts))


def section_table(text, heading):
    """The rows of the first table under `## <heading>`, as lists of cells."""
    m = re.search(r"^## %s[ \t]*$(.*?)(?=^## |\Z)" % re.escape(heading), text, re.M | re.S)
    if not m:
        return []
    rows = [cells(l) for l in m.group(1).split("\n") if l.strip().startswith("|")]
    return rows[2:]


def tier_value(cell):
    cell = str(cell).strip()
    return int(cell) if re.fullmatch(r"\d+", cell) else None


def report_screens(root):
    """{canonical url: (report, result)}: the newest Screen result each report records for a URL."""
    out = {}
    for _, _, p in reports(root):
        text = read(p)
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        found = []
        for c in section_table(text, "Dropped at screen"):
            if len(c) == len(DROPPED_COLUMNS):
                found.append({"url": clean(c[0]), "gate": "no", "reason": c[3], "tier": None, "touched": 0,
                              "required": 0, "key": c[4]})
        for c in section_table(text, "Screened, not fully fitted"):
            m = re.fullmatch(r"(\d+)/(\d+)", c[4]) if len(c) == len(SCREENED_COLUMNS) else None
            if m:
                found.append({"url": clean(c[2]), "gate": "yes", "tier": tier_value(c[3]), "touched": int(m.group(1)),
                              "required": int(m.group(2)), "key": c[5]})
        for u, _, body in fit_maps(text):
            m = SCREEN_LINE.search(body)
            if m:
                found.append({"url": u, "gate": "yes", "tier": tier_value(m.group(1)), "touched": int(m.group(2)),
                              "required": int(m.group(3)), "key": m.group(4)})
        for r in found:
            out[canonical(r["url"])] = (rel, r)
    return out


def slug(text):
    return "-".join(re.sub(r"[^0-9a-z]+", " ", (text or "").lower()).split()) or "posting"


def capture_url(path):
    """The first URL in a capture's first three lines, or None."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            head = "".join(f.readline() for _ in range(3))
    except OSError:
        return None
    found = urls(head)
    return found[0] if found else None


def earlier_captures(root, here):
    """{key: path} of the captures other runs left in .build/scan/*/postings/."""
    out = {}
    for p in sorted(glob.glob(os.path.join(root, ".build", "scan", "*", "postings", "*.md"))):
        if os.path.dirname(os.path.dirname(os.path.abspath(p))) == os.path.abspath(here):
            continue
        u = capture_url(p)
        for k in keys(u) if u else ():
            out[k] = p
    return out


def rough(touched, required):
    return "%d/%d" % (touched, required)


def tally(result):
    """(touched, required) of a Screen result, as the docstring says."""
    if "rows" not in result:
        return int(result.get("touched") or 0), int(result.get("required") or 0)
    rows = result["rows"]
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ScanError("%s: rows must be a list of objects" % result.get("url"))
    counted = [r for r in rows if r.get("kind") in ("required", "duty")] or rows
    return sum(1 for r in counted if any(isinstance(e, str) and e.strip() for e in r.get("entries") or [])), len(counted)


def check_result(r, where):
    found = urls(str(r.get("url") or ""))   # a subagent may copy the capture's whole first line
    if not found:
        raise ScanError("%s: a result without a url: %s" % (where, json.dumps(r, ensure_ascii=False)))
    r["url"] = found[0]
    for row in r.get("rows") or []:
        if not isinstance(row, dict) or row.get("kind") not in ("required", "preferred", "duty") \
                or not isinstance(row.get("entries"), list):
            raise ScanError("%s: %s: each row needs a kind (required, preferred or duty) and an entries list"
                            % (where, r["url"]))
    if r.get("gate") not in ("yes", "no"):
        raise ScanError("%s: %s: gate must be yes or no" % (where, r.get("url")))
    if r["gate"] == "no" and not str(r.get("reason") or "").strip():
        raise ScanError("%s: %s: a gate no needs its reason" % (where, r.get("url")))
    t = r.get("tier")
    if t is not None and (isinstance(t, bool) or not isinstance(t, int) or t < 1):
        raise ScanError("%s: %s: tier must be a whole number from 1, or null" % (where, r.get("url")))
    if r["gate"] == "yes" and "rows" not in r and "touched" not in r:
        raise ScanError("%s: %s: a gate yes needs its rows" % (where, r.get("url")))


def cmd_screen(root, date, d, screen_budget, fit_budget, sort):
    if screen_budget < 1 or fit_budget < 1:
        raise ScanError("--screen-budget and --fit-budget must be 1 or more")
    if screen_budget < fit_budget:
        raise ScanError("screen_budget (%d) is below fit_budget (%d): the user picks which one to change"
                        % (screen_budget, fit_budget))
    d = at_root(root, d)
    return (screen_sort if sort else screen_prepare)(root, date, d, fit_budget if sort else screen_budget)


def screen_prepare(root, date, d, budget):
    postings = read_jsonl(os.path.join(d, "prefiltered.jsonl"))
    key = screen_key(root)
    earlier = earlier_captures(root, d)
    stored = report_screens(root)
    folders, listed = set(), []
    for i, p in enumerate(postings[:budget]):
        if not p.get("url"):
            raise ScanError("prefiltered.jsonl: a posting without a url: %s" % json.dumps(p, ensure_ascii=False))
        base = "%s-%s-%s" % (date, slug(p.get("company")), slug(p.get("role")))
        folder, n = base, 2
        while folder in folders:
            folder, n = "%s-%d" % (base, n), n + 1
        folders.add(folder)
        listed.append(dict(p, order=i + 1, folder=folder,
                           capture=os.path.join(d, "postings", folder + ".md").replace(os.sep, "/")))
    write_jsonl(os.path.join(d, "screen-list.jsonl"), listed)
    write_jsonl(os.path.join(d, "not-screened.jsonl"), postings[budget:])
    sdir = os.path.join(d, "screen")
    os.makedirs(sdir, exist_ok=True)
    for old in glob.glob(os.path.join(sdir, "*.todo")) + glob.glob(os.path.join(sdir, "*.jsonl")):
        os.remove(old)   # results of an earlier prepare may have another key
    with open(os.path.join(sdir, "key"), "w", encoding="utf-8", newline="\n") as f:
        f.write(key + "\n")
    reused, todo, out = [], [], ["key: " + key]
    for p in listed:
        cap = os.path.join(root, p["capture"]) if not os.path.isabs(p["capture"]) else p["capture"]
        state = "have"
        held = keys(capture_url(cap) or "") if os.path.exists(cap) else set()
        if held and not held & keys(p["url"]) and any(held & keys(o["url"]) for o in listed if o is not p):
            os.replace(cap, cap + ".stale")   # another posting's capture, from before the list's order changed
        if not os.path.exists(cap):
            hit = next((earlier[k] for k in keys(p["url"]) if k in earlier), None)
            if hit:
                os.makedirs(os.path.dirname(cap), exist_ok=True)
                shutil.copyfile(hit, cap)
                state = "copied"
            else:
                state = "need"
        s = next((stored[k] for k in [canonical(p["url"])] if k in stored), None)
        if s and s[1]["key"] == key:
            reused.append(dict(s[1], url=p["url"], reused=s[0]))
            how = "reused " + s[0]
        else:
            todo.append(p)
            how = None
        p["_line"] = "posting: %s | capture %s (%s) | screen " % (p["url"], p["capture"], state)
        p["_how"] = how
    write_jsonl(os.path.join(sdir, "reused.jsonl"), reused)
    for b in range(0, len(todo), BATCH):
        name = "batch-%d" % (b // BATCH + 1)
        with open(os.path.join(sdir, name + ".todo"), "w", encoding="utf-8", newline="\n") as f:
            for p in todo[b:b + BATCH]:
                f.write(p["capture"] + "\n")
                p["_how"] = name
    out += [p["_line"] + p["_how"] for p in listed]
    out.append("screen: %d posting(s) listed, %d reused, %d in %d batch(es); %d not screened (past the budget)"
               % (len(listed), len(reused), len(todo), -(-len(todo) // BATCH), len(postings) - len(listed)))
    return out


def screen_sort(root, date, d, budget):
    listed = read_jsonl(os.path.join(d, "screen-list.jsonl"))
    key = screen_key(root)
    kfile = os.path.join(d, "screen", "key")
    if not os.path.exists(kfile) or read(kfile).strip() != key:
        raise ScanError("the entry list or direction.md changed since `screen` without --sort ran (key %s):"
                        " run it again, then screen the batches it prints" % key)
    results = {}
    for path in sorted(glob.glob(os.path.join(d, "screen", "*.jsonl"))):
        for r in read_jsonl(path):
            check_result(r, os.path.basename(path))
            for k in keys(str(r.get("url") or "")):
                results[k] = r
    missing, unreadable, passed, dropped = [], [], [], []
    for p in listed:
        r = next((results[k] for k in keys(p["url"]) if k in results), None)
        if r is None:   # a subagent may give the URL its capture holds
            cap_url = capture_url(at_root(root, p["capture"]))
            r = next((results[k] for k in keys(cap_url or "") if k in results), None)
        if r is None:
            (missing if os.path.exists(at_root(root, p["capture"])) else unreadable).append(p)
            continue
        touched, required = tally(r)
        item = dict(p, gate=r["gate"], reason=r.get("reason") or "", tier=r.get("tier"), touched=touched,
                    required=required, rough=rough(touched, required), key=r.get("key") or key,
                    check=r.get("check") or [], reused=r.get("reused"))
        (passed if r["gate"] == "yes" else dropped).append(item)
    if missing:
        raise ScanError("no Screen result yet for %d posting(s): %s" % (len(missing), ", ".join(p["url"] for p in missing)))

    def order(p):
        share = p["touched"] / p["required"] if p["required"] else 0.0
        return (p["tier"] is None, p["tier"] or 0, -share, p["order"])
    passed.sort(key=order)
    fit, rest = passed[:budget], passed[budget:]
    write_jsonl(os.path.join(d, "fit.jsonl"), fit)
    write_jsonl(os.path.join(d, "screened.jsonl"), rest)
    write_jsonl(os.path.join(d, "dropped.jsonl"), dropped)
    write_jsonl(os.path.join(d, "unreadable.jsonl"), unreadable)
    out = ["fit: %s | capture %s (%s)" % (p["url"], p["capture"],
                                          "have" if os.path.exists(at_root(root, p["capture"])) else "need")
           for p in fit]
    out.append("screen: %d to fit, %d screened, not fully fitted, %d dropped at screen, %d unreadable (no capture)"
               % (len(fit), len(rest), len(dropped), len(unreadable)))
    return out


def md_table(columns, rows):
    out = ["| " + " | ".join(h for h, _ in columns) + " |", "|" + "---|" * len(columns)]
    for r in rows:
        out.append("| " + " | ".join(("-" if r.get(k) in (None, "") else str(r.get(k))).replace("|", "/").replace("\n", " ")
                                     for _, k in columns) + " |")
    return out


def screen_sections(root, d):
    d = at_root(root, d)
    dropped = read_jsonl(os.path.join(d, "dropped.jsonl")) if os.path.exists(os.path.join(d, "dropped.jsonl")) else []
    screened = read_jsonl(os.path.join(d, "screened.jsonl")) if os.path.exists(os.path.join(d, "screened.jsonl")) else []
    out = ["## Dropped at screen", ""]
    out += md_table(DROPPED_COLUMNS, dropped) if dropped else ["None."]
    out += ["", "## Screened, not fully fitted", "",
            "Matched against the entry list (`tools/entries.py list`), not the entries' full text. Saying"
            " \"look at\" one of these runs a full fit on it.", ""]
    out += md_table(SCREENED_COLUMNS, screened) if screened else ["None."]
    return out


def add_screen_lines(body, fitted):
    """The body with this run's `Screen:` line after the `URL:` line of each fit map in fitted, in place
    of any `Screen:` line a reused map brought."""
    by_key = {}
    for p in fitted:
        for k in keys(p["url"]):
            by_key[k] = p
    m = re.search(r"^## Fit maps[ \t]*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    if not m:
        return body
    parts = re.split(r"(?=^### )", m.group(1), flags=re.M)
    for i, part in enumerate(parts):
        u = re.search(r"^URL:(.*)$", part, re.M)
        found = urls(u.group(1)) if u else []
        if not found:
            continue
        p = next((by_key[k] for k in keys(found[0]) if k in by_key), None)
        if p:
            part = re.sub(SCREEN_LINE.pattern + r"\n?", "", part, flags=re.M)
            u = re.search(r"^URL:(.*)$", part, re.M)
            line = "Screen: tier %s, rough %s, key %s" % (p["tier"] if p["tier"] is not None else "-", p["rough"], p["key"])
            parts[i] = part[:u.end()] + "\n" + line + part[u.end():]
    return body[:m.start(1)] + "".join(parts) + body[m.end(1):]


def cmd_report(root, date, src, top, name=None, body=None, screen=None):
    warn = fetch(root)
    rows = []
    for i, r in enumerate(read_jsonl(at_root(root, src)), 1):
        if r.get("status") not in STATUSES:
            raise ScanError("%s line %d: status must be one of %s" % (src, i, ", ".join(STATUSES)))
        r["url"] = clean(str(r.get("url") or ""))
        if not r["url"]:
            raise ScanError("%s line %d: a row without a url" % (src, i))
        rows.append(r)
    rs = reports(root)
    old = [r for r in pending_table(read(rs[-1][2]))[2] if r["status"] in PENDING] if rs else []
    branches = scan_branches(root) if old else {}

    def pruned(r):   # only when origin's branches are known: after a fetch that worked, or with no remote
        m = re.match(r"^(scan/[^:\s]+):", r["draft"])
        if m and not warn and m.group(1) not in branches:
            r["draft"], r["status"] = "pruned (%s)" % m.group(1), "undecided"
        return r
    for r in rows:   # a posting listed again keeps the draft an earlier scan made for it
        prev = next((o for o in old if keys(o["url"]) & keys(r["url"])), None)
        if prev and prev["draft"] not in ("", "-") and not r.get("draft"):
            r["status"], r["draft"], r["fit_commit"] = prev["status"], prev["draft"], prev["fit_commit"]
            pruned(r)
    have = set()
    for r in rows:
        have |= keys(r["url"])
    carried = [pruned(r) for r in old if not keys(r["url"]) & have]
    name = name or next_name(root, date)
    m = re.match(r"^(\d{4}-\d{2}-\d{2})((?:-\d+)?)$", name)
    if not m:
        raise ScanError("--name must be YYYY-MM-DD or YYYY-MM-DD-<n>, as `name` prints it")
    path = os.path.join(root, REPORTS, "%s-scan%s.md" % m.groups())
    if os.path.exists(path):
        raise ScanError("%s exists" % path)
    lines = ["# Scan %s" % name, "", top, "", "## Pending", ""] + table_lines(rows + carried)
    text = read(at_root(root, body)).replace("\r\n", "\n").strip("\n") if body else ""
    if screen:
        d = at_root(root, screen)
        fitted = read_jsonl(os.path.join(d, "fit.jsonl")) if os.path.exists(os.path.join(d, "fit.jsonl")) else []
        text = add_screen_lines(text, fitted)
        ranking = re.search(r"^## Ranking[ \t]*$.*?(?=^## |\Z)", text, re.M | re.S)
        cut = ranking.end() if ranking else 0
        block = "\n".join(screen_sections(root, screen))
        text = (text[:cut].rstrip("\n") + "\n\n" + block + "\n\n" + text[cut:].lstrip("\n")).strip("\n")
    if text:
        lines += [""] + text.split("\n")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return warn + ["wrote %s: %d row(s), %d carried over" % (os.path.relpath(path, root).replace(os.sep, "/"),
                                                            len(rows) + len(carried), len(carried))]


def cmd_status(root, date, url, status, draft, reason):
    if status not in STATUSES:
        raise ScanError("status must be one of %s" % ", ".join(STATUSES))
    want = keys(url)
    hit = None
    for _, _, p in reports(root):
        for r in pending_table(read(p))[2]:
            if keys(r["url"]) & want:
                hit = (p, r)
    if not hit and status == "declined":   # a posting the scan screened but never ranked
        items = [i for i in read_declined(root) if not keys(str(i.get("url", ""))) & want]
        write_declined(root, [{"url": clean(url), "date": date, "reason": reason or ""}] + items)
        return ["%s: in no Pending table" % clean(url), "%s: added %s" % (DECLINED, clean(url))]
    if not hit:
        raise ScanError("%s is in no scan report's Pending table" % url)
    p, r = hit
    lines = read(p).split("\n")
    old = dict(r)
    r["status"] = status
    if draft:
        r["draft"] = draft
    lines[r["_line"]] = table_lines([r])[2]
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    rel = os.path.relpath(p, root).replace(os.sep, "/")
    out = ["%s: %s: %s -> %s%s" % (rel, r["url"], old["status"], status,
                                   "; draft %s -> %s" % (old["draft"], draft) if draft else "")]
    if status == "declined":
        items = [i for i in read_declined(root) if not keys(str(i.get("url", ""))) & want]
        write_declined(root, [{"url": r["url"], "date": date, "reason": reason or ""}] + items)
        out.append("%s: added %s" % (DECLINED, r["url"]))
    return out


def cmd_cleanup(root, dry_run):
    warn = fetch(root)
    rows = newest_rows(root)
    names = {os.path.basename(p) for _, _, p in reports(root)}
    out = []
    for branch, where in sorted(scan_branches(root).items()):
        m = BRANCH_NAME.match(branch)
        report = "%s-scan%s.md" % (m.group(1), "-" + m.group(2) if m.group(2) else "")
        if report not in names:
            out.append("kept: %s (no report %s yet)" % (branch, report))
            continue
        # named by a row of any report (an accepted row's newest cell names its application folder instead)
        urls_named = {canonical(r["url"]) for _, _, p in reports(root) for r in pending_table(read(p))[2]
                      if r["draft"].startswith(branch + ":")}
        named = bool(urls_named)
        # pending: the newest row of each posting the branch drafted, whatever its Draft cell says now
        # (`pruned (...)` after another clone missed the push, say)
        pending = [rows[u][1] for u in urls_named if u in rows and rows[u][1]["status"] not in ("accepted", "declined")]
        if not named:   # drafting has not set its Draft cells yet, or stopped before it did
            out.append("kept: %s (no Draft cell names it; prune deletes it after %d days)" % (branch, PRUNE_DAYS))
        elif pending:
            out.append("kept: %s (%d pending)" % (branch, len(pending)))
        else:
            try:
                done = delete_branch(root, branch, where, dry_run)
            except ScanError as e:   # a worktree with uncommitted changes, say: keep it for the user
                out.append("kept: %s (%s)" % (branch, e))
                continue
            out.append("deleted: %s (%s)%s" % (branch, ", ".join(done), " (dry run: nothing deleted)" if dry_run else ""))
    return warn + (out or ["cleanup: no scan branches"])


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    ap = argparse.ArgumentParser(prog="scan.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("name")
    sp = sub.add_parser("prune")
    sp.add_argument("--dry-run", action="store_true")
    sub.add_parser("pending")
    sp = sub.add_parser("dedup")
    sp.add_argument("postings")
    sp.add_argument("--out", required=True)
    sp = sub.add_parser("screen")
    sp.add_argument("dir")
    sp.add_argument("--screen-budget", type=int, required=True)
    sp.add_argument("--fit-budget", type=int, required=True)
    sp.add_argument("--sort", action="store_true")
    sp = sub.add_parser("fitmap")
    sp.add_argument("url")
    sp = sub.add_parser("report")
    sp.add_argument("rows")
    sp.add_argument("--top", default="All sources read.")
    sp.add_argument("--name")
    sp.add_argument("--body")
    sp.add_argument("--screen")
    sp = sub.add_parser("status")
    sp.add_argument("url")
    sp.add_argument("status")
    sp.add_argument("--draft")
    sp.add_argument("--reason")
    sp = sub.add_parser("cleanup")
    sp.add_argument("--dry-run", action="store_true")
    try:
        a = ap.parse_args(argv)
        datetime.date.fromisoformat(a.date)
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    except ValueError:
        print("scan: --date must be YYYY-MM-DD")
        return 2
    root = a.root
    try:
        if a.cmd == "name":
            lines = cmd_name(root, a.date)
        elif a.cmd == "prune":
            lines = cmd_prune(root, a.date, a.dry_run)
        elif a.cmd == "pending":
            lines = cmd_pending(root)
        elif a.cmd == "dedup":
            lines = cmd_dedup(root, at_root(root, a.postings), at_root(root, a.out))
        elif a.cmd == "screen":
            lines = cmd_screen(root, a.date, a.dir, a.screen_budget, a.fit_budget, a.sort)
        elif a.cmd == "fitmap":
            lines = cmd_fitmap(root, a.url)
        elif a.cmd == "report":
            lines = cmd_report(root, a.date, a.rows, a.top, a.name, a.body, a.screen)
        elif a.cmd == "status":
            lines = cmd_status(root, a.date, a.url, a.status, a.draft, a.reason)
        else:
            lines = cmd_cleanup(root, a.dry_run)
    except (ScanError, OSError) as e:
        print("scan: %s" % e)
        return 1
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
