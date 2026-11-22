#!/bin/sh
# Build the shareable Template (Engine + empty Log skeleton) into a new folder.
#   tools/export-template.sh [--version <semver>[-dev.<n>]] <dest>
# --version names the release this export is (ADR 0011); without it the export is
# stamped `next`, a build no Log upgrades from or to. A Dev build's version, <semver>-dev.<n>
# (maintainer/devbuild.py), is a build towards the release not yet made: it ships the next guide
# as it stands, where a release refuses one that holds a change.
# Exports committed content only (git archive HEAD): the allowlist below, then the
# skeleton in tools/template/ overlaid at the root. Anything not on the allowlist
# (entries, sources, outputs, profile, direction, ...) never leaves, and neither do
# uncommitted edits or untracked files.
# Then scans every exported file name and file for the patterns in .export-deny
# (one extended regex per line, whole words, case-insensitive; that file stays here)
# and fails on any hit. See docs/adr/0002 and 0015. In the Template's source (the Engine repo,
# known by its maintainer/ folder), which holds no Log and so no .export-deny of its own, the
# scan reads tools/template/.export-deny, the list every Log starts with.
set -eu
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
USAGE="usage: tools/export-template.sh [--version <semver>[-dev.<n>]] <dest>"
VERSION=next
DEV=
if [ "${1:-}" = "--version" ]; then
  VERSION=${2:?$USAGE}; shift 2
  if printf '%s\n' "$VERSION" | grep -qxE '[0-9]+\.[0-9]+\.[0-9]+-dev\.[1-9][0-9]*'; then
    DEV=1
  elif ! printf '%s\n' "$VERSION" | grep -qxE '[0-9]+\.[0-9]+\.[0-9]+'; then
    echo "refusing: --version takes a semver such as 0.2.0, or a Dev build's such as 0.2.1-dev.1, not $VERSION"; exit 1
  fi
fi
DEST=${1:?$USAGE}
# The Template's source: the Engine repo, the one repo with the maintainer's tools (ADR 0015)
SOURCE=; [ -d "$ROOT/maintainer" ] && SOURCE=1
DENY="$ROOT/.export-deny"
if [ -n "$SOURCE" ] && [ ! -f "$DENY" ]; then DENY="$ROOT/tools/template/.export-deny"; fi

# The allowlist: the Engine, plus the files every Log needs as they are. The rest of docs/ is the
# source maintainer's: list docs/ subpaths one by one, never docs as a whole.
ALLOW="skills tools SETUP.md AGENTS.md CLAUDE.md GLOSSARY.md docs/guide.md docs/adr docs/upgrades docs/social-preview/social-preview.svg docs/social-preview/banner.svg .gitattributes .gitignore entries/_template.md"

if [ -e "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null)" ]; then
  echo "refusing: $DEST exists and is not empty"; exit 1
fi
# A release ships no unreleased guide: upgrade-next.* is renamed to the version first, unless it
# still holds only the empty skeleton: no Log format change (`## Changes`, CHECKS) and no new
# setting (`## 3. New settings`). Read from HEAD, the commit exported. A Dev build is no release.
if [ "$VERSION" != next ] && [ -z "$DEV" ]; then
  NEXT_MD=$(git -C "$ROOT" show HEAD:docs/upgrades/upgrade-next.md 2>/dev/null || true)
  NEXT_PY=$(git -C "$ROOT" show HEAD:docs/upgrades/upgrade-next.py 2>/dev/null || true)
  if { [ -n "$NEXT_MD" ] && ! printf '%s\n' "$NEXT_MD" | tr -d '\r' | grep -qxF 'No Log format change yet.'; } ||
     { [ -n "$NEXT_MD" ] && ! printf '%s\n' "$NEXT_MD" | tr -d '\r' | grep -qxF 'This release adds none.'; } ||
     { [ -n "$NEXT_PY" ] && ! printf '%s\n' "$NEXT_PY" | tr -d '\r' | grep -qxF 'CHECKS = []'; }; then
    echo "refusing: docs/upgrades/upgrade-next.* holds a Log format change or a new setting; rename them to upgrade-$VERSION.* first"; exit 1
  fi
fi
if [ ! -f "$DENY" ]; then
  echo "refusing: no $DENY (patterns that must not appear in the Template; see tools/template/.export-deny)"; exit 1
fi
# shellcheck disable=SC2086
if [ -n "$(git -C "$ROOT" status --porcelain -- $ALLOW)" ]; then
  echo "note: uncommitted changes under the allowlist are NOT exported; commit them first if they belong in the Template"
fi

# grep exits 2 on a malformed pattern; check them all before writing anything
NPAT=0
while IFS= read -r pat || [ -n "$pat" ]; do
  pat=$(printf '%s' "$pat" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  case "$pat" in ''|'#'*) continue ;; esac
  NPAT=$((NPAT + 1))
  RC=0; printf 'x\n' | grep -E -- "$pat" >/dev/null 2>&1 || RC=$?
  if [ "$RC" -gt 1 ]; then echo "FAIL: bad pattern in $DENY: $pat"; exit 1; fi
done < "$DENY"
if [ "$NPAT" -eq 0 ] && [ -z "$SOURCE" ]; then
  echo "refusing: $DENY has no patterns. Add your name, email, schools, employers and projects, one per line"; exit 1
fi
# The export is built and checked in $OUT and copied to DEST only once every check passes, so
# a failed export leaves DEST empty and a rerun into it is not refused.
mkdir -p "$DEST"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
OUT="$TMP/export"
mkdir "$OUT"

# core.autocrlf=false: Git for Windows sets it to true machine-wide, and the archive of the
# tools/template subtree does not see the root .gitattributes, so its files would come out CRLF
# shellcheck disable=SC2086
git -C "$ROOT" -c core.autocrlf=false archive --format=tar -o "$TMP/engine.tar" HEAD -- $ALLOW
git -C "$ROOT" -c core.autocrlf=false archive --format=tar -o "$TMP/skeleton.tar" HEAD:tools/template
tar xf "$TMP/engine.tar" -C "$OUT"
tar xf "$TMP/skeleton.tar" -C "$OUT"
# The maintainer's files in docs/upgrades/ stay here: the scratch Logs that test a guide
# (test-*.sh), the guide of the release not yet made (upgrade-next.*, which a Dev build ships as it
# stands) and its empty form (upgrade-skeleton.*).
rm -f "$OUT"/docs/upgrades/test-* "$OUT"/docs/upgrades/upgrade-skeleton.*
if [ -z "$DEV" ]; then rm -f "$OUT"/docs/upgrades/upgrade-next.*; fi
# Stamp the version and the commit exported: "Use this template" squashes the history, so this
# file is how a Log names its Template version (the upgrade mode, the issue form, import-chats
# step 8). Written before the scan, and only from the Template's own source: an export from a
# Log made from the Template keeps the stamp it came with.
if [ -n "$SOURCE" ]; then
  printf '%s\nsource %s\n' "$VERSION" "$(git -C "$ROOT" rev-parse HEAD)" > "$OUT/tools/TEMPLATE_VERSION"
fi
# Drop source-only blocks, text only the Template's source maintainer needs: in every .md file,
# the lines from a line that is exactly <!-- source-only --> through one that is exactly
# <!-- /source-only -->, plus one blank line after it. An unclosed, nested or unopened block
# fails the export, and so does a marker left at the start of a line in any exported file
# (indented, with other text after it, or outside a .md file), so a stray marker cannot drop
# the rest of a file.
MARK='^[[:space:]]*<!-- /?source-only -->'
RC=0; grep -rlE --include='*.md' -- "$MARK" "$OUT" > "$TMP/trim-files" || RC=$?
if [ "$RC" -gt 1 ]; then echo "FAIL: could not search the export for source-only markers"; exit 1; fi
while IFS= read -r f; do
  # awk exits 3 on a marker that is not alone on its line at column 0, 4 on unbalanced markers
  # (codes awk does not use for its own errors). Other leading whitespace, such as a form feed,
  # passes through here and the leftover check below catches it.
  RC=0; awk '{ s = $0; sub(/\r$/, "", s) }
             s ~ /^[ \t]*<!-- \/?source-only -->/ && s != "<!-- source-only -->" && s != "<!-- /source-only -->" { bad = 3; exit }
             s == "<!-- source-only -->" { if (on) { bad = 4; exit }; on = 1; next }
             s == "<!-- /source-only -->" { if (!on) { bad = 4; exit }; on = 0; skip = 1; next }
             on { next }
             skip { skip = 0; if (s == "") next }
             { print }
             END { if (bad) exit bad; if (on) exit 4 }' "$f" > "$f.trim" || RC=$?
  if [ "$RC" -eq 3 ]; then echo "FAIL: misplaced source-only marker in ${f#"$OUT"/}; each marker must be alone on its line, at column 0"; exit 1; fi
  if [ "$RC" -eq 4 ]; then echo "FAIL: unbalanced source-only markers in ${f#"$OUT"/} (a block left open, nested, or closed without opening)"; exit 1; fi
  if [ "$RC" -ne 0 ]; then echo "FAIL: could not trim source-only blocks in ${f#"$OUT"/}"; exit 1; fi
  mv "$f.trim" "$f"
done < "$TMP/trim-files"
RC=0; grep -rlE -- "$MARK" "$OUT" > "$TMP/marker-left" || RC=$?
if [ "$RC" -gt 1 ]; then echo "FAIL: could not search the export for source-only markers"; exit 1; fi
if [ "$RC" -eq 0 ]; then
  echo "FAIL: source-only marker left in the export; each marker must be alone on its line, at column 0, in a .md file:"
  while IFS= read -r f; do echo "  ${f#"$OUT"/}"; done < "$TMP/marker-left"
  exit 1
fi
mkdir -p "$OUT/sources/inbox" "$OUT/outputs/applications" "$OUT/outputs/resumes" "$OUT/outputs/reports"
touch "$OUT/sources/inbox/.gitkeep" "$OUT/outputs/applications/.gitkeep" "$OUT/outputs/resumes/.gitkeep" "$OUT/outputs/reports/.gitkeep"
# The front page ships in both languages
for f in README.md README.zh-TW.md; do
  if [ ! -f "$OUT/$f" ]; then echo "FAIL: $f missing from the export (expected in tools/template/)"; exit 1; fi
done

# Scan for personal content. LICENSE names the copyright holder on purpose.
FOUND=0
while IFS= read -r pat || [ -n "$pat" ]; do
  pat=$(printf '%s' "$pat" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  case "$pat" in ''|'#'*) continue ;; esac
  HITS=$( { (cd "$OUT" && find . | grep -iwE -- "$pat") || true
            (cd "$OUT" && grep -rniwE --exclude=LICENSE -- "$pat" .) || true; } )
  if [ -n "$HITS" ]; then
    echo "personal content: /$pat/"
    echo "$HITS" | head -5 | sed 's/^/  /'
    FOUND=1
  fi
done < "$DENY"
if [ "$FOUND" -ne 0 ] && [ -n "$SOURCE" ]; then echo "FAIL: a pattern in $DENY matched the export above; that list ships to every Log as it is, so take the pattern out of it, commit, then export again"; exit 1; fi
if [ "$FOUND" -ne 0 ]; then echo "FAIL: fix the Engine files above, commit, then export again. Where a hit is a common word or a tool's name that a .export-deny line matches, ask the user whether to clear that name instead; on a yes, run: python3 -I tools/deny_coverage.py clear <name> (py -3 on Windows) and follow its output"; exit 1; fi

cp -R "$OUT/." "$DEST"
echo "Template written to $DEST ($(find "$DEST" -type f | wc -l | tr -d ' ') files)"
echo "OK"
