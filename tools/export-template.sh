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
ALLOWED="$ROOT/.export-allow"

# The allowlist: the Engine, plus the files every Log needs as they are. The rest of docs/ is the
# source maintainer's: list docs/ subpaths one by one, never docs as a whole.
ALLOW="skills tools SETUP.md AGENTS.md CLAUDE.md GLOSSARY.md docs/adr docs/social-preview/social-preview.svg .gitattributes .gitignore entries/_template.md"

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
# Stamp the commit exported: "Use this template" squashes the history, so this file is how a
# Log names its Template version (the issue form, import-chats step 8). Written before the scan,
# and only from the Template's own source (it has .export-allow): an export from a Log made
# from the Template keeps the stamp it came with, a commit upstream can look up.
if [ -f "$ALLOWED" ]; then git -C "$ROOT" rev-parse HEAD > "$OUT/tools/TEMPLATE_VERSION"; fi
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
# The content scan reads a copy with the fixed strings in .export-allow masked out
# (the Template's own upstream URL), so the deny list itself never needs loosening.
SCAN="$TMP/scan"
cp -R "$OUT" "$SCAN"
# Matching ignores case, like the deny scan. LC_ALL=C makes awk treat every file as bytes, so
# a binary or non-UTF-8 file cannot stop it. A file awk still fails on stays unmasked, which can
# only add hits, never hide one, and the loop's exit status never aborts the export (set -e).
if [ -f "$ALLOWED" ]; then
  find "$SCAN" -type f > "$TMP/scan-files"
  while IFS= read -r f; do
    if LC_ALL=C awk 'NR == FNR { s = $0; sub(/\r$/, "", s); sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s)
                                 if (s != "" && s !~ /^#/) a[++n] = tolower(s); next }
                     { for (i = 1; i <= n; i++) while ((p = index(tolower($0), a[i])) > 0)
                         $0 = substr($0, 1, p - 1) substr($0, p + length(a[i])); print }' "$ALLOWED" "$f" > "$f.masked"
    then mv "$f.masked" "$f"
    else rm -f "$f.masked"; echo "note: could not mask $f; scanning it as is"
    fi
  done < "$TMP/scan-files"
fi
FOUND=0
while IFS= read -r pat || [ -n "$pat" ]; do
  pat=$(printf '%s' "$pat" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  case "$pat" in ''|'#'*) continue ;; esac
  HITS=$( { (cd "$OUT" && find . | grep -iwE -- "$pat") || true
            (cd "$SCAN" && grep -rniwE --exclude=LICENSE -- "$pat" .) || true; } )
  if [ -n "$HITS" ]; then
    echo "personal content: /$pat/"
    echo "$HITS" | head -5 | sed 's/^/  /'
    FOUND=1
  fi
done < "$DENY"
if [ "$FOUND" -ne 0 ]; then echo "FAIL: fix the Engine files above, commit, then export again"; exit 1; fi

cp -R "$OUT/." "$DEST"
echo "Template written to $DEST ($(find "$DEST" -type f | wc -l | tr -d ' ') files)"
echo "OK"
