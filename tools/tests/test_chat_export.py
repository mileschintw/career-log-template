#!/usr/bin/env python3
"""Tests for tools/chat_export.py, on anonymised fixtures (tools/tests/fixtures, built by make_fixtures.py).

  python3 -I tools/tests/test_chat_export.py            run every test
  python3 -I tools/tests/test_chat_export.py --update   rewrite tools/tests/expected from the current parser

After --update, read the diff of expected/ before committing: it is the parser's behaviour change.
"""
import contextlib, importlib.util, io, json, os, re, shutil, subprocess, sys, tarfile, tempfile, unittest, zipfile

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


def run(*args):
    p = subprocess.run([sys.executable, "-I", TOOL, *args], capture_output=True, text=True, encoding="utf-8")
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
