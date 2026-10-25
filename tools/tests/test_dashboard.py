#!/usr/bin/env python3
"""Tests for tools/dashboard.py, on Logs made in a temporary directory (a git repo).

  python3 -I tools/tests/test_dashboard.py
"""
import importlib.util, io, json, os, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout

sys.dont_write_bytecode = True   # the tool loaded below leaves no tools/__pycache__
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "dashboard.py")
spec = importlib.util.spec_from_file_location("dashboard", TOOL)
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)

REPORT = """# Scan {name}

{top}

## Pending

| URL | Company | Role | Status | Draft | Fit map commit |
|---|---|---|---|---|---|
{rows}

## Ranking

| Rank | Company | Role | Recommendation |
|---|---|---|---|
| 1 | {company} | Platform Engineer | apply |

## Dropped at screen

| URL | Company | Role | Reason | Screen key |
|---|---|---|---|---|
| https://jobs.example.com/d1 | Dropco | Sales | on-site only | aaaaaaaa-bbbbbbbb |

## Screened, not fully fitted

| Company | Role | URL | Tier | Rough | Screen key |
|---|---|---|---|---|---|
| Laterco | SRE | https://jobs.example.com/s1 | 2 | 1/4 | aaaaaaaa-bbbbbbbb |

## Fit maps

### {company} — Platform Engineer

URL: https://jobs.example.com/p1
Entries commit: {sha}

| Requirement | Entry |
|---|---|
| Kubernetes | 2030-01-widget.md |
"""

DIRECTION = """# Direction

## Target roles, ranked

1. Platform engineer
2. SRE

## Constraints
Hard constraints: a role that breaks one is out. Guidance, not a constraint.
<!-- a comment
   over two lines -->

- Remote or within 30 minutes
  (user, 2026-10-01)
"""


def git(root, *args):
    return subprocess.run(["git", "-C", root] + list(args), capture_output=True, encoding="utf-8", check=True).stdout


class DashboardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.root = os.path.join(self.tmp, "log")
        subprocess.run(["git", "init", "-q", "-b", "main", self.root], check=True)
        git(self.root, "config", "user.email", "t@example.invalid")
        git(self.root, "config", "user.name", "T")
        git(self.root, "config", "commit.gpgsign", "false")
        self.write("entries/2030-01-widget.md", "# widget\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "seed")
        self.sha = git(self.root, "rev-parse", "--short", "HEAD").strip()

    def write(self, rel, text):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return p

    def report(self, name, company="Acme", top="All sources read.", rows=None):
        if rows is None:
            rows = "| https://jobs.example.com/p1 | %s | Platform Engineer | undecided | - | %s |" % (company, self.sha)
        self.write("outputs/reports/%s-scan.md" % name, REPORT.format(name=name, top=top, rows=rows, company=company, sha=self.sha))

    def run_tool(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = dashboard.main(["--root", self.root] + list(args))
        return code, buf.getvalue().splitlines()

    def page(self):
        with open(os.path.join(self.root, dashboard.OUT), encoding="utf-8", newline="") as f:
            return f.read()

    # ---- tests ----

    def test_empty_log(self):
        code, out = self.run_tool()
        self.assertEqual(code, 0)
        self.assertEqual(out, ["wrote: outputs/dashboard/dashboard.html", "artifact: none"])
        page = self.page()
        self.assertIn("<title>Scan Dashboard</title>", page)
        self.assertIn("No scan report yet.", page)
        self.assertIn("None pending.", page)

    def test_sections_from_the_log(self):
        self.write("direction.md", DIRECTION)
        self.report("2026-10-20", company="Oldco", top="Board skipped: sign-in expired.")
        self.report("2026-10-22")
        self.write("outputs/reports/scan-declined.jsonl",
                   json.dumps({"url": "https://jobs.example.com/p1?utm_source=x", "date": "2026-10-22",
                               "reason": "too far"}) + "\n")
        self.write("outputs/applications/2026-09-01-acme-backend/posting.md", "https://acme.example.com/jobs/7\n\ntext\n")
        self.write("outputs/applications/2026-09-01-acme-backend/archived.md", "Archived (user, 2026-09-02)\n")
        self.write("outputs/applications/2026-10-01-beta-sre/posting.md", "no url here\n")
        self.assertEqual(self.run_tool()[0], 0)
        page = self.page()
        self.assertIn("Newest scan: <code>outputs/reports/2026-10-22-scan.md</code>", page)
        self.assertIn("<li>Platform engineer</li>", page)
        self.assertIn("<li>Remote or within 30 minutes (user, 2026-10-01)</li>", page)
        self.assertNotIn("Guidance", page)
        self.assertNotIn("comment", page)
        # Pending: the newest report's row, as written
        self.assertIn("<td>Acme</td><td>Platform Engineer</td><td>undecided</td><td>-</td><td>%s</td>" % self.sha, page)
        # Ranking as written, Screened, not fully fitted from its table
        self.assertIn("<td>1</td><td>Acme</td><td>Platform Engineer</td><td>apply</td>", page)
        self.assertIn("<td>Laterco</td><td>SRE</td>", page)
        # Declined, joined to the newest row of its URL through the canonical form
        self.assertIn("<td>2026-10-22</td><td>Acme</td><td>Platform Engineer</td><td>too far</td>", page)
        # Applications, newest first, with their level and posting URL
        self.assertLess(page.index("beta-sre"), page.index("acme-backend"))
        self.assertIn("<td>2026-09-01</td><td>acme-backend</td><td>Archived</td>"
                      '<td><a href="https://acme.example.com/jobs/7"', page)
        self.assertIn("<td>2026-10-01</td><td>beta-sre</td><td>Reference</td><td>-</td>", page)
        # History, newest first, with its counts
        self.assertLess(page.index("<td>2026-10-22-scan</td>"), page.index("<td>2026-10-20-scan</td>"))
        self.assertIn("<td>2026-10-20-scan</td><td>Board skipped: sign-in expired.</td><td>1 undecided</td>"
                      "<td>1</td><td>1</td><td>1</td>", page)

    def test_entry_commit_keeps_the_page(self):
        """The page reads the Log's files, not git history: an entry edit after it leaves it up to date."""
        self.report("2026-10-22")
        self.run_tool()
        self.write("entries/2030-01-widget.md", "# widget\n\nchanged\n")
        git(self.root, "commit", "-qam", "edit")
        self.assertEqual(self.run_tool("--check"), (0, ["dashboard: up to date"]))

    def test_log_text_is_escaped(self):
        rows = "| javascript:alert(1) | <script>x</script> | R&D | undecided | - | %s |" % self.sha
        self.report("2026-10-22", rows=rows)
        self.run_tool()
        page = self.page()
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", page)
        self.assertIn("R&amp;D", page)
        self.assertNotIn('href="javascript', page)

    def test_ranking_markdown(self):
        self.report("2026-10-22")
        p = os.path.join(self.root, "outputs/reports/2026-10-22-scan.md")
        with open(p, encoding="utf-8") as f:
            text = f.read()
        ranking = ("### Top\n\n1. **Acme**: [posting](https://jobs.example.com/p1\"onmouseover=x) and `code`\n"
                   "2. Beta <b>bold</b>\n\n- note\n")
        text = text.replace("| Rank | Company | Role | Recommendation |", ranking + "\n| Rank | Company | Role | Recommendation |")
        self.write("outputs/reports/2026-10-22-scan.md", text)
        self.run_tool()
        page = self.page()
        self.assertIn("<h5>Top</h5>", page)
        self.assertIn("<ol><li><strong>Acme</strong>: ", page)
        self.assertIn("<code>code</code>", page)
        self.assertIn("<li>Beta &lt;b&gt;bold&lt;/b&gt;</li></ol>", page)
        self.assertIn("<ul><li>note</li></ul>", page)
        self.assertNotIn('"onmouseover', page)

    def test_same_log_same_bytes(self):
        self.report("2026-10-22")
        self.run_tool()
        first = self.page()
        self.assertEqual(self.run_tool(), (0, ["unchanged: outputs/dashboard/dashboard.html", "artifact: none"]))
        self.assertEqual(self.page(), first)
        self.assertNotIn("\r", first)

    def test_check(self):
        self.assertEqual(self.run_tool("--check"), (1, ["dashboard: missing"]))
        self.assertFalse(os.path.exists(os.path.join(self.root, dashboard.OUT)))
        self.run_tool()
        self.assertEqual(self.run_tool("--check"), (0, ["dashboard: up to date"]))
        self.report("2026-10-22")
        self.assertEqual(self.run_tool("--check"), (1, ["dashboard: stale"]))

    def test_artifact_line(self):
        self.write(dashboard.ARTIFACT, "Artifact:\nnot-a-url\n")
        self.assertEqual(self.run_tool()[1][-1], "artifact: none")
        self.write(dashboard.ARTIFACT, "# Dashboard\n\nArtifact: https://claude.ai/artifact/abc\n")
        self.assertEqual(self.run_tool()[1][-1], "artifact: https://claude.ai/artifact/abc")

    def test_artifact_writes_the_line(self):
        url = "https://claude.ai/artifact/abc"
        self.assertEqual(self.run_tool("--artifact", url),
                         (0, ["wrote: outputs/dashboard/artifact.md", "artifact: " + url, "commit: dashboard: artifact"]))
        with open(os.path.join(self.root, dashboard.ARTIFACT), encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), "Artifact: %s\n" % url)
        self.assertEqual(self.run_tool("--artifact", url), (0, ["unchanged: outputs/dashboard/artifact.md", "artifact: " + url]))
        self.assertEqual(self.run_tool()[1][-1], "artifact: " + url)
        self.assertEqual(self.run_tool("--artifact", "not-a-url")[0], 1)
        self.assertEqual(self.run_tool("--artifact", url, "--check")[0], 2)

    def test_bad_declined_file(self):
        self.write("outputs/reports/scan-declined.jsonl", "not json\n")
        code, out = self.run_tool()
        self.assertEqual(code, 1)
        self.assertTrue(out[0].startswith("dashboard: outputs/reports/scan-declined.jsonl line 1"))

    def test_odd_declined_lines(self):
        self.write("outputs/reports/scan-declined.jsonl",
                   '["a list"]\n{"url": "https://jobs.example.com/x", "date": 20261022, "reason": null}\n'
                   '{"url": "http://[", "date": "2026-10-21"}\n')
        self.assertEqual(self.run_tool()[0], 0)
        self.assertIn("<td>20261022</td><td>-</td><td>-</td><td>-</td>", self.page())
        self.assertIn("<td>2026-10-21</td><td>-</td><td>-</td><td>-</td>", self.page())

    def test_decided_rows_leave_pending(self):
        rows = ("| https://jobs.example.com/p1 | Acme | Platform Engineer | declined | - | %s |\n"
                "| https://jobs.example.com/p2 | Beta | SRE | draft to review | scan/2026-10-22:scan-drafts/b | %s |"
                % (self.sha, self.sha))
        self.report("2026-10-22", rows=rows)
        self.run_tool()
        pending = self.page().split("<h2>Pending</h2>")[1].split("</section>")[0]
        self.assertNotIn("Acme", pending)
        self.assertIn("<td>Beta</td><td>SRE</td><td>draft to review</td>", pending)

    def test_archived_marker_is_exact(self):
        self.write("outputs/applications/2026-09-01-acme-backend/Archived.md", "x\n")
        self.run_tool()
        self.assertIn("<td>acme-backend</td><td>Reference</td>", self.page())

    def test_runs_isolated(self):
        """`-I` leaves the script's folder off sys.path: the tool still finds scan.py."""
        p = subprocess.run([sys.executable, "-I", TOOL, "--root", self.root, "--check"], capture_output=True,
                           encoding="utf-8")
        self.assertEqual((p.returncode, p.stdout.strip()), (1, "dashboard: missing"))


if __name__ == "__main__":
    unittest.main()
