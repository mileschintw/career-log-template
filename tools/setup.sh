#!/bin/sh
# Machine setup on macOS and Linux (SETUP.md step 5). Idempotent. Installs for this user only, with
# no password. On Linux a step that needs sudo (Chromium's system libraries) is printed for the user
# to run, at the end.
#
#   tools/setup.sh [--yes playwright-cli] [--no playwright-cli]
#
# Always: Python 3.11+ (through uv, into ~/.local/bin, when python3 is older), and TinyTeX (pdfTeX;
#   the templates use \pdfgentounicode, so XeTeX/LuaTeX and Tectonic will not do), the packages in
#   tools/tex-packages.txt, and poppler (pdfinfo, pdftotext, pdftoppm) for tools/resume.py's checks:
#   the user's own when tools/resume.py finds one, else conda-forge's, which micromamba installs
#   into ~/.career-log/poppler and a rerun updates (#281).
# Optional, installed only when ~/.career-log/machine.toml says yes for it:
#   playwright-cli  Node 18+ (through nvm), @playwright/cli (npm), its skill in this checkout,
#                   Chromium when Chrome and Edge are both missing (Linux: Chromium's system
#                   libraries need sudo; they are also checked when a playwright-cli config names
#                   Chromium)
# --yes and --no write the user's choice into machine.toml first; with only --no, that is all.
# A scheduled or unattended run (CAREER_LOG_UNATTENDED set) records any --yes or --no, then installs
# nothing, opens no dialog, and exits 3.
# Ends with tools/check.py setup.
# On Windows this script hands over to tools/setup.ps1.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TOOLS="playwright-cli"
MACHINE="$HOME/.career-log/machine.toml"

case "$(uname)" in
  MINGW*|MSYS*|CYGWIN*)   # Git Bash on Windows: hand over to PowerShell, with the same choices
    YES=; NO=
    while [ $# -gt 0 ]; do
      case "$1" in --yes) YES=$2; shift 2 ;; --no) NO=$2; shift 2 ;; *) shift ;; esac
    done
    exec powershell.exe -ExecutionPolicy Bypass -File "$ROOT/tools/setup.ps1" ${YES:+-Yes "$YES"} ${NO:+-No "$NO"} ;;
  Darwin) OS=mac; TEXDIR="$HOME/Library/TinyTeX"; BUNDLE=TinyTeX-1-darwin.tar.xz ;;
  Linux)  OS=linux; TEXDIR="$HOME/.TinyTeX"
          case "$(uname -m)" in aarch64|arm64) BUNDLE=TinyTeX-1-linux-arm64.tar.xz ;; *) BUNDLE=TinyTeX-1-linux-x86_64.tar.xz ;; esac ;;
  *) echo "unsupported OS: $(uname)"; exit 1 ;;
esac

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1. Install the prerequisites in SETUP.md step 1, then rerun"; exit 1; }; }
SUDO_LINES=
sudo_line() { SUDO_LINES="$SUDO_LINES
  $1"; }
USER_LINES=   # steps this script cannot do on this machine, for the user
user_line() { USER_LINES="$USER_LINES
  $1"; }

# ---- The user's choices: one `<tool> = true|false` line per optional tool in machine.toml ----

# TinyTeX was optional before #151; a leftover yes or no is dropped, since setup now always installs it
if [ -f "$MACHINE" ] && grep -q "^tinytex *=" "$MACHINE"; then
  grep -v "^tinytex *=" "$MACHINE" > "$MACHINE.tmp" || true
  mv "$MACHINE.tmp" "$MACHINE"
  echo "machine.toml: removed tinytex (TinyTeX is no longer optional: setup always installs it)"
fi
set_machine() {   # set_machine <key> <TOML value>: one `<key> = <value>` line in machine.toml
  mkdir -p "$(dirname "$MACHINE")"
  [ -f "$MACHINE" ] || printf '%s\n' "# career-log Machine setup: the optional tools the user wants on this machine" \
    "# (true) or declined (false), and where poppler came from. Written by tools/setup.sh and" \
    "# tools/setup.ps1; whether a tool is installed is detected on every run (tools/check.py)." > "$MACHINE"
  grep -v "^$1 *=" "$MACHINE" > "$MACHINE.tmp" || true
  echo "$1 = $2" >> "$MACHINE.tmp"
  mv "$MACHINE.tmp" "$MACHINE"
  echo "machine.toml: $1 = $2"
}
choose() {   # choose <comma list> <true|false>
  for t in $(echo "$1" | tr ',' ' '); do
    [ "$t" = tinytex ] && { echo "tinytex: not optional any more; setup always installs it"; continue; }
    case " $TOOLS " in *" $t "*) ;; *) echo "unknown tool: $t (tools: $TOOLS)"; exit 2 ;; esac
    set_machine "$t" "$2"
  done
}
GOT_YES=; GOT_NO=
while [ $# -gt 0 ]; do
  case "$1" in
    --yes) [ $# -ge 2 ] || { echo "--yes needs a tool"; exit 2; }; choose "$2" true; GOT_YES=1; shift 2 ;;
    --no)  [ $# -ge 2 ] || { echo "--no needs a tool"; exit 2; }; choose "$2" false; GOT_NO=1; shift 2 ;;
    *) echo "usage: tools/setup.sh [--yes <tool>[,<tool>]] [--no <tool>[,<tool>]]; tools: $TOOLS"; exit 2 ;;
  esac
done
# A no only records the answer: nothing to install
[ -n "$GOT_NO" ] && [ -z "$GOT_YES" ] && exit 0
chosen() { [ -f "$MACHINE" ] && grep -q "^$1 *= *$2" "$MACHINE"; }

if [ -n "${CAREER_LOG_UNATTENDED:-}" ]; then
  echo "unattended run (CAREER_LOG_UNATTENDED is set): setup installs nothing and opens no dialog. If tools/check.py reports something missing, run setup while the user is at the machine: sh '$ROOT/tools/setup.sh'"
  exit 3
fi

# ---- Python 3.11+ ----

py_ok() { "$1" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; }
find_py() {
  PY=
  for c in python3 "$HOME/.local/bin/python3" "$HOME"/.local/bin/python3.1[1-9]; do
    if command -v "$c" >/dev/null 2>&1 && py_ok "$c"; then PY=$(command -v "$c"); return; fi
  done
}
find_py
if [ -z "$PY" ]; then
  need curl
  if [ ! -x "$HOME/.local/bin/uv" ] && ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv into ~/.local/bin (it adds that folder to PATH in your shell profile)"
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
  UV=$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")
  echo "Installing Python 3.13 with uv, as python3 in ~/.local/bin"
  # --default also writes python3; older uv versions want it as a preview flag, and python3.13 comes either way
  "$UV" python install 3.13 --default || "$UV" python install 3.13
  find_py
  [ -n "$PY" ] || { echo "Python 3.11+ install failed: no python3.11+ in ~/.local/bin"; exit 1; }
fi
echo "python: $PY ($("$PY" --version 2>&1))"

# ---- playwright-cli ----

node_ok() { command -v node >/dev/null 2>&1 && node -e 'process.exit(process.versions.node.split(".")[0] < 18 ? 1 : 0)' 2>/dev/null; }
# A Node whose global npm folder needs sudo (a distribution's package) is passed over for nvm's.
npm_writable() {
  command -v npm >/dev/null 2>&1 || return 1
  p=$(npm prefix -g 2>/dev/null) || return 1
  [ -w "$p/lib" ] || { [ ! -e "$p/lib" ] && [ -w "$p" ]; }
}
nvm_path() {
  d=$(ls -d "$HOME"/.nvm/versions/node/v*/bin 2>/dev/null | sort -V | tail -n 1)
  [ -n "$d" ] && PATH="$d:$PATH" && export PATH
}

# nvm loads Node from ~/.bashrc or ~/.zshrc, which a non-interactive shell (bash -lc, an agent's
# shell tool) never reads, so its node, npm and playwright-cli are linked into ~/.local/bin, which
# login shells have on PATH. The links point at the newest nvm version that has playwright-cli
# (npm installs it per version), not at nvm's default; a rerun relinks, and removes links left
# dangling by `nvm uninstall`. A Node of the user's own (Homebrew's, say) is used as it is.
LOCAL_BIN="$HOME/.local/bin"
NVM_LINKS="node npm playwright-cli"
unlink_dangling() {
  for b in $NVM_LINKS; do
    t="$LOCAL_BIN/$b"
    if [ -L "$t" ] && [ ! -e "$t" ]; then
      case "$(readlink "$t")" in */.nvm/*) rm -f "$t" ;; esac
    fi
  done
}
link_nvm() {
  case "$(npm prefix -g)" in */.nvm/versions/node/*) ;; *) return 0 ;; esac   # not nvm's Node
  d=$(ls -d "$HOME"/.nvm/versions/node/v*/bin 2>/dev/null | sort -V -r | while IFS= read -r v; do
        [ -x "$v/playwright-cli" ] && { echo "$v"; break; }; done || true)
  [ -n "$d" ] || return 0
  mkdir -p "$LOCAL_BIN"
  for b in $NVM_LINKS; do   # a file or link that is not nvm's is the user's: left alone
    t="$LOCAL_BIN/$b"
    if [ -L "$t" ]; then
      case "$(readlink "$t")" in */.nvm/*) ;; *) echo "left alone: $t links to $(readlink "$t")"; continue ;; esac
    elif [ -e "$t" ]; then
      echo "left alone: $t is not a link"; continue
    fi
    ln -sfn "$d/$b" "$t"
    echo "linked $t -> $d/$b"
  done
  login_path
}
# ~/.local/bin on the login shell's PATH, for bash and for the user's shell when it is zsh: Ubuntu's
# ~/.profile adds it once it exists, and uv's installer adds it for bash; zsh -l reads ~/.zprofile,
# not the ~/.zshrc uv writes to.
login_path() {
  for sh_ in /bin/bash "${SHELL:-}"; do
    case "$sh_" in */zsh) LPROFILE="$HOME/.zprofile" ;; */bash) LPROFILE= ;; *) continue ;; esac
    command -v "$sh_" >/dev/null 2>&1 || continue
    # after a marker, so a profile that prints a banner cannot hide the PATH
    P=$(env -i HOME="$HOME" USER="${USER:-}" LOGNAME="${LOGNAME:-}" "$sh_" -lc 'printf "\n#PATH#%s" "$PATH"' 2>/dev/null </dev/null | sed -n 's/^#PATH#//p')
    case ":$P:" in *":$LOCAL_BIN:"*) continue ;; esac
    if [ -z "$LPROFILE" ]; then   # bash -l reads only the first of these that exists
      for p in .bash_profile .bash_login .profile; do
        [ -f "$HOME/$p" ] && { LPROFILE="$HOME/$p"; break; }
      done
      LPROFILE=${LPROFILE:-$HOME/.profile}
    fi
    LINE='export PATH="$HOME/.local/bin:$PATH"'
    grep -qsF "$LINE" "$LPROFILE" || { echo "$LINE" >> "$LPROFILE"; echo "added to $LPROFILE: $LINE"; }
  done
}

# Exits 0 when this checkout's playwright-cli configs make `playwright-cli open` launch Chromium:
# asks tools/check.py's config_names_chromium, so setup and check.py agree on when to check
# Chromium's libraries
config_names_chromium() {
  "$PY" -B -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import check
sys.exit(not check.config_names_chromium(check.cli_configs(check.Context("setup", root=sys.argv[2]))))' "$ROOT/tools" "$ROOT"
}

install_playwright() {
  unlink_dangling
  # nvm's Node, from an earlier run, when this shell has no Node 18+ of the user's own
  OWN_NODE=
  if node_ok && npm_writable; then
    case "$(command -v node)" in */.nvm/*|"$LOCAL_BIN"/*) ;; *) OWN_NODE=1 ;; esac
  fi
  [ -n "$OWN_NODE" ] || nvm_path || true
  if ! node_ok || ! npm_writable; then
    need curl; need bash
    if [ ! -s "$HOME/.nvm/nvm.sh" ]; then
      echo "Installing nvm into ~/.nvm (it adds itself to your shell profile)"
      curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
    fi
    echo "Installing Node LTS with nvm"
    bash -c '. "$HOME/.nvm/nvm.sh" && nvm install --lts'
    nvm_path
  fi
  echo "node: $(command -v node) ($(node --version))"
  command -v playwright-cli >/dev/null 2>&1 || npm install -g @playwright/cli@latest
  link_nvm
  # playwright-cli install --skills picks Chrome, then Edge, only where playwright-core looks for
  # them (macOS: /Applications, not ~/Applications); tools/check.py counts the same paths
  BROWSER=
  case "$OS" in
    mac) { [ -d "/Applications/Google Chrome.app" ] || [ -f "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" ]; } && BROWSER=1 ;;
    linux) { [ -x /opt/google/chrome/chrome ] || [ -f /opt/microsoft/msedge/msedge ]; } && BROWSER=1 ;;
  esac
  if [ -z "$BROWSER" ]; then
    echo "Chrome and Edge not found where playwright-cli looks: installing Chromium into Playwright's cache"
    playwright-cli install-browser chromium
  fi
  # The skill and, without Chrome, .playwright/cli.config.json (Edge or Chromium): per checkout, ignored by git
  (cd "$ROOT" && playwright-cli install --skills)
  # Chrome's and Edge's packages bring their libraries, but a playwright-cli config naming Chromium
  # launches it anyway
  if [ "$OS" = linux ] && { [ -z "$BROWSER" ] || config_names_chromium; }; then
    CLI=$(dirname "$(readlink -f "$(command -v playwright-cli)")")
    CORE=
    # The paths tools/check.py's playwright_core_cli tries
    for c in "$CLI/node_modules/playwright-core/cli.js" "$CLI/node_modules/@playwright/cli/node_modules/playwright-core/cli.js" \
             "$CLI/../lib/node_modules/@playwright/cli/node_modules/playwright-core/cli.js"; do
      [ -f "$c" ] && { CORE=$c; break; }
    done
    CACHE=${PLAYWRIGHT_BROWSERS_PATH:-${XDG_CACHE_HOME:-$HOME/.cache}/ms-playwright}
    # The libraries Chromium cannot find (ldd), as Playwright checks at launch
    if for b in "$CACHE"/chromium-*/chrome-linux*/chrome "$CACHE"/chromium_headless_shell-*/chrome-*/chrome-headless-shell; do
         [ -x "$b" ] && ldd "$b" 2>/dev/null; done | grep -q "not found"; then
      # playwright-core's install-deps downloads no browser; without it, no command here is libraries only
      if [ -n "$CORE" ]; then sudo_line "sudo $(command -v node) $CORE install-deps chromium   # Chromium's system libraries"
      else user_line "Chromium's system libraries: reinstall playwright-cli with \`npm install -g @playwright/cli@latest\`, since playwright-core, whose install-deps installs them, is not in $CLI"
      fi
    fi
  fi
}

# ---- poppler ----

# poppler's pdftotext (tools/resume.py needs its -bbox-layout, which xpdf's lacks), as tools/resume.py
# picks it: the user's own first (POPPLER_BIN, Homebrew's folders, PATH), setup's environment last
pdftotext_bin() {
  "$PY" -B -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import resume
p = resume.poppler_bin("pdftotext"); print(p or ""); sys.exit(not p)' "$ROOT/tools"
}
# tools/resume.py's poppler_env, spelled as it prints the paths it finds
POPPLER_ENV=$("$PY" -B -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import resume; print(resume.poppler_env())' "$ROOT/tools")
MAMBA_VERSION=2.9.0-0   # micromamba's release; the download is checked against the release's .sha256
MAMBA_ROOT="$(dirname "$POPPLER_ENV")/micromamba"   # micromamba and its package cache
MAMBA="$MAMBA_ROOT/micromamba"
get_micromamba() {
  [ -x "$MAMBA" ] && return 0
  need curl
  case "$OS-$(uname -m)" in
    mac-arm64) P=osx-arm64 ;; mac-*) P=osx-64 ;;
    linux-aarch64|linux-arm64) P=linux-aarch64 ;; linux-x86_64) P=linux-64 ;;
    *) echo "micromamba: no build for $(uname -m)"; return 1 ;;
  esac
  URL="https://github.com/mamba-org/micromamba-releases/releases/download/$MAMBA_VERSION/micromamba-$P"
  echo "Downloading micromamba $MAMBA_VERSION (about 15-20 MB) into $MAMBA_ROOT"
  mkdir -p "$MAMBA_ROOT"
  curl -fsSL --retry 5 -o "$MAMBA.part" "$URL" && SUM=$(curl -fsSL --retry 5 "$URL.sha256") || { rm -f "$MAMBA.part"; return 1; }
  GOT=$( { sha256sum "$MAMBA.part" 2>/dev/null || shasum -a 256 "$MAMBA.part"; } | cut -d' ' -f1)
  if [ "$GOT" != "$(echo "$SUM" | cut -d' ' -f1)" ]; then
    echo "micromamba: the download does not match its checksum"; rm -f "$MAMBA.part"; return 1
  fi
  chmod +x "$MAMBA.part" && mv "$MAMBA.part" "$MAMBA"
}
# --no-rc with --override-channels -c conda-forge: conda-forge only, whatever a .condarc of the user's says
mamba() { "$MAMBA" "$@" -y --no-rc -r "$MAMBA_ROOT"; }

install_poppler() {
  FOUND=$(pdftotext_bin) || FOUND=
  case "$FOUND" in
    ""|"$POPPLER_ENV"/*) ;;
    *) echo "poppler: $FOUND (the user's own: used as it is)"; set_machine poppler '"own"'
       # micromamba serves only setup's environment: with no working one left, both go
       if [ -d "$MAMBA_ROOT" ] && [ ! -f "$POPPLER_ENV/bin/pdftotext" ]; then
         if rm -rf "$MAMBA_ROOT" "$POPPLER_ENV"; then echo "removed $MAMBA_ROOT: setup has no poppler environment to manage"; fi
       fi
       return ;;
  esac
  if ! get_micromamba; then
    user_line "poppler: micromamba did not download (offline, or behind a proxy: set HTTPS_PROXY), so rerun this script; or install poppler yourself and set POPPLER_BIN to its bin folder"
    return
  fi
  # An environment with its pdftotext in place is updated, even when that pdftotext did not answer
  # (a first run slowed by a virus scan, say); one an interrupted run left without it is made afresh
  if [ -n "$FOUND" ] || { [ -d "$POPPLER_ENV/conda-meta" ] && [ -f "$POPPLER_ENV/bin/pdftotext" ]; }; then
    echo "Updating poppler in $POPPLER_ENV (micromamba, conda-forge)"
    mamba update -p "$POPPLER_ENV" --override-channels -c conda-forge --all ||
      echo "poppler: the update failed; rerun this script to try again"
  else
    rm -rf "$POPPLER_ENV"
    echo "Installing poppler into $POPPLER_ENV (micromamba, conda-forge)"
    # created empty, then filled: `create` with packages ends by telling the user to activate the
    # environment, which career-log never needs
    if ! { mamba create -p "$POPPLER_ENV" >/dev/null && mamba install -p "$POPPLER_ENV" --override-channels -c conda-forge poppler; }; then
      user_line "poppler: micromamba could not install it (its error is above), so rerun this script; or install poppler yourself and set POPPLER_BIN to its bin folder"
      return
    fi
  fi
  rm -rf "$MAMBA_ROOT/pkgs"   # the downloaded packages (about 300 MB): the environment has its own links or copies
  if pdftotext_bin >/dev/null; then set_machine poppler '"micromamba"'; fi
}

# ---- TinyTeX ----

find_bin() { for d in "$TEXDIR"/bin/*/; do [ -x "$d/pdflatex" ] && { echo "${d%/}"; return; }; done; }

install_tinytex() {
  BIN=$(find_bin || true)
  if [ -z "${BIN:-}" ]; then
    need curl; need tar
    [ "$OS" = linux ] && need xz   # macOS tar reads .xz itself
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

  install_poppler
  if ! pdftotext_bin >/dev/null; then
    echo "poppler missing: skipping the example build until it is installed"
    return
  fi
  echo "Checking: building the example resume"
  CHECK="$ROOT/.build/setup-check"
  mkdir -p "$CHECK"
  cp "$ROOT/skills/career-log/examples/resume.tex" "$CHECK/"   # build a copy, so the example stays untouched
  "$PY" "$ROOT/tools/resume.py" "$CHECK/resume.tex" --out "$CHECK/build"
}

echo "== tinytex"
install_tinytex
UNDECIDED=
for t in $TOOLS; do
  if chosen "$t" true; then
    echo "== $t"
    case "$t" in playwright-cli) install_playwright ;; esac
  elif ! chosen "$t" false; then
    UNDECIDED="$UNDECIDED $t"
  fi
done

[ -z "$UNDECIDED" ] || echo "not chosen yet on this machine:$UNDECIDED (rerun with --yes or --no for each)"
if [ -n "$SUDO_LINES" ]; then
  echo "needs sudo: run these yourself, then rerun this script:$SUDO_LINES"
fi
if [ -n "$USER_LINES" ]; then
  echo "not installed by this script: do these yourself, then rerun it:$USER_LINES"
fi
echo "== tools/check.py setup"
"$PY" -I "$ROOT/tools/check.py" setup || true
[ -z "$SUDO_LINES$USER_LINES" ]
