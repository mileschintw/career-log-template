#!/usr/bin/env python3
"""Tests for tools/speech.py's shared layer and setup, with no backend installed: a JSON fixture of
words and times (tools/tests/speech/), never a recording.

  python3 -I tools/tests/test_speech.py
"""
import importlib.util, io, json, os, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "speech.py")
FIXTURES = os.path.join(HERE, "speech")
spec = importlib.util.spec_from_file_location("speech", TOOL)
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)


def run(*args, home=None):
    out = io.StringIO()
    with redirect_stdout(out):
        code = speech.main(list(args), home=home)
    return code, out.getvalue().splitlines()


def words(*spans):
    """[(word, start, end)] as the backend's word dicts."""
    return [{"word": " " + w, "start": s, "end": e} for w, s, e in spans]


class AnalyzeTest(unittest.TestCase):
    """The Done when: from a fixture with a known pause and words after the last speech, the duration,
    the pause, no text after the speech, and two cue phrases found."""

    def setUp(self):
        code, self.lines = run("analyze", os.path.join(FIXTURES, "talk.json"),
                               "--parts", os.path.join(FIXTURES, "parts.txt"))
        self.assertEqual(code, 0)

    def line(self, prefix):
        found = [l for l in self.lines if l.startswith(prefix)]
        self.assertTrue(found, "no %r line in %s" % (prefix, self.lines))
        return found

    def test_duration_and_speech(self):
        self.assertEqual(self.line("duration:"), ["duration: 0:16.0 (speech 0:00.5 to 0:12.0)"])
        self.assertEqual(self.line("words:"), ["words: 24"])
        self.assertEqual(self.line("wpm:"), ["wpm: 125"])

    def test_the_known_pause(self):
        self.assertEqual(self.line("pauses:"), ["pauses: 0:05.2 (2.1 s)"])

    def test_no_text_after_the_speech(self):
        self.assertEqual(self.line("dropped:"), ['dropped: "Thank you." at 0:14.0 (after the last speech, in silence)'])
        transcript = self.lines[self.lines.index("transcript:") + 1:]
        self.assertEqual(len(transcript), 2)   # split at the pause
        self.assertTrue(transcript[1].startswith("[0:07.3] Second, the design."))
        self.assertNotIn("Thank", " ".join(transcript))

    def test_two_cue_phrases(self):
        self.assertEqual(self.line("part:"), [
            'part: 1 "First, the problem" 0:00.5, 0:06.8 long',
            'part: 2 "Second the design" 0:07.3, 0:04.7 long',
            'part: 3 "Third, the result" not found'])

    def test_heard_differently(self):
        self.assertEqual(self.line("heard differently:"), ['heard differently: 0:08.1 "design" / "desire" (small)'])

    def test_no_check_words_no_check_lines(self):
        with open(os.path.join(FIXTURES, "talk.json"), encoding="utf-8") as f:
            data = json.load(f)
        del data["check_words"]
        self.assertFalse([l for l in speech.report(data) if l.startswith("heard differently")])


class SharedLayerTest(unittest.TestCase):
    def test_clock(self):
        self.assertEqual(speech.clock(0), "0:00.0")
        self.assertEqual(speech.clock(418.04), "6:58.0")
        self.assertEqual(speech.clock(3723.4), "1:02:03.4")

    def test_nothing_dropped_without_voiced_intervals(self):
        ws = words(("a", 0, 0.2), ("b", 30, 30.2))
        self.assertEqual(speech.trim_after_speech(ws, []), (ws, []))

    def test_a_word_just_after_the_voiced_end_is_kept(self):
        ws = words(("a", 0, 0.2), ("b", 1.3, 1.6), ("c", 3.0, 3.2))
        kept, dropped = speech.trim_after_speech(ws, [[0, 1.0]])
        self.assertEqual([w["word"] for w in kept], [" a", " b"])
        self.assertEqual([w["word"] for w in dropped], [" c"])

    def test_a_gap_under_the_threshold_is_no_pause(self):
        ws = words(("a", 0, 0.2), ("b", 1.6, 1.8), ("c", 3.4, 3.6))
        self.assertEqual(speech.pauses(ws), [(1.8, 1.6)])

    def test_cues_in_order_with_a_slip(self):
        ws = words(*[(w, i, i + 0.5) for i, w in enumerate(
            "so second the desing comes later first the problem then second the design".split())])
        parts = speech.find_parts(ws, ["First, the problem", "Second, the design"])
        self.assertEqual([(c, s) for c, s, _ in parts], [("First, the problem", 6), ("Second, the design", 10)])
        slipped = speech.find_parts(ws, ["Second, the design"])
        self.assertEqual(slipped[0][1], 1)   # "second the desing" is close enough

    def test_a_long_cue_after_words_that_overlap_it(self):
        # #798: a window a word or two early shares most of a long cue; the cue starts at "here"
        text = ("have you ever lost an order because a queue dropped it i have at example freight "
                "here is what a durable queue is it writes each message to disk").split()
        ws = words(*[(w, i, i + 0.5) for i, w in enumerate(text)])
        here = text.index("here")
        parts = speech.find_parts(ws, ["Have you ever", "Here is what a durable queue is"])
        self.assertEqual([s for _, s, _ in parts], [0, here])
        slipped = speech.find_parts(ws, ["Here is what a durible queue is"])
        self.assertEqual(slipped[0][1], here)

    def test_a_number_spelled_two_ways_is_heard_alike(self):
        a = words(("two", 0, 0.2), ("seconds", 0.3, 0.5), ("Kubernetes", 0.6, 0.9))
        b = words(("2", 0, 0.2), ("seconds", 0.3, 0.5), ("communities", 0.6, 0.9))
        self.assertEqual(speech.differences(a, b), [(0.6, "kubernetes", "communities")])

    def test_parts_file_skips_blank_and_comment_lines(self):
        self.assertEqual(speech.read_cues(os.path.join(FIXTURES, "parts.txt")),
                         ["First, the problem", "Second the design", "Third, the result"])

    def test_no_speech(self):
        lines = speech.report({"duration": 5.0, "voiced": [], "words": []})
        self.assertIn("duration: 0:05.0 (no speech)", lines)
        self.assertIn("pauses: none of 1.5 s or more", lines)


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.home, ignore_errors=True))
        patch = mock.patch.object(speech, "nvidia_gpu", return_value=None)
        patch.start()
        self.addCleanup(patch.stop)

    def machine(self):
        with open(speech.machine_toml(self.home), encoding="utf-8") as f:
            return f.read()

    def test_setup_alone_states_the_download_and_installs_nothing(self):
        code, lines = run("setup", home=self.home)
        self.assertEqual(code, 0)
        self.assertTrue(any(l.startswith("download: about ") and l.endswith(" GB, packages and models") for l in lines))
        self.assertIn("installed: missing", lines)
        self.assertFalse(os.path.exists(speech.speech_dir(self.home)))
        self.assertFalse(os.path.exists(speech.machine_toml(self.home)))

    def test_no_records_the_answer_and_keeps_other_lines(self):
        os.makedirs(os.path.dirname(speech.machine_toml(self.home)))
        with open(speech.machine_toml(self.home), "w", encoding="utf-8") as f:
            f.write("# header\nplaywright-cli = true\nspeech = true\npoppler = \"own\"\n")
        code, lines = run("setup", "--no", home=self.home)
        self.assertEqual(code, 0)
        self.assertIn("machine.toml: speech = false", lines)
        self.assertEqual(self.machine(), "# header\nplaywright-cli = true\npoppler = \"own\"\nspeech = false\n")
        self.assertFalse(os.path.exists(speech.speech_dir(self.home)))

    def test_unattended_yes_records_and_installs_nothing(self):
        with mock.patch.object(speech, "UNATTENDED", True):
            code, lines = run("setup", "--yes", home=self.home)
        self.assertEqual(code, 3)
        self.assertIn("speech = true", self.machine())
        self.assertFalse(os.path.exists(speech.speech_dir(self.home)))

    def test_an_unsupported_machine_records_no_yes(self):
        """Otherwise the check would ask for the install on every run (review of #707)."""
        with mock.patch.object(speech, "unsupported", return_value="macOS 14 is needed"):
            code, lines = run("setup", "--yes", home=self.home)
        self.assertEqual(code, 1)
        self.assertIn("speech: cannot install here: macOS 14 is needed", lines)
        self.assertFalse(os.path.exists(speech.machine_toml(self.home)))

    def test_analyze_a_file_that_is_not_words(self):
        bad = os.path.join(self.home, "bad.json")
        with open(bad, "w", encoding="utf-8") as f:
            json.dump({"words": []}, f)
        code, lines = run("analyze", bad)
        self.assertEqual(code, 1)
        self.assertTrue(lines[1].startswith("error: not a words file (KeyError"), lines)

    def test_state(self):
        self.assertEqual(speech.state(self.home), ("missing", None))
        os.makedirs(os.path.dirname(speech.venv_python(self.home)))
        open(speech.venv_python(self.home), "w").close()
        with open(speech.marker(self.home), "w", encoding="utf-8") as f:
            json.dump({"backend": "faster-whisper", "gpu": False, "requirements": speech.requirements_hash(False)}, f)
        self.assertEqual(speech.state(self.home), ("ok", "faster-whisper on the CPU"))
        with open(speech.marker(self.home), "w", encoding="utf-8") as f:
            json.dump({"backend": "faster-whisper", "gpu": False, "requirements": "old"}, f)
        self.assertEqual(speech.state(self.home)[0], "outdated")

    def test_transcribe_before_setup_says_how(self):
        code, lines = run("transcribe", os.path.join(FIXTURES, "talk.json"), home=self.home)
        self.assertEqual(code, 3)
        self.assertTrue(lines[0].startswith("speech: missing. Set it up with `"), lines)

    def test_gpu_wheels_only_with_a_gpu(self):
        with_gpu, without = speech.requirement_lines(True), speech.requirement_lines(False)
        self.assertTrue(any(l.startswith("nvidia-cudnn-cu12") for l in with_gpu))
        self.assertFalse(any(l.startswith("nvidia-") for l in without))
        self.assertTrue(any(l.startswith("faster-whisper==") for l in without))


class CommandLineTest(unittest.TestCase):
    def test_help_runs_with_the_standard_library_alone(self):
        r = subprocess.run([sys.executable, "-I", TOOL, "--help"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("transcribe", r.stdout)
        self.assertIn("heard differently", r.stdout)


if __name__ == "__main__":
    unittest.main()
