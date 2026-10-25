#!/usr/bin/env python3
"""Tests for tools/chat_export.py, on anonymised fixtures (tools/tests/fixtures, built by make_fixtures.py).

  python3 -I tools/tests/test_chat_export.py            run every test
  python3 -I tools/tests/test_chat_export.py --update   rewrite tools/tests/expected from the current parser

After --update, read the diff of expected/ before committing: it is the parser's behaviour change.
"""
import contextlib, importlib.util, io, json, os, re, shutil, subprocess, sys, tarfile, tempfile, unittest, zipfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "chat_export.py")
FIX = os.path.join(HERE, "fixtures")
EXP = os.path.join(HERE, "expected")


def pick(work):
    """What expected/extract holds: the first three conversations of every platform in the index,
    plus every one with a user turn on another branch (the T<n>.A<k> output)."""
    seen = {}
    for r in read(os.path.join(work, "index.tsv")).splitlines()[1:]:
        n, platform = r.split("\t")[:2]
        seen.setdefault(platform, []).append(int(n))
    picked = {n for ns in seen.values() for n in ns[:3]}
    with open(os.path.join(work, "conversations.json"), encoding="utf-8") as f:
        picked |= {i for i, c in enumerate(json.load(f)) if c["alt"]}
    return ",".join(map(str, sorted(picked)))


sys.path.insert(0, HERE)
import make_fixtures  # noqa: E402  (the leak check)


def run(*args, env=None):
    p = subprocess.run([sys.executable, "-I", TOOL, *args], capture_output=True, text=True, encoding="utf-8",
                       env=None if env is None else {**os.environ, **env})
    return p.returncode, p.stdout, p.stderr


def warnings(stderr):
    return [l for l in stderr.splitlines() if l.startswith("warning:")]


def index(paths, out, *extra):
    code, _, err = run("index", *paths, "--out", out, *extra)
    if code:
        raise AssertionError(err)
    with open(os.path.join(out, "conversations.json"), encoding="utf-8") as f:
        return json.load(f), err


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, data):
    with open(path, "wb") as f:
        f.write(data)


def zip_dir(src, dst, prefix=""):
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, names in os.walk(src):
            for n in names:
                full = os.path.join(root, n)
                z.write(full, prefix + os.path.relpath(full, src).replace(os.sep, "/"))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="chat_export_test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def path(self, *p):
        return os.path.join(self.tmp, *p)

    def inbox(self):
        """A fresh copy of the fixtures, laid out as the user drops them."""
        dst = self.path("inbox")
        shutil.copytree(FIX, dst)
        return dst


class Fixtures(unittest.TestCase):
    def test_only_made_up_words(self):
        make_fixtures.check(FIX)

    def test_failed_check_leaves_nothing(self):
        """When a check fails, the builder leaves neither the output folder nor its temp folder."""
        parent = tempfile.mkdtemp(prefix="chat_export_test-")
        self.addCleanup(shutil.rmtree, parent, ignore_errors=True)
        out = os.path.join(parent, "fx")
        real_check, argv = make_fixtures.check, sys.argv

        def failing(folder):
            raise AssertionError("made to fail")
        make_fixtures.check = failing
        sys.argv = ["make_fixtures.py", "--claude", os.path.join(FIX, "claude", "conversations.json"), "--out", out]
        try:
            with self.assertRaises(AssertionError):
                make_fixtures.main()
        finally:
            make_fixtures.check, sys.argv = real_check, argv
        self.assertEqual(os.listdir(parent), [])

    def install_into(self):
        parent = tempfile.mkdtemp(prefix="chat_export_test-")
        self.addCleanup(shutil.rmtree, parent, ignore_errors=True)
        new = os.path.join(parent, "checked")
        os.makedirs(new)
        write(os.path.join(new, "new.json"), b"[]")
        final = os.path.join(parent, "fx")
        os.makedirs(final)
        write(os.path.join(final, "old.json"), b"[]")
        for keep in ("fx.old", "fx.incoming"):  # look-alike folders that must survive
            os.makedirs(os.path.join(parent, keep))
            write(os.path.join(parent, keep, "mine.txt"), b"keep")
        return parent, new, final

    def test_install_swaps_and_touches_nothing_else(self):
        parent, new, final = self.install_into()
        make_fixtures.install(new, final)
        self.assertEqual(os.listdir(final), ["new.json"])
        self.assertEqual(sorted(os.listdir(parent)), ["checked", "fx", "fx.incoming", "fx.old"])

    def test_install_rolls_back_when_the_swap_fails(self):
        parent, new, final = self.install_into()
        real, calls = make_fixtures.replace, []

        def flaky(src, dst):
            calls.append(dst)
            if dst == final and calls.count(final) == 1:  # the new fixtures cannot move in; the rollback can
                raise PermissionError("a file is in use")
            return real(src, dst)
        make_fixtures.replace = flaky
        try:
            with self.assertRaises(PermissionError):
                make_fixtures.install(new, final)
        finally:
            make_fixtures.replace = real
        self.assertEqual(os.listdir(final), ["old.json"])  # the old fixtures are back
        self.assertEqual(sorted(os.listdir(parent)), ["checked", "fx", "fx.incoming", "fx.old"])

    def test_install_keeps_the_old_fixtures_when_rollback_fails(self):
        parent, new, final = self.install_into()
        real = make_fixtures.replace

        def broken(src, dst):
            if dst == final:
                raise PermissionError("a file is in use")
            return real(src, dst)
        make_fixtures.replace = broken
        err = io.StringIO()
        try:
            with self.assertRaises(PermissionError), contextlib.redirect_stderr(err):
                make_fixtures.install(new, final)
        finally:
            make_fixtures.replace = real
        kept = [n for n in os.listdir(parent) if n.startswith(".make_fixtures-old-")]
        self.assertEqual(len(kept), 1)  # the only copy is kept, and the message says where
        self.assertEqual(os.listdir(os.path.join(parent, kept[0])), ["old.json"])
        self.assertIn(kept[0], err.getvalue())

    def test_refuses_a_folder_that_is_not_fixtures(self):
        parent = tempfile.mkdtemp(prefix="chat_export_test-")
        self.addCleanup(shutil.rmtree, parent, ignore_errors=True)
        with open(os.path.join(parent, "notes.txt"), "w", encoding="utf-8") as f:
            f.write("keep me")
        argv = sys.argv
        sys.argv = ["make_fixtures.py", "--claude", os.path.join(FIX, "claude", "conversations.json"), "--out", parent]
        try:
            with self.assertRaises(SystemExit):
                make_fixtures.main()
        finally:
            sys.argv = argv
        self.assertEqual(os.listdir(parent), ["notes.txt"])


class Index(Base):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="chat_export_test-")
        cls.convs, cls.err = index([FIX], cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_conversations_match_expected(self):
        self.assertEqual(self.convs, json.loads(read(os.path.join(EXP, "conversations.json"))))

    def test_index_matches_expected(self):
        self.assertEqual(read(os.path.join(self.work, "index.tsv")), read(os.path.join(EXP, "index.tsv")))

    def test_no_warnings(self):
        self.assertEqual(warnings(self.err), [])

    def test_every_platform_found(self):
        self.assertEqual({c["platform"] for c in self.convs}, {"chatgpt", "claude", "gemini", "gemini-apps", "perplexity"})

    def test_uploads_skipped_unread(self):
        uploads = [n for _, _, ns in os.walk(FIX) for n in ns if make_fixtures.UPLOAD.search(n)]
        self.assertIn(f"skipped {len(uploads)} file(s) as Takeout uploads", self.err)

    def test_upload_trap_is_a_real_export(self):
        """The zip among the uploads holds a valid Claude.ai export: skipped where it is, read once renamed."""
        folder = os.path.join(FIX, "takeout", "Takeout", "我的活動", "Gemini Apps")
        trap = [n for n in os.listdir(folder) if n.endswith(".zip")]
        self.assertEqual(len(trap), 1)
        root = self.path("in")
        os.makedirs(root)
        shutil.copy(os.path.join(folder, trap[0]), os.path.join(root, "conversations.zip"))
        convs, _ = index([root], self.path("w"))
        self.assertEqual(len(convs), 1)
        self.assertNotIn(convs[0]["id"], {c["id"] for c in self.convs})

    def test_work_dir_left_clean(self):
        self.assertEqual(sorted(os.listdir(self.work)), ["conversations.json", "index.tsv", "meta.json"])

    def test_gap_changes_sessions(self):
        fewer, _ = index([FIX], self.path("w"), "--gap", "600")
        n = lambda cs: sum(c["platform"] == "gemini-apps" for c in cs)
        self.assertLess(n(fewer), n(self.convs))


class Repackaged(Base):
    """However the files arrive, the same conversations come out."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="chat_export_test-")
        cls.base, _ = index([FIX], cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def same(self, root, *extra_warnings):
        convs, err = index([root], self.path("work"))
        self.assertEqual(convs, self.base)
        got = warnings(err)
        for w in extra_warnings:
            self.assertTrue(any(w in g for g in got), f"no warning with {w!r} in {got}")
        if not extra_warnings:
            self.assertEqual(got, [])
        return err

    def test_extra_wrapper_folders(self):
        root = self.path("in")
        shutil.copytree(FIX, os.path.join(root, "export", "export"))
        self.same(root)

    def test_each_platform_zipped(self):
        src, root = self.inbox(), self.path("in")
        os.makedirs(root)
        for d in os.listdir(src):
            zip_dir(os.path.join(src, d), os.path.join(root, d + ".zip"))
        self.same(root)

    def test_zip_inside_zip(self):
        src, root = self.inbox(), self.path("in")
        os.makedirs(root)
        zip_dir(src, self.path("inner.zip"))
        with zipfile.ZipFile(os.path.join(root, "outer.zip"), "w") as z:
            z.write(self.path("inner.zip"), "download/inner.zip")
        self.same(root)

    def test_tgz(self):
        src, root = self.inbox(), self.path("in")
        os.makedirs(root)
        with tarfile.open(os.path.join(root, "takeout.tgz"), "w:gz") as t:
            t.add(src, "Takeout-export")
        self.same(root)

    def test_renamed_exports(self):
        root = self.inbox()
        for old, new in (("chatgpt/conversations-000.json", "chatgpt/my history.json"),
                         ("claude/conversations.json", "claude/claude-data.json")):
            os.rename(os.path.join(root, old), os.path.join(root, new))
        self.same(root)

    def test_gemini_page_zipped_alone(self):
        root = self.inbox()
        folder = os.path.join(root, "takeout", "Takeout", "我的活動", "Gemini Apps")
        page = os.path.join(folder, "我的活動.html")
        with zipfile.ZipFile(os.path.join(root, "gemini.zip"), "w") as z:
            z.write(page, "MyActivity.html")
        shutil.rmtree(os.path.join(root, "takeout"))
        convs, err = index([root], self.path("work"))
        self.assertEqual([c for c in convs if c["platform"] == "gemini-apps"],
                         [c for c in self.base if c["platform"] == "gemini-apps"])
        self.assertIn("read as the Gemini Apps activity page by its content", err)

    def test_macos_leftovers(self):
        src, root = self.inbox(), self.path("in")
        os.makedirs(root)
        zip_dir(src, os.path.join(root, "export.zip"))
        with zipfile.ZipFile(os.path.join(root, "export.zip"), "a") as z:
            z.writestr("__MACOSX/chatgpt/._conversations-000.json", b"\x00\x05\x16\x07")
            z.writestr("chatgpt/.DS_Store", b"\x00")
        err = self.same(root)
        self.assertIn("skipped 2 operating-system leftover(s)", err)

    def test_unsupported_archive(self):
        root = self.inbox()
        write(os.path.join(root, "more.7z"), b"7z\xbc\xaf\x27\x1c")
        self.same(root, "more.7z: this kind of archive cannot be opened")

    def test_too_deep(self):
        root = self.inbox()
        data = b""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("conversations.json", "[]")
        data = buf.getvalue()
        for _ in range(4):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("n.zip", data)
            data = buf.getvalue()
        write(os.path.join(root, "deep.zip"), data)
        err = self.same(root, "archives nested more than 3 deep")
        self.assertNotIn("deep.zip: no export found", err)  # one warning per problem

    def test_broken_member(self):
        root = self.inbox()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("conversations.json", json.dumps([{"uuid": "x", "chat_messages": []}] * 200))
        b = bytearray(buf.getvalue())
        for i in range(60, 120):
            b[i] ^= 0xFF
        write(os.path.join(root, "broken.zip"), bytes(b))
        err = self.same(root, "broken.zip!conversations.json: could not be read")
        self.assertNotIn("broken.zip: no export found", err)

    def test_folder_of_uploads_only(self):
        root = self.inbox()
        os.makedirs(os.path.join(root, "gemini-part-2"))
        write(os.path.join(root, "gemini-part-2", "photo-0123456789abcdef.jpg"), b"made-up upload\n")
        self.same(root, "gemini-part-2: no export found (0 file(s) read")

    def test_missing_path(self):
        convs, err = index([FIX, self.path("nope")], self.path("work"))
        self.assertEqual(convs, self.base)
        self.assertTrue(any("no such file or folder" in w for w in warnings(err)))


class Extract(Base):
    def test_matches_expected(self):
        work = self.path("work")
        index([FIX], work)
        out = self.path("sources")
        code, _, err = run("extract", work, "--pick", pick(work), "--date", "2030-01-01", "--out", out)
        self.assertEqual(code, 0, err)
        got = {os.path.relpath(os.path.join(r, n), out).replace(os.sep, "/"): read(os.path.join(r, n))
               for r, _, ns in os.walk(out) for n in ns}
        exp_root = os.path.join(EXP, "extract")
        want = {os.path.relpath(os.path.join(r, n), exp_root).replace(os.sep, "/"): read(os.path.join(r, n))
                for r, _, ns in os.walk(exp_root) for n in ns}
        self.assertEqual(sorted(got), sorted(want))
        for k in want:
            self.assertEqual(got[k], want[k], k)

    def test_refuses_to_overwrite(self):
        work = self.path("work")
        index([FIX], work)
        out = self.path("sources")
        self.assertEqual(run("extract", work, "--pick", "0", "--date", "2030-01-01", "--out", out)[0], 0)
        code, _, err = run("extract", work, "--pick", "0", "--date", "2030-01-01", "--out", out)
        self.assertNotEqual(code, 0)


class Times(unittest.TestCase):
    """Checked against hand-worked answers, not against the parser's own output."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("chat_export_under_test", TOOL)
        cls.ce = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.ce)

    def utc(self, stamp):
        _, when = self.ce.ts_match(stamp + "<br>")
        return self.ce.iso(when) if when else None

    def test_zh_period_words(self):
        for stamp, want in [
            ("2026年3月5日 凌晨12:05:00 PST", "2026-03-05T08:05:00+00:00"),
            ("2026年3月5日 凌晨3:00:00 PST", "2026-03-05T11:00:00+00:00"),
            ("2026年3月5日 清晨5:30:00 PST", "2026-03-05T13:30:00+00:00"),
            ("2026年3月5日 早上7:00:00 PST", "2026-03-05T15:00:00+00:00"),
            ("2026年3月5日 上午11:00:00 PST", "2026-03-05T19:00:00+00:00"),
            ("2026年3月5日 中午12:30:00 PST", "2026-03-05T20:30:00+00:00"),
            ("2026年3月5日 下午1:00:00 PST", "2026-03-05T21:00:00+00:00"),
            ("2026年3月5日 傍晚6:00:00 PST", "2026-03-06T02:00:00+00:00"),
            ("2026年3月5日 晚上11:00:00 PST", "2026-03-06T07:00:00+00:00"),
            ("2026年3月5日 晚上12:00:00 PST", "2026-03-05T08:00:00+00:00"),  # midnight starting the 5th
            ("2026年3月5日 深夜11:00:00 PST", "2026-03-06T07:00:00+00:00"),
            ("2026年3月5日 深夜1:00:00 PST", "2026-03-05T09:00:00+00:00"),   # just after midnight
            ("2026年3月5日 深夜12:00:00 PST", "2026-03-05T08:00:00+00:00"),
            ("2026年3月5日 半夜1:00:00 PST", "2026-03-05T09:00:00+00:00"),
            ("2026年3月5日 午夜12:00:00 PST", "2026-03-05T08:00:00+00:00"),
        ]:
            self.assertEqual(self.utc(stamp), want, stamp)

    def test_english_form(self):
        for stamp, want in [
            ("Mar 5, 2026, 12:05:00 AM PST", "2026-03-05T08:05:00+00:00"),
            ("Mar 5, 2026, 12:30:00 PM PST", "2026-03-05T20:30:00+00:00"),
            ("Mar 5, 2026, 11:59:59 PM PDT", "2026-03-06T06:59:59+00:00"),
            ("Jan 1, 2026, 1:00:00 AM EST", "2026-01-01T06:00:00+00:00"),
        ]:
            self.assertEqual(self.utc(stamp), want, stamp)

    def test_zones(self):
        for zone, want in [("GMT+08:00", "05:00"), ("GMT-3", "16:00"), ("UTC+5:30", "07:30"), ("JST", "04:00"),
                           ("CEST", "11:00"), ("UTC", "13:00")]:
            self.assertEqual(self.utc(f"2026年3月5日 下午1:00:00 {zone}"), f"2026-03-05T{want}:00+00:00", zone)

    def test_unknown_zone_is_utc_with_a_warning(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            got = self.utc("2026年3月5日 下午1:00:00 XYZT")
        self.assertEqual(got, "2026-03-05T13:00:00+00:00")
        self.assertIn("time zone XYZT is unknown", err.getvalue())

    def test_not_a_timestamp(self):
        self.assertIsNone(self.utc("sometime last spring"))

    def test_iso(self):
        for value, want in [(1772668800, "2026-03-05T00:00:00+00:00"), (1772668800000, "2026-03-05T00:00:00+00:00"),
                            ("1772668800.5", "2026-03-05T00:00:00+00:00"), ("2026-03-05T10:00:00.1Z", "2026-03-05T10:00:00+00:00"),
                            ("2026-03-05T10:00:00.1234567+02:00", "2026-03-05T08:00:00+00:00"),
                            ("2026-03-05 10:00:00", "2026-03-05T10:00:00+00:00"), (None, ""), ("", "")]:
            self.assertEqual(self.ce.iso(value), want, value)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(self.ce.iso("5 March, teatime"), "")
        self.assertIn("unknown timestamp form", err.getvalue())


class Duplicates(Base):
    """The same conversation in two exports (a re-export, an older download) is kept once."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="chat_export_test-")
        cls.base, _ = index([FIX], cls.work)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def second_export(self, platform_file, change):
        """FIX, plus a second folder with a changed copy of one fixture file."""
        with open(os.path.join(FIX, *platform_file.split("/")), encoding="utf-8") as f:
            data = json.load(f)
        change(data)
        root = self.path("again")
        os.makedirs(os.path.join(root, os.path.dirname(platform_file)))
        write(os.path.join(root, *platform_file.split("/")), json.dumps(data).encode())
        return root

    def by_id(self, convs, cid):
        return [c for c in convs if c["id"] == cid]

    def test_identical_copies_in_either_order(self):
        copy = self.path("copy")
        shutil.copytree(FIX, copy)
        for order in ([FIX, copy], [copy, FIX]):
            convs, err = index(order, self.path("w"))
            self.assertEqual(convs, self.base)
            self.assertEqual(warnings(err), [])

    def test_later_update_wins_even_if_shorter(self):
        def change(data):
            c = next(c for c in data if len(c["chat_messages"]) >= 4
                     and all((m.get("text") or "").strip() for m in c["chat_messages"][:2]))
            self.cid, c["updated_at"] = c["uuid"], "2099-01-01T00:00:00Z"
            c["chat_messages"] = c["chat_messages"][:2]  # an edit made the thread shorter
        root = self.second_export("claude/conversations.json", change)
        for order in ([FIX, root], [root, FIX]):
            convs, _ = index(order, self.path("w"))
            kept = self.by_id(convs, self.cid)
            self.assertEqual(len(kept), 1)
            self.assertEqual(kept[0]["updated"], "2099-01-01T00:00:00+00:00")
            self.assertLessEqual(len(kept[0]["messages"]), 2)

    def test_chatgpt_later_update_wins(self):
        def change(data):
            c = data[0]
            self.cid, c["update_time"], c["title"] = c["conversation_id"], 4070908800.0, "renamed"
        root = self.second_export("chatgpt/conversations-000.json", change)
        convs, _ = index([root, FIX], self.path("w"))
        kept = self.by_id(convs, self.cid)
        self.assertEqual([c["title"] for c in kept], ["renamed"])

    def test_without_update_times_the_later_last_message_wins(self):
        def change(data):
            th = data[0]
            self.cid = th["slug"]
            th["entries"].append({"t": "2099-01-01T00:00:00", "q": "alpha bravo", "a": "charlie", "att": []})
        root = self.second_export("perplexity/perplexity-capture-madeup.json", change)
        for order in ([FIX, root], [root, FIX]):
            convs, _ = index(order, self.path("w"))
            kept = self.by_id(convs, self.cid)
            self.assertEqual(len(kept), 1)
            self.assertEqual(kept[0]["messages"][-1]["time"], "2099-01-01T00:00:00+00:00")

    def test_overlapping_takeouts(self):
        """A second Takeout of the same account: no record twice, and an emptied answer never wins."""
        page_dir = os.path.join(FIX, "takeout", "Takeout", "我的活動", "Gemini Apps")
        page = read(os.path.join(page_dir, "我的活動.html"))
        answer = re.compile(r'(\d{1,2}:\d\d:\d\d\s*[A-Z]{2,5}<br>)(.+?)(</div><div\s+class="content-cell)', re.S)
        emptied = answer.sub(r"\1\3", page, count=5)
        self.assertTrue(emptied != page, "no answer found to empty")
        root = self.path("second-takeout", "Takeout", "我的活動", "Gemini Apps")
        os.makedirs(root)
        write(os.path.join(root, "我的活動.html"), emptied.encode("utf-8"))
        convs, _ = index([FIX, self.path("second-takeout")], self.path("w"))
        pick = lambda cs: [c for c in cs if c["platform"] == "gemini-apps"]
        self.assertEqual(pick(convs), pick(self.base))


class Warnings(Base):
    """Every packing or format problem says so, once."""

    def warned(self, root, text):
        convs, err = index([root], self.path("work"))
        got = warnings(err)
        self.assertTrue(any(text in w for w in got), f"no warning with {text!r} in {got}")
        return convs, err

    def test_activity_page_in_unknown_folder(self):
        root = self.inbox()
        src = os.path.join(root, "takeout", "Takeout", "我的活動", "Gemini Apps", "我的活動.html")
        os.makedirs(os.path.join(root, "takeout", "Takeout", "我的活動", "Bard"))
        shutil.copy(src, os.path.join(root, "takeout", "Takeout", "我的活動", "Bard", "我的活動.html"))
        self.warned(root, "My Activity page in a folder not known as Gemini Apps")

    def test_gemini_folder_page_without_records(self):
        root = self.inbox()
        write(os.path.join(root, "takeout", "Takeout", "我的活動", "Gemini Apps", "extra.html"), b"<html><body></body></html>")
        self.warned(root, "has no activity records")

    def test_unknown_json_shape(self):
        root = self.inbox()
        write(os.path.join(root, "chatgpt", "conversations-009.json"), b'[{"something": "else"}]')
        self.warned(root, "matches no known format")

    def test_invalid_json(self):
        root = self.inbox()
        write(os.path.join(root, "chatgpt", "conversations-009.json"), b'[{"mapping": ')
        self.warned(root, "not readable JSON")

    def test_truncated_tgz(self):
        src, root = self.inbox(), self.path("in")
        os.makedirs(root)
        full = self.path("full.tgz")
        with tarfile.open(full, "w:gz") as t:
            t.add(src, "Takeout-export")
        with open(full, "rb") as f:
            data = f.read()
        write(os.path.join(root, "takeout.tgz"), data[: len(data) * 3 // 5])
        _, err = self.warned(root, "could not be read")
        self.assertEqual(sum("takeout.tgz" in w for w in warnings(err)), 1)

    def test_encrypted_zip(self):
        root = self.inbox()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr(zipfile.ZipInfo("conversations.json", (2030, 1, 1, 0, 0, 0)), b"[]")
        data = bytearray(buf.getvalue())
        for sig, at in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):  # mark it encrypted, as a password-protected zip is
            i = data.find(sig)
            data[i + at] |= 0x1
        write(os.path.join(root, "locked.zip"), bytes(data))
        self.warned(root, "locked.zip!conversations.json: could not be read")

    def test_chatgpt_rendering_is_skipped_quietly(self):
        root = self.inbox()
        write(os.path.join(root, "chatgpt", "chat.html"), b'<html><div class="outer-cell">Gemini</div></html>')
        convs, err = index([root], self.path("work"))
        self.assertEqual(warnings(err), [])


class Commands(Base):
    def test_show(self):
        work = self.path("work")
        index([FIX], work)
        code, out, _ = run("show", work, "0", "1")
        self.assertEqual(code, 0)
        self.assertIn("===== 0 · ", out)
        self.assertIn("===== 1 · ", out)
        code, _, err = run("show", work, "9999")
        self.assertNotEqual(code, 0)
        self.assertIn("index.tsv has conversations 0-", err)

    def test_show_lists_other_branches(self):
        work = self.path("work")
        convs, _ = index([FIX], work)
        n = next(i for i, c in enumerate(convs) if c["alt"])
        self.assertIn("other branch", run("show", work, str(n))[1])

    def test_label_names_files_and_key(self):
        work, out = self.path("work"), self.path("sources")
        index([FIX], work)
        code, stdout, err = run("extract", work, "--pick", "0", "--date", "2030-01-01", "--out", out, "--label", "second")
        self.assertEqual(code, 0, err)
        self.assertIn("-2030-01-01-second T<n>.U<k>", stdout)
        names = [n for _, _, ns in os.walk(out) for n in ns]
        self.assertTrue(names and all("2030-01-01-second-" in n for n in names), names)

    def test_pick_out_of_range(self):
        work = self.path("work")
        index([FIX], work)
        code, _, _ = run("extract", work, "--pick", "9999", "--date", "2030-01-01", "--out", self.path("s"))
        self.assertNotEqual(code, 0)

    def test_gap_below_one_minute_refused(self):
        code, _, err = run("index", FIX, "--out", self.path("w"), "--gap", "0")
        self.assertNotEqual(code, 0)
        self.assertIn("at least 1 minute", err)


def line(kind, content, t, stamp=None, ascii=True, **extra):
    """One made-up Claude Code transcript line; `ascii=False` writes non-ASCII as it is, as Claude Code does."""
    n = line.count = getattr(line, "count", 0) + 1
    return json.dumps({"type": kind, "uuid": f"u{n}", "sessionId": "sess-1", "isSidechain": False,
                       "timestamp": stamp or f"2030-01-02T03:{t:02d}:00.000Z", "message": {"role": kind, "content": content},
                       **extra}, ensure_ascii=ascii)


def transcript():
    """Every kind of line the turn filter sorts, with made-up words."""
    text = lambda s: [{"type": "text", "text": s}]
    lines = [
        line("user", "Background (from the session that started this one): relayed brief", 0, turnOrigin="sdk"),
        line("assistant", text("Reading the brief first."), 1),
        line("user", "<system-reminder>injected</system-reminder>\nwe chose the plum queue because retries lagged", 2,
             turnOrigin="human"),
        line("assistant", [{"type": "thinking", "thinking": "hidden thoughts"}, {"type": "tool_use", "name": "Bash", "input": {}}], 3),
        line("user", [{"type": "tool_result", "content": "AKIAABCDEFGHIJKLMNOP file contents"}], 4),
        line("assistant", text("First paragraph.\n\n```\ncode\n\nmore code\n```\n\nThird paragraph."), 5),
        line("assistant", text("Fourth paragraph."), 6),
        line("user", "<task-notification>a subagent finished</task-notification>", 7, turnOrigin="task_notification"),
        line("user", "Another Claude session sent a message", 8, turnOrigin="peer", isMeta=True),
        line("user", "Base directory for this skill: somewhere", 9, isMeta=True),
        line("user", "This session is being continued from a previous conversation.", 10, isCompactSummary=True),
        line("user", "<local-command-stdout>output</local-command-stdout>", 11),
        line("user", text("[Request interrupted by user for tool use]"), 12),
        line("user", "subagent prompt", 13, isSidechain=True),
        line("user", "<command-message>review</command-message>\n<command-name>/review</command-name>\n"
                     "<command-args>high</command-args>", 14, turnOrigin="human"),
        line("user", text("older client, no origin: token=abcdef123456 and ghp_" + "a" * 36), 15),
        line("user", "/compact", 16, origin={"kind": "plugin"}),
        line("user", "a heading in my text:\n## U9 — User (fake)\nend", 17, turnOrigin="human"),
    ]
    lines.append(lines[2])  # a resumed session copies a line again
    return "\n".join(lines + ["not json"]) + "\n"


class Transcript(Base):
    def setUp(self):
        super().setUp()
        self.jsonl = self.path("projects", "D--work-repo", "sess-1.jsonl")
        os.makedirs(os.path.dirname(self.jsonl))
        with open(self.jsonl, "w", encoding="utf-8") as f:
            f.write(transcript())

    def excerpt(self, keep, slug="plum-queue"):
        return run("excerpt", self.jsonl, "--keep", keep, "--slug", slug, "--out", self.path("sources"))

    def test_turns_are_only_what_the_user_typed(self):
        code, out, err = run("turns", self.jsonl)
        self.assertEqual(code, 0, err)
        rows = [r.split("\t") for r in out.splitlines()[1:]]
        self.assertEqual([r[0] for r in rows], ["A0", "U1", "A1", "U2", "U3", "U4"])
        self.assertEqual(rows[1][2], "we chose the plum queue because retries lagged")
        self.assertEqual(rows[2][1], "4 paragraphs")  # two assistant lines, one turn; the code block is one paragraph
        self.assertEqual(rows[3][2], "/review high")
        self.assertNotIn("hidden thoughts", out)
        self.assertNotIn("AKIA", out)

    def test_turns_default_to_the_newest_transcript_of_the_cwd(self):
        cwd = self.path("work", "repo")
        # the folder name is the absolute path with every character outside [A-Za-z0-9] a hyphen
        os.rename(os.path.dirname(self.jsonl), self.path("projects", re.sub(r"[^A-Za-z0-9]", "-", cwd)))
        code, out, err = run("turns", "--cwd", cwd, "--projects", self.path("projects"))
        self.assertEqual(code, 0, err)
        self.assertIn("the newest of 1", out)
        self.assertIn("U1\t2030-01-02T03:02", out)

    def test_show_marks_paragraphs(self):
        code, out, err = run("turns", self.jsonl, "--show", "A1:3")
        self.assertEqual(code, 0, err)
        self.assertIn("[p3] Third paragraph.", out)
        self.assertNotIn("First paragraph", out)

    def test_excerpt_format_and_redaction(self):
        code, out, err = self.excerpt("U1,A1:1,A1:4,U3")
        self.assertEqual(code, 0, err)
        self.assertIn("redacted: 1 GitHub token, 1 secret value", err)
        self.assertIn("key `claude-code-2030-01-02-plum-queue U<k>`", out)
        text = read(self.path("sources", "claude-code", "2030-01-02-plum-queue.md"))
        self.assertIn("- Session: `sess-1`", text)
        self.assertIn("- Key date: session start (UTC)", text)
        self.assertIn("## U1 — User (2030-01-02 03:02)\n\n````text\nwe chose the plum queue because retries lagged\n````", text)
        self.assertIn("## A1 — Assistant (paragraphs 1, 4 of 4)", text)
        self.assertIn("First paragraph.\n\n[…]\n\nFourth paragraph.", text)
        self.assertIn("token=[redacted: secret value] and [redacted: GitHub token]", text)
        self.assertNotIn("ghp_", text)

    def test_excerpt_only_adds(self):
        self.excerpt("U3")
        target = self.path("sources", "claude-code", "2030-01-02-plum-queue.md")
        before = read(target)
        code, out, err = self.excerpt("U1,U3")
        self.assertEqual(code, 0, err)
        self.assertIn("added U1", out)
        after = read(target)
        self.assertLess(after.index("## U1"), after.index("## U3"))
        self.assertTrue(after.endswith(before[before.index("## U3"):]))
        # a turn already there stays as the file has it, a hand redaction included, while new turns are added
        with open(target, "w", encoding="utf-8") as f:
            f.write(after.replace("plum queue", "[redacted: password]"))
        code, out, err = self.excerpt("U1,A1:2,U4")
        self.assertEqual(code, 0, err)
        self.assertIn("U1 is already in", err)
        self.assertIn("added A1, U4", out)
        again = read(target)
        self.assertIn("we chose the [redacted: password] because", again)
        self.assertNotIn("plum queue", again)
        code, out, err = self.excerpt("U2")  # U4's text holds a turn heading: the file still splits at real turns only
        self.assertEqual(code, 0, err)
        self.assertEqual(read(target).count("## U9 — User (fake)"), 1)
        self.assertEqual(re.findall(r"^## ([UA]\d+) — ", read(target), re.M)[:5], ["U1", "A1", "U2", "U3", "U4"])

    def test_redaction_patterns(self):
        spec = importlib.util.spec_from_file_location("chat_export_under_test", TOOL)
        chat_export = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(chat_export)
        cases = ["GITHUB_TOKEN=ghx0123456789abcdef", "DB_PASSWORD=hunter2hunter2", '"password": "s3cr3tpass"',
                 "sk_live_" + "b" * 24, "glpat-" + "c" * 20, "npm_" + "d" * 36, "hf_" + "e" * 34,
                 "Authorization: Basic dXNlcjpwYXNzd29yZDEyMw==", "https://me:pw12345@example.com/x",
                 "-----BEGIN RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----", "AKIA" + "Z" * 16]
        for c in cases:
            counts = {}
            out = chat_export.redact(c, counts)
            self.assertIn("[redacted: ", out, c)
            self.assertTrue(counts, c)
        self.assertEqual(chat_export.redact("max_tokens: 4096 and the secret of good tests", {}),
                         "max_tokens: 4096 and the secret of good tests")

    def test_excerpt_of_another_session_refused(self):
        self.excerpt("U1")
        target = self.path("sources", "claude-code", "2030-01-02-plum-queue.md")
        with open(target, encoding="utf-8") as f:
            text = f.read().replace("sess-1", "sess-0")
        with open(target, "w", encoding="utf-8") as f:
            f.write(text)
        code, _, err = self.excerpt("U2")
        self.assertNotEqual(code, 0)
        self.assertIn("another session", err)

    def test_excerpt_of_a_fork_refused(self):
        """A forked session's file copies the parent's sessionId but numbers its own turns."""
        self.excerpt("U1")
        fork = self.path("projects", "D--work-repo", "sess-2.jsonl")
        shutil.copy(self.jsonl, fork)
        code, _, err = run("excerpt", fork, "--keep", "U2", "--slug", "plum-queue", "--out", self.path("sources"))
        self.assertNotEqual(code, 0)
        self.assertIn("another session", err)

    def test_bad_keep_refused(self):
        for keep, says in (("U1:1", "kept whole"), ("U9", "not in this transcript"), ("A1:5", "paragraphs 1-4"), ("X1", "cannot read")):
            code, _, err = self.excerpt(keep)
            self.assertNotEqual(code, 0, keep)
            self.assertIn(says, err)
        code, _, err = self.excerpt("U1", slug="Bad Slug")
        self.assertIn("--slug", err)

    def test_find_names_the_turn(self):
        code, out, err = run("find", "no such words", "PLUM   queue", "--projects", self.path("projects"))
        self.assertEqual(code, 0, err)
        self.assertEqual(out.split("\t")[0], "2")
        self.assertEqual(out.split("\t")[2:4], ["U1", "2030-01-02T03:02"])
        code, _, _ = run("find", "relayed brief", "--projects", self.path("projects"))
        self.assertNotEqual(code, 0)  # another session's message is not the user's turn

    def other_project(self, folder, *lines):
        p = self.path("projects", folder, "sess-9.jsonl")
        os.makedirs(os.path.dirname(p))
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return p

    def test_find_folder_limits_the_search(self):
        self.other_project("-home-me-log--claude-worktrees-a", line("user", "plum tree in the worktree", 30))
        self.other_project("-home-me-other", line("user", "plum tree elsewhere", 31))
        projects = self.path("projects")
        code, out, err = run("find", "plum tree", "--projects", projects, "--folder=-home-me-log*")
        self.assertEqual(code, 0, err)
        self.assertIn("in the worktree", out)
        self.assertNotIn("elsewhere", out)
        code, out, err = run("find", "plum", "--projects", projects, "--folder", "D--work*", "--folder=-home-me-other")
        self.assertEqual(code, 0, err)  # repeatable; a glob is matched against the whole folder name
        self.assertIn("plum queue", out)
        self.assertIn("elsewhere", out)
        self.assertNotIn("in the worktree", out)
        code, _, err = run("find", "plum", "--projects", projects, "--folder=-home-me")
        self.assertNotEqual(code, 0)
        self.assertIn("no project folder", err)
        if os.name == "nt":  # a Windows drive letter's case varies, so the match ignores case there
            code, out, err = run("find", "plum", "--projects", projects, "--folder", "d--WORK*")
            self.assertEqual(code, 0, err)
            self.assertIn("plum queue", out)
        code, _, err = run("find", "pear", "--projects", projects, "--folder=-home-me-log*")
        self.assertNotEqual(code, 0)
        self.assertIn("in the folders --folder matches", err)

    def test_find_skips_files_without_the_words(self):
        self.other_project("D--junk", "unreadable line about pears")
        code, out, err = run("find", "plum queue", "about plums", "pears about", "--projects", self.path("projects"))
        self.assertEqual(code, 0, err)
        self.assertNotIn("D--junk", err)  # never parsed (no phrase in it, its words in order): parsing it would warn
        code, out, err = run("find", "bout pea", "--projects", self.path("projects"))
        self.assertIn("D--junk", err)  # its raw text holds the phrase, so it is parsed
        code, out, err = run("find", "plum queue", *[f"word{n}" for n in range(3)], "--projects", self.path("projects"))
        self.assertEqual(code, 0, err)
        self.assertNotIn("D--junk", err)  # 4 phrases: still checked
        code, out, err = run("find", "plum queue", *[f"word{n}" for n in range(4)], "--projects", self.path("projects"))
        self.assertEqual(code, 0, err)
        self.assertIn("D--junk", err)  # over 4 phrases the raw check costs more than it saves: every file is parsed
        code, out, err = run("find", "/review high", "--projects", self.path("projects"))
        self.assertEqual(code, 0, err)  # a slash command the reader rebuilt from its tags: every file is parsed
        self.assertEqual(out.split("\t")[2], "U2")
        self.assertIn("D--junk", err)

    def test_find_through_json_escapes(self):
        self.other_project("D--escapes",
                           line("user", 'she said "plum" twice', 40),  # the quote is \" in the raw text
                           line("user", "同意 這個做法", 41),  # \uXXXX in the raw text
                           line("user", "核准 下一步", 42, ascii=False),  # U+2028 written raw ends no line
                           line("user", "PLUM Tree in capitals", 43),
                           line("user", "Été comme hiver", 44),  # É: a lowered phrase cannot match its escape
                           line("user", "the plum\n\t queue　next", 45, ascii=False))  # \n and \t escaped, U+3000 raw
        projects = self.path("projects")
        for phrase, label in (('"plum" twice', "U1"), ("同意 這個", "U2"), ("核准 下一步", "U3"), ("plum tree", "U4"),
                              ("été comme", "U5"), ("plum queue next", "U6")):
            code, out, err = run("find", phrase, "--projects", projects, "--folder", "D--escapes")
            self.assertEqual(code, 0, phrase + err)
            self.assertEqual(out.split("\t")[2], label, phrase)

    def test_key_date_is_the_sessions_first_day(self):
        """A session that spans midnight UTC: every turn's excerpt lands under the day it started."""
        jsonl = self.other_project("D--night", line("user", "late plum", 0, stamp="2030-01-01T23:55:00.000Z"),
                                   line("user", "after midnight plum", 0, stamp="2030-01-02T00:10:00.000Z"))
        out_dir = self.path("sources")
        code, out, err = run("excerpt", jsonl, "--keep", "U2", "--slug", "night-plum", "--out", out_dir)
        self.assertEqual(code, 0, err)
        self.assertIn("key `claude-code-2030-01-01-night-plum U<k>`", out)
        code, out, err = run("excerpt", jsonl, "--keep", "U1", "--slug", "night-plum", "--out", out_dir)
        self.assertEqual(code, 0, err)
        self.assertEqual(os.listdir(os.path.join(out_dir, "claude-code")), ["2030-01-01-night-plum.md"])

    def test_an_older_key_is_added_to(self):
        """A file of this session and slug under another date (an earlier rule's, or hand-written) keeps its name."""
        old = self.path("sources", "claude-code", "2030-01-05-plum-queue.md")
        os.makedirs(os.path.dirname(old))
        with open(old, "w", encoding="utf-8") as f:
            f.write("# Claude Code session 2030-01-05: plum queue\n\nWritten by hand.\n\n- Session: `sess-1`\n\n"
                    "## U3 — User (2030-01-05 08:00)\n\n````text\nan older copy\n````\n")
        code, out, err = self.excerpt("U1,U3")
        self.assertEqual(code, 0, err)
        self.assertIn("key `claude-code-2030-01-05-plum-queue U<k>`", out)
        self.assertIn("added U1", out)
        self.assertEqual(os.listdir(os.path.dirname(old)), ["2030-01-05-plum-queue.md"])
        text = read(old)
        self.assertIn("Written by hand.", text)
        self.assertIn("an older copy", text)
        self.assertLess(text.index("## U1"), text.index("## U3"))
        with open(self.path("sources", "claude-code", "2030-01-07-other-topic.md"), "w", encoding="utf-8") as f:
            f.write("# Claude Code session 2030-01-07: other\n\n- Session: `sess-1`\n")
        code, out, err = self.excerpt("U2", slug="review-level")  # another topic: the earliest of the session's dates
        self.assertEqual(code, 0, err)
        self.assertIn("key `claude-code-2030-01-05-review-level U<k>`", out)
        self.assertIn("- Key date: another excerpt of the session",
                      read(self.path("sources", "claude-code", "2030-01-05-review-level.md")))


def load_tool():
    """A fresh copy of chat_export, for tests that call it in-process."""
    spec = importlib.util.spec_from_file_location("chat_export_under_test", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args, cwd):
    subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True)


class FindRoot(Base):
    """find --root: the Log's own project folders first, then every folder for the phrases not found there."""

    def project(self, path, *texts):
        folder = self.path("projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(path)))
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, f"s{len(os.listdir(folder))}.jsonl"), "w", encoding="utf-8") as f:
            f.write("\n".join(line("user", t, i, turnOrigin="human") for i, t in enumerate(texts)) + "\n")

    @unittest.skipUnless(shutil.which("git"), "no git on PATH")
    def test_two_rounds(self):
        log = self.path("log")
        os.makedirs(log)
        git("init", "-q", cwd=log)
        git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "x", cwd=log)
        outside = self.path("outside-tree")
        git("worktree", "add", "-q", outside, "-b", "topic", cwd=log)
        self.project(log, "plum alpha in the main checkout")
        self.project(outside, "plum beta in a worktree outside it")
        self.project(os.path.join(log, ".claude", "worktrees", "gone"), "plum gamma in a removed worktree")
        self.project(self.path("log-sibling"), "plum alpha next door", "plum delta next door")
        self.project(self.path("log - Copy"), "plum alpha in a copy", "plum eta in a copy")
        code, out, err = run("find", "plum alpha", "plum beta", "plum gamma", "plum delta", "plum zeta", "plum eta",
                             "--root", outside, "--projects", self.path("projects"))
        self.assertEqual(code, 0, err)
        rows = [r.split("\t") for r in out.splitlines()]
        found = {r[0]: r[-1] for r in rows if len(r) == 6}
        self.assertEqual(found, {"1": "log", "2": "log", "3": "log", "4": "elsewhere", "6": "elsewhere"})  # a copy is not the Log
        self.assertNotIn("next door", "".join(r[4] for r in rows if r[0] == "1"))  # found in the Log: not searched again
        self.assertIn(["5", f"not found under {self.path('projects')}"], rows)

    def test_folder_is_one_round(self):
        self.project(self.path("a"), "plum one")
        code, out, err = run("find", "plum one", "--projects", self.path("projects"), "--folder", "*")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.split("\t")[-1].strip(), "folder")


class Dates(Base):
    def test_excerpt_prints_each_user_turn_with_its_local_day(self):
        jsonl = self.path("projects", "D--night", "s.jsonl")
        os.makedirs(os.path.dirname(jsonl))
        with open(jsonl, "w", encoding="utf-8") as f:
            f.write(line("user", "late plum", 0, stamp="2030-01-01T23:55:00.000Z") + "\n"
                    + line("assistant", [{"type": "text", "text": "noted"}], 0, stamp="2030-01-01T23:56:00.000Z") + "\n"
                    + line("user", "after midnight plum", 0, stamp="2030-01-02T00:10:00.000Z") + "\n")
        code, out, err = run("excerpt", jsonl, "--keep", "U2,A1,U1", "--slug", "night-plum", "--out", self.path("sources"))
        self.assertEqual(code, 0, err)
        day = lambda t: datetime.fromisoformat(t).astimezone().date().isoformat()  # this machine's zone, as the tool's
        self.assertEqual(out.splitlines()[1:], [f"`claude-code-2030-01-01-night-plum U1` (user, {day('2030-01-01T23:55:00+00:00')})",
                                                f"`claude-code-2030-01-01-night-plum U2` (user, {day('2030-01-02T00:10:00+00:00')})"])

    @unittest.skipIf(os.name == "nt", "TZ sets the zone on macOS and Linux only")
    def test_a_day_off_the_key(self):
        # nine hours east of UTC both turns fall on the next day, while the key keeps the session's first day in UTC
        jsonl = self.path("projects", "D--east", "s.jsonl")
        os.makedirs(os.path.dirname(jsonl))
        with open(jsonl, "w", encoding="utf-8") as f:
            f.write(line("user", "late plum", 0, stamp="2030-01-01T23:55:00.000Z") + "\n"
                    + line("user", "after midnight plum", 0, stamp="2030-01-02T00:10:00.000Z") + "\n")
        code, out, err = run("excerpt", jsonl, "--keep", "U1,U2", "--slug", "east-plum", "--out", self.path("sources"),
                             env={"TZ": "JST-9"})
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines()[1:], ["`claude-code-2030-01-01-east-plum U1` (user, 2030-01-02)",
                                                "`claude-code-2030-01-01-east-plum U2` (user, 2030-01-02)"])


class Quote(Base):
    def quote(self, turns, *args):
        path = self.path("turns.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(turns)
        return run("quote", "--turns", path, "--out", self.path("sources"),
                   "--note", "Copied from the Codex app's history pane.", *args)

    def test_known_session(self):
        turns = "--- U1 2030-03-04 05:06\nwe kept the plum cache\n\n--- A1\nAn answer, password=hunter2hunter2\n"
        code, out, err = self.quote(turns, "--agent", "Codex", "--slug", "plum-cache", "--session", "abc-1",
                                    "--started", "2030-03-04 05:00", "--title", "Plum cache")
        self.assertEqual(code, 0, err)
        self.assertIn("redacted: 1 secret value", err)
        path = self.path("sources", "codex", "2030-03-04-plum-cache.md")
        self.assertIn(f"{path}: written; key `codex-2030-03-04-plum-cache`", out)
        self.assertIn("`codex-2030-03-04-plum-cache U1` (user, ", out)
        text = read(path)
        self.assertTrue(text.startswith("# Codex session 2030-03-04: Plum cache\n\nCopied from the Codex app's history pane. "
                                        "Only **User** turns are the user's own words"))
        for want in ("- Session: `abc-1`\n- Started: 2030-03-04 05:00 UTC\n- Key date: session start (UTC)\n",
                     "## U1 — User (2030-03-04 05:06)\n\n````text\nwe kept the plum cache\n````\n",
                     "## A1 — Assistant\n\n````text\nAn answer, password=[redacted: secret value]\n````\n"):
            self.assertIn(want, text)
        # entries.py check reads it as an excerpt: the heading and the turns are what it looks for
        self.assertRegex(text, r"^# .+ session \d{4}-\d{2}-\d{2}")
        self.assertEqual(re.findall(r"^## ([UAQ]\d+)\b", text, re.M), ["U1", "A1"])
        code, out, err = self.quote("--- U4 2030-03-09 10:00\nlater\n", "--agent", "codex", "--slug", "plum-ttl",
                                    "--session", "abc-1", "--started", "2030-03-09 09:00")
        self.assertEqual(code, 0, err)  # a new slug of the session: the earliest of its files' dates
        self.assertIn("key `codex-2030-03-04-plum-ttl`", out)
        self.assertIn("- Key date: another excerpt of the session", read(self.path("sources", "codex", "2030-03-04-plum-ttl.md")))
        code, _, err = self.quote("--- U5 2030-03-09 10:00\nmore\n", "--agent", "codex", "--slug", "plum-ttl", "--session", "abc-1")
        self.assertNotEqual(code, 0)
        self.assertIn("already has a file with the slug plum-ttl", err)

    def test_unknown_session(self):
        code, out, err = self.quote("--- Q1 2030-05-06\nwe shipped it on a Friday\n", "--agent", "claude-code",
                                    "--slug", "friday-ship", "--session", "unknown")
        self.assertEqual(code, 0, err)
        self.assertIn("key `claude-code-2030-05-06-friday-ship`", out)
        self.assertIn("`claude-code-2030-05-06-friday-ship Q1` (user, 2030-05-06)", out)
        text = read(self.path("sources", "claude-code", "2030-05-06-friday-ship.md"))
        self.assertIn("- Session: `unknown`\n- Key date: quote (session unknown)\n", text)
        self.assertIn("## Q1 — User (2030-05-06)\n", text)
        self.assertNotIn("Times are UTC", text)
        for turns, args, says in (
                ("--- Q1 2030-05-06\na\n--- Q2 2030-05-06\nb\n", (), "one turn"),
                ("--- Q1 2030-05-06\na\n", ("--started", "2030-05-06 01:00"), "no known start"),
                ("--- U1 2030-05-06\na\n", (), "write `--- U<k> YYYY-MM-DD HH:MM`"),
                ("stray\n--- Q1 2030-05-06\na\n", (), "text before the first"),
                ("--- Q1 2030-05-06\n\n", (), "Q1 is empty")):
            code, _, err = self.quote(turns, "--agent", "codex", "--slug", "other", "--session", "unknown", *args)
            self.assertNotEqual(code, 0, turns)
            self.assertIn(says, err)
        code, _, err = self.quote("--- Q1 2030-05-06\na\n", "--agent", "9lives", "--slug", "x", "--session", "unknown")
        self.assertIn("--agent", err)


class Keys(Base):
    KEYS = "# Source keys\n\nIntro, citing `claude-ai-2030-01-01-second T1.U1`.\n\n| Key | Points at |\n|---|---|\n| `old T<n>` | `sources/old/a.md` |\n\nAfter the table.\n"

    def setUp(self):
        super().setUp()
        self.work, self.out = self.path("work"), self.path("log", "sources")
        self.convs, _ = index([FIX], self.work)
        os.makedirs(self.out)
        self.keys = os.path.join(self.out, "keys.md")
        with open(self.keys, "w", encoding="utf-8") as f:
            f.write(self.KEYS)

    def first(self, platform):
        return str(next(i for i, c in enumerate(self.convs) if c["platform"] == platform))

    def extract(self, pick, *extra):
        return run("extract", self.work, "--pick", pick, "--date", "2030-01-01", "--out", self.out, "--keys", self.keys, *extra)

    def test_rows(self):
        code, out, err = self.extract(f"{self.first('chatgpt')},{self.first('gemini-apps')}")
        self.assertEqual(code, 0, err)
        self.assertIn(f"{self.keys}: added the row of `chatgpt-2030-01-01`", out)
        text = read(self.keys)
        self.assertIn("| `old T<n>` | `sources/old/a.md` |\n| `", text)
        self.assertTrue(text.endswith(" |\n\nAfter the table.\n"), text)
        self.assertIn("| `chatgpt-2030-01-01 T<n>.U<k>` | `sources/chatgpt/2030-01-01-chats-prompts.md`: conversation n, "
                      "user turn k (full exchange: `2030-01-01-chats-threads.md`; `T<n>.A<k>`: a user turn on another "
                      "branch) |\n", text)
        self.assertIn("| `gemini-apps-2030-01-01 T<n>.U<k>` | `sources/gemini/2030-01-01-chats-apps-prompts.md`: session n, "
                      "user turn k (full exchange: `2030-01-01-chats-apps-threads.md`) |\n", text)
        code, out, err = self.extract(self.first("claude"), "--label", "second")
        self.assertEqual(code, 0, err)
        self.assertIn("`claude-ai-2030-01-01-second T<n>.U<k>` | `sources/claude/2030-01-01-second-prompts.md`", read(self.keys))
        # a key already in keys.md is not added again (its files moved away, say, and extracted anew)
        shutil.rmtree(os.path.join(self.out, "claude"))
        code, out, err = self.extract(self.first("claude"), "--label", "second")
        self.assertEqual(code, 0, err)
        self.assertIn("already has the row of `claude-ai-2030-01-01-second`", out)
        self.assertEqual(read(self.keys).count("| `claude-ai-2030-01-01-second "), 1)
        # entries.py check finds every folder the extracts wrote in keys.md
        spec = importlib.util.spec_from_file_location("entries_under_test", os.path.join(HERE, "..", "entries.py"))
        entries = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entries)
        os.makedirs(os.path.join(self.out, "unlisted"))
        with open(os.path.join(self.out, "unlisted", "x.md"), "w", encoding="utf-8") as f:
            f.write("# x\n")
        self.assertEqual(entries.source_folder_findings(self.path("log")), ["source folder not in keys.md: sources/unlisted/"])

    def test_keys_checked_before_writing(self):
        os.remove(self.keys)
        code, _, err = self.extract(self.first("chatgpt"))
        self.assertNotEqual(code, 0)
        self.assertIn("nothing was written", err)
        with open(self.keys, "w", encoding="utf-8") as f:
            f.write("# Source keys\n\nNo table yet.\n")
        code, _, err = self.extract(self.first("chatgpt"))
        self.assertIn("no table with a Key column", err)
        self.assertEqual(os.listdir(self.out), ["keys.md"])


class Manifest(Base):
    def manifest(self, data, *args):
        path = self.path("claude-manifest-x.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        before = sorted(os.listdir(self.tmp))
        got = run("manifest", path, *args)
        self.assertEqual(sorted(os.listdir(self.tmp)), before)  # it writes nothing
        return got

    DATA = {"instructions": "Links expire.", "data_files": [
        {"category": c, "part": p, "filename": f"{c}-00{p}.zip", "export_url": f"https://example.com/{c}/{p}"}
        for c, p in (("projects", 0), ("conversations", 1), ("memories", 0), ("conversations", 0))]}

    def test_links(self):
        code, out, err = self.manifest(self.DATA)
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines()[:3], ["- [conversations-000.zip](https://example.com/conversations/0)",
                                                "- [conversations-001.zip](https://example.com/conversations/1)",
                                                "Not needed: memories-000.zip, projects-000.zip"])
        self.assertIn("Never open or download them yourself", out)
        code, out, err = self.manifest(self.DATA, "--memories")
        self.assertIn("- [memories-000.zip](https://example.com/memories/0)", out.splitlines()[2])

    def test_unknown_shape(self):
        for data, why in (({"files": []}, "no data_files list"),
                          ({"data_files": [{"category": "conversations", "filename": "c.zip", "url": "https://x"}]},
                           "lacks one of"),
                          ({"data_files": [dict(self.DATA["data_files"][0], category="memories")]}, "no conversations item")):
            code, out, _ = self.manifest(data)
            self.assertEqual(code, 1, data)
            self.assertTrue(out.startswith("unknown shape: "), out)
            self.assertIn(why, out)
            self.assertNotIn("https://", out)


class WarningKinds(Base):
    def test_each_warning_says_its_kind(self):
        root = self.inbox()
        write(os.path.join(root, "more.7z"), b"7z\xbc\xaf\x27\x1c")
        write(os.path.join(root, "chatgpt", "conversations-009.json"), b'[{"something": "else"}]')
        _, err = index([root], self.path("work"))
        got = warnings(err)
        self.assertTrue(any(w.endswith("cannot be opened; extract it into a new folder and index that [packing]") for w in got), got)
        self.assertTrue(any("matches no known format" in w and w.endswith("[parser]") for w in got), got)

    def test_a_nested_archive_too_large_for_the_disk(self):
        root = self.path("in")
        os.makedirs(root)
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as z:
            z.writestr("conversations.json", "[]")
        with zipfile.ZipFile(os.path.join(root, "outer.zip"), "w") as z:
            z.writestr("inner.zip", inner.getvalue())
        tool, err = load_tool(), io.StringIO()
        tool.NESTED_MAX = 0
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            tool.cmd_index(tool.argparse.Namespace(paths=[root], out=self.path("work"), gap=45))
        self.assertIn("too large to copy into the work dir", err.getvalue())
        self.assertTrue(warnings(err.getvalue())[0].endswith("[disk]"), err.getvalue())

    def test_help_lists_every_leftover_skipped(self):
        """Finding 20: the help's list of operating-system leftovers is the one the skip uses."""
        tool = load_tool()
        _, out, _ = run("--help")
        for name in tool.JUNK_NAMES:
            self.assertIn(name, out)
        for path in ("__MACOSX/a/b.json", "x/._conversations.json", "x/.DS_Store", "x/Thumbs.db", "Desktop.ini"):
            self.assertTrue(tool.is_junk(path), path)
        self.assertFalse(tool.is_junk("x/conversations.json"))


class Cut(Base):
    def files(self):
        threads = ("# ChatGPT: picked conversations\n\nIntro.\n\n## T1: plums\n\n- Platform id: `a`\n\n"
                   "### T1.U1 — User (2030-01-01T00:00)\n\n````text\nmy landlord again\n````\n\n#### Assistant\n\n````text\nsorry\n````\n\n"
                   "### T1.U2 — User (2030-01-01T00:05)\n\n````text\nthe plum queue\n### T1.U3 — not a heading\n````\n\n"
                   "#### Assistant\n\n````text\nok\n````\n\n### T1: user turns on other branches (edited prompts, abandoned follow-ups)\n\n"
                   "#### T1.A1 — User (2030-01-01T00:01)\n\n````text\nmy landlord, edited\n````\n\n"
                   "## T2: pears\n\n- Platform id: `b`\n\n### T2.U1 — User (2030-01-02T00:00)\n\n````text\nnot mine\n````\n")
        prompts = re.sub(r"#### Assistant\n\n````text\n[^`]*````\n\n", "", threads).replace("picked conversations", "prompts")
        base = self.path("sources", "chatgpt", "2030-01-01-chats")
        os.makedirs(os.path.dirname(base))
        for suffix, text in (("threads", threads), ("prompts", prompts)):
            with open(f"{base}-{suffix}.md", "w", encoding="utf-8") as f:
                f.write(text)
        return base

    def test_cut_from_both_files(self):
        base = self.files()
        code, out, err = run("cut", base + "-prompts.md", "T1.U1,T1.A1,T2")
        self.assertEqual(code, 0, err)
        self.assertIn("every other number is unchanged", out)
        for suffix in ("threads", "prompts"):
            text = read(f"{base}-{suffix}.md")
            self.assertNotIn("landlord", text)
            self.assertNotIn("other branches", text)  # its last turn on another branch is cut
            self.assertNotIn("T2", text)
            self.assertIn("### T1.U2 — User (2030-01-01T00:05)\n\n````text\nthe plum queue\n### T1.U3 — not a heading\n````", text)
        self.assertNotIn("sorry", read(base + "-threads.md"))  # the cut turn's answer goes with it
        self.assertIn("ok", read(base + "-threads.md"))

    def test_nothing_cut_unless_every_turn_is_there(self):
        base = self.files()
        before = read(base + "-threads.md")
        for turns, says in (("T1.U1,T1.U3", "has no T1.U3"), ("T1.X1", "give turns"), ("T1.U1:2", "give turns")):
            code, _, err = run("cut", base + "-threads.md", turns)
            self.assertNotEqual(code, 0, turns)
            self.assertIn(says, err)
        self.assertEqual(read(base + "-threads.md"), before)
        code, _, err = run("cut", self.path("notes.md"), "T1")
        self.assertIn("-threads.md or -prompts.md", err)

    def test_a_real_extract(self):
        work, out = self.path("work"), self.path("sources")
        convs, _ = index([FIX], work)
        n = next(i for i, c in enumerate(convs) if c["alt"] and sum(m["role"] == "user" for m in c["messages"]) > 1)
        code, stdout, err = run("extract", work, "--pick", str(n), "--date", "2030-01-01", "--out", out)
        self.assertEqual(code, 0, err)
        base = os.path.join(out, "chatgpt", "2030-01-01-chats")
        code, _, err = run("cut", base + "-threads.md", "T1.U1,T1.A1")
        self.assertEqual(code, 0, err)
        for suffix in ("threads", "prompts"):
            text = read(f"{base}-{suffix}.md")
            self.assertNotIn("### T1.U1 —", text)
            self.assertNotIn("#### T1.A1 —", text)
            self.assertIn("### T1.U2 —", text)


class Tally(Base):
    def setUp(self):
        super().setUp()
        self.work = self.path("work")
        os.makedirs(self.work)
        rows = ["n\tplatform\tstart_utc\tuser_turns\tspace\ttitle\tfirst_prompt"] + [
            f"{n}\tchatgpt\t2030-01-{n + 1:02d}T10:00\t1\t\tTitle {n}\tprompt {n}" for n in range(8)]
        with open(os.path.join(self.work, "index.tsv"), "w", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")

    def marks(self, text):
        with open(os.path.join(self.work, "marks.tsv"), "w", encoding="utf-8") as f:
            f.write(text)

    def test_three_lines_and_groups(self):
        self.marks("n\tmark\tstatus\n0\thealth\n1\thealth\n2\tG1\tpicked\n3\tG1\tdropped\n4\tG2\tnot picked\n"
                   "5\tG2\tnot picked\n6\tcalled unimportant by the user\n")
        code, out, err = run("tally", self.work, "--date", "2030-02-01")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines(), [
            "Left out by category: health 2, called unimportant by the user 1, other, not career-relevant 1",
            "Groups not picked: 1 group, 2 conversations", "Dropped: 1 conversation (user, 2030-02-01)"])
        code, out, err = run("tally", self.work)   # --date defaults to today
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines()[2], f"Dropped: 1 conversation (user, {datetime.now().date().isoformat()})")
        code, out, err = run("tally", self.work, "--groups")
        self.assertEqual(out.splitlines(), ["G1: 2 conversations (2-3), 2030-01-03 to 2030-01-04 (UTC)",
                                            "G2: 2 conversations (4-5), 2030-01-05 to 2030-01-06 (UTC)"])

    def test_groups_before_the_user_answers(self):
        self.marks("2\tG1\n3\tG1\n5\tG2\n")
        code, out, err = run("tally", self.work, "--groups")
        self.assertEqual(code, 0, err)
        self.assertIn("G2: 1 conversation (5), 2030-01-06 (UTC)", out)
        code, _, err = run("tally", self.work)
        self.assertNotEqual(code, 0)
        self.assertIn("no status", err)

    def test_nothing_left_out(self):
        self.marks("".join(f"{n}\tG1\tpicked\n" for n in range(8)))
        code, out, err = run("tally", self.work)
        self.assertEqual(out.splitlines(), ["Left out by category: none", "Groups not picked: none", "Dropped: none"])

    def test_bad_marks(self):
        for text, says in (("9\thealth\n", "not in index.tsv"), ("1\thealth\n1\tshopping\n", "marked twice"),
                           ("1\tfinances\n", "not a category or a group"), ("1\thealth\tpicked\n", "only a group's row"),
                           ("1\tG1\tmaybe\n", "status is one of"), ("2\thealth\nx\thealth\n", "n is not a number")):
            self.marks(text)
            code, _, err = run("tally", self.work)
            self.assertNotEqual(code, 0, text)
            self.assertIn(says, err)


class Leaks(Base):
    def test_hits_in_the_last_section_only(self):
        self.work = self.path("work")
        os.makedirs(self.work)
        rows = ["n\tplatform\tstart_utc\tuser_turns\tspace\ttitle\tfirst_prompt",
                "0\tchatgpt\t2030-01-01T10:00\t1\t\tPython\twrite me a script please now",
                "1\tchatgpt\t2030-01-02T10:00\t1\t\tC++\thow do  I  fix my   landlord problem today",
                "2\tchatgpt\t2030-01-03T10:00\t1\t\tAI\tsomething",
                "3\tgemini-apps\t2030-01-04T10:00\t1\t\t\tplan a trip to the coast"]
        with open(os.path.join(self.work, "index.tsv"), "w", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")
        log = self.path("import-log.md")
        with open(log, "w", encoding="utf-8") as f:
            f.write("# Import log\n\n## 2029 import\n\nC++ was left out.\n\n## 2030 import (chatgpt)\n\nPicked: Python work.\n"
                    "Left out: the c++ talk, and How do I fix my landlord problem.\nAlso PLAN A TRIP TO THE coast.\n")
        code, out, err = run("leaks", self.work, "--pick", "0", log)
        self.assertEqual(code, 0, err)
        lines = out.splitlines()
        self.assertEqual(lines[:-1], ['10: conversation 1\'s title "C++": Left out: the c++ talk, and How do I fix my landlord problem.',
                                      '10: conversation 1\'s first prompt "how do I fix my": Left out: the c++ talk, and How do I fix my landlord problem.',
                                      '11: conversation 3\'s first prompt "plan a trip to the": Also PLAN A TRIP TO THE coast.'])
        self.assertEqual(lines[-1], f"3 hits in {log} from line 7 (## 2030 import (chatgpt)); 1 title(s) under 3 characters not searched")
        code, _, err = run("leaks", self.work, "--pick", "9", log)
        self.assertIn("--pick [9]", err)


class Encoding(unittest.TestCase):
    def test_unencodable_text_prints_escaped(self):
        """Finding 21: a lone surrogate (a JSON escape no UTF-8 can encode) prints as a backslash escape."""
        tmp = tempfile.mkdtemp(prefix="chat_export_test-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        jsonl = os.path.join(tmp, "s.jsonl")
        with open(jsonl, "w", encoding="utf-8") as f:
            f.write(line("user", "bad \udcff byte", 0, turnOrigin="human") + "\n")
        tool, buf = load_tool(), io.BytesIO()
        out = io.TextIOWrapper(buf, encoding="ascii")
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.TextIOWrapper(io.BytesIO(), encoding="ascii")):
            argv, sys.argv = sys.argv, ["chat_export.py", "turns", jsonl]
            try:
                tool.main()
            finally:
                sys.argv = argv
            out.flush()
        self.assertIn(b"bad \\udcff byte", buf.getvalue())


def update():
    work = tempfile.mkdtemp(prefix="chat_export_update-")
    try:
        convs, err = index([FIX], work)
        if warnings(err):
            sys.exit("the fixtures index with warnings; fix those first:\n" + "\n".join(warnings(err)))
        shutil.rmtree(EXP, ignore_errors=True)
        os.makedirs(EXP)
        shutil.copy(os.path.join(work, "conversations.json"), EXP)
        shutil.copy(os.path.join(work, "index.tsv"), EXP)
        code, _, err = run("extract", work, "--pick", pick(work), "--date", "2030-01-01", "--out", os.path.join(EXP, "extract"))
        if code:
            sys.exit(err)
        print(f"expected/ rewritten from {len(convs)} conversations; review its diff before committing")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    if "--update" in sys.argv:
        update()
    else:
        unittest.main()
