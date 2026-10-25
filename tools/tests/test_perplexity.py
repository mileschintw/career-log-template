#!/usr/bin/env python3
"""Tests for tools/perplexity-list.js, perplexity-job.js and perplexity-extras.js, run with Node against a
made-up Perplexity API (perplexity_fake.js) through perplexity_harness.js. Needs `node` on PATH.

  python3 -I tools/tests/test_perplexity.py
"""
import importlib.util, json, os, shutil, subprocess, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, ".."))
LIST, JOB, EXTRAS = (os.path.join(TOOLS, f"perplexity-{n}.js") for n in ("list", "job", "extras"))
spec = importlib.util.spec_from_file_location("chat_export", os.path.join(TOOLS, "chat_export.py"))
chat_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chat_export)

NODE = shutil.which("node")


class ScriptFormTest(unittest.TestCase):
    def test_each_script_ends_on_its_function(self):
        """run-code wraps the file as `await (<file>)`: a `;` or a comment after the function breaks it."""
        for path in (LIST, JOB, EXTRAS):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.assertTrue(text.startswith("// "), path)
            self.assertTrue(text.rstrip().endswith("})"), path)


def run(fake, *steps, keep=(), settle=False, delay=0, url=None):
    """Runs the steps (a script path, or a dict of window variables to set) in one page; returns
    (each script's result, the kept window variables, the calls made)."""
    case = {"spec": fake, "steps": [{"run": s} if isinstance(s, str) else {"set": s} for s in steps],
            "keep": list(keep), "settle": settle, "delay": delay, "url": url}
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "case.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(case, f)
        p = subprocess.run([NODE, os.path.join(HERE, "perplexity_harness.js"), path], capture_output=True,
                           encoding="utf-8")
    if p.returncode:
        raise AssertionError(p.stderr)
    out = json.loads(p.stdout)
    return out["results"], out["window"], out["calls"]


@unittest.skipUnless(NODE, "needs node on PATH")
class ListTest(unittest.TestCase):
    def test_small_account(self):
        """Both directions meet, so the listing is complete; a project's threads get its space."""
        fake = {"threads": 7, "projects": [{"title": "Work", "uuid": "u1", "slug": "work", "threads": [1, 3]}]}
        (r,), w, calls = run(fake, LIST, keep=["__threads", "__projects"])
        self.assertEqual((r["threads"], r["added"], r["complete"], r["projects"], r["project_threads"]), (7, 7, True, 1, 2))
        self.assertEqual([t["space"] for t in w["__threads"]], ["", "Work", "", "Work", "", "", ""])
        self.assertEqual(w["__projects"], [{"title": "Work", "uuid": "u1", "slug": "work", "instructions": "", "description": ""}])
        self.assertEqual(len(r["next"]), 2)
        self.assertIn('eval "() => window.__threads" --filename=<scratch>/perplexity-threads.json', r["next"][0])
        self.assertIn("run-code --filename=<root>/tools/perplexity-job.js", r["next"][1])
        self.assertIn("POST /rest/thread/list_ask_threads", calls)

    def test_short_pages_before_the_end(self):
        """A page short of the limit is not the end: the listing goes on until has_next_page is false."""
        fake = {"threads": 350, "hidden": [5, 120, 121, 260]}
        (r,), w, calls = run(fake, LIST, keep=["__threads"])
        self.assertEqual((r["threads"], r["newest_first"], r["complete"]), (346, 346, True))
        self.assertNotIn("t120", {t["slug"] for t in w["__threads"]})

    def test_short_page_ends_a_listing_without_has_next_page(self):
        (r,), _, _ = run({"threads": 150, "noNext": True}, LIST)
        self.assertEqual((r["threads"], r["complete"]), (150, True))

    def test_wrapped_listings(self):
        """A listing that comes as an object holding the array is read the same."""
        fake = {"threads": 3, "wrap": True, "projects": [{"title": "P", "uuid": "u", "slug": "p", "threads": [0]}]}
        (r,), w, _ = run(fake, LIST, keep=["__threads"])
        self.assertEqual((r["threads"], r["complete"], w["__threads"][0]["space"]), (3, True, "P"))

    def test_capped_account_then_search_words(self):
        """Past the cap the directions do not meet: the output asks for search words, and a run with them adds
        what they find to the threads already listed."""
        fake = {"threads": 2500, "words": ["python", "notes"], "cap": 1000}
        first, second = run(fake, LIST, {"__terms": ["python"]}, LIST)[0]
        self.assertEqual((first["threads"], first["complete"]), (2000, False))
        self.assertIn("Some listings stopped early", first["next"][0])
        self.assertIn("window.__terms", first["next"][1])
        self.assertIn("may be incomplete", first["next"][1])
        self.assertEqual(second["searched"], ["python"])
        self.assertGreater(second["added"], 0)
        self.assertIn("add new career and technical words", second["next"][1])

    def test_page_error_past_the_cap_ends_that_listing(self):
        fake = {"threads": 1200, "cap": 1000, "capError": True}
        (r,), _, _ = run(fake, LIST)
        self.assertEqual((r["errors"], r["threads"], len(r["stopped"])), ([], 1200, 2))
        self.assertIn("newest first at offset 1000: HTTP 400", r["stopped"][0])

    def test_failing_project_is_stopped_not_fatal(self):
        """A project whose listing fails is reported under stopped; the others and the steps go on."""
        fake = {"threads": 4, "projects": [{"title": "Gone", "uuid": "g", "slug": "gone", "threads": [0], "broken": True},
                                           {"title": "Work", "uuid": "w", "slug": "work", "threads": [1]}]}
        (r,), w, _ = run(fake, LIST, keep=["__threads"])
        self.assertEqual((r["errors"], r["stopped"]), ([], ["project gone at offset 0: HTTP 500 from /rest/collections/list_collection_threads"]))
        self.assertEqual(w["__threads"][1]["space"], "Work")
        self.assertIn("Some listings stopped early", r["next"][0])
        self.assertIn("perplexity-job.js", r["next"][-1])

    def test_no_page(self):
        for script in (LIST, JOB, EXTRAS):
            (r,), _, calls = run({}, script, url="about:blank")
            self.assertEqual((r["state"], calls), ("no page", []))

    def test_signed_out(self):
        (r,), _, _ = run({"unauth": True}, LIST)
        self.assertEqual(len(r["errors"]), 1)
        self.assertEqual(len(r["next"]), 1)
        self.assertIn("Sign-in item 3", r["next"][0])

    def test_empty_account(self):
        (r,), _, _ = run({"threads": 0}, LIST)
        self.assertEqual(len(r["next"]), 1)
        self.assertIn("listing is empty", r["next"][0])


@unittest.skipUnless(NODE, "needs node on PATH")
class JobTest(unittest.TestCase):
    def test_capture_reads_in_the_chat_parser(self):
        """Every page of a thread is followed; the capture is what tools/chat_export.py reads."""
        fake = {"threads": 2, "entries": 3, "pageSize": 2,
                "projects": [{"title": "Work", "uuid": "u1", "slug": "work", "threads": [1]}]}
        (_, r), w, _ = run(fake, LIST, JOB, keep=["__cap"])
        self.assertEqual((r["state"], r["captured"], r["failed"], r["threads"]), ("done", 2, 0, 2))
        self.assertEqual(r["next"], ['Write the capture (create <scratch>/capture/ first): playwright-cli -s=<name> eval "() => window.__cap"'
                                     ' --filename=<scratch>/capture/perplexity-capture.json. Check: the file lists 2 threads.',
                                     "Then go on with import-web.md step 4."])
        cap = sorted(w["__cap"], key=lambda t: t["slug"])
        self.assertEqual([len(t["entries"]) for t in cap], [3, 3])
        self.assertEqual(cap[1]["space"], "Work")
        self.assertEqual(cap[0]["entries"][0], {"t": "2030-01-01T00:00:00Z", "q": "question 0 of t0", "a": "answer 0 of t0",
                                                "att": ["report.pdf?sig=x", "notes.txt"]})
        convs = chat_export.read_perplexity(cap)
        self.assertEqual([(c["id"], c["space"], len(c["messages"])) for c in convs], [("t0", "", 6), ("t1", "Work", 6)])
        self.assertIn("[attachments: report.pdf, notes.txt]", convs[0]["messages"][0]["text"])

    def test_retry_once_then_report(self):
        """A failed thread is retried on the next run; one that fails again is listed, not retried again."""
        fake = {"threads": 3, "fail": {"t1": 1, "t2": 5}}
        (_, a, b, c), w, _ = run(fake, LIST, JOB, JOB, JOB, keep=["__err"])
        self.assertEqual((a["captured"], a["failed"]), (1, 2))
        self.assertIn("retries the 2 failed threads once", a["next"][0])
        self.assertEqual((b["retrying"], b["started"], b["captured"], b["failed"]), (True, 2, 2, 1))
        self.assertEqual(len(b["next"]), 3)
        self.assertIn("--filename=<scratch>/perplexity-failed.json", b["next"][1])
        self.assertEqual((c["started"], c["failed"]), (0, 1))
        self.assertEqual(w["__err"], [{"slug": "t2", "title": "notes thread 2", "space": "", "error": "Error: HTTP 500"}])

    def test_signed_out_partway_asks_for_sign_in(self):
        """Threads failing with 401 while the listing fails too mean a lost sign-in, whatever their number."""
        # 2 listing calls (newest, projects) and 4 of the 6 threads succeed, then everything answers 401
        (_, r), _, _ = run({"threads": 6, "unauthAfter": 6}, LIST, JOB)
        self.assertEqual((r["captured"], r["failed"]), (4, 2))
        self.assertEqual(len(r["next"]), 1)
        self.assertIn("session is signed out", r["next"][0])
        self.assertIn("Sign-in item 3", r["next"][0])

    def test_one_login_page_among_many_is_listed_not_a_sign_in(self):
        """A thread that always answers a login page is retried once, then listed; the capture is still written."""
        (_, a, b, c), _, _ = run({"threads": 4, "html": ["t0"]}, LIST, JOB, JOB, JOB)
        self.assertIn("retries the 1 failed threads once", a["next"][0])
        self.assertEqual((b["retrying"], b["failed"]), (True, 1))
        self.assertTrue(b["next"][0].startswith("Write the capture"))
        self.assertIn("perplexity-failed.json", b["next"][1])
        self.assertEqual(b["next"][2], "Then go on with import-web.md step 4.")
        self.assertEqual(c["started"], 0)

    def test_running_then_done(self):
        """A run returns while the capture goes on; a run during it starts nothing more."""
        res, _, calls = run({"threads": 8}, LIST, {"__waitMs": 1}, JOB, JOB, delay=400, settle=True)
        self.assertEqual((res[1]["state"], res[1]["started"]), ("running", 8))
        self.assertIn("Run this script again to check on it", res[1]["next"][0])
        self.assertEqual(res[2]["started"], 0)
        threads = [c for c in calls if c.startswith("GET /rest/thread/")]
        self.assertEqual(len(threads), 8)

    def test_new_threads_after_a_finished_job(self):
        """Threads a later listing adds are captured by the next run, without fetching the others again."""
        fake = {"threads": 2500, "words": ["python", "notes"], "cap": 1000, "entries": 1}
        res, _, calls = run(fake, LIST, JOB, {"__terms": ["python"]}, LIST, JOB)
        self.assertEqual(res[1]["captured"], 2000)
        self.assertEqual(res[3]["started"], res[2]["added"])
        self.assertEqual(res[3]["captured"], res[2]["threads"])
        threads = [c for c in calls if c.startswith("GET /rest/thread/")]
        self.assertEqual(len(threads), len(set(threads)))

    def test_no_listing(self):
        (r,), _, _ = run({}, JOB)
        self.assertEqual(r["state"], "no listing")
        self.assertIn("perplexity-list.js", r["next"][0])


@unittest.skipUnless(NODE, "needs node on PATH")
class ExtrasTest(unittest.TestCase):
    def test_no_input_says_how_to_set_it(self):
        (r,), _, calls = run({}, EXTRAS)
        self.assertEqual(r["state"], "no input")
        self.assertIn("window.__want", r["next"][0])
        self.assertEqual(calls, [])

    def test_reads_only_what_was_authorised(self):
        fake = {"memories": 120, "files": {"u1": ["a.md", "docs/b.md"], "u2": ["c.md"]}}
        (r,), w, calls = run(fake, {"__want": {"memories": True, "files": ["u1"]}}, EXTRAS, keep=["__extras"])
        self.assertEqual((r["instructions"], r["memories"], r["files"], r["errors"]), (False, 120, 2, []))
        self.assertEqual(w["__extras"]["files"], [{"project": "u1", "path": "a.md", "content": "text of a.md"},
                                                  {"project": "u1", "path": "docs/b.md", "content": "text of docs/b.md"}])
        self.assertFalse(any("get_user_ai_profile" in c or "/u2/" in c for c in calls))
        self.assertEqual(r["next"], ['Write what it read: playwright-cli -s=<name> eval "() => window.__extras" --filename=<scratch>/perplexity-extras.json.'])

    def test_instructions(self):
        (r,), w, _ = run({"profile": {"bio": "x"}}, {"__want": {"instructions": True}}, EXTRAS, keep=["__extras"])
        self.assertEqual((r["instructions"], w["__extras"]["instructions"]), (True, {"bio": "x"}))

    def test_signed_out(self):
        (r,), _, _ = run({"unauth": True}, {"__want": {"memories": True}}, EXTRAS)
        self.assertEqual(len(r["errors"]), 1)
        self.assertIn("Sign-in item 3", r["next"][0])


if __name__ == "__main__":
    unittest.main()
