#!/usr/bin/env python3
"""Tests for tools/scan.py, on Logs made in a temporary directory (a git repo with a bare origin).

  python3 -I tools/tests/test_scan.py
"""
import importlib.util, io, json, os, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout

sys.dont_write_bytecode = True   # the tool loaded below leaves no tools/__pycache__
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "scan.py")
spec = importlib.util.spec_from_file_location("scan", TOOL)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)

TODAY = "2026-10-22"
# The Screen key of test_screen_key_is_the_one_earlier_releases_wrote's Log, as scan.py wrote it before #300
SCREEN_KEY = "7d767673-b87970d6"
REPORT = """# Scan {name}

All sources read.

## Pending

| URL | Company | Role | Status | Draft | Fit map commit |
|---|---|---|---|---|---|
{rows}

## Ranking

1. something
"""


def git(root, *args):
    return subprocess.run(["git", "-C", root] + list(args), capture_output=True, encoding="utf-8", check=True).stdout


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.root = os.path.join(self.tmp, "log")
        self.remote = os.path.join(self.tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remote], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", self.root], check=True)
        git(self.root, "config", "user.email", "t@example.invalid")
        git(self.root, "config", "user.name", "T")
        git(self.root, "config", "commit.gpgsign", "false")
        self.write("README.md", "# log\n")
        self.commit("seed")
        git(self.root, "remote", "add", "origin", self.remote)
        git(self.root, "push", "-q", "-u", "origin", "main")

    # ---- helpers ----

    def write(self, rel, text):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return p

    def read(self, rel):
        with open(os.path.join(self.root, rel), encoding="utf-8") as f:
            return f.read()

    def commit(self, msg):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", msg)
        return git(self.root, "rev-parse", "--short", "HEAD").strip()

    def run_tool(self, *args, date=TODAY):
        out = io.StringIO()
        with redirect_stdout(out):
            code = scan.main(["--root", self.root, "--date", date] + list(args))
        return code, out.getvalue().splitlines()

    def report(self, name, rows):
        date = name[:10]
        suffix = name[10:]
        return self.write("outputs/reports/%s-scan%s.md" % (date, suffix),
                          REPORT.format(name=name, rows="\n".join("| " + " | ".join(r) + " |" for r in rows)))

    def branch(self, name, push=True):
        git(self.root, "branch", name)
        if push:
            git(self.root, "push", "-q", "origin", name)

    def lines(self, path):
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f]

    def jsonl(self, rel, items):
        return self.write(rel, "".join(json.dumps(i) + "\n" for i in items))

    # ---- URLs ----

    def test_canonical_drops_tracking_keeps_ids(self):
        self.assertEqual(scan.canonical("https://www.Example.com/jobs/1/?utm_source=x#top"), "example.com/jobs/1")
        self.assertEqual(scan.canonical("https://acme.com/careers?gh_jid=42&ref=y"), "acme.com/careers?gh_jid=42")

    def test_job_ids(self):
        self.assertEqual(scan.job_id("https://boards.greenhouse.io/acme/jobs/123?x=1"), "greenhouse:123")
        self.assertEqual(scan.job_id("https://acme.com/careers?gh_jid=123"), "greenhouse:123")
        uid = "0f1e2d3c-4b5a-6978-8a9b-0c1d2e3f4a5b"
        self.assertEqual(scan.job_id("https://jobs.lever.co/acme/%s/apply" % uid), "lever:" + uid)
        self.assertEqual(scan.job_id("https://jobs.ashbyhq.com/acme/%s" % uid), "ashbyhq:" + uid)
        self.assertEqual(scan.job_id("https://acme.wd5.myworkdayjobs.com/en-US/ext/job/NY/Engineer_R12345"),
                         "workday:acme:R12345")
        self.assertIsNone(scan.job_id("https://example.com/about"))

    # ---- name ----

    def test_name_first_and_next(self):
        code, lines = self.run_tool("name")
        self.assertEqual(code, 0)
        self.assertEqual(lines, ["name: 2026-10-22", "report: outputs/reports/2026-10-22-scan.md", "branch: scan/2026-10-22",
                                 "worktree: .build/worktrees/scan-2026-10-22", "drafts: .build/scan/2026-10-22/drafts",
                                 "dir: .build/scan/2026-10-22", "remote: yes"])
        self.report("2026-10-22", [])
        self.assertEqual(self.run_tool("name")[1][:2], ["name: 2026-10-22-2", "report: outputs/reports/2026-10-22-scan-2.md"])
        self.branch("scan/2026-10-22-2")
        self.assertEqual(self.run_tool("name")[1][2], "branch: scan/2026-10-22-3")

    def test_name_without_remote(self):
        git(self.root, "remote", "remove", "origin")
        self.assertEqual(self.run_tool("name")[1][-1], "remote: no")

    # ---- dedup ----

    def test_dedup(self):
        self.write("outputs/applications/2026-09-01-acme-backend-engineer/posting.md",
                   "URL: https://boards.greenhouse.io/acme/jobs/111\n\nBackend Engineer, New York, NY\n")
        self.write("outputs/applications/2026-09-02-globex-data-engineer/posting.md",
                   "URL: https://globex.com/careers/7\n\nData Engineer\nLocation: Austin, TX\n")
        self.write("applications.md", "| 2026-08-01 | Initech | Platform Engineer | applied on site |\n"
                                      "| 2026-08-02 | Hooli | SRE | https://hooli.com/jobs/9 |\n")
        self.jsonl("outputs/reports/scan-declined.jsonl", [{"url": "https://umbrella.com/jobs/5", "date": "2026-10-01", "reason": ""}])
        self.report("2026-10-15", [["https://stark.com/jobs/3", "Stark", "ML Engineer", "undecided", "-", "-"]])
        src = self.jsonl("in.jsonl", [
            {"url": "https://acme.com/careers?gh_jid=111", "company": "Acme", "role": "Backend Engineer"},   # job id
            {"url": "https://hooli.com/jobs/9/?utm_source=list", "company": "Hooli", "role": "SRE"},       # URL
            {"url": "https://initech.com/j/1", "company": "Initech", "role": "Platform Engineer"},          # company + role
            {"url": "https://globex.com/j/2", "company": "Globex", "role": "Data Engineer", "location": "Austin, TX"},
            {"url": "https://globex.com/j/3", "company": "Globex", "role": "Data Engineer", "location": "Springfield, IL"},
            {"url": "https://umbrella.com/jobs/5", "company": "Umbrella", "role": "SWE"},                   # declined
            {"url": "https://stark.com/jobs/3", "company": "Stark", "role": "ML Engineer"},                 # seen
            {"url": "https://wayne.com/jobs/1", "company": "Wayne", "role": "SWE"},                         # new
            {"url": "https://www.wayne.com/jobs/1#apply", "company": "Wayne", "role": "SWE"},               # repeated
        ])
        out = os.path.join(self.tmp, "kept.jsonl")
        code, lines = self.run_tool("dedup", src, "--out", out)
        self.assertEqual(code, 0, lines)
        dropped = [l for l in lines if l.startswith("dropped:")]
        self.assertEqual(len(dropped), 6, lines)
        self.assertIn("applied: outputs/applications/2026-09-01-acme-backend-engineer", dropped[0])
        self.assertIn("applied: applications.md:2", dropped[1])
        self.assertIn("applied: applications.md:1, by company and role", dropped[2])
        self.assertIn("2026-09-02-globex-data-engineer, by company and role", dropped[3])
        self.assertIn("declined 2026-10-01", dropped[4])
        self.assertIn("repeated in this batch", dropped[5])
        with open(out, encoding="utf-8") as f:
            kept = [json.loads(l) for l in f]
        self.assertEqual([k["url"] for k in kept], ["https://globex.com/j/3", "https://stark.com/jobs/3", "https://wayne.com/jobs/1"])
        self.assertEqual([k["seen"] for k in kept], [None, "2026-10-15", None])
        self.assertEqual(lines[-2], "kept: 3 (2 new, 1 listed before); dropped: 6; written to %s" % out)
        self.assertEqual(lines[-1], "dropped by reason: before the window 0, applied 4, declined 1, repeated 1")

    # ---- report, pending, status ----

    def test_report_carries_pending_and_marks_pruned(self):
        self.branch("scan/2026-10-20")
        self.report("2026-10-20", [
            ["https://a.com/1", "A", "SWE", "draft to review", "scan/2026-10-20:a-swe", "abc1234"],
            ["https://b.com/2", "B", "SWE", "accepted", "outputs/applications/2026-10-21-b-swe/", "abc1234"],
            ["https://c.com/3", "C", "SWE", "draft to review", "scan/2026-10-19:c-swe", "abc1234"],
            ["https://d.com/4", "D", "SWE", "undecided", "-", "abc1234"],
        ])
        rows = self.jsonl("rows.jsonl", [
            {"url": "https://d.com/4", "company": "D", "role": "SWE", "status": "draft to review",
             "draft": "scan/2026-10-22:d-swe", "fit_commit": "def5678"},
            {"url": "https://e.com/5", "company": "E", "role": "SWE", "status": "undecided", "draft": "", "fit_commit": "def5678"},
        ])
        code, lines = self.run_tool("report", rows, "--top", "Skipped: Board X (login expired).")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["wrote outputs/reports/2026-10-22-scan.md: 4 row(s), 2 carried over",
                                 "wrote: outputs/dashboard/dashboard.html", "artifact: none", "commit: scan(2026-10-22): 2 postings"])
        text = self.read("outputs/reports/2026-10-22-scan.md")
        self.assertTrue(text.startswith("# Scan 2026-10-22\n\nSkipped: Board X (login expired).\n\n## Pending\n\n"
                                        "| URL | Company | Role | Status | Draft | Fit map commit |\n"))
        self.assertIn("| https://d.com/4 | D | SWE | draft to review | scan/2026-10-22:d-swe | def5678 |", text)
        self.assertIn("| https://e.com/5 | E | SWE | undecided | - | def5678 |", text)
        self.assertIn("| https://a.com/1 | A | SWE | draft to review | scan/2026-10-20:a-swe | abc1234 |", text)
        self.assertIn("| https://c.com/3 | C | SWE | undecided | pruned (scan/2026-10-19) | abc1234 |", text)
        self.assertNotIn("b.com", text)
        self.assertNotIn("score", text.lower())
        code, lines = self.run_tool("pending")
        self.assertEqual(lines[0], "report: outputs/reports/2026-10-22-scan.md")
        self.assertEqual(len(lines), 6)
        self.assertEqual(lines[-1], "count: 4 pending row(s)")
        self.assertEqual(self.run_tool("report", rows)[1][0], "wrote outputs/reports/2026-10-22-scan-2.md: 4 row(s), 2 carried over")
        self.assertEqual(self.run_tool("report", rows, "--name", "2026-10-22-2")[0], 1)   # taken
        self.assertEqual(self.run_tool("report", rows, "--name", "2026-10-22-5")[1][0][:42],
                         "wrote outputs/reports/2026-10-22-scan-5.md")
        self.assertEqual(self.run_tool("report", rows, "--name", "today")[0], 1)

    def test_report_rejects_a_bad_status(self):
        rows = self.jsonl("rows.jsonl", [{"url": "https://e.com/5", "company": "E", "role": "SWE", "status": "maybe"}])
        self.assertEqual(self.run_tool("report", rows)[0], 1)

    def test_pending_none(self):
        self.assertEqual(self.run_tool("pending")[1], ["report: none", "pending: none"])
        self.report("2026-10-20", [["https://b.com/2", "B", "SWE", "accepted", "x", "-"]])
        self.assertEqual(self.run_tool("pending")[1][1], "pending: none")

    def test_status_accept_and_decline(self):
        self.report("2026-10-20", [["https://a.com/1", "A", "SWE", "undecided", "-", "-"]])
        self.report("2026-10-21", [["https://a.com/1", "A", "SWE", "draft to review", "scan/2026-10-21:a-swe", "-"],
                                   ["https://b.com/2", "B", "SWE", "undecided", "-", "-"]])
        code, lines = self.run_tool("status", "https://a.com/1/", "accepted", "--draft", "outputs/applications/2026-10-22-a-swe/")
        self.assertEqual(code, 0, lines)
        self.assertIn("| https://a.com/1 | A | SWE | accepted | outputs/applications/2026-10-22-a-swe/ | - |",
                      self.read("outputs/reports/2026-10-21-scan.md"))
        self.assertIn("| undecided |", self.read("outputs/reports/2026-10-20-scan.md"))   # an older report is left as it was
        self.jsonl("outputs/reports/scan-declined.jsonl", [{"url": "https://z.com/9", "date": "2026-10-01", "reason": ""}])
        code, lines = self.run_tool("status", "https://b.com/2", "declined", "--reason", "on-site only")
        self.assertEqual(code, 0, lines)
        first = json.loads(self.read("outputs/reports/scan-declined.jsonl").split("\n")[0])
        self.assertEqual(first, {"url": "https://b.com/2", "date": TODAY, "reason": "on-site only"})
        self.assertTrue(self.read("outputs/reports/2026-10-21-scan.md").endswith("1. something\n"))
        self.assertEqual(self.run_tool("status", "https://nowhere.com/1", "accepted")[0], 1)
        code, lines = self.run_tool("status", "https://screened.com/1", "declined")   # screened, never ranked
        self.assertEqual(lines[:3], ["https://screened.com/1: in no Pending table", "%s: added https://screened.com/1" % scan.DECLINED,
                                     "wrote: outputs/dashboard/dashboard.html"])
        self.assertEqual(self.run_tool("status", "https://b.com/2", "maybe")[0], 1)

    # ---- prune, cleanup ----

    def test_prune_at_90_days(self):
        self.jsonl("outputs/reports/scan-declined.jsonl", [
            {"url": "https://new.com/1", "date": "2026-10-01", "reason": ""},
            {"url": "https://edge.com/1", "date": "2026-07-24", "reason": ""},   # exactly 90 days: kept
            {"url": "https://old.com/1", "date": "2026-07-23", "reason": "x"},
        ])
        self.branch("scan/2026-07-23")
        self.branch("scan/2026-07-24")
        wt = os.path.join(self.tmp, "wt")
        git(self.root, "worktree", "add", "-q", wt, "scan/2026-07-23")
        code, lines = self.run_tool("prune", "--dry-run")
        self.assertEqual(code, 0, lines)
        self.assertIn("old.com", self.read("outputs/reports/scan-declined.jsonl"))
        code, lines = self.run_tool("prune")
        self.assertEqual(code, 0, lines)
        self.assertIn("pruned: declined https://old.com/1 (2026-07-23)", lines)
        self.assertTrue(any(l.startswith("pruned: scan/2026-07-23 (worktree ") for l in lines), lines)
        text = self.read("outputs/reports/scan-declined.jsonl")
        self.assertNotIn("old.com", text)
        self.assertIn("edge.com", text)
        self.assertEqual(sorted(scan.scan_branches(self.root)), ["scan/2026-07-24"])
        self.assertNotIn("scan/2026-07-23", git(self.remote, "branch"))
        self.assertFalse(os.path.exists(wt))

    def test_cleanup(self):
        self.branch("scan/2026-10-20")
        self.branch("scan/2026-10-21")
        self.branch("scan/2026-10-22")   # its report is not written yet
        self.report("2026-10-20", [["https://a.com/1", "A", "SWE", "draft to review", "scan/2026-10-20:a", "-"]])
        self.report("2026-10-21", [["https://a.com/1", "A", "SWE", "declined", "scan/2026-10-20:a", "-"],
                                   ["https://b.com/2", "B", "SWE", "draft to review", "scan/2026-10-21:b", "-"]])
        code, lines = self.run_tool("cleanup")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["deleted: scan/2026-10-20 (local branch, origin's branch)",
                                 "kept: scan/2026-10-21 (1 pending)",
                                 "kept: scan/2026-10-22 (no report 2026-10-22-scan.md yet)"])
        self.assertEqual(sorted(scan.scan_branches(self.root)), ["scan/2026-10-21", "scan/2026-10-22"])

    # ---- fitmap ----

    def test_fitmap_reuse_and_stale(self):
        self.write("entries/2025-01-widget.md", "# widget\n")
        self.write("entries/2025-02-gadget.md", "# gadget\n")
        sha = self.commit("entries")
        body = ("# Scan 2026-10-20\n\nAll sources read.\n\n## Pending\n\n| URL | Company | Role | Status | Draft | Fit map commit |\n"
                "|---|---|---|---|---|---|\n\n## Fit maps\n\n### A — SWE\n\nURL: https://a.com/1\nEntries commit: %s\n\n"
                "| Requirement | Written by | Own work | Category | Entry |\n|---|---|---|---|---|\n"
                "| Go | user | | covered | `2025-01-widget.md` |\n" % sha)
        self.write("outputs/reports/2026-10-20-scan.md", body)
        self.commit("report")
        self.assertEqual(self.run_tool("fitmap", "https://a.com/1")[1],
                         ["fit map: outputs/reports/2026-10-20-scan.md (entries commit %s)" % sha, "fit map: reuse"])
        self.write("entries/2025-02-gadget.md", "# gadget changed\n")
        self.commit("other entry")
        self.assertEqual(self.run_tool("fitmap", "https://a.com/1")[1][1], "fit map: reuse")
        self.write("entries/2025-01-widget.md", "# widget changed\n")
        self.commit("cited entry")
        self.assertEqual(self.run_tool("fitmap", "https://a.com/1")[1][1], "fit map: stale (entries/2025-01-widget.md)")
        self.assertEqual(self.run_tool("fitmap", "https://b.com/1")[1], ["fit map: none"])

    # ---- review fixes (round 1) ----

    def test_canonical_keeps_port_scheme_free_and_unknown_ids(self):
        self.assertEqual(scan.canonical("http://127.0.0.1:8765/initech/jobs/2"), "127.0.0.1:8765/initech/jobs/2")
        self.assertEqual(scan.canonical("https://acme.com:443/j/1"), "acme.com/j/1")
        self.assertNotEqual(scan.canonical("https://acme.taleo.net/careersection/jobdetail.ftl?job=111"),
                            scan.canonical("https://acme.taleo.net/careersection/jobdetail.ftl?job=222"))
        self.assertEqual(scan.urls("see https://acme.com/jobs/1. And **https://b.com/2**, then"),
                         ["https://acme.com/jobs/1", "https://b.com/2"])

    def test_report_keeps_the_url_as_given(self):
        rows = self.jsonl("rows.jsonl", [{"url": "http://127.0.0.1:8765/initech/jobs/2?utm_source=x", "company": "I",
                                          "role": "SWE", "status": "undecided", "draft": "", "fit_commit": "abc1234"}])
        self.assertEqual(self.run_tool("report", rows)[0], 0)
        self.assertIn("| http://127.0.0.1:8765/initech/jobs/2?utm_source=x | I |", self.read("outputs/reports/2026-10-22-scan.md"))
        self.assertEqual(self.run_tool("pending")[1][1],
                         "pending: http://127.0.0.1:8765/initech/jobs/2?utm_source=x | I | SWE | undecided | - | fit map none")

    def test_report_keeps_a_relisted_draft(self):
        self.branch("scan/2026-10-20")
        self.report("2026-10-20", [["https://a.com/1", "A", "SWE", "draft to review", "scan/2026-10-20:scan-drafts/a", "abc1234"]])
        rows = self.jsonl("rows.jsonl", [{"url": "https://www.a.com/1/", "company": "A", "role": "SWE", "status": "undecided",
                                          "draft": "", "fit_commit": "def5678"}])
        code, lines = self.run_tool("report", rows)
        self.assertEqual(lines[0], "wrote outputs/reports/2026-10-22-scan.md: 1 row(s), 0 carried over")
        self.assertIn("| https://www.a.com/1/ | A | SWE | draft to review | scan/2026-10-20:scan-drafts/a | abc1234 |",
                      self.read("outputs/reports/2026-10-22-scan.md"))
        self.assertEqual(self.run_tool("cleanup")[1], ["kept: scan/2026-10-20 (1 pending)"])

    def other_clone(self):
        other = os.path.join(self.tmp, "other")
        subprocess.run(["git", "clone", "-q", self.remote, other], check=True)
        return other

    def test_a_branch_deleted_from_another_clone(self):
        self.branch("scan/2026-07-01")
        self.branch("scan/2026-10-20")
        self.report("2026-10-20", [["https://a.com/1", "A", "SWE", "declined", "scan/2026-10-20:scan-drafts/a", "-"]])
        other = self.other_clone()
        git(other, "push", "-q", "origin", "--delete", "scan/2026-07-01", "scan/2026-10-20")
        code, lines = self.run_tool("prune")
        self.assertEqual(code, 0, lines)
        self.assertIn("pruned: scan/2026-07-01 (local branch)", lines)
        code, lines = self.run_tool("cleanup")
        self.assertEqual((code, lines), (0, ["deleted: scan/2026-10-20 (local branch)"]))

    def test_origin_ref_gone_without_a_fetch(self):
        self.branch("scan/2026-10-20")
        self.report("2026-10-20", [["https://a.com/1", "A", "SWE", "declined", "scan/2026-10-20:scan-drafts/a", "-"]])
        git(self.remote, "branch", "-D", "scan/2026-10-20")   # origin lost it; this clone's ref is stale
        lines = scan.delete_branch(self.root, "scan/2026-10-20", (True, True), False)
        self.assertEqual(lines, ["local branch", "origin's branch"])
        self.assertEqual(scan.scan_branches(self.root), {})

    def test_name_sees_another_clones_push(self):
        other = self.other_clone()
        git(other, "branch", "scan/2026-10-22")
        git(other, "push", "-q", "origin", "scan/2026-10-22")
        self.assertEqual(self.run_tool("name")[1][2], "branch: scan/2026-10-22-2")
        os.makedirs(os.path.join(self.root, ".build", "scan", "2026-10-22-2"))
        self.assertEqual(self.run_tool("name")[1][2], "branch: scan/2026-10-22-3")

    def test_dedup_company_and_role_needs_the_whole_role(self):
        self.write("outputs/applications/2026-09-01-acme-senior-software-engineer/posting.md", "Senior Software Engineer\n")
        self.write("outputs/applications/2026-09-02-hooli-sre/posting.md",
                   "URL: https://boards.greenhouse.io/hooli/jobs/1\n\nSRE\n")
        self.write("applications.md", "| 2026-08-01 | Initech | Software Engineer | applied on site | x |\n"
                                      "Met Globex and Software Engineer folks at a fair\n")
        src = self.jsonl("in.jsonl", [
            {"url": "https://acme.com/j/1", "company": "Acme", "role": "Software Engineer"},             # not senior
            {"url": "https://boards.greenhouse.io/hooli/jobs/2", "company": "Hooli", "role": "SRE"},     # both have ids
            {"url": "https://globex.com/j/1", "company": "Globex", "role": "Software Engineer"},         # prose line
            {"url": "https://initech.com/j/9", "company": "Initech", "role": "Software Engineer"},       # table row
            {"url": "https://acme.com/j/2", "company": "Acme", "role": "Senior Software Engineer"},      # folder
        ])
        code, lines = self.run_tool("dedup", src, "--out", os.path.join(self.tmp, "kept.jsonl"))
        dropped = [l for l in lines if l.startswith("dropped:")]
        self.assertEqual(dropped, ["dropped: https://initech.com/j/9 (applied: applications.md:1, by company and role)",
                                   "dropped: https://acme.com/j/2 (applied: outputs/applications/"
                                   "2026-09-01-acme-senior-software-engineer, by company and role)"])

    # ---- screen ----

    DIRECTION = "# Direction\n\n## Target roles, ranked\n\n1. Backend\n\n## Constraints\n\n- US only\n\n## Writing preferences\n\nshort\n"

    def screen_log(self, n=5, direction=None):
        self.write("entries/2025-01-widget.md", "# Widget\n")
        self.write("direction.md", direction or self.DIRECTION)
        self.commit("entries")
        d = os.path.join(self.root, ".build", "scan", TODAY)
        self.jsonl(".build/scan/%s/prefiltered.jsonl" % TODAY,
                   [{"url": "https://c%d.com/j/%d" % (i, i), "company": "C%d" % i, "role": "SWE", "source": "list"}
                    for i in range(n)] + [{"url": "https://c9.com/j/9", "company": "C0", "role": "SWE", "source": "list"}])
        return d

    def result(self, d, name, items):
        self.jsonl(os.path.relpath(os.path.join(d, "screen", name), self.root), items)

    def rows(self, required, touched):
        return [{"requirement": "r%d" % i, "kind": "required", "entries": ["2025-01-widget.md"] if i < touched else [],
                 "skill": "S%d" % i} for i in range(required)] + [{"requirement": "nice", "kind": "preferred", "entries": [],
                                                                   "skill": "Nice"}]

    def test_screen_budgets_must_hold_the_fit(self):
        d = self.screen_log()
        code, lines = self.run_tool("screen", d, "--screen-budget", "3", "--fit-budget", "4")
        self.assertEqual(code, 1)
        self.assertIn("screen_budget (3) is below fit_budget (4)", lines[0])

    def test_screen_prepare_sort_and_report(self):
        two = self.DIRECTION.replace("1. Backend\n", "1. Backend\n2. Data\n")   # c0's tier 2
        d = self.screen_log(5, two)
        code, lines = self.run_tool("screen", d, "--screen-budget", "5", "--fit-budget", "2")
        self.assertEqual(code, 0, lines)
        self.assertRegex(lines[0], r"^key: [0-9a-f]{8}-[0-9a-f]{8}$")
        self.assertTrue(lines[1].startswith("posting: https://c0.com/j/0 | capture "), lines[1])
        self.assertTrue(lines[1].endswith("postings/2026-10-22-c0-swe.md (need) | screen batch-1"), lines[1])
        self.assertEqual(lines[-1], "screen: 5 posting(s) listed, 0 reused, 5 in 1 batch(es); 1 not screened (past the budget)")
        listed = self.lines(os.path.join(d, "screen-list.jsonl"))
        self.assertEqual([p["folder"] for p in listed][:1], ["2026-10-22-c0-swe"])
        with open(os.path.join(d, "screen", "batch-1.todo"), encoding="utf-8") as f:
            self.assertEqual(len(f.read().split()), 5)
        for p in self.lines(os.path.join(d, "screen-list.jsonl"))[:4]:   # c4's page could not be read
            self.write(p["capture"], "URL: %s\n\ntext\n" % p["url"])
        code, lines = self.run_tool("screen", d, "--screen-budget", "5", "--fit-budget", "2", "--sort")
        self.assertEqual(code, 1)   # no results yet
        self.assertIn("no Screen result yet for 4 posting(s)", lines[0])
        self.result(d, "batch-1.jsonl", [
            {"url": "https://c0.com/j/0", "gate": "yes", "tier": 2, "rows": self.rows(4, 4)},
            {"url": "https://c1.com/j/1", "gate": "yes", "tier": 1, "rows": self.rows(4, 1)},
            {"url": "https://c2.com/j/2", "gate": "yes", "tier": 1, "rows": self.rows(4, 3)},
            {"url": "https://c3.com/j/3", "gate": "no", "reason": "US only: \"London office\""},
            {"url": "https://c4.com/j/4", "gate": "yes", "tier": None, "rows": self.rows(2, 2)},
        ])
        code, lines = self.run_tool("screen", d, "--screen-budget", "5", "--fit-budget", "2", "--sort")
        self.assertEqual(code, 0, lines)
        self.assertEqual([l.split(" | ")[0] for l in lines[:-1]], ["fit: https://c2.com/j/2", "fit: https://c1.com/j/1"])
        self.assertEqual(lines[-1], "screen: 2 to fit, 2 screened, not fully fitted, 1 dropped at screen, 0 unreadable (no capture)")
        fit = self.lines(os.path.join(d, "fit.jsonl"))
        self.assertEqual(fit[0]["rough"], "3/4")
        # the report places the Screen sections and the Screen lines
        body = self.write("body.md", "## Ranking\n\n1. C2\n2. C1\n\n## Not fitted\n\n1 past the budget\n\n## Fit maps\n\n"
                                     "### C2 — SWE\n\nURL: https://c2.com/j/2\nEntries commit: abc1234\n\n| map |\n")
        rows = self.jsonl("rows.jsonl", [{"url": "https://c2.com/j/2", "company": "C2", "role": "SWE", "status": "undecided"}])
        code, lines = self.run_tool("report", rows, "--name", TODAY, "--body", body, "--screen", d)
        self.assertEqual(code, 0, lines)
        text = self.read("outputs/reports/2026-10-22-scan.md")
        order = [text.index(h) for h in ("## Pending", "## Ranking", "## Dropped at screen", "## Screened, not fully fitted",
                                         "## Not fitted", "## Fit maps")]
        self.assertEqual(order, sorted(order))
        self.assertIn("| https://c3.com/j/3 | C3 | SWE | US only: \"London office\" |", text)
        self.assertIn("| C0 | SWE | https://c0.com/j/0 | 2 | 4/4 |", text)
        self.assertIn("| C4 | SWE | https://c4.com/j/4 | - | 2/2 |", text)
        self.assertRegex(text, r"URL: https://c2.com/j/2\nScreen: tier 1, rough 3/4, key [0-9a-f]{8}-[0-9a-f]{8}\nEntries commit")
        self.commit("report")
        # the next run reuses every result while the key holds, and a direction change makes them stale
        os.rename(d, d + "-old")
        d = self.screen_log(5, two)
        self.write(".build/scan/%s-old/postings/2026-10-22-c0-swe.md" % TODAY, "URL: https://c0.com/j/0\n\ntext\n")
        code, lines = self.run_tool("screen", d, "--screen-budget", "5", "--fit-budget", "2")
        self.assertEqual(lines[-1], "screen: 5 posting(s) listed, 4 reused, 1 in 1 batch(es); 1 not screened (past the budget)")
        self.assertTrue(lines[1].endswith("(copied) | screen reused outputs/reports/2026-10-22-scan.md"), lines[1])
        self.assertTrue(lines[2].endswith("screen batch-1"), lines[2])   # C1 was fitted, not reused: no Screen line
        self.write("direction.md", self.DIRECTION.replace("US only", "US or Canada"))
        code, lines = self.run_tool("screen", d, "--screen-budget", "5", "--fit-budget", "2")
        self.assertIn("0 reused, 5 in 1 batch(es)", lines[-1])

    def test_screen_disambiguates_folders(self):
        d = self.screen_log(1)
        self.run_tool("screen", d, "--screen-budget", "2", "--fit-budget", "1")
        listed = self.lines(os.path.join(d, "screen-list.jsonl"))
        self.assertEqual([p["folder"] for p in listed], ["2026-10-22-c0-swe", "2026-10-22-c0-swe-2"])

    def test_screen_key_ignores_token_counts(self):
        self.write("entries/2025-01-widget.md", "# Widget\n")
        self.write("direction.md", self.DIRECTION)
        key = scan.screen_key(self.root)
        self.write("entries/2025-01-widget.md", "# Widget\n\nA much longer body that changes the token count.\n")
        self.assertEqual(scan.screen_key(self.root), key)
        self.write("direction.md", self.DIRECTION.replace("short", "longer"))   # another section
        self.assertEqual(scan.screen_key(self.root), key)

    # ---- review fixes (round 2) ----

    def test_cleanup_keeps_a_branch_no_draft_cell_names(self):
        self.branch("scan/2026-10-20")
        self.report("2026-10-20", [["https://a.com/1", "A", "SWE", "undecided", "-", "-"]])
        wt = os.path.join(self.tmp, "wt")
        git(self.root, "worktree", "add", "-q", wt, "scan/2026-10-20")
        with open(os.path.join(wt, "draft.tex"), "w") as f:
            f.write("uncommitted\n")
        code, lines = self.run_tool("cleanup")
        self.assertEqual(lines, ["kept: scan/2026-10-20 (no Draft cell names it; prune deletes it after 90 days)"])
        self.assertTrue(os.path.exists(os.path.join(wt, "draft.tex")))

    def test_cleanup_deletes_a_branch_whose_draft_was_accepted(self):
        self.branch("scan/2026-10-20")
        self.report("2026-10-20", [["https://a.com/1", "A", "SWE", "draft to review", "scan/2026-10-20:scan-drafts/a", "-"]])
        self.report("2026-10-21", [["https://a.com/1", "A", "SWE", "draft to review", "scan/2026-10-20:scan-drafts/a", "-"]])
        self.assertEqual(self.run_tool("status", "https://a.com/1", "accepted", "--draft", "outputs/applications/2026-10-22-a-swe/")[0], 0)
        self.assertEqual(self.run_tool("cleanup")[1], ["deleted: scan/2026-10-20 (local branch, origin's branch)"])

    def test_cleanup_keeps_a_branch_whose_row_reads_pruned(self):
        self.branch("scan/2026-10-20", push=False)   # its push failed; another clone marked the row pruned
        self.report("2026-10-20", [["https://a.com/1", "A", "SWE", "draft to review", "scan/2026-10-20:scan-drafts/a", "-"]])
        self.report("2026-10-21", [["https://a.com/1", "A", "SWE", "undecided", "pruned (scan/2026-10-20)", "-"]])
        self.assertEqual(self.run_tool("cleanup")[1], ["kept: scan/2026-10-20 (1 pending)"])

    def test_report_after_a_failed_fetch_keeps_drafts(self):
        self.report("2026-10-20", [["https://a.com/1", "A", "SWE", "draft to review", "scan/2026-10-20:scan-drafts/a", "-"]])
        git(self.root, "remote", "set-url", "origin", os.path.join(self.tmp, "gone.git"))   # offline
        rows = self.jsonl("rows.jsonl", [{"url": "https://e.com/5", "company": "E", "role": "SWE", "status": "undecided"}])
        code, lines = self.run_tool("report", rows)
        self.assertTrue(lines[0].startswith("fetch: failed"), lines)
        self.assertIn("| https://a.com/1 | A | SWE | draft to review | scan/2026-10-20:scan-drafts/a | - |",
                      self.read("outputs/reports/2026-10-22-scan.md"))

    def test_screen_sort_refuses_a_changed_key_and_checks_results(self):
        d = self.screen_log(1)
        self.run_tool("screen", d, "--screen-budget", "2", "--fit-budget", "1")
        for p in self.lines(os.path.join(d, "screen-list.jsonl")):
            self.write(p["capture"], "URL: %s\n\ntext\n" % p["url"])
        self.result(d, "batch-1.jsonl", [
            {"url": "URL: https://c0.com/j/0", "gate": "yes", "tier": 1, "rows": self.rows(2, 1)},   # the whole first line
            {"url": "https://c9.com/j/9", "gate": "yes", "tier": 1, "rows": [{"requirement": "x", "kind": "Required", "entries": "none"}]},
        ])
        code, lines = self.run_tool("screen", d, "--screen-budget", "2", "--fit-budget", "1", "--sort")
        self.assertEqual(code, 1)
        self.assertIn("https://c9.com/j/9: each row needs a kind", lines[0])
        self.result(d, "batch-1.jsonl", [
            {"url": "URL: https://c0.com/j/0", "gate": "yes", "tier": 1, "rows": self.rows(2, 1)},
            {"url": "https://c9.com/j/9", "gate": "no", "reason": "x"},
        ])
        self.assertEqual(self.run_tool("screen", d, "--screen-budget", "2", "--fit-budget", "1", "--sort")[0], 0)
        self.write("direction.md", self.DIRECTION.replace("US only", "US or Canada"))
        code, lines = self.run_tool("screen", d, "--screen-budget", "2", "--fit-budget", "1", "--sort")
        self.assertEqual(code, 1)
        self.assertIn("changed since", lines[0])
        self.assertEqual(self.run_tool("screen", d, "--screen-budget", "0", "--fit-budget", "0")[0], 1)

    def test_screen_drops_another_postings_capture(self):
        d = self.screen_log(1)
        cap = os.path.join(d, "postings", "2026-10-22-c0-swe.md")
        self.write(os.path.relpath(cap, self.root), "URL: https://c9.com/j/9\n\nc9's text\n")   # the other listed posting's
        code, lines = self.run_tool("screen", d, "--screen-budget", "2", "--fit-budget", "1")
        self.assertTrue(lines[1].endswith("(need) | screen batch-1"), lines[1])
        self.assertTrue(os.path.exists(cap + ".stale"))
        self.write(os.path.relpath(cap, self.root), "# Title\nURL: https://ats.example.com/c0/123\n\ntext\n")   # a resolved URL
        code, lines = self.run_tool("screen", d, "--screen-budget", "2", "--fit-budget", "1")
        self.assertTrue(lines[1].endswith("(have) | screen batch-1"), lines[1])

    def test_cleanup_goes_on_past_a_dirty_worktree(self):
        for b in ("scan/2026-10-19", "scan/2026-10-20"):
            self.branch(b)
        self.report("2026-10-19", [["https://a.com/1", "A", "SWE", "declined", "scan/2026-10-19:scan-drafts/a", "-"]])
        self.report("2026-10-20", [["https://b.com/1", "B", "SWE", "declined", "scan/2026-10-20:scan-drafts/b", "-"]])
        wt = os.path.join(self.tmp, "wt")
        git(self.root, "worktree", "add", "-q", wt, "scan/2026-10-19")
        with open(os.path.join(wt, "draft.tex"), "w") as f:
            f.write("uncommitted\n")
        code, lines = self.run_tool("cleanup")
        self.assertEqual(code, 0)
        self.assertTrue(lines[0].startswith("kept: scan/2026-10-19 (git worktree remove"), lines)
        self.assertEqual(lines[1], "deleted: scan/2026-10-20 (local branch, origin's branch)")

    def test_fit_map_url_in_markdown(self):
        self.write("outputs/reports/2026-10-20-scan.md", "# Scan 2026-10-20\n\n## Fit maps\n\n### A — SWE\n\n"
                                                         "URL: <https://a.com/1>\nEntries commit: abc1234\n")
        self.assertEqual(self.run_tool("fitmap", "https://a.com/1")[1][0],
                         "fit map: outputs/reports/2026-10-20-scan.md (entries commit abc1234)")

    def test_screen_key_changes_with_the_list_and_the_direction(self):
        self.write("entries/2025-01-widget.md", "# Widget\n")
        self.write("direction.md", self.DIRECTION)
        key = scan.screen_key(self.root)
        self.write("direction.md", self.DIRECTION.replace("1. Backend", "1. Platform"))
        self.assertNotEqual(scan.screen_key(self.root)[9:], key[9:])
        self.write("entries/2025-02-gadget.md", "# Gadget\n")
        self.assertNotEqual(scan.screen_key(self.root)[:8], key[:8])

    # ---- collect and filter (#300) ----

    def test_name_checks_the_budgets_first(self):
        code, lines = self.run_tool("name", "--screen-budget", "3", "--fit-budget", "4")
        self.assertEqual(code, 1)
        self.assertIn("screen_budget (3) is below fit_budget (4): the user picks which one to change", lines[0])
        self.assertEqual(self.run_tool("name", "--screen-budget", "3")[0], 2)
        code, lines = self.run_tool("name", "--screen-budget", "4", "--fit-budget", "4")
        self.assertEqual((code, lines[0]), (0, "name: 2026-10-22"))

    def test_root_after_the_subcommand(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = scan.main(["--date", TODAY, "name", "--root", self.root])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("dir: .build/scan/2026-10-22", out.getvalue().splitlines())

    def test_a_relative_root(self):
        here = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, here)
        self.write("page.txt", "text\n")
        self.write(".build/scan/x/fetched.jsonl", json.dumps({"url": "https://a.example/1"}) + "\n")
        out = io.StringIO()
        with redirect_stdout(out):
            code = scan.main(["capture", "--root", "log", ".build/scan/x/postings/a.md", "https://a.example/1", "page.txt"])
        self.assertEqual(code, 0, out.getvalue())
        self.assertTrue(os.path.exists(os.path.join(self.root, ".build", "scan", "x", "postings", "a.md")))

    def test_sources(self):
        self.assertEqual(self.run_tool("sources")[1], ["sources: none (no scan-sources.md)"])
        self.write("scan-sources.md", "# Sources\n\n<!-- one section each -->\n")
        self.assertEqual(self.run_tool("sources")[1], ["sources: none (no ## section)"])
        self.write("scan-sources.md", "# Sources\n\n## Jobs list\n- URL: https://github.com/o/jobs\n- Kind: GitHub list\n"
                                      "- Read: README.md, the table\n- Fields: GAP: not read yet\n\n"
                                      "## Board\n- URL: https://board.example/search\n- Kind: job site\n")
        self.assertEqual(self.run_tool("sources")[1], [
            "source: Jobs list | kind GitHub list | url https://github.com/o/jobs | read set | fields GAP"
            " | clone .build/scan-sources/jobs-list",
            "source: Board | kind unknown (job site) | url https://board.example/search | read GAP | fields GAP",
            "sources: 2"])
        self.write("scan-sources.md", "## A\n- URL: https://a.example\n- Kind: GAP: ask\n\n## A\n- URL: https://b.example\n")
        self.assertEqual(self.run_tool("sources")[1][:2], ["source: A | kind GAP | url https://a.example | read GAP | fields GAP",
                                                          "source: A | kind GAP | url https://b.example | read GAP | fields GAP"])

    def test_sources_clone_folder_needs_no_quoting(self):
        gh = "- URL: https://github.com/o/l\n- Kind: GitHub list\n\n"
        self.write("scan-sources.md", "## Fake jobs list\n" + gh + "## 職缺列表\n" + gh + "## Jobs: new!\n" + gh
                   + "## jobs-new\n" + gh + "## Board\n- URL: https://board.example\n- Kind: public job board\n")
        lines = self.run_tool("sources")[1]
        clones = [l.split(" | clone ")[1] for l in lines[:4]]
        self.assertEqual(clones[0], ".build/scan-sources/fake-jobs-list")
        self.assertEqual(clones[1], ".build/scan-sources/" + scan.short_hash("職缺列表"))
        self.assertEqual(clones[2:], [".build/scan-sources/jobs-new-" + scan.short_hash(n) for n in ("Jobs: new!", "jobs-new")])
        for c in clones:
            self.assertRegex(c, r"^[0-9a-z./-]+$")
        self.assertNotIn(" | clone ", lines[4])
        self.assertTrue(lines[4].endswith(" | session scan-board"), lines[4])

    def test_sources_board_session_needs_no_quoting(self):
        board = "- URL: https://board.example\n- Kind: %s\n\n"
        self.write("scan-sources.md", "## Fake job board\n" + board % "public job board" + "## 求職網\n" + board % "signed-in job board"
                   + "## Jobs: new!\n" + board % "public job board" + "## jobs-new\n" + board % "signed-in job board"
                   + "## Odd\n" + board % "job site" + "## Unset\n" + board % "GAP: ask")
        lines = self.run_tool("sources")[1]
        sessions = [l.split(" | session ")[1] for l in lines[:4]]
        self.assertEqual(sessions, ["scan-fake-job-board", "scan-" + scan.short_hash("求職網")]
                         + ["scan-jobs-new-" + scan.short_hash(n) for n in ("Jobs: new!", "jobs-new")])
        for s in sessions:
            self.assertRegex(s, r"^scan-[0-9a-z-]+$")
        for l in lines[4:6]:   # a kind unknown or unset names no session
            self.assertNotIn(" | session ", l)

    # ---- exploratory query run (#570) ----

    EXPLORE_SOURCES = ("# Sources\n\n## Board\n- URL: https://board.example/jobs\n- Kind: public job board\n"
                       "- Query: https://board.example/search?q={query}&days=7\n\n"
                       "## List\n- URL: https://github.com/o/l\n- Kind: GitHub list\n- Read: README.md\n\n"
                       "## Odd\n- URL: https://odd.example\n- Kind: public job board\n- Query: https://odd.example/search\n\n"
                       "## Later\n- URL: https://later.example\n- Kind: signed-in job board\n- Query: GAP: not found yet\n\n"
                       "## Repo\n- URL: https://github.com/o/r\n- Kind: GitHub list\n- Query: the rows of README.md that hold {query}\n")

    def explore(self, query="Fintech  backend", date=TODAY):
        code, lines = self.run_tool("explore", query, date=date)
        self.assertEqual(code, 0, lines)
        return next(l[len("dir: "):] for l in lines if l.startswith("dir: ")), lines

    def test_explore_names_the_sources_it_reads_and_skips(self):
        self.write("scan-sources.md", self.EXPLORE_SOURCES)
        d, lines = self.explore()
        self.assertEqual(d, ".build/scan/explore-fintech-backend-" + scan.short_hash("fintech backend"))
        self.assertEqual(lines, [
            "query: Fintech  backend",
            "name: " + d.split("/")[-1],
            "dir: " + d,
            "read: Board | https://board.example/search?q=Fintech%20backend&days=7",
            "skip: List (no Query: line)",
            "skip: Odd (its Query: line has no {query})",
            "skip: Later (no Query: line)",
            "read: Repo | the rows of README.md that hold Fintech backend",
            "sources: 2 read with the query, 3 skipped",
            "reuse: none (the first run of this query)",
            "records: none (an exploratory run writes no scan report, declined line, seen date, draft or branch)"])
        self.assertEqual(json.loads(self.read(d + "/explore.json")), {"query": "Fintech  backend"})
        self.assertEqual(self.explore("fintech backend")[0], d)   # the same query, in other letters: the same run
        self.assertNotEqual(self.explore("fintech frontend")[0], d)
        d, lines = self.explore("金融科技 後端")   # no ASCII letters: the hash names it
        self.assertEqual(d, ".build/scan/explore-" + scan.short_hash("金融科技 後端"))
        self.assertIn("read: Board | https://board.example/search?q=%E9%87%91%E8%9E%8D%E7%A7%91%E6%8A%80%20%E5%BE%8C%E7%AB%AF"
                      "&days=7", lines)
        self.assertIn("read: Repo | the rows of README.md that hold 金融科技 後端", lines)

    def test_explore_refuses_with_no_source_to_query(self):
        self.assertEqual(self.run_tool("explore", "fintech"), (1, ["scan: explore: no source to read (no scan-sources.md)"]))
        self.write("scan-sources.md", "## List\n- URL: https://github.com/o/l\n- Kind: GitHub list\n")
        code, lines = self.run_tool("explore", "fintech")
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["scan: explore: no source has a Query: line with {query}; nothing written",
                                 "skip: List (no Query: line)"])
        self.assertFalse(os.path.exists(os.path.join(self.root, ".build")))
        self.assertEqual(self.run_tool("explore", "  ")[0], 1)

    def test_explore_dedup_keeps_applied_and_declined(self):
        self.write("scan-sources.md", self.EXPLORE_SOURCES)
        d = self.explore()[0]
        self.write("outputs/applications/2026-09-01-acme-backend-engineer/posting.md",
                   "URL: https://boards.greenhouse.io/acme/jobs/111\n\nBackend Engineer\n")
        self.jsonl("outputs/reports/scan-declined.jsonl", [{"url": "https://umbrella.com/jobs/5", "date": "2026-10-01", "reason": ""}])
        self.report("2026-10-15", [["https://stark.com/jobs/3", "Stark", "ML Engineer", "undecided", "-", "-"]])
        self.jsonl(d + "/collected.jsonl", [
            {"url": "https://acme.com/careers?gh_jid=111", "company": "Acme", "role": "Backend Engineer", "posted": TODAY},
            {"url": "https://umbrella.com/jobs/5", "company": "Umbrella", "role": "SWE", "posted": TODAY},
            {"url": "https://stark.com/jobs/3", "company": "Stark", "role": "ML Engineer", "posted": TODAY},
            {"url": "https://www.stark.com/jobs/3#apply", "company": "Stark", "role": "ML Engineer", "posted": TODAY},
            {"url": "https://old.com/jobs/1", "company": "Old", "role": "SWE", "posted": "2026-09-01"}])
        code, lines = self.run_tool("dedup", d + "/collected.jsonl", "--out", d + "/kept.jsonl", "--window", "7")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, [
            "dropped: https://www.stark.com/jobs/3#apply (repeated in this batch)",
            "dropped: https://old.com/jobs/1 (posted 2026-09-01, before the window (from 2026-10-15))",
            "kept: 3; dropped: 2; written to %s" % os.path.join(self.root, d + "/kept.jsonl"),
            "dropped by reason: before the window 1, applied 0, declined 0, repeated 1",
            "explore: applied and declined postings kept, no seen dates (an exploratory run)"])
        kept = self.lines(os.path.join(self.root, d, "kept.jsonl"))
        self.assertEqual([k["url"] for k in kept], ["https://acme.com/careers?gh_jid=111", "https://umbrella.com/jobs/5",
                                                    "https://stark.com/jobs/3"])
        self.assertFalse(any("seen" in k for k in kept))
        out = os.path.join(self.tmp, "elsewhere.jsonl")   # the postings file alone in the run's folder: still exploratory
        self.assertEqual(self.run_tool("dedup", d + "/collected.jsonl", "--out", out)[1][-1],
                         "explore: applied and declined postings kept, no seen dates (an exploratory run)")

    def test_explore_writes_no_records(self):
        self.write("scan-sources.md", self.EXPLORE_SOURCES)
        self.write(".gitignore", ".build/\n")   # as the Log ignores it
        d = self.explore()[0]
        self.commit("sources")
        before = git(self.root, "status", "--porcelain")
        row = {"url": "https://a.com/1", "company": "A", "role": "SWE", "status": "undecided", "draft": "", "fit_commit": ""}
        self.jsonl(d + "/rows.jsonl", [row])
        self.jsonl(d + "/ranked.jsonl", [dict(row, rank=1, recommendation="apply", folder="2026-10-22-a-swe")])
        self.jsonl(d + "/collected.jsonl", [{"url": "https://a.com/1", "company": "A", "role": "SWE"}])
        refused = "is an exploratory run (query \"Fintech  backend\")"
        for args in (("report", d + "/rows.jsonl", "--name", TODAY, "--screen", d), ("report", d + "/rows.jsonl"),
                     ("drafts", d, "--m", "1"), ("drafts", d, "--save")):
            code, lines = self.run_tool(*args)
            self.assertEqual(code, 1, (args, lines))
            self.assertIn(refused, lines[0], args)
        code, lines = self.run_tool("summary", d)
        self.assertEqual(code, 0, lines)
        self.assertIn("report: none (an exploratory run writes no scan report)", lines)
        self.assertEqual(git(self.root, "status", "--porcelain"), before)
        self.assertEqual(git(self.root, "branch", "--list", "scan/*", "-a"), "")
        self.assertFalse(os.path.exists(os.path.join(self.root, "outputs")))

    def test_explore_again_reuses_captures_and_screen_results(self):
        self.write("scan-sources.md", self.EXPLORE_SOURCES)
        self.write("entries/2025-01-widget.md", "# Widget\n")
        self.write("direction.md", self.DIRECTION)
        self.commit("log")
        d = self.explore()[0]
        posts = [{"url": "https://c%d.com/j/%d" % (i, i), "company": "C%d" % i, "role": "SWE", "tier": 1} for i in (1, 2)]
        self.jsonl(d + "/prefiltered.jsonl", posts)
        args = ("screen", d, "--screen-budget", "5", "--fit-budget", "1")
        self.assertEqual(self.run_tool(*args)[0], 0)
        listed = self.lines(os.path.join(self.root, d, "screen-list.jsonl"))
        for p in listed:
            self.write(p["capture"], "%s\n\ntext\n" % p["url"])
        self.result(os.path.join(self.root, d), "batch-1.jsonl", [
            {"url": "https://c1.com/j/1", "gate": "yes", "tier": 1, "rows": self.rows(2, 2)},
            {"url": "https://c2.com/j/2", "gate": "no", "reason": "US only: \"London\""}])
        self.assertEqual(self.run_tool(*args, "--sort")[0], 0)

        later = "2026-10-25"   # a second run, days on: its capture paths are the first run's
        self.assertEqual(self.explore(date=later)[1][-2], "reuse: 2 capture(s) and 2 Screen result(s) from an earlier run of this query")
        posts.insert(0, {"url": "https://c3.com/j/3", "company": "C3", "role": "SWE", "tier": 1})
        self.jsonl(d + "/prefiltered.jsonl", posts)
        code, lines = self.run_tool(*args, date=later)
        self.assertEqual(code, 0, lines)
        cap = lambda i: "%s/postings/c%d-swe.md" % (os.path.join(self.root, d).replace(os.sep, "/"), i)
        self.assertEqual(lines[1:], [
            "posting: https://c3.com/j/3 | capture %s (need) | screen batch-1" % cap(3),
            "posting: https://c1.com/j/1 | capture %s (have) | screen reused an earlier run" % cap(1),
            "posting: https://c2.com/j/2 | capture %s (have) | screen reused an earlier run" % cap(2),
            "screen: 3 posting(s) listed, 2 reused, 1 in 1 batch(es); 0 not screened (past the budget)"])
        reused = self.lines(os.path.join(self.root, d, "screen", "reused.jsonl"))
        self.assertEqual([(r["url"], r["gate"], len(r.get("rows") or [])) for r in reused],
                         [("https://c1.com/j/1", "yes", 3), ("https://c2.com/j/2", "no", 0)])
        self.write(cap(3), "https://c3.com/j/3\n\ntext\n")
        self.result(os.path.join(self.root, d), "batch-1.jsonl", [
            {"url": "https://c3.com/j/3", "gate": "yes", "tier": 1, "rows": self.rows(2, 1)}])
        code, lines = self.run_tool(*args, "--sort", date=later)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[-1], "screen: 1 to fit, 1 screened, not fully fitted, 1 dropped at screen, 0 unreadable (no capture)")

        # a third run: c1 has left the list, and another posting of C1's SWE takes its folder's name
        self.jsonl(d + "/prefiltered.jsonl", [{"url": "https://c1.com/j/9", "company": "C1", "role": "SWE", "tier": 1}])
        code, lines = self.run_tool(*args, date=later)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[1], "posting: https://c1.com/j/9 | capture %s (need) | screen batch-1" % cap(1))
        with open(cap(1) + ".stale", encoding="utf-8") as f:
            self.assertEqual(f.readline().strip(), "https://c1.com/j/1")

    def test_pending_gives_each_rows_fit_map(self):
        self.write("entries/2025-01-widget.md", "# widget\n")
        sha = self.commit("entries")
        self.write("outputs/reports/2026-10-20-scan.md",
                   "# Scan 2026-10-20\n\nAll sources read.\n\n## Pending\n\n| URL | Company | Role | Status | Draft | Fit map commit |\n"
                   "|---|---|---|---|---|---|\n| https://a.com/1 | A | SWE | undecided | - | %s |\n"
                   "| https://b.com/2 | B | SWE | undecided | - | - |\n\n## Fit maps\n\n### A — SWE\n\n"
                   "URL: https://a.com/1\nEntries commit: %s\n\n| Go | `2025-01-widget.md` |\n" % (sha, sha))
        self.commit("report")
        self.assertEqual(self.run_tool("pending")[1], [
            "report: outputs/reports/2026-10-20-scan.md",
            "pending: https://a.com/1 | A | SWE | undecided | - | fit map reuse",
            "pending: https://b.com/2 | B | SWE | undecided | - | fit map none",
            "count: 2 pending row(s)"])
        self.write("entries/2025-01-widget.md", "# widget changed\n")
        self.commit("cited entry")
        self.assertEqual(self.run_tool("pending")[1][1],
                         "pending: https://a.com/1 | A | SWE | undecided | - | fit map stale (entries/2025-01-widget.md)")

    def test_dedup_window(self):
        src = self.jsonl("collected.jsonl", [
            {"url": "https://a.com/1", "company": "A", "role": "SWE", "posted": "2026-10-15"},   # the window's first day
            {"url": "https://b.com/2", "company": "B", "role": "SWE", "posted": "2026-10-14"},
            {"url": "https://c.com/3", "company": "C", "role": "SWE", "posted": "2026-10-21T08:00:00Z"},
            {"url": "https://d.com/4", "company": "D", "role": "SWE", "posted": "2d ago"},
            {"url": "https://d.com/4?utm_source=x", "company": "D", "role": "SWE", "posted": "2d ago"},   # dropped: no undated line
        ])
        out = os.path.join(self.root, "kept.jsonl")
        code, lines = self.run_tool("dedup", src, "--out", out, "--window", "7")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[0], "dropped: https://b.com/2 (posted 2026-10-14, before the window (from 2026-10-15))")
        self.assertIn('undated: https://d.com/4 (posted "2d ago"): kept; write it as YYYY-MM-DD to window it', lines)
        self.assertEqual(lines[-1], "dropped by reason: before the window 1, applied 0, declined 0, repeated 1")
        self.assertEqual(len([l for l in lines if l.startswith("undated:")]), 1)
        self.assertEqual([p["url"] for p in self.lines(out)], ["https://a.com/1", "https://c.com/3", "https://d.com/4"])
        self.assertEqual(len(self.lines(out)), 3)
        self.run_tool("dedup", src, "--out", out)   # no --window: every date kept
        self.assertEqual(len(self.lines(out)), 4)

    def prefilter_log(self, roles="1. Backend\n2. Data\n"):
        self.write("direction.md", "# Direction\n\n## Target roles, ranked\n<!-- A numbered list -->\n%s\n## Constraints\n\n- US only\n"
                   % roles)
        self.write("scan-sources.md", "# Sources\n\n## Board\n- URL: https://board.example\n\n## List\n- URL: https://github.com/o/l\n")
        d = ".build/scan/%s" % TODAY
        self.jsonl(d + "/kept.jsonl", [
            {"url": "https://l.com/1", "company": "L1", "role": "Data Engineer", "source": "List"},
            {"url": "https://l.com/2", "company": "L2", "role": "Backend Engineer", "source": "List"},
            {"url": "https://b.com/1", "company": "B1", "role": "Backend Engineer", "source": "Board"},
            {"url": "https://b.com/2", "company": "B2", "role": "Designer", "source": "Board"},
            {"url": "https://b.com/3", "company": "B3", "role": "Backend Engineer", "location": "London", "source": "Board"},
            {"url": "https://x.com/1", "company": "X", "role": "Platform Engineer", "source": "Elsewhere"},
        ])
        return d

    def test_prefilter_orders_and_counts(self):
        d = self.prefilter_log()
        self.jsonl(d + "/titles.jsonl", [
            {"url": "https://l.com/1", "tier": 2}, {"url": "https://l.com/2?utm_source=x", "tier": 1},
            {"url": "https://b.com/1", "tier": 1}, {"url": "https://b.com/2", "tier": None, "drop": "role"},
            {"url": "https://b.com/3", "tier": 1, "drop": "constraint: US only"}, {"url": "https://x.com/1", "tier": None},
        ])
        code, lines = self.run_tool("prefilter", d)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["dropped: https://b.com/2 (role)", "dropped: https://b.com/3 (constraint: US only)",
                                 "sources not in scan-sources.md (ordered last): Elsewhere",
                                 "prefilter: 4 kept, written to prefiltered.jsonl; 2 dropped (constraint: US only 1, role 1)"])
        kept = self.lines(os.path.join(self.root, d, "prefiltered.jsonl"))
        self.assertEqual([p["url"] for p in kept], ["https://b.com/1", "https://l.com/2", "https://l.com/1", "https://x.com/1"])
        self.assertEqual([p["drop"] for p in self.lines(os.path.join(self.root, d, "prefilter-dropped.jsonl"))],
                         ["role", "constraint: US only"])

    def test_prefilter_keeps_a_title_close_to_a_target(self):
        d = self.prefilter_log()
        self.jsonl(d + "/titles.jsonl", [   # Platform Engineer: no target's title, but close to Backend
            {"url": "https://l.com/1", "tier": 2}, {"url": "https://l.com/2", "tier": 1},
            {"url": "https://b.com/1", "tier": 1}, {"url": "https://b.com/2", "tier": None, "drop": "role"},
            {"url": "https://b.com/3", "tier": 1, "drop": "constraint: US only"},
            {"url": "https://x.com/1", "tier": 1, "by": "content"},
        ])
        code, lines = self.run_tool("prefilter", d)
        self.assertEqual(code, 0, lines)
        self.assertIn("close: https://x.com/1 (tier 1, by content: Screen tiers it)", lines)
        self.assertEqual(lines[-1], "prefilter: 4 kept, written to prefiltered.jsonl; 2 dropped (constraint: US only 1, role 1)")
        kept = self.lines(os.path.join(self.root, d, "prefiltered.jsonl"))   # after tier 1's own titles, before tier 2
        self.assertEqual([p["url"] for p in kept], ["https://b.com/1", "https://l.com/2", "https://x.com/1", "https://l.com/1"])
        self.assertEqual([p.get("by") for p in kept], [None, None, "content", None])
        self.write("entries/2025-01-widget.md", "# Widget\n")
        self.commit("entries")
        code, lines = self.run_tool("screen", d, "--screen-budget", "3", "--fit-budget", "1")
        self.assertEqual(code, 0, lines)
        listed = self.lines(os.path.join(self.root, d, "screen-list.jsonl"))
        self.assertEqual([p["url"] for p in listed][-1], "https://x.com/1")   # within the budget, so Screen sees it
        for p in listed:
            self.write(p["capture"], "URL: %s\n\ntext\n" % p["url"])
        self.result(os.path.join(self.root, d), "batch-1.jsonl", [
            {"url": "https://b.com/1", "gate": "yes", "tier": 1, "rows": self.rows(4, 1)},
            {"url": "https://l.com/2", "gate": "yes", "tier": 1, "rows": self.rows(4, 2)},
            {"url": "https://x.com/1", "gate": "yes", "tier": 1, "rows": self.rows(4, 4),
             "check": ["1 (Backend, by content: builds the backend services)"]},
        ])
        code, lines = self.run_tool("screen", d, "--screen-budget", "3", "--fit-budget", "1", "--sort")
        self.assertEqual(code, 0, lines)
        fitted = self.lines(os.path.join(self.root, d, "fit.jsonl"))
        self.assertEqual([(p["url"], p["tier"]) for p in fitted], [("https://x.com/1", 1)])

    def test_prefilter_refuses_a_bad_by(self):
        d = self.prefilter_log()
        marks = [{"url": u, "tier": 1} for u in ("https://l.com/1", "https://l.com/2", "https://b.com/1")]
        self.jsonl(d + "/titles.jsonl", marks + [
            {"url": "https://b.com/2", "tier": None, "by": "content"},
            {"url": "https://b.com/3", "tier": 1, "by": "content", "drop": "constraint: US only"},
            {"url": "https://x.com/1", "tier": 1, "by": "title"},
        ])
        code, lines = self.run_tool("prefilter", d)
        self.assertEqual(code, 1)
        text = "\n".join(lines)
        self.assertIn("prefilter: 3 problem(s)", lines[0])
        self.assertIn("line 4 (https://b.com/2): by content needs the close target's tier, and no drop", text)
        self.assertIn("line 5 (https://b.com/3): by content needs", text)
        self.assertIn('line 6 (https://x.com/1): by must be "content"', text)

    def test_prefilter_refuses_what_does_not_add_up(self):
        d = self.prefilter_log()
        self.jsonl(d + "/titles.jsonl", [
            {"url": "https://l.com/1", "tier": 3}, {"url": "https://l.com/2", "tier": 1}, {"url": "https://l.com/2", "tier": 1},
            {"url": "https://b.com/1", "tier": "1"}, {"url": "https://b.com/2", "drop": "not my thing"},
            {"url": "https://z.com/9", "tier": 1},
        ])
        code, lines = self.run_tool("prefilter", d)
        self.assertEqual(code, 1)
        self.assertIn("prefilter: 7 problem(s)", lines[0])
        text = "\n".join(lines)
        for want in ("tier 3, but direction.md lists 2 target role(s)", "repeated: titles.jsonl line 3",
                     "line 4 (https://b.com/1): tier must be", 'drop must be "role" or "constraint: <which>"',
                     "extra: titles.jsonl line 6 (https://z.com/9)", "missing: https://b.com/3", "missing: https://x.com/1"):
            self.assertIn(want, text)
        self.assertFalse(os.path.exists(os.path.join(self.root, d, "prefiltered.jsonl")))
        self.write(d + "/titles.jsonl", '["not an object"]\n')
        code, lines = self.run_tool("prefilter", d)
        self.assertEqual(code, 1)
        self.assertIn("line 1 is no JSON object", lines[0])

    def test_target_roles_are_configs(self):
        config = scan.config
        self.write("direction.md", "# Direction\n\n## Target roles, ranked\n<!-- A numbered list -->\n1. Backend\n"
                   "   - indented note\n2. Data (user, 2026-10-01)\n\n- Product roles: considered, not a target\n\n## Constraints\n")
        self.assertEqual(config.target_roles(self.root), ["Backend", "Data (user, 2026-10-01)"])
        shown = [l.split(": ", 1)[1] for l in config.direction_lines(self.root) if l.startswith("direction target roles: ")]
        self.assertEqual([l for l in shown if not l.startswith(" ")], config.target_roles(self.root))
        self.write("direction.md", "## Target roles, ranked\n- Backend\n- Data\n")   # a list written as bullets
        self.assertEqual(config.target_roles(self.root), ["Backend", "Data"])
        self.write("direction.md", "## Target roles, ranked\n1. GAP: ask the user\n")
        self.assertEqual(config.target_roles(self.root), [])
        self.write("direction.md", "## Constraints\n")
        self.assertEqual(config.target_roles(self.root), [])
        os.remove(os.path.join(self.root, "direction.md"))
        self.assertEqual(config.target_roles(self.root), [])

    def test_prefilter_counts_no_note_as_a_role(self):
        d = self.prefilter_log(roles="1. Backend\n2. Data\n\n- Product roles: considered, not a target\n")
        marks = [{"url": u, "tier": 1} for u in ("https://l.com/1", "https://l.com/2", "https://b.com/1", "https://b.com/2",
                                                 "https://b.com/3")]
        self.jsonl(d + "/titles.jsonl", marks + [{"url": "https://x.com/1", "tier": 3}])
        code, lines = self.run_tool("prefilter", d)
        self.assertEqual(code, 1)
        self.assertIn("tier 3, but direction.md lists 2 target role(s)", "\n".join(lines))

    def test_prefilter_counts_a_gap_line_as_a_place(self):
        # a GAP: line between two roles takes a place, as tools/fit.py heatmap counts it (ranks())
        d = self.prefilter_log(roles="1. Backend\n2. GAP: a second role?\n3. Platform\n")
        marks = [{"url": u, "tier": 1} for u in ("https://l.com/1", "https://l.com/2", "https://b.com/1", "https://b.com/2",
                                                 "https://b.com/3")]
        self.jsonl(d + "/titles.jsonl", marks + [{"url": "https://x.com/1", "tier": 3}])
        code, lines = self.run_tool("prefilter", d)
        self.assertEqual(code, 0, lines)
        kept = self.lines(os.path.join(self.root, d, "prefiltered.jsonl"))
        self.assertEqual([(p["url"], p["tier"]) for p in kept][-1], ("https://x.com/1", 3))
        for tier, want in ((2, "tier 2 is the `GAP:` line of direction.md's Target roles, no role"),
                           (4, "tier 4, but direction.md lists 3 target role(s)")):
            self.jsonl(d + "/titles.jsonl", marks + [{"url": "https://x.com/1", "tier": tier}])
            code, lines = self.run_tool("prefilter", d)
            self.assertEqual(code, 1)
            self.assertIn("titles.jsonl line 6 (https://x.com/1): " + want, "\n".join(lines))
        d = self.prefilter_log(roles="1. Backend\n2. GAP: a second role?\n")   # a GAP: line after the last role
        self.jsonl(d + "/titles.jsonl", marks + [{"url": "https://x.com/1", "tier": 2}])
        code, lines = self.run_tool("prefilter", d)
        self.assertEqual(code, 1)
        self.assertIn("tier 2, but direction.md's last target role is 1", "\n".join(lines))

    def test_prefilter_with_no_target_roles(self):
        d = self.prefilter_log(roles="")
        marks = [{"url": u, "tier": None} for u in ("https://l.com/1", "https://l.com/2", "https://b.com/1", "https://b.com/3",
                                                    "https://x.com/1")]
        self.jsonl(d + "/titles.jsonl", marks + [{"url": "https://b.com/2", "drop": "role"}])
        code, lines = self.run_tool("prefilter", d)
        self.assertEqual(code, 1)
        self.assertIn("dropped for its role, but direction.md's Target roles are empty", "\n".join(lines))
        self.jsonl(d + "/titles.jsonl", marks + [{"url": "https://b.com/2", "tier": None}])
        code, lines = self.run_tool("prefilter", d)
        self.assertEqual(code, 0, lines)
        self.assertIn("target roles: empty (no title was dropped for its role; the report says so)", lines)
        kept = self.lines(os.path.join(self.root, d, "prefiltered.jsonl"))   # no tier: source order, then list order
        self.assertEqual([p["url"] for p in kept], ["https://b.com/1", "https://b.com/2", "https://b.com/3", "https://l.com/1",
                                                    "https://l.com/2", "https://x.com/1"])

    def test_screen_check(self):
        d = self.screen_log(3)
        self.run_tool("screen", d, "--screen-budget", "3", "--fit-budget", "1")
        todo = os.path.join(d, "screen", "batch-1.todo")
        listed = self.lines(os.path.join(d, "screen-list.jsonl"))
        for p in listed[:2]:   # c2's capture could not be made
            self.write(p["capture"], "%s\n\ntext\n" % p["url"])
        res = os.path.join(d, "screen", "batch-1.jsonl")
        self.result(d, "batch-1.jsonl", [{"url": "https://c0.com/j/0", "gate": "yes", "tier": 1, "rows": self.rows(2, 1)},
                                         {"url": "https://c1.com/j/1", "gate": "no", "reason": "US only: \"Paris\""}])
        self.assertEqual(self.run_tool("screen", "--check", res, "--batch", todo)[1],
                         ["check: ok, 2 result(s), one per capture of the batch"])
        self.assertEqual(self.run_tool("screen", "--check", res)[0], 0)
        self.result(d, "batch-1.jsonl", [{"url": "https://c0.com/j/0", "gate": "yes", "tier": 1, "rows": self.rows(2, 1)},
                                         {"url": "https://c0.com/j/0/", "gate": "no", "reason": "x"},
                                         {"url": "https://c7.com/j/7", "gate": "maybe"},
                                         {"url": "https://c8.com/j/8", "gate": "no", "reason": "x"}])
        code, lines = self.run_tool("screen", "--check", res, "--batch", todo)
        self.assertEqual(code, 1)
        self.assertIn("screen --check: 4 problem(s)", lines[0])
        self.assertEqual([l.split(":")[0] for l in lines[1:]], ["bad", "repeated", "extra", "missing"])
        self.assertIn("https://c1.com/j/1", lines[-1])
        self.write(os.path.relpath(res, self.root), '"just text"\n{"url": "https://c0.com/j/0", "gate": "no", "reason": "x"}\n{oops\n')
        code, lines = self.run_tool("screen", "--check", res)
        self.assertEqual((code, len(lines)), (1, 3))
        self.assertEqual([l[:12] for l in lines[1:]], ["bad: line 1 ", "bad: line 3 "])
        self.assertEqual(self.run_tool("screen", d, "--check", res)[0], 2)   # --check takes no dir
        # #569: each row names its skill, as a map row does, for fit.py heatmap's rough rows
        for skill in (None, "  ", 3):
            rows = self.rows(2, 1)
            rows[1] = dict(rows[1], skill=skill) if skill is not None else {k: v for k, v in rows[1].items() if k != "skill"}
            self.result(d, "batch-1.jsonl", [{"url": "https://c0.com/j/0", "gate": "yes", "tier": 1, "rows": rows}])
            code, lines = self.run_tool("screen", "--check", res)
            self.assertEqual((code, lines[1:]), (1, ["bad: line 1: https://c0.com/j/0: each row needs a skill, "
                                                     "named as a map row's (tools/fit.py --help)"]), skill)
        self.assertEqual(self.run_tool("screen", d, "--screen-budget", "3", "--fit-budget", "1", "--give-up")[0], 2)

    def test_screen_result_tier_is_a_target_roles_place(self):
        # a Screen tier is read as prefilter and tools/fit.py heatmap read it (fit.tier_problem)
        d = self.screen_log(1)
        res = os.path.join(d, "screen", "batch-1.jsonl")
        for roles, tier, want in (("1. Backend\n2. GAP: a second role?\n3. Platform\n", 3, None),
                                  ("1. Backend\n2. GAP: a second role?\n3. Platform\n", 2,
                                   "tier 2 is the `GAP:` line of direction.md's Target roles, no role"),
                                  ("1. Backend\n2. GAP: a second role?\n3. Platform\n", 4,
                                   "tier 4, but direction.md lists 3 target role(s)"),
                                  ("1. Backend\n2. GAP: a second role?\n", 2, "tier 2, but direction.md's last target role is 1"),
                                  ("", 1, "tier 1, but direction.md's Target roles are empty")):
            self.write("direction.md", self.DIRECTION.replace("1. Backend\n", roles))
            self.result(d, "batch-1.jsonl", [{"url": "https://c0.com/j/0", "gate": "yes", "tier": tier, "rows": self.rows(2, 1)}])
            code, lines = self.run_tool("screen", "--check", res)
            if want is None:
                self.assertEqual((code, lines), (0, ["check: ok, 1 result(s)"]))
            else:
                self.assertEqual((code, lines[1:]), (1, ["bad: line 1: https://c0.com/j/0: " + want]))
        # --sort refuses it too, before it writes anything
        self.write("direction.md", self.DIRECTION)
        self.run_tool("screen", d, "--screen-budget", "2", "--fit-budget", "1")
        for p in self.lines(os.path.join(d, "screen-list.jsonl")):
            self.write(p["capture"], "%s\n\ntext\n" % p["url"])
        self.result(d, "batch-1.jsonl", [{"url": "https://c0.com/j/0", "gate": "yes", "tier": 2, "rows": self.rows(2, 1)},
                                         {"url": "https://c9.com/j/9", "gate": "no", "reason": "x"}])
        code, lines = self.run_tool("screen", d, "--screen-budget", "2", "--fit-budget", "1", "--sort")
        self.assertEqual(code, 1)
        self.assertIn("https://c0.com/j/0: tier 2, but direction.md lists 1 target role(s)", "\n".join(lines))
        self.assertFalse(os.path.exists(os.path.join(d, "fit.jsonl")))

    def test_screen_sort_give_up(self):
        d = self.screen_log(2)
        self.run_tool("screen", d, "--screen-budget", "3", "--fit-budget", "1")
        listed = self.lines(os.path.join(d, "screen-list.jsonl"))
        for p in listed:
            self.write(p["capture"], "%s\n\ntext\n" % p["url"])
        self.result(d, "batch-1.jsonl", [{"url": "https://c0.com/j/0", "gate": "yes", "tier": 1, "rows": self.rows(2, 1)}])
        args = ("screen", d, "--screen-budget", "3", "--fit-budget", "1", "--sort")
        self.assertEqual(self.run_tool(*args)[0], 1)
        code, lines = self.run_tool(*args, "--give-up")
        self.assertEqual(code, 0, lines)
        self.assertEqual([l.split(" (")[0] for l in lines[:2]], ["gave up: https://c1.com/j/1", "gave up: https://c9.com/j/9"])
        self.assertEqual(lines[-1], "screen: 1 to fit, 0 screened, not fully fitted, 0 dropped at screen, 2 unreadable (no capture)")
        self.assertEqual([p["url"] for p in self.lines(os.path.join(d, "unreadable.jsonl"))], ["https://c1.com/j/1", "https://c9.com/j/9"])
        cap = os.path.join(self.root, listed[1]["capture"]) if not os.path.isabs(listed[1]["capture"]) else listed[1]["capture"]
        self.assertFalse(os.path.exists(cap))
        self.assertTrue(os.path.exists(cap + ".unreadable"))
        earlier = scan.earlier_captures(self.root, d + "-next")
        self.assertIn("c0.com/j/0", earlier)   # the posting with a result keeps its capture for the next run
        self.assertNotIn("c1.com/j/1", earlier)
        self.assertFalse([p for p in earlier.values() if p.endswith(".unreadable")])

    def fetched(self, *urls, folder=".build/scan/x"):
        with open(os.path.join(self.root, folder, "fetched.jsonl"), "a", encoding="utf-8") as f:
            f.writelines(json.dumps({"url": u, "status": 403, "chars": 0, "capture": False}) + "\n" for u in urls)

    def fake_get(self, status, ctype, body):
        calls = []
        def get(url):
            calls.append(url)
            if isinstance(status, Exception):
                raise status
            return status, ctype, body
        old = scan.http_get
        scan.http_get = get
        self.addCleanup(setattr, scan, "http_get", old)
        return calls

    def test_fetch_writes_the_capture_from_the_page(self):
        body = ("<html><head><title>t</title><script>var x = 'not text';</script></head><body><nav>Jobs</nav>"
                "<h1>Backend Engineer</h1><div>" + "<p>Build the queue &amp; its workers.</p>" * 30 + "</div></body></html>")
        url = "https://jobs.lever.co/acme/1234abcd-0000-0000-0000-000000000000"
        calls = self.fake_get(200, "text/html; charset=utf-8", body)
        code, lines = self.run_tool("fetch", ".build/scan/x/postings/a.md", url + ".")
        self.assertEqual(code, 0, lines)
        self.assertEqual(calls, [url])
        self.assertRegex(lines[0], r"^capture: \.build/scan/x/postings/a\.md \(https://jobs\.lever\.co/acme/\S+, fetch, \d+ characters\)$")
        self.assertTrue(lines[1].startswith("next: read the capture's first 30 lines"), lines)
        text =self.read(".build/scan/x/postings/a.md")
        self.assertTrue(text.startswith(url + "\nread: fetch, open\n\nJobs\nBackend Engineer\n"), text[:120])
        self.assertIn("Build the queue & its workers.", text)
        self.assertNotIn("not text", text)
        rec = json.loads(self.read(".build/scan/x/fetched.jsonl").splitlines()[-1])
        self.assertEqual((rec["url"], rec["status"], rec["capture"]), (url, 200, True))
        # a fetched page that turns out to be no posting is read again, and captured over the fetch's
        page = self.write(".playwright-cli/posting-page.json", json.dumps("Backend Engineer, read again\n"))
        self.assertEqual(self.run_tool("capture", ".build/scan/x/postings/a.md", url + "/apply?lever-source=x", page)[0], 0)

    def test_fetch_refuses_a_shell_or_an_error_and_records_it(self):
        self.fake_get(200, "text/html", "<html><body><div id=root></div><noscript>Enable JavaScript to run this app.</noscript></body></html>")
        code, lines = self.run_tool("fetch", ".build/scan/x/postings/a.md", "https://jobs.ashbyhq.com/acme/1")
        self.assertEqual(code, 1)
        self.assertEqual(lines[0], "scan: fetch: no capture from https://jobs.ashbyhq.com/acme/1"
                                   " (0 characters of text, a page built by script or a wall)")
        self.assertTrue(lines[1].startswith("next: read the page with playwright-cli"), lines)
        self.assertFalse(os.path.exists(os.path.join(self.root, ".build/scan/x/postings/a.md")))
        self.fake_get(404, "", "")
        lines = self.run_tool("fetch", ".build/scan/x/postings/b.md", "https://b.example/1")[1]
        self.assertIn("(status 404)", lines[0])
        self.assertTrue(lines[1].startswith("next: status 404: the posting may be gone; read the page"), lines)
        self.fake_get(scan.urllib.error.URLError("no host"), "", "")
        self.assertIn("(no answer: no host)", self.run_tool("fetch", ".build/scan/x/postings/c.md", "https://c.example/1")[1][0])
        recs = [json.loads(l) for l in self.read(".build/scan/x/fetched.jsonl").splitlines()]
        self.assertEqual([(r["url"], r["status"], r["capture"]) for r in recs],
                         [("https://jobs.ashbyhq.com/acme/1", 200, False), ("https://b.example/1", 404, False),
                          ("https://c.example/1", 0, False)])
        page = self.write(".playwright-cli/posting-page.json", json.dumps("Backend Engineer\n"))
        code, lines = self.run_tool("capture", ".build/scan/x/postings/a.md", "https://jobs.ashbyhq.com/acme/1", page,
                                    "--stand-in", "https://api.ashbyhq.com/posting-api/job-board/acme")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["capture: .build/scan/x/postings/a.md (https://jobs.ashbyhq.com/acme/1, 16 characters,"
                                 " stand-in https://api.ashbyhq.com/posting-api/job-board/acme)"])

    def test_fetch_refuses_an_api_and_its_record_never_counts(self):
        calls = self.fake_get(200, "application/json", json.dumps({"text": "Backend Engineer " * 100}))
        for api in ("https://api.lever.co/v0/postings/acme/1234abcd-0000-0000-0000-000000000000",
                    "https://boards-api.greenhouse.io/v1/boards/acme/jobs/123",
                    "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/External/job/x_R1"):
            code, lines = self.run_tool("fetch", ".build/scan/x/postings/a.md", api)
            self.assertEqual(code, 1, lines)
            self.assertEqual(lines[0], "scan: fetch: %s is an API or JSON endpoint, not the posting's page" % api)
        self.assertEqual(calls, [])
        os.makedirs(os.path.join(self.root, ".build/scan/x"))
        self.fetched("https://boards-api.greenhouse.io/v1/boards/acme/jobs/123")   # shares the posting's id
        page = self.write("api.txt", "Backend Engineer\n")
        self.assertEqual(self.run_tool("capture", ".build/scan/x/postings/a.md",
                                       "https://job-boards.greenhouse.io/acme/jobs/123", page)[0], 1)

    def test_page_text(self):
        self.assertEqual(scan.page_text("<html><head><title>T</title><meta charset=utf-8><body><table><tr><td>Location"
                                        "</td><td>Remote</td></tr></table><main>Duties</main>", "text/html"),
                         "Location\nRemote\nDuties")   # no </head>: the body is still read
        self.assertEqual(scan.meta_charset(b'<html><meta charset="big5">'), "big5")
        for page in ("https://boards.greenhouse.io/apiture/jobs/123", "https://jobs.lever.co/apixio/abc-123"):
            self.assertFalse(scan.is_api(page), page)   # a company whose name starts with "api"
        self.assertTrue(scan.is_api("https://example.com/api/jobs/1"))

    def test_capture_refuses_a_page_never_fetched(self):
        page = self.write(".playwright-cli/posting-page.json", json.dumps("Backend Engineer\n"))
        url = "https://job-boards.greenhouse.io/acme/jobs/123"
        code, lines = self.run_tool("capture", ".build/scan/x/postings/a.md", url, page)
        self.assertEqual(code, 1)
        self.assertEqual(lines[0], "scan: capture: refused: no fetch of %s on record, so its own page was never read" % url)
        self.assertTrue(lines[1].startswith("next: run fetch .build/scan/x/postings/a.md %s first;" % url), lines)
        self.assertFalse(os.path.exists(os.path.join(self.root, ".build/scan/x/postings/a.md")))
        os.makedirs(os.path.join(self.root, ".build/scan/y"))
        self.fetched(url, folder=".build/scan/y")   # another run's fetch does not count
        self.assertEqual(self.run_tool("capture", ".build/scan/x/postings/a.md", url, page)[0], 1)
        os.makedirs(os.path.join(self.root, ".build/scan/x"), exist_ok=True)
        self.fetched("https://boards.greenhouse.io/acme/jobs/123")   # the same posting under its other URL
        self.assertEqual(self.run_tool("capture", ".build/scan/x/postings/a.md", url, page)[0], 0)

    def test_capture(self):
        os.makedirs(os.path.join(self.root, ".build/scan/x"))
        self.fetched("https://acme.example/jobs/1", "https://b.example/1", "https://c.example/1")
        self.fetched("https://c.example/1", folder="")
        page = self.write(".playwright-cli/posting-page.json", json.dumps("Backend Engineer\r\nAcme | Remote\n"))
        code, lines = self.run_tool("capture", ".build/scan/x/postings/a.md", "https://acme.example/jobs/1.", page)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["capture: .build/scan/x/postings/a.md (https://acme.example/jobs/1, 30 characters)"])
        self.assertEqual(self.read(".build/scan/x/postings/a.md"),
                         "https://acme.example/jobs/1\nread: browser, open\n\nBackend Engineer\nAcme | Remote\n")
        self.assertEqual(scan.capture_url(os.path.join(self.root, ".build/scan/x/postings/a.md")), "https://acme.example/jobs/1")
        txt = self.write("page.txt", "Plain text page\n")
        self.assertEqual(self.run_tool("capture", ".build/scan/x/postings/b.md", "https://b.example/1", txt)[0], 0)
        self.write(".playwright-cli/empty-page.json", json.dumps("  \n"))
        code, lines = self.run_tool("capture", ".build/scan/x/postings/c.md", "https://c.example/1", ".playwright-cli/empty-page.json")
        self.assertEqual(code, 1)
        self.assertIn("holds no text: leave the capture unwritten", lines[0])
        self.assertFalse(os.path.exists(os.path.join(self.root, ".build/scan/x/postings/c.md")))
        self.write(".playwright-cli/cr-page.json", json.dumps("one\rtwo"))
        self.assertEqual(self.run_tool("capture", "cr.md", "https://c.example/1", ".playwright-cli/cr-page.json")[0], 0)
        with open(os.path.join(self.root, "cr.md"), "rb") as f:
            self.assertEqual(f.read(), b"https://c.example/1\nread: browser, open\n\none\ntwo\n")
        self.write(".playwright-cli/obj-page.json", json.dumps({"text": "x"}))
        self.assertEqual(self.run_tool("capture", "c.md", "https://c.example/1", ".playwright-cli/obj-page.json")[0], 1)
        self.assertEqual(self.run_tool("capture", "c.md", "not a url", txt)[0], 1)

    # ---- a capture's state: open or closed, and how it was read (#568) ----

    POSTING = "<html><body><h1>Backend Engineer</h1>" + "<p>Build the queue and its workers.</p>" * 30 + "%s</body></html>"

    def test_fetch_records_a_closed_posting(self):
        self.fake_get(404, "", "")
        self.assertEqual(self.run_tool("fetch", ".build/scan/x/postings/a.md", "https://a.example/1")[0], 1)
        self.assertEqual(self.run_tool("state", ".build/scan/x/postings/a.md")[1],
                         ["state: .build/scan/x/postings/a.md | https://a.example/1 | no capture | closed (status 404)"])
        self.assertEqual(scan.capture_state(os.path.join(self.root, ".build/scan/x/postings/a.md")),
                         {"url": "https://a.example/1", "read": None, "stand_in": None, "open": False, "why": "status 404"})
        # a page read after the fetch that found it gone is a closed posting's page
        page = self.write(".playwright-cli/posting-page.json", json.dumps("Backend Engineer\n"))
        code, lines = self.run_tool("capture", ".build/scan/x/postings/a.md", "https://a.example/1", page)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["capture: .build/scan/x/postings/a.md (https://a.example/1, 16 characters, closed (status 404))"])
        self.assertTrue(self.read(".build/scan/x/postings/a.md").startswith(
            "https://a.example/1\nread: browser, closed (status 404)\n\nBackend Engineer\n"))
        self.fake_get(410, "", "")
        self.run_tool("fetch", ".build/scan/x/postings/b.md", "https://b.example/1")
        self.assertIn("closed (status 410)", self.run_tool("state", ".build/scan/x/postings/b.md")[1][0])
        # a page that says it takes no applications: captured, as closed
        self.fake_get(200, "text/html", self.POSTING % "<div>This job is no longer accepting applications.</div>")
        code, lines = self.run_tool("fetch", ".build/scan/x/postings/c.md", "https://c.example/1")
        self.assertEqual(code, 0, lines)
        self.assertRegex(lines[0], r", fetch, \d+ characters, closed \(the page says \"no longer accepting applications\"\)\)$")
        self.assertEqual(self.run_tool("state", ".build/scan/x/postings/c.md")[1],
                         ['state: .build/scan/x/postings/c.md | https://c.example/1 | read fetch'
                          ' | closed (the page says "no longer accepting applications")'])
        for closed in ("The position has been filled.", "Sorry, this job is no longer available",
                       "Applications are now closed", "This posting has expired.", "Applications closed",
                       "The job you are looking for is no longer open.", "This role is no\nlonger accepting applications"):
            self.assertIsNotNone(scan.closed_wording("Backend Engineer\n" + closed), closed)
        for still in ("We are accepting applications on a rolling basis.", "Close the loop with customers.",
                      "Own the team's composition is filled in later.", "Build a job is closed-loop control system."):
            self.assertIsNone(scan.closed_wording(still), still)
        self.assertEqual(self.run_tool("state", ".build/scan/x/postings/none.md")[0], 1)
        # a capture written before a later fetch found the posting gone is set to closed
        self.fake_get(200, "text/html", self.POSTING % "")
        self.assertEqual(self.run_tool("fetch", ".build/scan/x/postings/d.md", "https://d.example/1")[0], 0)
        self.fake_get(410, "", "")
        self.run_tool("fetch", ".build/scan/x/postings/d.md", "https://d.example/1")
        self.assertEqual(self.run_tool("state", ".build/scan/x/postings/d.md")[1],
                         ["state: .build/scan/x/postings/d.md | https://d.example/1 | read fetch | closed (status 410)"])
        self.assertIn("Build the queue", self.read(".build/scan/x/postings/d.md"))

    def test_capture_records_how_it_was_read(self):
        self.fake_get(200, "text/html", self.POSTING % "")
        self.assertEqual(self.run_tool("fetch", ".build/scan/x/postings/a.md", "https://a.example/1")[0], 0)
        self.assertEqual(self.run_tool("state", ".build/scan/x/postings/a.md")[1],
                         ["state: .build/scan/x/postings/a.md | https://a.example/1 | read fetch | open"])
        self.fetched("https://b.example/1", "https://c.example/1")
        page = self.write(".playwright-cli/posting-page.json", json.dumps("Backend Engineer\n"))
        self.assertEqual(self.run_tool("capture", ".build/scan/x/postings/b.md", "https://b.example/1", page)[0], 0)
        self.assertEqual(self.run_tool("state", ".build/scan/x/postings/b.md")[1],
                         ["state: .build/scan/x/postings/b.md | https://b.example/1 | read browser | open"])
        txt = self.write("api.txt", "Backend Engineer\nThis role has been filled.\n")
        self.assertEqual(self.run_tool("capture", ".build/scan/x/postings/c.md", "https://c.example/1", txt,
                                       "--stand-in", "https://api.c.example/jobs/1")[0], 0)
        self.assertEqual(self.run_tool("state", ".build/scan/x/postings/c.md")[1],
                         ['state: .build/scan/x/postings/c.md | https://c.example/1 | read stand-in https://api.c.example/jobs/1'
                          ' | closed (the page says "role has been filled")'])
        # pasted: no fetch on record needed, and the same record as any other
        pasted = self.write("pasted.txt", "Backend Engineer\nAcme\n")
        code, lines = self.run_tool("capture", ".build/scan/x/postings/d.md", "https://d.example/1", pasted, "--pasted")
        self.assertEqual(lines, ["capture: .build/scan/x/postings/d.md (https://d.example/1, 21 characters, pasted)"])
        self.assertEqual(self.read(".build/scan/x/postings/d.md"), "https://d.example/1\nread: pasted, open\n\nBackend Engineer\nAcme\n")
        self.assertEqual(self.run_tool("capture", "e.md", "https://e.example/1", pasted, "--pasted",
                                       "--stand-in", "https://api.e.example/1")[0], 1)
        # readable from the path alone, outside any run folder: an application's saved posting
        shutil.copyfile(os.path.join(self.root, ".build/scan/x/postings/c.md"),
                        self.write("outputs/applications/c/posting.md", ""))
        self.assertEqual(scan.capture_state(os.path.join(self.root, "outputs/applications/c/posting.md")),
                         {"url": "https://c.example/1", "read": "stand-in", "stand_in": "https://api.c.example/jobs/1",
                          "open": False, "why": 'the page says "role has been filled"'})
        # a capture from before these records: its state is unknown
        self.write("old.md", "https://f.example/1\n\nBackend Engineer\n")
        self.assertEqual(self.run_tool("state", "old.md")[1],
                         ["state: old.md | https://f.example/1 | read unknown | unknown (a capture from before read lines)"])
        self.assertEqual(scan.capture_state(os.path.join(self.root, "old.md"))["open"], None)

    def test_cleanup_deletes_decided_run_folders(self):
        for name in ("2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22"):
            self.write(".build/scan/%s/postings/p.md" % name, "https://x.com/1\n")
        self.report("2026-10-19", [["https://a.com/1", "A", "SWE", "undecided", "-", "-"]])
        self.report("2026-10-20", [["https://b.com/2", "B", "SWE", "declined", "-", "-"]])
        self.report("2026-10-21", [["https://a.com/1", "A", "SWE", "accepted", "outputs/applications/a/", "-"],
                                   ["https://c.com/3", "C", "SWE", "undecided", "-", "-"]])
        code, lines = self.run_tool("cleanup", "--dry-run")
        self.assertEqual(lines, ["deleted: .build/scan/2026-10-19/ (dry run: nothing deleted)",
                                 "deleted: .build/scan/2026-10-20/ (dry run: nothing deleted)",
                                 "kept: .build/scan/2026-10-21/ (1 pending)",
                                 "kept: .build/scan/2026-10-22/ (no report yet)"])
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".build/scan/2026-10-19")))
        self.run_tool("cleanup")
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, ".build/scan"))), ["2026-10-21", "2026-10-22"])

    def test_a_pipe_in_a_cell_round_trips(self):
        rows = self.jsonl("rows.jsonl", [{"url": "https://a.com/1", "company": "A | B Labs", "role": "SWE", "status": "undecided"}])
        self.assertEqual(self.run_tool("report", rows, "--name", TODAY)[0], 0)
        self.assertIn("| https://a.com/1 | A \\| B Labs | SWE |", self.read("outputs/reports/2026-10-22-scan.md"))
        self.assertEqual(self.run_tool("pending")[1][1], "pending: https://a.com/1 | A \\| B Labs | SWE | undecided | - | fit map none")
        self.assertEqual(self.run_tool("status", "https://a.com/1", "declined")[0], 0)
        self.assertIn("| https://a.com/1 | A \\| B Labs | SWE | declined |", self.read("outputs/reports/2026-10-22-scan.md"))
        self.assertEqual(self.run_tool("pending")[1][1], "pending: none")

    def test_no_git_is_a_refusal_not_a_traceback(self):
        def no_git(*a, **k):
            raise FileNotFoundError(2, "No such file or directory", "git")
        real = scan.logfiles.subprocess.run
        scan.logfiles.subprocess.run = no_git
        self.addCleanup(setattr, scan.logfiles.subprocess, "run", real)
        code, lines = self.run_tool("cleanup")
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith("scan: git remote get-url origin: git failed:"), lines)

    def test_screen_key_is_the_one_earlier_releases_wrote(self):
        self.write("entries/2025-01-widget.md", "---\ntype: project\n---\n# Widget\n")
        self.write("direction.md", self.DIRECTION)
        self.assertEqual(scan.screen_key(self.root), SCREEN_KEY)

    # ---- rank, the report's sections, summary (#301) ----

    FIT_ROWS = [{"requirement": "Go", "kind": "required", "written_by": "user", "own_work": "", "category": "covered",
                 "entry": "2025-01-widget.md"},
                {"requirement": "SQL", "kind": "required", "written_by": "user", "own_work": "", "category": "covered",
                 "entry": "2024-02-新.md"},
                {"requirement": "Kafka", "kind": "required", "written_by": "user", "own_work": "", "category": "shallow",
                 "entry": "2025-01-widget.md"},
                {"requirement": "Rust", "kind": "preferred", "written_by": "user", "own_work": "", "category": "covered",
                 "entry": "2025-01-widget.md"},
                {"requirement": "Own the on-call", "kind": "duty", "written_by": "", "own_work": "", "category": "gap",
                 "entry": ""}]

    def run_to_fit(self, name=TODAY):
        """A run from collect to fit: c fitted, d to fit but unreadable at fit, e dropped at screen, h
        screened but not fully fitted, g past the screen budget, f dropped by the prefilter, a and b by dedup."""
        self.write("entries/2025-01-widget.md", "# Widget\n")
        self.write("entries/2024-02-新.md", "# 新\n")
        self.write("direction.md", self.DIRECTION)
        self.write("outputs/applications/2026-09-01-a-swe/posting.md", "https://a.com/j/1\n\ntext\n")
        self.jsonl("outputs/reports/scan-declined.jsonl", [{"url": "https://b.com/j/2", "date": "2026-10-01", "reason": ""}])
        self.commit("log")
        d = ".build/scan/" + name
        self.jsonl(d + "/collected.jsonl", [{"url": "https://%s.com/j/%d" % (c, i), "company": c.upper(), "role": "SWE",
                                             "posted": TODAY, "source": "list"} for i, c in enumerate("abcdefgh", 1)])
        self.jsonl(d + "/read.jsonl", [{"source": "list", "read": "API"}])
        self.assertEqual(self.run_tool("dedup", d + "/collected.jsonl", "--out", d + "/kept.jsonl")[0], 0)
        self.jsonl(d + "/titles.jsonl", [{"url": "https://%s.com/j/%d" % (c, i), "tier": None if c == "g" else 1}
                                         for i, c in enumerate("abcdefgh", 1) if c not in "ab" and c != "f"]
                   + [{"url": "https://f.com/j/6", "tier": None, "drop": "constraint: US only"}])
        self.assertEqual(self.run_tool("prefilter", d)[0], 0)
        args = ("screen", d, "--screen-budget", "4", "--fit-budget", "2")
        self.assertEqual(self.run_tool(*args)[0], 0)
        listed = {p["url"]: p for p in self.lines(os.path.join(self.root, d, "screen-list.jsonl"))}
        self.assertEqual(sorted(listed), ["https://c.com/j/3", "https://d.com/j/4", "https://e.com/j/5", "https://h.com/j/8"])
        for u, p in listed.items():
            self.write(p["capture"], "%s\n\ntext\n" % u)
        self.result(os.path.join(self.root, d), "batch-1.jsonl", [
            {"url": "https://c.com/j/3", "gate": "yes", "tier": 1, "rows": self.rows(4, 4)},
            {"url": "https://d.com/j/4", "gate": "yes", "tier": 1, "rows": self.rows(4, 3)},
            {"url": "https://e.com/j/5", "gate": "no", "reason": "US only: \"London\""},
            {"url": "https://h.com/j/8", "gate": "yes", "tier": 1, "rows": self.rows(4, 1)}])
        code, lines = self.run_tool(*args, "--sort")
        self.assertEqual(code, 0, lines)
        os.remove(os.path.join(self.root, listed["https://d.com/j/4"]["capture"]))   # 7.2: no read gives d's page
        return d, listed

    def fit_result(self, d, folder, url, rows=None):
        self.write("%s/fit/%s.jsonl" % (d, folder),
                   json.dumps({"url": url, "recommendation": "apply with caveats", "check": ["sponsorship"],
                               "notes": ["Map: 5 requirements and duties, 5 rows; no row: none"],
                               "rows": rows or self.FIT_ROWS}, ensure_ascii=False) + "\n")

    def test_rank_report_and_summary(self):
        d, listed = self.run_to_fit()
        c = listed["https://c.com/j/3"]
        self.assertEqual(self.run_tool("fitmap", c["url"], "--out", "%s/fit/%s.jsonl" % (d, c["folder"]))[1], ["fit map: none"])
        self.fit_result(d, c["folder"], c["url"])
        sha = git(self.root, "log", "-1", "--format=%h", "--", "entries").strip()
        code, lines = self.run_tool("rank", d, "--n", "3", "--m", "2")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["rank: 1 | C | SWE | apply with caveats | 2/4 | https://c.com/j/3", "only 1 found",
                                 "draft: https://c.com/j/3 | folder %s | capture %s" % (c["folder"], c["capture"]),
                                 "ranked: 1 fitted, the top 1 written to rows.jsonl; 1 unreadable at fit"])
        self.assertEqual(self.lines(os.path.join(self.root, d, "rows.jsonl")),
                         [{"url": "https://c.com/j/3", "company": "C", "role": "SWE", "status": "undecided", "draft": "",
                           "fit_commit": sha}])
        self.assertEqual(self.run_tool("rank", d, "--n", "3")[0], 0)   # a rerun adds no unreadable line twice
        unreadable = self.lines(os.path.join(self.root, d, "unreadable.jsonl"))
        self.assertEqual([(u["url"], u.get("at")) for u in unreadable], [("https://d.com/j/4", "fit")])
        code, lines = self.run_tool("report", d + "/rows.jsonl", "--name", TODAY, "--screen", d)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[1:], ["wrote: outputs/dashboard/dashboard.html", "artifact: none", "commit: scan(2026-10-22): 1 postings"])
        text = self.read("outputs/reports/2026-10-22-scan.md")
        order = [text.index(h) for h in ("## Pending", "## Ranking", "## Dropped at screen", "## Screened, not fully fitted",
                                         "## Not fitted", "## Fit maps")]
        self.assertEqual(order, sorted(order))
        self.assertIn("| 1 | C | SWE | https://c.com/j/3 | apply with caveats | 1 | 2/4 | 4/4 | list | - |", text)
        self.assertIn("- Dropped by dedup: 2 (applied 1, declined 1)\n- Dropped by the prefilter: 1 (constraint: US only 1)", text)
        self.assertIn("- Past the screen budget: 1\n\n| Company | Role | URL |\n|---|---|---|\n| G | SWE | https://g.com/j/7 |", text)
        self.assertIn("- Unreadable: 1\n\n| Company | Role | URL |\n|---|---|---|\n| D | SWE | https://d.com/j/4 |", text)
        self.assertRegex(text, r"### C — SWE\n\nURL: https://c.com/j/3\nScreen: tier 1, rough 4/4, key \S+\n"
                               r"Entries commit: %s\nRecommendation: apply with caveats\n\nThings to check:\n\n- sponsorship\n" % sha)
        self.assertIn("| Requirement | Kind | Written by | Own work | Category | Entry |", text)
        self.assertIn("| Own the on-call | duty | - | - | gap | - |", text)
        code, lines = self.run_tool("summary", d)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, ["collected: 8", "dropped by dedup: 2", "dropped by the prefilter: 1", "past the screen budget: 1",
                                 "dropped at screen: 1", "screened, not fully fitted: 1", "unreadable: 1", "fitted and ranked: 1",
                                 "top: 1 | C | SWE | apply with caveats | https://c.com/j/3",
                                 "summary: ok, every posting collected is in one of the run's files"])
        # a posting no file accounts for, and one in two files
        self.jsonl(d + "/dedup-dropped.jsonl", self.lines(os.path.join(self.root, d, "dedup-dropped.jsonl"))[:1])
        self.jsonl(d + "/not-screened.jsonl", self.lines(os.path.join(self.root, d, "not-screened.jsonl")) * 2)
        code, lines = self.run_tool("summary", d)
        self.assertEqual(code, 1)
        self.assertIn("repeated: https://g.com/j/7 (in not-screened.jsonl and not-screened.jsonl)", lines)
        self.assertIn("missing: https://b.com/j/2 (collected, in none of the run's files)", lines)
        self.assertEqual(lines[-1], "summary: 2 finding(s)")

    def test_report_says_how_each_source_was_read(self):
        """#485: read.jsonl gives the report a `## Sources` line per source, before `## Not fitted`; a bad
        line refuses the report."""
        d, listed = self.run_to_fit()
        c = listed["https://c.com/j/3"]
        self.fit_result(d, c["folder"], c["url"])
        self.assertEqual(self.run_tool("rank", d, "--n", "3")[0], 0)
        for bad, why in (({"source": "list", "read": "api"}, "read must be one of API, fetch, browser, file"),
                         ({"read": "API"}, "a line without a source")):
            self.jsonl(d + "/read.jsonl", [bad])
            code, lines = self.run_tool("report", d + "/rows.jsonl", "--name", TODAY, "--screen", d)
            self.assertEqual(code, 1, lines)
            self.assertIn("read.jsonl line 1: " + why, "\n".join(lines))
            self.assertFalse(os.path.exists(os.path.join(self.root, "outputs/reports/2026-10-22-scan.md")))
        self.jsonl(d + "/read.jsonl", [{"source": "list", "read": "API"}, {"source": "board", "read": "browser"}])
        code, lines = self.run_tool("report", d + "/rows.jsonl", "--name", TODAY, "--screen", d)
        self.assertEqual(code, 0, lines)
        text = self.read("outputs/reports/2026-10-22-scan.md")
        self.assertIn("## Screened, not fully fitted", text)
        self.assertIn("\n\n## Sources\n\n- list: read: API\n- board: read: browser\n\n## Not fitted\n", text)
        self.assertLess(text.index("## Screened, not fully fitted"), text.index("## Sources"))

    def test_report_refuses_a_collected_source_with_no_read_line(self):
        d, listed = self.run_to_fit()
        c = listed["https://c.com/j/3"]
        self.fit_result(d, c["folder"], c["url"])
        self.assertEqual(self.run_tool("rank", d, "--n", "3")[0], 0)
        for read in ([{"source": "other", "read": "fetch"}], None):
            if read:
                self.jsonl(d + "/read.jsonl", read)
            else:
                os.remove(os.path.join(self.root, d, "read.jsonl"))
            code, lines = self.run_tool("report", d + "/rows.jsonl", "--name", TODAY, "--screen", d)
            self.assertEqual(code, 1, lines)
            self.assertIn("read.jsonl has no line for list: add how each was read (scan.md step 3)", "\n".join(lines))
            self.assertFalse(os.path.exists(os.path.join(self.root, "outputs/reports/2026-10-22-scan.md")))

    def test_sponsorship_records_in_report_and_summary(self):
        """#284: with a Visa sponsorship needed line, the report gives each fitted employer its records once,
        and summary finds an employer with none."""
        d, listed = self.run_to_fit()
        c = listed["https://c.com/j/3"]
        self.fit_result(d, c["folder"], c["url"])
        self.assertEqual(self.run_tool("rank", d, "--n", "3")[0], 0)
        ranked = self.lines(os.path.join(self.root, d, "ranked.jsonl"))
        self.jsonl(d + "/ranked.jsonl", ranked + [dict(ranked[0], url="https://c.com/j/9", company="C, Inc.")])
        self.write("direction.md", self.DIRECTION.replace("- US only\n", "- US only\n- **Visa sponsorship needed:** H-1B;"
                                                          " green card (PERM) (user, 2026-10-01)\n"))
        today = TODAY
        self.jsonl("outputs/reports/sponsorship.jsonl", [
            {"employer": "C", "kind": "lca", "date": today,
             "records": [{"url": "https://lca.example/c|1", "filer": "C INC", "certain": True}]},
            {"employer": "C", "kind": "perm", "date": today, "records": [], "data_date": "2026-09"}])
        code, lines = self.run_tool("report", d + "/rows.jsonl", "--name", TODAY, "--screen", d)
        self.assertEqual(code, 0, lines)
        text = self.read("outputs/reports/2026-10-22-scan.md")
        self.assertLess(text.index("## Not fitted"), text.index("## Sponsorship records"))
        self.assertLess(text.index("## Sponsorship records"), text.index("## Fit maps"))
        section = text[text.index("## Sponsorship records"):text.index("## Fit maps")]
        self.assertEqual(section.count("| C |"), 2)   # two postings of C (one as `C, Inc.`): its records once
        self.assertIn("| C | H-1B LCA | %s | - | https://lca.example/c\\|1 | C INC | yes |" % today, section)
        self.assertIn("| C | PERM | %s | 2026-09 | none found | - | - |" % today, section)
        self.assertNotIn("C, Inc.", section)
        code, lines = self.run_tool("summary", d)
        self.assertNotIn("no sponsorship record", "\n".join(lines))
        self.assertNotIn("sponsorship unanswered", "\n".join(lines))
        # #437: an unanswered lookup is a finding of its own, with why
        self.jsonl("outputs/reports/sponsorship.jsonl", [
            {"employer": "C", "kind": "lca", "date": today, "records": [], "unanswered": "lca.example answered 403"},
            {"employer": "C", "kind": "perm", "date": today, "records": []}])
        code, lines = self.run_tool("summary", d)
        self.assertEqual(code, 1, lines)
        self.assertIn("sponsorship unanswered: C | lca | lca.example answered 403", lines)
        self.assertNotIn("no sponsorship record", "\n".join(lines))
        self.jsonl("outputs/reports/sponsorship.jsonl", [
            {"employer": "C", "kind": "lca", "date": "2020-01-01", "records": []}])
        code, lines = self.run_tool("summary", d)
        self.assertIn("no sponsorship record: C | lca", lines)   # too old
        self.assertIn("no sponsorship record: C | perm", lines)   # never looked up
        # no line: no section, no finding
        self.write("direction.md", self.DIRECTION)
        self.assertEqual(scan.sponsorship.report_lines(self.root, ["C"]), [])
        code, lines = self.run_tool("summary", d)
        self.assertNotIn("no sponsorship record", "\n".join(lines))

    def test_reusing_a_new_reports_map_ranks_it_the_same(self):
        d, listed = self.run_to_fit()
        c = listed["https://c.com/j/3"]
        self.fit_result(d, c["folder"], c["url"])
        first = self.run_tool("rank", d, "--n", "3")[1][0]
        self.run_tool("report", d + "/rows.jsonl", "--name", TODAY, "--screen", d)
        self.commit("report")
        # the next run: the map is reused, kinds and all
        d2 = ".build/scan/2026-10-23"
        os.makedirs(os.path.join(self.root, d2))
        shutil.copy(os.path.join(self.root, d, "fit.jsonl"), os.path.join(self.root, d2, "fit.jsonl"))
        code, lines = self.run_tool("fitmap", c["url"], "--out", "%s/fit/%s.jsonl" % (d2, c["folder"]), date="2026-10-23")
        self.assertEqual(lines[-2:], ["wrote: %s/fit/%s.jsonl" % (d2, c["folder"]), "fit map: reuse"])
        code, lines = self.run_tool("rank", d2, "--n", "3", date="2026-10-23")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[0], first)
        self.assertIn("| 2/4 |", lines[0])
        self.run_tool("report", d2 + "/rows.jsonl", "--name", "2026-10-23", "--screen", d2, date="2026-10-23")
        again = self.read("outputs/reports/2026-10-23-scan.md")
        self.assertIn("| Own the on-call | duty | - | - | gap | - |", again)   # the map as the first report kept it
        self.assertEqual(again.count("Recommendation: apply with caveats"), 1)

    def test_an_old_reports_map_ranks_on_every_row(self):
        self.write("entries/2025-01-widget.md", "# Widget\n")
        sha = self.commit("entries")
        self.write("outputs/reports/2026-10-01-scan.md",
                   "# Scan 2026-10-01\n\nAll sources read.\n\n## Pending\n\n## Ranking\n\n"
                   "1. A, SWE, https://a.com/1: apply, tier 1\n\n## Fit maps\n\n### A — SWE\n\nURL: https://a.com/1\n"
                   "Entries commit: %s\n\nCheck the visa.\n\n| Requirement | Written by | Own work | Category | Entry |\n"
                   "|---|---|---|---|---|\n| Go | user | | covered | `2025-01-widget.md` |\n"
                   "| SQL | user | | shallow | `2025-01-widget.md` |\n| Rust | user | | covered | `2025-01-widget.md` |\n" % sha)
        self.commit("old report")
        d = ".build/scan/" + TODAY
        self.jsonl(d + "/fit.jsonl", [{"url": "https://a.com/1", "company": "A", "role": "SWE", "tier": 1, "order": 1,
                                       "folder": "a", "capture": d + "/postings/a.md", "rough": "1/1", "key": "k"}])
        code, lines = self.run_tool("fitmap", "https://a.com/1", "--out", d + "/fit/a.jsonl")
        self.assertEqual(lines[-1], "fit map: reuse", lines)
        result = json.loads(self.read(d + "/fit/a.jsonl"))
        self.assertEqual(result["recommendation"], "apply")   # from the old Ranking line
        self.assertEqual([r["kind"] for r in result["rows"]], [None, None, None])
        self.assertEqual(self.run_tool("rank", d, "--n", "1")[1][0], "rank: 1 | A | SWE | apply | 2/3 | https://a.com/1")
        self.run_tool("report", d + "/rows.jsonl", "--name", TODAY, "--screen", d)
        self.assertIn("Check the visa.\n\n| Requirement | Written by |", self.read("outputs/reports/2026-10-22-scan.md"))

    def test_fitmap_sees_a_change_to_an_entry_named_in_chinese(self):
        """Finding 5: a map citing an entry whose name is not ASCII goes stale when that entry changes."""
        self.write("entries/2024-02-新.md", "# 新\n")
        sha = self.commit("entry")
        self.write("outputs/reports/2026-10-01-scan.md",
                   "# Scan 2026-10-01\n\n## Fit maps\n\n### A — SWE\n\nURL: https://a.com/1\nEntries commit: %s\n"
                   "Recommendation: apply\n\n| Requirement | Kind | Written by | Own work | Category | Entry |\n"
                   "|---|---|---|---|---|---|\n| SQL | required | user | - | covered | 2024-02-新.md |\n" % sha)
        self.commit("report")
        self.assertEqual(self.run_tool("fitmap", "https://a.com/1")[1][-1], "fit map: reuse")
        self.write("entries/2024-02-新.md", "# 新\n\nchanged\n")
        self.commit("edit")
        self.assertEqual(self.run_tool("fitmap", "https://a.com/1")[1][-1], "fit map: stale (entries/2024-02-新.md)")

    def test_rank_refuses_a_bad_result_and_a_missing_one(self):
        d, listed = self.run_to_fit()
        c = listed["https://c.com/j/3"]
        self.write(c["capture"], "%s\n\ntext\n" % c["url"])
        code, lines = self.run_tool("rank", d, "--n", "3")
        self.assertEqual((code, lines), (1, ["scan: no fit result yet for 1 posting(s): https://c.com/j/3"]))
        self.fit_result(d, c["folder"], c["url"], rows=[dict(self.FIT_ROWS[0], kind="must")])
        code, lines = self.run_tool("rank", d, "--n", "3")
        self.assertEqual(code, 1)
        self.assertIn("bad: fit/%s.jsonl: rows[1].kind: 'must' is not one of required, preferred, duty" % c["folder"], lines)
        os.remove(os.path.join(self.root, d, "fit", c["folder"] + ".jsonl"))
        code, lines = self.run_tool("rank", d, "--n", "3", "--give-up")
        self.assertEqual(code, 0, lines)
        self.assertTrue(lines[0].startswith("gave up: https://c.com/j/3"), lines)
        self.assertEqual(lines[-1], "ranked: 0 fitted, the top 0 written to rows.jsonl; 2 unreadable at fit")

    def test_dedup_keeps_what_it_dropped(self):
        self.jsonl("outputs/reports/scan-declined.jsonl", [{"url": "https://b.com/1", "date": "2026-10-01", "reason": ""}])
        src = self.jsonl("run/in.jsonl", [{"url": "https://b.com/1", "company": "B", "role": "SWE"},
                                           {"url": "https://c.com/1", "company": "C", "role": "SWE"},
                                           {"url": "https://c.com/1/", "company": "C", "role": "SWE"}])
        lines = self.run_tool("dedup", src, "--out", "run/kept.jsonl")[1]
        dropped = self.lines(os.path.join(self.root, "run", "dedup-dropped.jsonl"))
        self.assertEqual([(p["url"], p["drop"]) for p in dropped], [("https://b.com/1", "declined"), ("https://c.com/1/", "repeated")])
        self.assertEqual(lines[-1], "dropped by reason: before the window 0, applied 0, declined 1, repeated 1")

    def test_report_drafting_without_a_remote(self):
        git(self.root, "remote", "remove", "origin")
        rows = self.jsonl("rows.jsonl", [{"url": "https://a.com/1", "company": "A", "role": "SWE", "status": "undecided"}])
        self.assertEqual(self.run_tool("report", rows, "--name", TODAY, "--drafting")[0], 0)
        self.assertIn("\n\nAll sources read. The drafts are on this machine only (no remote).\n\n",
                      self.read("outputs/reports/2026-10-22-scan.md"))

    def test_status_regenerates_and_names_the_commit(self):
        self.report("2026-10-21", [["https://a.com/1", "A", "SWE", "undecided", "-", "-"],
                                   ["https://b.com/2", "B", "SWE", "undecided", "-", "-"],
                                   ["https://c.com/3", "C", "SWE", "undecided", "-", "-"]])
        self.jsonl("outputs/reports/scan-declined.jsonl", [{"url": "https://z.com/9", "date": "2026-10-01", "reason": ""}])
        self.commit("report")
        lines = self.run_tool("status", "https://a.com/1", "draft to review", "--draft", "scan/2026-10-21:scan-drafts/a")[1]
        self.assertEqual(lines[1:], ["wrote: outputs/dashboard/dashboard.html", "artifact: none", "commit: scan(2026-10-21): 1 drafts"])
        self.commit("drafts")
        self.run_tool("status", "https://b.com/2", "declined")
        lines = self.run_tool("status", "https://screened.com/1", "declined")[1]   # in no Pending table
        self.assertEqual(lines[-1], "commit: scan(2026-10-21): 0 accepted, 2 declined")
        lines = self.run_tool("status", "https://c.com/3", "accepted", "--draft", "outputs/applications/x/")[1]
        self.assertEqual(lines[-3:], ["wrote: outputs/dashboard/dashboard.html", "artifact: none", "commit: scan(2026-10-21): 1 accepted, 2 declined"])
        self.assertEqual(subprocess.run([sys.executable, "-I", os.path.join(HERE, "..", "dashboard.py"), "--root", self.root,
                                         "--check"], capture_output=True, encoding="utf-8").stdout.strip(), "dashboard: up to date")

    def test_a_dashboard_error_leaves_no_report(self):
        """report runs again once a file the dashboard reads is fixed."""
        self.write("outputs/reports/scan-declined.jsonl", "not json\n")
        rows = self.jsonl("rows.jsonl", [{"url": "https://a.com/1", "company": "A", "role": "SWE", "status": "undecided"}])
        code, lines = self.run_tool("report", rows, "--name", TODAY)
        self.assertEqual(code, 1)
        self.assertIn("the report is not written", lines[-1])
        self.assertFalse(os.path.exists(os.path.join(self.root, "outputs/reports/2026-10-22-scan.md")))
        self.write("outputs/reports/scan-declined.jsonl", "")
        self.assertEqual(self.run_tool("report", rows, "--name", TODAY)[0], 0)

    def old_map(self, table):
        self.write("entries/2025-01-widget.md", "# Widget\n")
        sha = self.commit("entries")
        self.write("outputs/reports/2026-10-01-scan.md", "# Scan 2026-10-01\n\n## Fit maps\n\n### A — SWE\n\nURL: https://a.com/1\n"
                                                         "Entries commit: %s\nRecommendation: apply\n\n%s" % (sha, table))
        self.commit("report")

    def test_an_old_map_with_other_columns(self):
        """An entry named under another column still makes the map stale; rows this format cannot read are fitted again."""
        self.old_map("| Requirement | Coverage | Evidence |\n|---|---|---|\n| Go | **covered** | `2025-01-widget.md` |\n")
        code, lines = self.run_tool("fitmap", "https://a.com/1", "--out", "run/fit/a.jsonl")
        self.assertTrue(lines[-1].startswith("fit map: stale (its map's rows do not parse: rows[1].category: ''"), lines)
        self.assertFalse(os.path.exists(os.path.join(self.root, "run/fit/a.jsonl")))
        self.write("entries/2025-01-widget.md", "# Widget\n\nchanged\n")
        self.commit("edit")
        self.assertEqual(self.run_tool("fitmap", "https://a.com/1")[1][-1], "fit map: stale (entries/2025-01-widget.md)")

    def test_an_old_map_with_bold_cells(self):
        self.old_map("| Requirement | Category | Entry |\n|---|---|---|\n| Go | **covered** | `2025-01-widget.md` |\n")
        self.assertEqual(self.run_tool("fitmap", "https://a.com/1", "--out", "run/fit/a.jsonl")[1][-1], "fit map: reuse")
        self.assertEqual(json.loads(self.read("run/fit/a.jsonl"))["rows"][0]["category"], "covered")

    def test_summary_takes_a_trailing_slash_and_rank_two_results_for_one_url(self):
        d, listed = self.run_to_fit()
        c = listed["https://c.com/j/3"]
        self.fit_result(d, c["folder"], c["url"])
        self.fit_result(d, "copy", c["url"])
        code, lines = self.run_tool("rank", d, "--n", "3")
        self.assertEqual(code, 1)
        self.assertIn("bad: fit/copy.jsonl: https://c.com/j/3 has a result in fit/%s.jsonl already" % c["folder"], lines)
        os.remove(os.path.join(self.root, d, "fit", "copy.jsonl"))
        self.run_tool("rank", d, "--n", "3")
        self.run_tool("report", d + "/rows.jsonl", "--name", TODAY, "--screen", d)
        self.assertEqual(self.run_tool("summary", d + "/")[0], 0)

    def test_a_dashboard_error_is_one_line(self):
        """Finding 21: run as a script, scan.py loads dashboard.py, which uses it rather than a second copy;
        an error while regenerating is one line and exit 1, with no traceback."""
        self.report("2026-10-21", [["https://a.com/1", "A", "SWE", "undecided", "-", "-"]])
        self.write("outputs/reports/scan-declined.jsonl", "not json\n")
        p = subprocess.run([sys.executable, "-I", TOOL, "--root", self.root, "status", "https://a.com/1", "accepted"],
                           capture_output=True, encoding="utf-8")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertEqual(p.stderr, "")
        self.assertEqual(p.stdout.splitlines()[-1][:69],
                         "scan: dashboard: outputs/reports/scan-declined.jsonl line 1 does not ")

    def test_no_pycache_left(self):
        """Finding 21: scan.py, fit.py, dashboard.py and sponsorship.py leave no __pycache__ in a clean copy of tools/."""
        tools = os.path.join(self.tmp, "tools")
        os.makedirs(tools)
        for name in ("scan.py", "fit.py", "dashboard.py", "logfiles.py", "entries.py", "sponsorship.py", "config.py",
                     "config.default.toml"):
            shutil.copy(os.path.join(HERE, "..", name), tools)
        self.report("2026-10-21", [["https://a.com/1", "A", "SWE", "undecided", "-", "-"]])
        rows = self.jsonl("rows.jsonl", [{"url": "https://b.com/1", "company": "B", "role": "SWE", "status": "undecided"}])
        env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
        for args in (["dashboard.py", "--root", self.root], ["scan.py", "--root", self.root, "report", rows, "--name", TODAY],
                     ["scan.py", "--root", self.root, "status", "https://a.com/1", "declined"],
                     ["fit.py", "--root", self.root, "check", rows],
                     ["sponsorship.py", "--root", self.root, "need", "--kinds", "lca", "A"]):
            p = subprocess.run([sys.executable, "-I", os.path.join(tools, args[0])] + args[1:], capture_output=True,
                               encoding="utf-8", env=env)
            self.assertIn(p.returncode, (0, 1), p.stdout + p.stderr)
            self.assertEqual(p.stderr, "", args)
        self.assertEqual([d for d, _, _ in os.walk(tools) if os.path.basename(d) == "__pycache__"], [])

    # ---- drafts ----

    DECISIONS = ("| Decision | Chosen | Alternatives | Why |\n|---|---|---|---|\n"
                 "| Which version to start from | backend.tex | data.tex | closest role |\n"
                 "| needs you: the repo's link | GAP | - | resume.tex, the Widget bullet |\n")

    def ready_to_draft(self, remote=True):
        """A run at step 10: c fitted and ranked, the report committed; with remote, pushed."""
        if not remote:
            git(self.root, "remote", "remove", "origin")
        d, listed = self.run_to_fit()
        c = listed["https://c.com/j/3"]
        self.fit_result(d, c["folder"], c["url"])
        code, lines = self.run_tool("rank", d, "--n", "3", "--m", "2")
        self.assertEqual(code, 0, lines)
        self.assertEqual(self.run_tool("report", d + "/rows.jsonl", "--name", TODAY, "--screen", d)[0], 0)
        self.commit("report")
        if remote:
            git(self.root, "push", "-q", "origin", "main")
        return d, c, [l for l in lines if l.startswith("draft: ")]

    def fill(self, folder, answers=False):
        """The files a draft subagent writes into the folder."""
        files = {"resume.tex": "\\documentclass{article}\n% GAP: the repo's link\n", "company.md": "- C: https://c.com\n",
                 "decisions.md": self.DECISIONS, "handoff.md": "https://c.com/j/3\n"}
        if answers:
            files["answers.md"] = "## Why us?\n\nBecause.\n"
        for name, text in files.items():
            with open(os.path.join(self.root, folder, name), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)

    def test_drafts_opens_the_branch_and_copies_capture_and_map(self):
        d, c, rank_lines = self.ready_to_draft()
        code, lines = self.run_tool("drafts", d, "--m", "2")
        self.assertEqual(code, 0, lines)
        folder = ".build/worktrees/scan-2026-10-22/scan-drafts/" + c["folder"]
        self.assertEqual(lines, ["branch: scan/2026-10-22 (from origin/main)", "worktree: .build/worktrees/scan-2026-10-22",
                                 "draft: https://c.com/j/3 | folder %s | capture %s" % (folder, c["capture"]),
                                 "drafts: 1 folder(s), each with posting.md and fit.md"])
        # the same posting rank --m named
        self.assertEqual(rank_lines, ["draft: https://c.com/j/3 | folder %s | capture %s" % (c["folder"], c["capture"])])
        self.assertEqual(self.read(folder + "/posting.md"), self.read(c["capture"]))
        fit_md = self.read(folder + "/fit.md")
        self.assertTrue(fit_md.startswith("### C — SWE\n\nURL: https://c.com/j/3\nScreen: tier 1"), fit_md)
        self.assertIn("| Own the on-call | duty | - | - | gap | - |", fit_md)
        self.assertNotIn("## ", fit_md.replace("### ", ""))
        wt = os.path.join(self.root, ".build/worktrees/scan-2026-10-22")
        self.assertEqual(git(wt, "rev-parse", "--abbrev-ref", "HEAD").strip(), "scan/2026-10-22")
        self.assertEqual(git(wt, "rev-parse", "HEAD"), git(self.root, "rev-parse", "origin/main"))
        # run again: the branch and worktree exist, so it refuses and writes nothing
        code, lines = self.run_tool("drafts", d, "--m", "2")
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["scan: drafts: 2 problem(s); nothing written",
                                 "exists: the branch scan/2026-10-22 (a draft run of this name started already)",
                                 "exists: .build/worktrees/scan-2026-10-22"])

    def test_drafts_refuses_a_branch_another_clone_pushed_and_leaves_nothing(self):
        d, c, _ = self.ready_to_draft()
        other = self.other_clone()
        git(other, "push", "-q", "origin", "HEAD:refs/heads/scan/2026-10-22")
        code, lines = self.run_tool("drafts", d, "--m", "2")
        self.assertEqual(code, 1)
        self.assertIn("exists: the branch scan/2026-10-22 (a draft run of this name started already)", lines)
        self.assertFalse(os.path.exists(os.path.join(self.root, ".build/worktrees")))
        self.assertEqual(git(self.root, "branch", "--list", "scan/*"), "")

    def test_drafts_skips_a_skip_as_rank_does(self):
        d, c, _ = self.ready_to_draft()
        self.write("%s/fit/%s.jsonl" % (d, c["folder"]),
                   json.dumps({"url": c["url"], "recommendation": "skip", "check": [], "notes": [], "rows": self.FIT_ROWS}) + "\n")
        lines = self.run_tool("rank", d, "--n", "3", "--m", "2")[1]
        self.assertEqual([l for l in lines if l.startswith("draft:")], [])
        self.assertEqual(self.run_tool("drafts", d, "--m", "2")[1],
                         ["drafts: none (no posting of rows.jsonl is recommended above skip, or --m is 0)"])
        self.assertEqual([p["url"] for p in scan.draft_picks([{"url": 1, "recommendation": "skip"},
                                                               {"url": 2, "recommendation": "apply"},
                                                               {"url": 3, "recommendation": "apply with caveats"}], 1)], [2])

    def test_drafts_without_a_remote(self):
        d, c, _ = self.ready_to_draft(remote=False)
        code, lines = self.run_tool("drafts", d, "--m", "1")
        self.assertEqual(code, 0, lines)
        folder = ".build/scan/2026-10-22/drafts/" + c["folder"]
        self.assertEqual(lines[0], "draft: https://c.com/j/3 | folder %s | capture %s" % (folder, c["capture"]))
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, folder))), ["fit.md", "posting.md"])
        self.assertEqual(self.run_tool("drafts", d, "--m", "1")[1][1], "exists: " + folder)

    def test_drafts_check(self):
        folder = ".build/drafts-check/x"
        self.write(folder + "/posting.md", "https://c.com/j/3\n\ntext\n")
        self.write(folder + "/fit.md", "### C — SWE\n")
        self.fill(folder)
        self.assertEqual(self.run_tool("drafts", "--check", folder), (0, ["check: ok"]))   # no answers.md: still ok
        self.fill(folder, answers=True)
        self.assertEqual(self.run_tool("drafts", "--check", folder), (0, ["check: ok"]))
        self.write(folder + "/resume.pdf", "%PDF")
        os.remove(os.path.join(self.root, folder, "handoff.md"))
        self.write(folder + "/decisions.md", self.DECISIONS.replace("| needs you: the repo's link | GAP | - |",
                                                                    "| needs you: the repo's link | missing | - |"))
        code, lines = self.run_tool("drafts", "--check", folder)
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["missing: handoff.md",
                                 "extra: resume.pdf (a draft folder holds no PDF: the accept builds it)",
                                 "bad: decisions.md line 4: a needs-you row is | needs you: <what> | GAP | - | <where it appears> |",
                                 "check: 3 problem(s)"])
        self.write(folder + "/decisions.md", "| Decision | Choice | Why |\n|---|---|---|\n")
        self.assertIn("bad: decisions.md: its table's header must be | Decision | Chosen | Alternatives | Why |",
                      self.run_tool("drafts", "--check", folder)[1])
        self.assertEqual(self.run_tool("drafts", "--check", folder, "--m", "1")[0], 2)
        self.assertEqual(self.run_tool("drafts", ".build/scan/" + TODAY)[0], 2)

    def drafted(self):
        """drafts run, the folder filled and committed in the worktree; (d, c, worktree, folder)."""
        d, c, _ = self.ready_to_draft()
        self.assertEqual(self.run_tool("drafts", d, "--m", "2")[0], 0)
        wt = os.path.join(self.root, ".build/worktrees/scan-2026-10-22")
        self.fill(".build/worktrees/scan-2026-10-22/scan-drafts/" + c["folder"])
        git(wt, "add", "-A")
        git(wt, "commit", "-q", "-m", "scan(2026-10-22): drafts for 1 postings")
        self.write(".playwright-cli/x.log", "x")
        return d, c, wt

    def test_drafts_save(self):
        d, c, wt = self.drafted()
        git(wt, "push", "-q", "-u", "origin", "HEAD:refs/heads/scan/2026-10-22")
        code, lines = self.run_tool("drafts", d, "--save")
        self.assertEqual(code, 0, lines)
        cell = "scan/2026-10-22:scan-drafts/" + c["folder"]
        self.assertEqual(lines, ["outputs/reports/2026-10-22-scan.md: https://c.com/j/3: undecided -> draft to review; draft - -> %s" % cell,
                                 "removed: the worktree .build/worktrees/scan-2026-10-22 (origin/scan/2026-10-22 keeps the drafts)",
                                 "wrote: outputs/dashboard/dashboard.html", "artifact: none", "deleted: .playwright-cli/",
                                 "commit: scan(2026-10-22): 1 drafts"])
        self.assertFalse(os.path.exists(wt))
        self.assertFalse(os.path.exists(os.path.join(self.root, ".playwright-cli")))
        self.assertIn("| https://c.com/j/3 | C | SWE | draft to review | %s |" % cell, self.read("outputs/reports/2026-10-22-scan.md"))
        # an earlier --save removed the worktree, then stopped: a rerun sets the same cell again
        code, lines = self.run_tool("drafts", d, "--save")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[-1], "commit: scan(2026-10-22): 1 drafts")

    def test_drafts_save_refuses_when_the_push_failed(self):
        d, c, wt = self.drafted()   # committed, never pushed: the push was refused
        before = self.read("outputs/reports/2026-10-22-scan.md")
        code, lines = self.run_tool("drafts", d, "--save")
        self.assertEqual(code, 1)
        self.assertRegex(lines[0], r"^scan: save: refused: the branch is not pushed \(origin/scan/2026-10-22 lacks the worktree's HEAD \w{7}\); nothing changed$")
        self.assertEqual(lines[1], "branch: scan/2026-10-22")
        self.assertTrue(lines[2].startswith("next: run step 5.1's sync.py commit again (it retries the push)"), lines)
        self.assertTrue(os.path.isdir(wt))
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".playwright-cli")))
        self.assertEqual(self.read("outputs/reports/2026-10-22-scan.md"), before)
        # a later commit not pushed either
        git(wt, "push", "-q", "-u", "origin", "HEAD:refs/heads/scan/2026-10-22")
        self.write(".build/worktrees/scan-2026-10-22/scan-drafts/%s/handoff.md" % c["folder"], "more\n")
        self.assertIn("has uncommitted changes", self.run_tool("drafts", d, "--save")[1][0])
        git(wt, "commit", "-q", "-am", "more")
        self.assertIn("the branch is not pushed", self.run_tool("drafts", d, "--save")[1][0])

    def test_drafts_save_refuses_a_folder_the_check_fails(self):
        d, c, wt = self.drafted()
        os.remove(os.path.join(wt, "scan-drafts", c["folder"], "handoff.md"))
        git(wt, "commit", "-q", "-am", "no handoff")
        git(wt, "push", "-q", "-u", "origin", "HEAD:refs/heads/scan/2026-10-22")
        code, lines = self.run_tool("drafts", d, "--save")
        self.assertEqual((code, lines[:2]), (1, ["scan: save: refused: 1 problem(s); nothing changed",
                                                 "%s: missing: handoff.md" % c["folder"]]))
        self.assertTrue(lines[2].startswith("next: fix each one named as scan.md › Draft a posting step 4 says"), lines)
        self.assertTrue(os.path.isdir(wt))

    def test_drafts_save_without_a_remote(self):
        d, c, _ = self.ready_to_draft(remote=False)
        self.run_tool("drafts", d, "--m", "1")
        folder = ".build/scan/2026-10-22/drafts/" + c["folder"]
        self.fill(folder)
        code, lines = self.run_tool("drafts", d, "--save")
        self.assertEqual(code, 0, lines)
        self.assertIn("| https://c.com/j/3 | C | SWE | draft to review | %s |" % folder, self.read("outputs/reports/2026-10-22-scan.md"))
        # draft reads it where it is, on this machine
        code, lines = self.run_tool("draft", "https://c.com/j/3")
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines[1], "folder: .build/drafts/%s/" % c["folder"])
        shutil.rmtree(os.path.join(self.root, folder))
        self.assertIn("is not on this machine", self.run_tool("draft", "https://c.com/j/3", "--out", "x")[1][0])

    def test_drafts_refuses_without_a_report_or_a_map(self):
        d, c, _ = self.ready_to_draft()
        report = os.path.join(self.root, "outputs/reports/2026-10-22-scan.md")
        text = self.read("outputs/reports/2026-10-22-scan.md")
        self.write("outputs/reports/2026-10-22-scan.md", text[:text.index("## Fit maps")])
        os.remove(os.path.join(self.root, c["capture"]))
        code, lines = self.run_tool("drafts", d, "--m", "1")
        self.assertEqual((code, lines[0]), (1, "scan: drafts: 2 problem(s); nothing written"))
        self.assertIn("no capture: %s (https://c.com/j/3)" % c["capture"], lines)
        os.remove(report)
        self.assertEqual(self.run_tool("drafts", d, "--m", "1")[1],
                         ["scan: no report outputs/reports/2026-10-22-scan.md yet: write it (step 9) first"])
        self.assertFalse(os.path.exists(os.path.join(self.root, ".build/worktrees")))

    def test_drafts_save_checks_origins_copy_once_the_worktree_is_gone(self):
        d, c, wt = self.drafted()
        os.remove(os.path.join(wt, "scan-drafts", c["folder"], "company.md"))
        git(wt, "commit", "-q", "-am", "no company")
        git(wt, "push", "-q", "-u", "origin", "HEAD:refs/heads/scan/2026-10-22")
        git(self.root, "worktree", "remove", wt)
        code, lines = self.run_tool("drafts", d, "--save")
        self.assertEqual((code, lines[1]), (1, "%s: missing: company.md" % c["folder"]))
        self.assertNotIn("draft to review", self.read("outputs/reports/2026-10-22-scan.md"))

    def test_drafts_save_refuses_a_stray_file_and_a_row_missing(self):
        d, c, wt = self.drafted()
        self.write(".build/worktrees/scan-2026-10-22/scan-drafts/notes.txt", "x\n")
        git(wt, "add", "-A")
        git(wt, "commit", "-q", "-m", "notes")
        git(wt, "push", "-q", "-u", "origin", "HEAD:refs/heads/scan/2026-10-22")
        code, lines = self.run_tool("drafts", d, "--save")
        self.assertEqual(code, 1)
        self.assertIn("notes.txt: not a folder (a draft is a folder)", lines)
        self.assertIn("no posting: notes.txt is no folder of ranked.jsonl", lines)
        git(wt, "rm", "-q", "scan-drafts/notes.txt")
        git(wt, "commit", "-q", "-m", "no notes")
        git(wt, "push", "-q", "origin", "HEAD:refs/heads/scan/2026-10-22")
        self.write("outputs/reports/2026-10-22-scan.md", self.read("outputs/reports/2026-10-22-scan.md").replace("https://c.com/j/3", "https://moved.com/1"))
        code, lines = self.run_tool("drafts", d, "--save")
        self.assertIn("no row: https://c.com/j/3 (%s) is in no report's Pending table" % c["folder"], lines)
        self.assertTrue(lines[-1].startswith("next: fix each one named"), lines)

    def test_drafts_save_keeps_a_worktree_git_cannot_remove(self):
        d, c, wt = self.drafted()
        git(wt, "push", "-q", "-u", "origin", "HEAD:refs/heads/scan/2026-10-22")
        self.write(".build/worktrees/scan-2026-10-22/README.md", "changed outside the drafts\n")
        code, lines = self.run_tool("drafts", d, "--save")
        self.assertEqual(code, 0, lines)
        self.assertTrue(any(l.startswith("kept: the worktree .build/worktrees/scan-2026-10-22 (git could not remove it")
                            for l in lines), lines)
        self.assertEqual(lines[-1], "commit: scan(2026-10-22): 1 drafts")
        self.assertTrue(os.path.isdir(wt))

    def test_draft_reads_a_pushed_draft_in_another_clone(self):
        d, c, wt = self.drafted()
        git(wt, "push", "-q", "-u", "origin", "HEAD:refs/heads/scan/2026-10-22")
        self.run_tool("drafts", d, "--save")
        self.commit("drafts")
        git(self.root, "push", "-q", "origin", "main")
        other = self.other_clone()

        def draft(*args):
            out = io.StringIO()
            with redirect_stdout(out):
                code = scan.main(["--root", other, "draft", "https://c.com/j/3"] + list(args))
            return code, out.getvalue().splitlines()
        code, lines = draft()
        self.assertEqual(code, 0, lines)
        here = ".build/drafts/" + c["folder"]
        self.assertEqual(lines, ["draft: https://c.com/j/3 | scan/2026-10-22:scan-drafts/" + c["folder"],
                                 "folder: %s/" % here,
                                 "files: company.md, decisions.md, fit.md, handoff.md, posting.md, resume.tex",
                                 "needs you: the repo's link | resume.tex, the Widget bullet"])
        with open(os.path.join(other, here, "decisions.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), self.DECISIONS)
        # the same files again (Look, then Accept), a build's own files beside them: fine
        with open(os.path.join(other, here, "resume.pdf"), "w") as f:
            f.write("%PDF")
        self.assertEqual(draft()[0], 0)
        # a file there that differs: refused, nothing overwritten
        with open(os.path.join(other, here, "resume.tex"), "a", encoding="utf-8") as f:
            f.write("% edited\n")
        code, lines = draft()
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["scan: %s holds a different resume.tex; nothing written" % here,
                                 "next: it is this draft from an earlier look, accept or build: use the draft there as"
                                 " it is (or give --out <another folder> for the draft as it was saved)"])
        self.assertEqual(draft("--out", ".build/elsewhere")[0], 0)

    def test_draft_refuses_a_pruned_or_missing_draft(self):
        self.report("2026-10-21", [["https://a.com/1", "A", "SWE", "undecided", "pruned (scan/2026-07-01)", "-"],
                                   ["https://b.com/2", "B", "SWE", "undecided", "-", "-"],
                                   ["https://c.com/3", "C", "SWE", "accepted", "outputs/applications/x/", "-"]])
        code, lines = self.run_tool("draft", "https://a.com/1")
        self.assertEqual(code, 1)
        self.assertIn("its branch deleted (pruned (scan/2026-07-01))", lines[0])
        self.assertEqual(self.run_tool("draft", "https://b.com/2")[1],
                         ["scan: https://b.com/2 has no draft",
                          "next: treat it as a posting with no draft (scan-results.md › Look at a posting with no"
                          " draft; an accept is an ordinary write posting run)"])
        self.assertIn("is accepted, not a draft", self.run_tool("draft", "https://c.com/3")[1][0])
        self.assertIn("is in no scan report", self.run_tool("draft", "https://z.com/9")[1][0])
        self.assertFalse(os.path.exists(os.path.join(self.root, ".build/drafts")))

    def test_bad_date(self):
        self.assertEqual(self.run_tool("name", date="22-10-2026")[0], 2)


if __name__ == "__main__":
    unittest.main()
