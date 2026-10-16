#!/bin/sh
# Install the local LaTeX toolchain for building resumes. Idempotent; no sudo.
#   - TinyTeX (pdfTeX; the templates use \pdfgentounicode, so XeTeX/LuaTeX and Tectonic will not do)
#   - the TeX packages in tools/tex-packages.txt
#   - poppler (pdfinfo, pdftotext, pdftoppm) for tools/resume.py checks
# On Windows this script hands over to tools/setup.ps1.
set -eu
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)

case "$(uname)" in
  MINGW*|MSYS*|CYGWIN*)   # Git Bash on Windows: hand over to PowerShell
          exec powershell.exe -ExecutionPolicy Bypass -File "$ROOT/tools/setup.ps1" ;;
  Darwin) TEXDIR="$HOME/Library/TinyTeX"; BUNDLE=TinyTeX-1-darwin.tar.xz ;;
  Linux)  TEXDIR="$HOME/.TinyTeX"
          case "$(uname -m)" in aarch64|arm64) BUNDLE=TinyTeX-1-linux-arm64.tar.xz ;; *) BUNDLE=TinyTeX-1-linux-x86_64.tar.xz ;; esac ;;
  *) echo "unsupported OS: $(uname)"; exit 1 ;;
esac

find_bin() { for d in "$TEXDIR"/bin/*/; do [ -x "$d/pdflatex" ] && { echo "${d%/}"; return; }; done; }

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1. Install the prerequisites in SETUP.md step 1, then rerun"; exit 1; }; }

BIN=$(find_bin || true)
if [ -z "${BIN:-}" ]; then
  need curl; need tar
  [ "$(uname)" = Linux ] && need xz   # macOS tar reads .xz itself
  echo "Installing TinyTeX into $TEXDIR"
  TMP=$(mktemp -d)
  trap 'rm -rf "$TMP"' EXIT   # no 60 MB leftover when a step fails
  trap 'exit 130' INT TERM HUP  # route Ctrl-C through the EXIT trap
  curl -L -f --retry 5 -o "$TMP/$BUNDLE" "https://github.com/rstudio/tinytex-releases/releases/download/daily/$BUNDLE"
  mkdir -p "$(dirname "$TEXDIR")"
  tar xf "$TMP/$BUNDLE" -C "$(dirname "$TEXDIR")"
  BIN=$(find_bin)
fi
echo "pdflatex: $BIN/pdflatex"

PKGS=$(grep -v '^\s*#' "$ROOT/tools/tex-packages.txt" | tr '\n' ' ')
# A TinyTeX older than the repository refuses to install until tlmgr updates itself.
"$BIN/tlmgr" update --self
# shellcheck disable=SC2086
"$BIN/tlmgr" install $PKGS

# poppler's pdftotext, not xpdf's: tools/resume.py needs -bbox-layout
if ! pdftotext -h 2>&1 | grep -q -- -bbox-layout; then
  if command -v brew >/dev/null 2>&1; then brew install poppler
  elif command -v apt-get >/dev/null 2>&1; then echo "Run: sudo apt-get install poppler-utils"; exit 1
  else echo "Install poppler (pdfinfo, pdftotext, pdftoppm) with your package manager"; exit 1
  fi
fi

echo "Checking: building the example resume"
NEWEST="$ROOT/skills/career-log/examples/resume.tex"
CHECK="$ROOT/.build/setup-check"
mkdir -p "$CHECK"
cp "$NEWEST" "$CHECK/"   # build a copy, so the example stays untouched
python3 "$ROOT/tools/resume.py" "$CHECK/$(basename "$NEWEST")" --out "$CHECK/build"
