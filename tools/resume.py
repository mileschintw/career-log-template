#!/usr/bin/env python3
"""Build a resume .tex locally and check its layout.

    python3 tools/resume.py <file.tex> [--out DIR] [--install-missing] [--no-png]
    python3 tools/resume.py --check <file.pdf>

Build: pdflatex into a scratch dir (default <repo>/.build/<stem>/), then copy the
PDF next to the .tex. With --install-missing, packages reported missing are
installed with tlmgr and the build is retried.

Check (always runs after a build): page count, bullets over the line limit,
dangling last lines, bottom slack, overfull boxes, contact details in the text
layer. Writes a PNG of each page for a visual read. Exit status 1 when any check
fails, 2 when the build itself fails. Needs only the standard library plus
TinyTeX and poppler (tools/setup.sh or tools/setup.ps1 installs both).

Runs on macOS, Linux and Windows. Binaries are found in TINYTEX_BIN and POPPLER_BIN
first, then in the default install locations, then on PATH. PATH comes last because
on Windows it often holds copies setup did not install: Git for Windows ships xpdf's
pdftotext (no -bbox-layout), and an older TeX Live may sit ahead of TinyTeX.
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

MAX_PAGES = 1
MAX_BULLET_LINES = 2
DANGLING_RATIO = 0.25   # last line of a wrapped bullet filling < 25% of the width
OVERFULL_PT = 1.0       # overfull \hbox warnings above this many points
BULLET = "•"


WINDOWS = os.name == "nt"
SETUP_HINT = "Run tools\\setup.ps1 first." if WINDOWS else "Run tools/setup.sh first."


def _search(name, env_var, patterns, usable=lambda path: True):
    """$env_var, then each glob pattern, then PATH; tries Windows extensions too."""
    names = [name + ext for ext in (".exe", ".bat", ".cmd")] if WINDOWS else [name]
    dirs = [os.environ[env_var]] if os.environ.get(env_var) else []
    for pattern in patterns:
        dirs += sorted(glob.glob(os.path.expandvars(os.path.expanduser(pattern))))
    dirs += os.environ.get("PATH", "").split(os.pathsep)
    for d in filter(None, dirs):
        for n in names:
            path = os.path.join(d, n)
            if os.path.isfile(path) and os.access(path, os.X_OK) and usable(path):
                return path
    return None


def _has_bbox_layout(pdftotext):
    """poppler's pdftotext has -bbox-layout; xpdf's (Git for Windows ships one) does not."""
    run = subprocess.run([pdftotext, "-h"], capture_output=True, text=True, errors="replace")
    return "-bbox-layout" in run.stdout + run.stderr


def find_tex_bin(name):
    found = _search(name, "TINYTEX_BIN", [
        "~/Library/TinyTeX/bin/*/", "~/.TinyTeX/bin/*/",
        "%APPDATA%/TinyTeX/bin/windows/", "%ProgramData%/TinyTeX/bin/windows/"])
    if not found:
        sys.exit(f"{name} not found. {SETUP_HINT}")
    return found


def find_poppler_bin(name):
    found = _search(name, "POPPLER_BIN", [
        "%LOCALAPPDATA%/Microsoft/WinGet/Packages/*Poppler*/*/Library/bin/",
        "%LOCALAPPDATA%/Microsoft/WinGet/Packages/*Poppler*/*/bin/",
        "~/scoop/apps/poppler/current/Library/bin/", "~/scoop/apps/poppler/current/bin/",
        "%ProgramData%/chocolatey/bin/"], _has_bbox_layout if name == "pdftotext" else lambda path: True)
    if not found:
        sys.exit(f"{name} (poppler) not found. {SETUP_HINT}")
    return found


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    # Outside a git checkout (a downloaded ZIP, or no git), the repo root is the folder above tools/.
    try:
        run = subprocess.run(["git", "-C", here, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True)
    except OSError:
        return os.path.dirname(here)
    return run.stdout.strip() if run.returncode == 0 else os.path.dirname(here)


def build(tex, outdir, install_missing):
    pdflatex = find_tex_bin("pdflatex")
    outdir = os.path.abspath(outdir)  # pdflatex runs from the .tex folder, so a relative path would point elsewhere
    os.makedirs(outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(tex))[0]
    cmd = [pdflatex, "-interaction=nonstopmode", "-halt-on-error",
           f"-output-directory={outdir}", os.path.basename(tex)]
    for _ in range(10):
        run = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(tex)),
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        missing = re.search(r"File `([^']+)' not found", run.stdout)
        if run.returncode == 0 or not (missing and install_missing):
            break
        tlmgr = find_tex_bin("tlmgr")
        hit = subprocess.run([tlmgr, "search", "--global", "--file", "/" + missing.group(1)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        pkg = next((l.rstrip(":") for l in hit.splitlines()
                    if l and not l.startswith(("tlmgr", " ", "\t"))), None)
        if not pkg:
            print(f"tlmgr found no package providing {missing.group(1)}")
            break
        print(f"installing {pkg} for {missing.group(1)}")
        inst = subprocess.run([tlmgr, "install", pkg], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if inst.returncode != 0:
            print(f"tlmgr install {pkg} failed (exit {inst.returncode}): {(inst.stderr or inst.stdout).strip()[-500:]}")
            break
    log_path = os.path.join(outdir, stem + ".log")
    if run.returncode != 0:
        errors = [l for l in run.stdout.splitlines() if l.startswith("!") or re.match(r"l\.\d+", l)]
        print("BUILD FAILED")
        print("\n".join(errors[:10]) or run.stdout[-2000:])
        if missing and not install_missing:
            print("Missing package file; rerun with --install-missing.")
        sys.exit(2)
    pdf = os.path.join(outdir, stem + ".pdf")
    final = os.path.join(os.path.dirname(os.path.abspath(tex)), stem + ".pdf")
    shutil.copyfile(pdf, final)
    return final, log_path


def lines_of(pdf):
    run = subprocess.run([find_poppler_bin("pdftotext"), "-enc", "UTF-8", "-bbox-layout", pdf, "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if run.returncode != 0:   # a tool failure, not a layout failure: exit 2 like a failed build
        print(f"pdftotext failed (exit {run.returncode}): {run.stderr.strip()[:500]}")
        sys.exit(2)
    xml = run.stdout
    xml = re.sub(r"<!DOCTYPE[^>]*>", "", xml).replace('xmlns="http://www.w3.org/1999/xhtml"', "")
    root = ET.fromstring(xml)
    pages = []
    for page in root.iter("page"):
        rows = []
        for ln in page.iter("line"):
            text = " ".join(w.text or "" for w in ln.iter("word"))
            rows.append({k: float(ln.get(k)) for k in ("xMin", "xMax", "yMin", "yMax")} | {"text": text})
        # pdftotext may split one visual line into several (a bullet glyph, a right-aligned
        # date); merge lines whose tops are within 2pt into one row
        merged = []
        for r in sorted(rows, key=lambda r: (r["yMin"], r["xMin"])):
            if merged and abs(r["yMin"] - merged[-1]["yMin"]) < 2:
                m = merged[-1]
                m["xMin"], m["xMax"] = min(m["xMin"], r["xMin"]), max(m["xMax"], r["xMax"])
                m["yMax"] = max(m["yMax"], r["yMax"])
                m["text"] = (m["text"] + " " + r["text"]) if r["xMin"] >= m["xMin"] else (r["text"] + " " + m["text"])
            else:
                merged.append(dict(r))
        pages.append({"w": float(page.get("width")), "h": float(page.get("height")), "lines": merged})
    return pages


def check(pdf, log_path=None, png=True):
    fails, notes = [], []
    pages = lines_of(pdf)
    if len(pages) != MAX_PAGES:
        fails.append(f"pages: {len(pages)} (limit {MAX_PAGES})")

    for pno, page in enumerate(pages, 1):
        rows = page["lines"]
        if not rows:
            continue
        left = min(r["xMin"] for r in rows)
        right = max(r["xMax"] for r in rows)
        # group lines into bullets: a bullet line starts with "•"; continuation lines
        # sit indented right of the bullet glyph and start before the next bullet or heading
        bullets, cur = [], None
        for r in sorted(rows, key=lambda r: (r["yMin"], r["xMin"])):
            if r["text"].startswith(BULLET):
                cur = {"lines": [r]}
                bullets.append(cur)
            elif cur and r["xMin"] > cur["lines"][0]["xMin"] + 4 and r["yMin"] - cur["lines"][-1]["yMin"] < 20:
                cur["lines"].append(r)
            else:
                cur = None
        for b in bullets:
            head = b["lines"][0]["text"][:60]
            n = len(b["lines"])
            if n > MAX_BULLET_LINES:
                fails.append(f"p{pno} bullet has {n} lines: {head}")
            if n > 1:
                last = b["lines"][-1]
                width = right - last["xMin"]
                ratio = (last["xMax"] - last["xMin"]) / width if width else 1
                if ratio < DANGLING_RATIO:
                    fails.append(f"p{pno} dangling last line ({ratio:.0%} of width): {head} … {last['text']}")
        bottom = max(r["yMax"] for r in rows)
        notes.append(f"p{pno}: {len(bullets)} bullets, text block x {left:.0f}–{right:.0f}, "
                     f"bottom slack {page['h'] - bottom:.0f}pt")

    text = " ".join(r["text"] for p in pages for r in p["lines"])
    if not re.search(r"[\w.+-]+@[\w-]+\.\w+", text):
        fails.append("no email address in the text layer")
    if re.search(r"\(cid:\d+\)|�", text):
        fails.append("garbage glyphs in the text layer")
    if "–" in text:
        notes.append("dates use en dashes (–); some ATS imports (Workday) drop them")

    if log_path and os.path.exists(log_path):
        log = open(log_path, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"Overfull \\hbox \(([\d.]+)pt too wide\)[^\n]*lines (\d+)", log):
            if float(m.group(1)) > OVERFULL_PT:
                fails.append(f"overfull box {m.group(1)}pt at source line {m.group(2)}")

    if png:
        prefix = os.path.splitext(pdf)[0]
        subprocess.run([find_poppler_bin("pdftoppm"), "-png", "-r", "110", pdf, prefix], check=True)
        notes.append("png: " + ", ".join(sorted(glob.glob(glob.escape(prefix) + "-*.png"))))

    for n in notes:
        print("note:", n)
    for f in fails:
        print("FAIL:", f)
    print("OK" if not fails else f"{len(fails)} check(s) failed")
    return not fails


def main():
    # Windows consoles default to a legacy code page; the report prints "•", "–" and "…"
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help=".tex to build and check, or .pdf with --check")
    ap.add_argument("--check", action="store_true", help="only check an existing PDF")
    ap.add_argument("--out", help="scratch build dir (default <repo>/.build/<stem>)")
    ap.add_argument("--install-missing", action="store_true", help="tlmgr-install missing packages and retry")
    ap.add_argument("--no-png", action="store_true", help="skip page images")
    a = ap.parse_args()
    if a.check:
        ok = check(a.path, png=not a.no_png)
    else:
        stem = os.path.splitext(os.path.basename(a.path))[0]
        out = a.out or os.path.join(repo_root(), ".build", stem)
        pdf, log = build(a.path, out, a.install_missing)
        print("pdf:", pdf)
        ok = check(pdf, log, png=not a.no_png)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
