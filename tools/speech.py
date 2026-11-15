#!/usr/bin/env python3
"""Transcribe a recording on this machine, with the times a spoken practice round needs (#707).

  python3 -I tools/speech.py transcribe <file>... [--terms "<proper nouns>"] [--parts <file>] [--check]
                                         [--model <name>] [--check-model <name>] [--cpu]
  python3 -I tools/speech.py analyze <words.json>... [--parts <file>]
  python3 -I tools/speech.py setup [--yes | --no] [--no-gpu]
  python3 -I tools/speech.py state

(Windows: py -3 -I tools/speech.py ...)

transcribe prints, per file: `file:`, `device:` (what ran it), `speed:` (times real time, and a
`slow:` line naming a faster option this machine has when it ran slower than 3x), `duration:` (the
recording, and where the speech starts and ends), `words:`, `wpm:` (over the speech), `pauses:`
(each gap of 1.5 s or more between words, with its time and length), `dropped:` (text after the last
speech when the audio there is silence: a model's invented ending), then `transcript:` and the text,
one line per stretch between pauses, each with its start time.
  --terms   proper nouns the model should expect, as one string ("Kubernetes, gRPC, Acme"): a prompt.
  --parts   a file of cue phrases, one per line (blank and `#` lines skipped): one `part:` line per
            phrase, in order, with its start time and its length up to the next part found (the last
            one up to the end of the speech), or `not found`. A cue matches its words in the
            transcript, punctuation and case ignored, with small slips allowed.
  --check   transcribe again with a second, smaller model and print a `heard differently:` line per
            stretch of words the two heard differently, with its time: the words worth saying more
            clearly.
  --model, --check-model  other models than setup's (a backend's model name; downloaded on first use).
  --cpu     run on the CPU even when a GPU is usable.
It writes nothing: the transcript goes to stdout, and the agent keeps what the practice log needs.

analyze prints the same lines from a JSON file of words and times (the backend's output, `{"duration":
<s>, "voiced": [[<start>, <end>], ...], "words": [{"word": .., "start": .., "end": ..}, ...]}`, plus
optional "check_words" for --check's lines): the shared layer alone, with no backend.

setup picks the backend for this machine and prints what it would install (`backend:`, `models:`,
`download:`, `into:`, `installed:`); with --yes it records `speech = true` in
~/.career-log/machine.toml, creates ~/.career-log/speech/venv, installs the pinned packages of
tools/speech-requirements.txt (the NVIDIA libraries only when an NVIDIA GPU is found, never with
--no-gpu), downloads the models into ~/.career-log/speech/models and ends with `speech: ok`. --no
records `speech = false` and installs nothing. With CAREER_LOG_UNATTENDED set it records the answer,
installs nothing and exits 3. Nothing needs an administrator; removing ~/.career-log/speech removes
all of it. state prints `speech: ok (...)`, `speech: missing` or `speech: outdated (...)`, as
tools/check.py reads it.

Backends (ADR 0013): faster-whisper (CTranslate2) on Windows, Linux and x86-64 Macs, on an NVIDIA GPU
when one is usable, else on the CPU, tuned; mlx-whisper on Apple Silicon. This script itself uses the
standard library only: transcribe re-runs it with the environment's Python for the backend, which
returns words and times as JSON, and this side computes every line from them (the shared layer).
tools/logfiles.py beside it, which it imports for its globs (never in the backend's process), is
standard library only too.

Exit 0 on success; 1 when a file cannot be read or transcribed, or setup cannot install (an
unsupported machine, records no answer; pip or a download failing: run it again); 2 on a bad
argument; 3 for an unattended setup and when the tool is not set up (the message says how).
"""
import argparse, difflib, functools, hashlib, json, os, platform, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS = os.path.join(HERE, "speech-requirements.txt")
WINDOWS = os.name == "nt"
MAC = platform.system() == "Darwin"
APPLE_SILICON = MAC and platform.machine() == "arm64"
UNATTENDED = bool(os.environ.get("CAREER_LOG_UNATTENDED"))

PAUSE = 1.5        # seconds between words that count as a pause
SLOW = 3.0         # below this many times real time, a `slow:` line
TAIL = 0.5         # seconds after the last voiced audio a word may still start
MODELS = {         # backend: (main model, --check model), the names setup downloads
    "faster-whisper": ("large-v3-turbo", "small"),
    "mlx-whisper": ("mlx-community/whisper-large-v3-turbo", "mlx-community/whisper-small-mlx"),
}
SIZES_GB = {       # what setup downloads, roughly, for its `download:` line
    "faster-whisper": 0.15, "gpu": 1.3, "mlx-whisper": 0.3,
    "large-v3-turbo": 1.6, "small": 0.5,
    "mlx-community/whisper-large-v3-turbo": 1.6, "mlx-community/whisper-small-mlx": 0.5,
}


def python_cmd():
    return "py -3" if WINDOWS else "python3"


def this_cmd():
    return '%s -I "%s"' % (python_cmd(), os.path.abspath(__file__))


# ---- Where it lives ----

def speech_dir(home=None):
    return os.path.join(home or os.path.expanduser("~"), ".career-log", "speech")


def venv_python(home=None):
    venv = os.path.join(speech_dir(home), "venv")
    return os.path.join(venv, "Scripts", "python.exe") if WINDOWS else os.path.join(venv, "bin", "python")


def marker(home=None):
    return os.path.join(speech_dir(home), "installed.json")


def models_dir(home=None):
    return os.path.join(speech_dir(home), "models")


def machine_toml(home=None):
    return os.path.join(home or os.path.expanduser("~"), ".career-log", "machine.toml")


# ---- The shared layer: lines from words and times (standard library only) ----

def clock(seconds):
    """0:41.2, or 1:02:03.4 past an hour."""
    tenths = int(round(max(seconds, 0) * 10))
    m, s = divmod(tenths, 600)
    h, m = divmod(m, 60)
    return ("%d:%02d:%04.1f" % (h, m, s / 10)) if h else ("%d:%04.1f" % (m, s / 10))


NUMBERS = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen"
    " seventeen eighteen nineteen twenty".split())}
NUMBERS.update({w: str(10 * i) for i, w in enumerate("thirty forty fifty sixty seventy eighty ninety".split(), 3)})


def tokens(text):
    """Words, case and punctuation gone, a number word as its digits: two models may spell it either way."""
    return [NUMBERS.get(t, t) for t in re.findall(r"\w+(?:'\w+)?", text.lower())]


def speech_end(voiced):
    return max((e for _, e in voiced), default=None)


def trim_after_speech(words, voiced):
    """(kept, dropped): words that start after the last voiced audio (plus TAIL) are dropped, since a
    model invents them from silence. With no voiced intervals given, nothing is dropped."""
    end = speech_end(voiced)
    if end is None:
        return list(words), []
    return [w for w in words if w["start"] <= end + TAIL], [w for w in words if w["start"] > end + TAIL]


def pauses(words, gap=PAUSE):
    """[(time the pause starts, its length)] for each gap of `gap` seconds or more between words."""
    return [(a["end"], round(b["start"] - a["end"], 2)) for a, b in zip(words, words[1:]) if b["start"] - a["end"] >= gap]


def stretches(words, gap=PAUSE):
    """The words split at each pause: [(start, text)]."""
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and w["start"] - words[i - 1]["end"] >= gap:
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return [(s[0]["start"], " ".join(w["word"].strip() for w in s)) for s in out]


def read_cues(path):
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


def find_cue(toks, cue, start):
    """Index of the first word, at or after `start`, of a window of `toks` matching `cue` (a list of
    tokens), case and punctuation already gone; small slips allowed. None when no window matches.
    A window a word or two before the cue shares most of a long cue and can pass too (#798), so from
    the first window that passes, the best of the windows overlapping it wins (the earliest on a tie)."""
    n = len(cue)
    if not n:
        return None
    target = " ".join(cue)

    def score(i):
        window = toks[i:i + n]
        return 1.0 if window == cue else difflib.SequenceMatcher(None, " ".join(window), target, autojunk=False).ratio()

    last = len(toks) - n
    for i in range(start, last + 1):
        if score(i) >= 0.8:
            return max(range(i, min(i + n, last + 1)), key=lambda j: (score(j), -j))
    return None


def find_parts(words, cues):
    """[(cue, start or None, length or None)], in the cues' order: each cue searched after the last one
    found; a part runs to the next part found, the last one to the end of the speech."""
    flat = []   # (token, index of its word)
    for i, w in enumerate(words):
        flat += [(t, i) for t in tokens(w["word"])]
    toks = [t for t, _ in flat]
    found, pos = [], 0
    for cue in cues:
        at = find_cue(toks, tokens(cue), pos)
        if at is None:
            found.append([cue, None])
        else:
            found.append([cue, words[flat[at][1]]["start"]])
            pos = at + 1
    end = words[-1]["end"] if words else 0
    starts = [s for _, s in found if s is not None]
    out = []
    for cue, s in found:
        if s is None:
            out.append((cue, None, None))
            continue
        later = [t for t in starts if t > s]
        out.append((cue, s, (min(later) if later else end) - s))
    return out


def differences(words, check_words, longest=4):
    """[(time, what the main model heard, what the check model heard)] for each stretch of up to
    `longest` words the two transcripts put differently, aligned word by word."""
    def flat(ws):
        out = []
        for w in ws:
            out += [(t, w["start"]) for t in tokens(w["word"])]
        return out
    a, b = flat(words), flat(check_words)
    sm = difflib.SequenceMatcher(None, [t for t, _ in a], [t for t, _ in b], autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "replace" and i2 - i1 <= longest and j2 - j1 <= longest:
            out.append((a[i1][1], " ".join(t for t, _ in a[i1:i2]), " ".join(t for t, _ in b[j1:j2])))
    return out


def report(result, cues=None):
    """The lines for one file's result (the backend's JSON, as a dict), from `duration:` on."""
    words = sorted(result.get("words", []), key=lambda w: w["start"])
    kept, dropped = trim_after_speech(words, result.get("voiced") or [])
    lines = []
    if kept:
        first, last = kept[0]["start"], kept[-1]["end"]
        lines.append("duration: %s (speech %s to %s)" % (clock(result["duration"]), clock(first), clock(last)))
        minutes = (last - first) / 60
        lines.append("words: %d" % len(kept))
        lines.append("wpm: %d" % round(len(kept) / minutes) if minutes > 0 else "wpm: unknown (too short)")
    else:
        lines += ["duration: %s (no speech)" % clock(result["duration"]), "words: 0", "wpm: unknown (no speech)"]
    found = pauses(kept)
    lines.append("pauses: " + (", ".join("%s (%.1f s)" % (clock(t), n) for t, n in found) if found
                               else "none of %.1f s or more" % PAUSE))
    if dropped:
        lines.append('dropped: "%s" at %s (after the last speech, in silence)'
                     % (" ".join(w["word"].strip() for w in dropped), clock(dropped[0]["start"])))
    for n, (cue, s, length) in enumerate(find_parts(kept, cues or []), 1):
        lines.append('part: %d "%s" ' % (n, cue) + ("%s, %s long" % (clock(s), clock(length)) if s is not None
                                                     else "not found"))
    if "check_words" in result:
        check, _ = trim_after_speech(sorted(result["check_words"], key=lambda w: w["start"]), result.get("voiced") or [])
        diffs = differences(kept, check)
        lines += ['heard differently: %s "%s" / "%s" (%s)' % (clock(t), x, y, result.get("check_model", "check model"))
                  for t, x, y in diffs] or ["heard differently: none"]
    lines.append("transcript:")
    lines += ["[%s] %s" % (clock(s), text) for s, text in stretches(kept)]
    return lines


# ---- This machine ----

@functools.lru_cache(maxsize=None)
def nvidia_gpu():
    """The NVIDIA GPU's name, or None (nvidia-smi comes with the driver); asked once per run."""
    smi = shutil.which("nvidia-smi")
    if not smi and WINDOWS:
        cand = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "nvidia-smi.exe")
        smi = cand if os.path.exists(cand) else None
    if not smi:
        return None
    try:
        out = subprocess.run([smi, "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                             text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    name = out.stdout.strip().splitlines()[0].strip() if out.returncode == 0 and out.stdout.strip() else None
    return name


def backend_for_machine():
    return "mlx-whisper" if APPLE_SILICON else "faster-whisper"


def unsupported():
    """Why setup cannot install here, or None."""
    if sys.version_info < (3, 11):
        return "Python 3.11 or later is needed (SETUP.md step 5 installs it)"
    if APPLE_SILICON:
        major = int((platform.mac_ver()[0] or "0").split(".")[0])
        if major < 14:
            return "mlx-whisper and PyAV's wheels need macOS 14 or later on Apple Silicon"
    return None


def requirement_lines(gpu):
    """The requirement specs setup installs: every line of the file, the `# gpu` ones only with gpu."""
    out = []
    with open(REQUIREMENTS, encoding="utf-8") as f:
        for line in f:
            spec, _, comment = line.partition("#")
            if spec.strip() and (gpu or comment.strip() != "gpu"):
                out.append(spec.strip())
    return out


def requirements_hash(gpu):
    return hashlib.sha256("\n".join(requirement_lines(gpu)).encode()).hexdigest()[:12]


def read_marker(home=None):
    try:
        with open(marker(home), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def state(home=None):
    """('ok'|'missing'|'outdated', detail)."""
    m = read_marker(home)
    if not m or not os.path.exists(venv_python(home)):
        return "missing", None
    if m.get("requirements") != requirements_hash(m.get("gpu", False)):
        return "outdated", "tools/speech-requirements.txt changed since setup"
    return "ok", "%s on %s" % (m.get("backend"), "the GPU" if m.get("gpu") or m.get("backend") == "mlx-whisper"
                                 else "the CPU")


def plan(gpu_wanted=True):
    """What setup would install here: (backend, gpu name or None, models, GB)."""
    backend = backend_for_machine()
    gpu = nvidia_gpu() if backend == "faster-whisper" and gpu_wanted and not MAC else None
    models = MODELS[backend]
    gb = SIZES_GB[backend] + (SIZES_GB["gpu"] if gpu else 0) + sum(SIZES_GB[m] for m in models)
    return backend, gpu, models, gb


def set_machine(home, key, value):
    """One `<key> = <value>` line in machine.toml, as tools/setup.sh writes it."""
    path = machine_toml(home)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if not re.match(r"%s\s*=" % re.escape(key), l)]
    else:
        lines = ["# career-log Machine setup: the optional tools the user wants on this machine",
                 "# (true) or declined (false), and where poppler came from. Written by tools/setup.sh,",
                 "# tools/setup.ps1 and tools/speech.py (its setup); whether a tool is installed is detected",
                 "# on every run (tools/check.py)."]
    lines.append("%s = %s" % (key, value))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("machine.toml: %s = %s" % (key, value))


def setup(args, home=None):
    backend, gpu, models, gb = plan(not args.no_gpu)
    print("backend: %s on %s" % (backend, "the NVIDIA GPU (%s)" % gpu if gpu else
                                 "the Apple GPU" if backend == "mlx-whisper" else "the CPU"))
    print("models: %s (main), %s (--check)" % models)
    print("download: about %.1f GB, packages and models" % gb)
    print("into: %s (remove the folder to remove all of it)" % speech_dir(home))
    st, detail = state(home)
    print("installed: %s" % (st + (" (%s)" % detail if detail else "")))
    if args.no:
        set_machine(home, "speech", "false")
        return 0
    if not args.yes:
        return 0
    why = unsupported()
    if why:   # no yes recorded: the check would otherwise ask for this install on every run
        print("speech: cannot install here: %s" % why)
        return 1
    set_machine(home, "speech", "true")
    if UNATTENDED:   # as tools/setup.sh does: the answer is recorded, nothing installed
        print("unattended (CAREER_LOG_UNATTENDED): installs nothing")
        return 3
    venv = os.path.dirname(os.path.dirname(venv_python(home)))
    if subprocess.run([venv_python(home), "-c", "import pip"], capture_output=True).returncode \
            if os.path.exists(venv_python(home)) else True:   # none yet, or one a failed run left without pip
        print("creating %s" % venv, flush=True)
        r = subprocess.run([sys.executable, "-m", "venv", "--clear", venv])
        if r.returncode:
            print("speech: cannot create the environment (on Debian or Ubuntu, the python3-venv package is"
                  " needed: `sudo apt-get install python3-venv`)")
            return 1
    specs = requirement_lines(bool(gpu))
    print("installing: %s" % ", ".join(s.split(";")[0] for s in specs), flush=True)
    r = subprocess.run([venv_python(home), "-m", "pip", "install", "--disable-pip-version-check",
                        "--only-binary=:all:", *specs])
    if r.returncode:
        print("speech: pip failed (exit %d); nothing recorded as installed" % r.returncode)
        return 1
    print("downloading models into %s" % models_dir(home), flush=True)
    code, out = run_backend(home, {"op": "download", "backend": backend, "models": list(models),
                                   "models_dir": models_dir(home)})
    if code:
        print("speech: model download failed; run setup again")
        return 1
    with open(marker(home), "w", encoding="utf-8") as f:
        json.dump({"backend": backend, "gpu": bool(gpu), "models": list(models),
                   "requirements": requirements_hash(bool(gpu))}, f, indent=1)
    print("speech: ok (%s)" % state(home)[1])
    return 0


# ---- Running the backend in the environment's Python ----

def logfiles_module():
    """tools/logfiles.py, imported when first needed: the backend's process never needs it, so
    tools/ stays off its sys.path, where a file such as config.py could shadow a package's module."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)   # -I leaves this folder off sys.path
    sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
    import logfiles
    return logfiles


def site_packages(home=None):
    venv = os.path.dirname(os.path.dirname(venv_python(home)))
    if WINDOWS:
        return [os.path.join(venv, "Lib", "site-packages")]
    return logfiles_module().glob_under(venv, "lib", "python3*", "site-packages")


def gpu_lib_dirs(home=None):
    """The folders of the NVIDIA wheels' libraries (cuBLAS, cuDNN), which CTranslate2 loads."""
    sub = "bin" if WINDOWS else "lib"
    return [d for sp in site_packages(home) for d in sorted(logfiles_module().glob_under(sp, "nvidia", "*", sub))]


def run_backend(home, request):
    """(exit code, parsed JSON from the backend's stdout, or None)."""
    env = dict(os.environ)
    libs = gpu_lib_dirs(home)
    if libs:
        var = "PATH" if WINDOWS else "LD_LIBRARY_PATH"
        env[var] = os.pathsep.join(libs + ([env[var]] if env.get(var) else []))
    if request.get("backend") == "mlx-whisper":
        env["HF_HOME"] = models_dir(home)
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    r = subprocess.run([venv_python(home), "-I", os.path.abspath(__file__), "_backend", json.dumps(request)],
                       env=env, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    try:   # the JSON is the last line: a library may print before it
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        return r.returncode, json.loads(last) if last else None
    except ValueError:
        sys.stderr.write(r.stdout)
        return r.returncode or 1, None


def slow_option(result, args, home=None):
    """A faster option this machine has, or None."""
    m = read_marker(home) or {}
    if result.get("device") == "cpu":
        if args.cpu:
            return "drop --cpu to use the GPU"
        if not MAC and nvidia_gpu() and not m.get("gpu"):
            return "this machine has an NVIDIA GPU: `%s setup --yes` installs its libraries" % this_cmd()
        if (args.model or result.get("model")) not in ("small", "base", "tiny"):
            return "a smaller model, `--model small`, is faster and less exact"
    return None


def transcribe(args, home=None):
    st, detail = state(home)
    if st != "ok":
        print("speech: %s%s. Set it up with `%s setup --yes` (it states the download first: `%s setup`)."
              % (st, " (%s)" % detail if detail else "", this_cmd(), this_cmd()))
        return 3
    m = read_marker(home)
    backend = m["backend"]
    main, check = MODELS[backend]
    cues = read_cues(args.parts) if args.parts else None
    code = 0
    for path in args.files:
        print("file: %s" % path)
        if not os.path.isfile(path):
            print("error: no such file")
            code = 1
            continue
        req = {"op": "transcribe", "backend": backend, "file": os.path.abspath(path), "terms": args.terms,
               "model": args.model or main, "check_model": (args.check_model or check) if args.check else None,
               "cpu": args.cpu, "models_dir": models_dir(home)}
        rc, result = run_backend(home, req)
        if not result and backend == "faster-whisper" and not args.cpu:   # a GPU library that kills the process
            gpu_rc = rc
            rc, result = run_backend(home, dict(req, cpu=True))
            if result and "error" not in result:
                result["note"] = "the GPU run ended with exit %s and no result; ran on the CPU" % gpu_rc
        if rc or not result or "error" in result:
            print("error: %s" % ((result or {}).get("error") or "the backend failed (exit %s)" % rc))
            code = 1
            continue
        print("device: %s (%s, %s%s)" % (result["device_name"], backend, result["model"],
                                         ", %s" % result["compute"] if result.get("compute") else ""))
        speed = result["duration"] / result["seconds"] if result["seconds"] else 0
        print("speed: %.1fx real time (%.1f s, the model's load included)" % (speed, result["seconds"]))
        if speed < SLOW:
            option = slow_option(result, args, home)
            if option:
                print("slow: %s" % option)
        if result.get("note"):
            print("note: %s" % result["note"])
        for line in report(result, cues):
            print(line)
    return code


# ---- The backend, inside the environment (never imported outside it) ----

def voiced_intervals(audio, rate=16000, frame=0.03):
    """[[start, end]] of the stretches whose loudness stands out from the recording's own noise floor."""
    import numpy as np
    n = int(rate * frame)
    if len(audio) < n:
        return []
    frames = audio[:len(audio) // n * n].reshape(-1, n)
    rms = np.sqrt((frames.astype("float64") ** 2).mean(axis=1))
    floor, peak = np.percentile(rms, 10), rms.max()
    if peak <= 0:
        return []
    loud = rms > max(floor * 4, peak * 0.03, 1e-4)
    out = []
    for i, on in enumerate(loud):
        t = i * frame
        if on:
            if out and t - out[-1][1] < 0.3:
                out[-1][1] = t + frame
            else:
                out.append([t, t + frame])
    return [[round(a, 2), round(b, 2)] for a, b in out if b - a >= 0.1]


def decode(path, rate=16000):
    """Mono float32 samples at `rate`, through PyAV's bundled FFmpeg."""
    import av, numpy as np
    chunks = []
    with av.open(path) as container:
        stream = next(s for s in container.streams if s.type == "audio")
        resampler = av.AudioResampler(format="flt", layout="mono", rate=rate)
        for packet_frame in container.decode(stream):
            for f in resampler.resample(packet_frame):
                chunks.append(f.to_ndarray().reshape(-1))
        for f in resampler.resample(None):
            chunks.append(f.to_ndarray().reshape(-1))
    return np.concatenate(chunks).astype("float32") if chunks else np.zeros(0, dtype="float32")


@functools.lru_cache(maxsize=None)
def physical_cores():
    """CTranslate2 runs slower on every logical CPU than on the physical cores (measured: 147 s against
    85 s for a 3-minute file), so it gets one thread per core."""
    logical = os.cpu_count() or 4
    try:
        if WINDOWS:
            out = subprocess.run(["powershell", "-NoProfile", "-Command",
                                  "(Get-CimInstance Win32_Processor | Measure-Object NumberOfCores -Sum).Sum"],
                                 capture_output=True, text=True, timeout=30).stdout.strip()
            return int(out) if out.isdigit() and int(out) > 0 else logical
        if MAC:
            return int(subprocess.run(["sysctl", "-n", "hw.physicalcpu"], capture_output=True, text=True).stdout)
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                cores = set(re.findall(r"physical id\s*:\s*(\d+)[\s\S]*?core id\s*:\s*(\d+)", f.read()))
            return len(cores) or logical
    except (OSError, ValueError, subprocess.SubprocessError):
        return logical
    return logical


def fw_load(name, models, cpu):
    """A faster-whisper model on the GPU when one is usable, else on the CPU, tuned."""
    import ctranslate2
    from faster_whisper import WhisperModel
    note = None
    if not cpu and ctranslate2.get_cuda_device_count() > 0:
        try:
            return WhisperModel(name, device="cuda", compute_type="float16", download_root=models), "cuda", "float16", None
        except Exception as e:   # a missing cuBLAS or cuDNN shows up here or at the first transcription
            note = "the GPU failed (%s); ran on the CPU" % str(e).splitlines()[0]
    threads = physical_cores()
    model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=threads, download_root=models)
    return model, "cpu", "int8", note


def fw_words(model, device, audio, terms):
    from faster_whisper import BatchedInferencePipeline
    pipe = BatchedInferencePipeline(model=model)
    segments, _ = pipe.transcribe(audio, language=None, beam_size=1 if device == "cpu" else 5,
                                  batch_size=16 if device == "cuda" else 8, word_timestamps=True,
                                  initial_prompt=terms or None, vad_filter=True)
    return [{"word": w.word, "start": round(w.start, 2), "end": round(w.end, 2)}
            for s in segments for w in (s.words or [])]


def mlx_words(model_path, audio, terms):
    import mlx_whisper
    out = mlx_whisper.transcribe(audio, path_or_hf_repo=model_path, word_timestamps=True,
                                 initial_prompt=terms or None, condition_on_previous_text=False, verbose=None)
    return [{"word": w["word"], "start": round(w["start"], 2), "end": round(w["end"], 2)}
            for s in out.get("segments", []) for w in s.get("words", [])]


def mlx_model(name, models):
    from huggingface_hub import snapshot_download
    try:
        return snapshot_download(name, cache_dir=models, local_files_only=True)
    except Exception:
        return snapshot_download(name, cache_dir=models)


def fw_model_name(name, models):
    """The model's local folder when it is downloaded, else its name (faster-whisper downloads it)."""
    from faster_whisper import download_model
    try:
        return download_model(name, cache_dir=models, local_files_only=True)
    except Exception:
        return download_model(name, cache_dir=models)


def backend_main(request):
    req = json.loads(request)
    models = req["models_dir"]
    if WINDOWS:   # CTranslate2 finds cuBLAS and cuDNN on PATH, which the caller set; this covers Python's own loader
        for d in os.environ.get("PATH", "").split(os.pathsep):
            if os.sep + "nvidia" + os.sep in d and os.path.isdir(d):
                os.add_dll_directory(d)
    if req["op"] == "download":
        for name in req["models"]:
            (mlx_model if req["backend"] == "mlx-whisper" else fw_model_name)(name, models)
        print(json.dumps({"downloaded": req["models"]}))
        return 0
    t0 = time.time()
    try:
        audio = decode(req["file"])
    except Exception as e:
        print(json.dumps({"error": "cannot decode %s: %s" % (req["file"], e)}))
        return 1
    result = {"duration": round(len(audio) / 16000, 2), "voiced": voiced_intervals(audio), "model": req["model"]}

    def run(name):
        if req["backend"] == "mlx-whisper":
            return mlx_words(mlx_model(name, models), audio, req["terms"]), "mps", "Apple GPU (MLX)", None, None
        model, device, compute, note = fw_load(fw_model_name(name, models), models, req["cpu"])
        try:
            words = fw_words(model, device, audio, req["terms"])
        except RuntimeError as e:
            if device != "cuda":
                raise
            model, device, compute, _ = fw_load(fw_model_name(name, models), models, True)
            note = "the GPU failed (%s); ran on the CPU" % str(e).splitlines()[0]
            words = fw_words(model, device, audio, req["terms"])
        if device == "cuda":
            import ctranslate2
            label = "cuda (NVIDIA GPU, %d device(s))" % ctranslate2.get_cuda_device_count()
        else:
            label = "cpu (%d threads)" % physical_cores()
        return words, device, label, compute, note

    try:
        words, device, label, compute, note = run(req["model"])
        result.update(words=words, device=device, device_name=label, compute=compute, note=note,
                      seconds=round(time.time() - t0, 2))
        if req.get("check_model"):
            result["check_words"] = run(req["check_model"])[0]
            result["check_model"] = req["check_model"]
    except Exception as e:
        print(json.dumps({"error": "%s: %s" % (type(e).__name__, e)}))
        return 1
    print(json.dumps(result))
    return 0


# ---- Command line ----

def main(argv=None, home=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["_backend"]:
        return backend_main(argv[1])
    p = argparse.ArgumentParser(prog="speech.py", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("transcribe")
    t.add_argument("files", nargs="+")
    t.add_argument("--terms")
    t.add_argument("--parts")
    t.add_argument("--check", action="store_true")
    t.add_argument("--model")
    t.add_argument("--check-model")
    t.add_argument("--cpu", action="store_true")
    a = sub.add_parser("analyze")
    a.add_argument("files", nargs="+")
    a.add_argument("--parts")
    s = sub.add_parser("setup")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--yes", action="store_true")
    g.add_argument("--no", action="store_true")
    s.add_argument("--no-gpu", action="store_true")
    sub.add_parser("state")
    args = p.parse_args(argv)
    if args.cmd == "transcribe":
        return transcribe(args, home)
    if args.cmd == "setup":
        return setup(args, home)
    if args.cmd == "state":
        st, detail = state(home)
        print("speech: %s%s" % (st, " (%s)" % detail if detail else ""))
        return 0
    cues = read_cues(args.parts) if args.parts else None
    code = 0
    for path in args.files:
        print("file: %s" % path)
        try:
            with open(path, encoding="utf-8") as f:
                result = json.load(f)
            lines = report(result, cues)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
            print("error: not a words file (%s: %s)" % (type(e).__name__, e))
            code = 1
            continue
        for line in lines:
            print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
