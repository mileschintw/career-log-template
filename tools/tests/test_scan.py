#!/usr/bin/env python3
"""Tests for tools/scan.py, on Logs made in a temporary directory (a git repo with a bare origin).

  python3 -I tools/tests/test_scan.py
"""
import importlib.util, io, json, os, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "scan.py")
spec = importlib.util.spec_from_file_location("scan", TOOL)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)

TODAY = "2026-10-22"
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
        self.assertEqual(lines, ["report: outputs/reports/2026-10-22-scan.md", "branch: scan/2026-10-22",
                                 "worktree: .build/worktrees/scan-2026-10-22", "drafts: .build/scan/2026-10-22/drafts",
                                 "remote: yes"])
        self.report("2026-10-22", [])
        self.assertEqual(self.run_tool("name")[1][0], "report: outputs/reports/2026-10-22-scan-2.md")
        self.branch("scan/2026-10-22-2")
        self.assertEqual(self.run_tool("name")[1][1], "branch: scan/2026-10-22-3")

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
        self.assertEqual(lines[-1], "kept: 3 (2 new, 1 listed before); dropped: 6; written to %s" % out)

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
        self.assertEqual(lines, ["wrote outputs/reports/2026-10-22-scan.md: 4 row(s), 2 carried over"])
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
        self.assertEqual(len(lines), 5)
        self.assertEqual(self.run_tool("report", rows)[1], ["wrote outputs/reports/2026-10-22-scan-2.md: 4 row(s), 2 carried over"])
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
        self.assertEqual(lines, ["https://screened.com/1: in no Pending table", "%s: added https://screened.com/1" % scan.DECLINED])
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
                         "pending: http://127.0.0.1:8765/initech/jobs/2?utm_source=x | I | SWE | undecided | -")

    def test_report_keeps_a_relisted_draft(self):
        self.branch("scan/2026-10-20")
        self.report("2026-10-20", [["https://a.com/1", "A", "SWE", "draft to review", "scan/2026-10-20:scan-drafts/a", "abc1234"]])
        rows = self.jsonl("rows.jsonl", [{"url": "https://www.a.com/1/", "company": "A", "role": "SWE", "status": "undecided",
                                          "draft": "", "fit_commit": "def5678"}])
        code, lines = self.run_tool("report", rows)
        self.assertEqual(lines, ["wrote outputs/reports/2026-10-22-scan.md: 1 row(s), 0 carried over"])
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
        self.assertEqual(self.run_tool("name")[1][1], "branch: scan/2026-10-22-2")
        os.makedirs(os.path.join(self.root, ".build", "scan", "2026-10-22-2"))
        self.assertEqual(self.run_tool("name")[1][1], "branch: scan/2026-10-22-3")

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

    def screen_log(self, n=5):
        self.write("entries/2025-01-widget.md", "# Widget\n")
        self.write("direction.md", self.DIRECTION)
        self.commit("entries")
        d = os.path.join(self.root, ".build", "scan", TODAY)
        self.jsonl(".build/scan/%s/prefiltered.jsonl" % TODAY,
                   [{"url": "https://c%d.com/j/%d" % (i, i), "company": "C%d" % i, "role": "SWE", "source": "list"}
                    for i in range(n)] + [{"url": "https://c9.com/j/9", "company": "C0", "role": "SWE", "source": "list"}])
        return d

    def result(self, d, name, items):
        self.jsonl(os.path.relpath(os.path.join(d, "screen", name), self.root), items)

    def rows(self, required, touched):
        return [{"requirement": "r%d" % i, "kind": "required", "entries": ["2025-01-widget.md"] if i < touched else []}
                for i in range(required)] + [{"requirement": "nice", "kind": "preferred", "entries": []}]

    def test_screen_budgets_must_hold_the_fit(self):
        d = self.screen_log()
        code, lines = self.run_tool("screen", d, "--screen-budget", "3", "--fit-budget", "4")
        self.assertEqual(code, 1)
        self.assertIn("screen_budget (3) is below fit_budget (4)", lines[0])

    def test_screen_prepare_sort_and_report(self):
        d = self.screen_log(5)
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
        d = self.screen_log(5)
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

    def test_bad_date(self):
        self.assertEqual(self.run_tool("name", date="22-10-2026")[0], 2)


if __name__ == "__main__":
    unittest.main()
