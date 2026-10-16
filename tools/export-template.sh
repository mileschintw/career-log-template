#!/bin/sh
# Build the shareable Template (Engine + empty Log skeleton) into a new folder.
#   tools/export-template.sh <dest>
# Exports committed content only (git archive HEAD): the allowlist below, then the
# skeleton in tools/template/ overlaid at the root. Anything not on the allowlist
# (entries, sources, outputs, profile, direction, ...) never leaves, and neither do
# uncommitted edits or untracked files.
# Then scans every exported file name and file for the patterns in .export-deny
# (one extended regex per line, whole words, case-insensitive; that file stays here)
# and fails on any hit. See docs/adr/0001 and 0002.
set -eu
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
DEST=${1:?usage: tools/export-template.sh <dest>}
DENY="$ROOT/.export-deny"

# The allowlist: the Engine, plus the files every Log needs as they are.
ALLOW="skills tools SETUP.md CLAUDE.md GLOSSARY.md docs/adr .gitattributes .gitignore entries/_template.md"

if [ -e "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null)" ]; then
  echo "refusing: $DEST exists and is not empty"; exit 1
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
if [ "$NPAT" -eq 0 ]; then
  echo "refusing: $DENY has no patterns. Add your name, email, schools, employers and projects, one per line"; exit 1
fi

mkdir -p "$DEST"
DEST=$(cd "$DEST" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# core.autocrlf=false: Git for Windows sets it to true machine-wide, and the archive of the
# tools/template subtree does not see the root .gitattributes, so its files would come out CRLF
# shellcheck disable=SC2086
git -C "$ROOT" -c core.autocrlf=false archive --format=tar -o "$TMP/engine.tar" HEAD -- $ALLOW
git -C "$ROOT" -c core.autocrlf=false archive --format=tar -o "$TMP/skeleton.tar" HEAD:tools/template
tar xf "$TMP/engine.tar" -C "$DEST"
tar xf "$TMP/skeleton.tar" -C "$DEST"
mkdir -p "$DEST/sources/inbox" "$DEST/outputs"
touch "$DEST/sources/inbox/.gitkeep" "$DEST/outputs/.gitkeep"

# Scan for personal content. LICENSE names the copyright holder on purpose.
FOUND=0
while IFS= read -r pat || [ -n "$pat" ]; do
  pat=$(printf '%s' "$pat" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  case "$pat" in ''|'#'*) continue ;; esac
  HITS=$( { (cd "$DEST" && find . | grep -iwE -- "$pat") || true
            grep -rniwE --exclude=LICENSE -- "$pat" "$DEST" || true; } )
  if [ -n "$HITS" ]; then
    echo "personal content: /$pat/"
    echo "$HITS" | head -5 | sed 's/^/  /'
    FOUND=1
  fi
done < "$DENY"
if [ "$FOUND" -ne 0 ]; then echo "FAIL: fix the Engine files above, commit, then export again"; exit 1; fi

echo "Template written to $DEST ($(find "$DEST" -type f | wc -l | tr -d ' ') files)"
echo "OK"
