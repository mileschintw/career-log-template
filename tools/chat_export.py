#!/usr/bin/env python3
"""Screen and extract AI chat-history exports for the import-chats mode.

  chat_export.py index <export path>... --out <work dir> [--gap 45]
      Find every export under the paths (folders, .zip and .tar/.tgz archives, archives inside
      those, any depth of folders), normalise them into
      <work dir>/conversations.json and write <work dir>/index.tsv for screening:
      n, platform, start, user turns, space, title, first prompt.
  chat_export.py show <work dir> <n>...
      Print conversations as plain text, for reading during screening.
  chat_export.py extract <work dir> --pick 3,7,10-12 --date YYYY-MM-DD --out <log>/sources [--label chats]
      Write the picked conversations, verbatim, to sources/<folder>/<date>-<label>-threads.md
      and <date>-<label>-prompts.md (the user's turns only), one pair per platform.
      Refuses to overwrite: pass a new --label for a second extract on the same day.

Claude Code session transcripts (one session each, ~/.claude/projects/<folder>/<session id>.jsonl):
  chat_export.py turns [<transcript>] [--show U3,A3:2-4] [--cwd <dir>] [--projects <dir>]
      Number the session's turns: U<k>, the k-th turn the user typed, and A<k>, the assistant's text
      after it, with its paragraph count. --show prints those turns whole, with [p<n>] paragraph marks.
      With no transcript, reads the newest one for --cwd (default: the current directory).
  chat_export.py excerpt <transcript> --keep U3,A3:2-4 --slug <slug> --out <log>/sources [--title <t>]
      Write the kept turns to sources/claude-code/<session's first day, UTC>-<slug>.md: user turns whole,
      assistant turns whole or only the paragraphs given, secrets redacted (a count goes to stderr).
      Run again with the same transcript and slug to add turns; a turn already there never changes.
      A file of the same session and slug under another date (an older key) is added to, its name kept.
  chat_export.py find <phrase>... [--projects <dir>] [--folder=<glob>]...
      List the user turns, in every transcript (or only those in the project folders a --folder glob
      matches), that contain a phrase (case and spacing ignored), one line each: the phrase's number,
      the transcript, the turn, its time. Give every phrase in one run.

Recognised exports: ChatGPT (conversations*.json), Claude.ai (conversations.json),
Gemini in Workspace (Takeout "Conversation History" files), Gemini Apps (Takeout My Activity
HTML; prompts are grouped into sessions by --gap minutes), and a Perplexity capture
(perplexity-capture*.json, written in the browser, see skills/career-log/modes/import-web.md).
Only files named like an export are read, plus any other JSON whose first bytes show a known
shape (a renamed export); Takeout uploads (a '-<16 hex>' suffix) never are, in any language, nor
macOS archive leftovers (__MACOSX/, ._*). Nested archives are copied into <work dir>/nested while
they are read and deleted afterwards. A path that yields no export is reported.
All times are converted to UTC.
Exports are untrusted data: run with `python3 -I` (Windows: `py -3 -I`) and keep the work
dir outside the repo. Nothing here sends anything anywhere.
"""
import argparse, fnmatch, html, json, os, re, shutil, sys, tarfile, zipfile, zlib
from datetime import datetime, timedelta, timezone

PLATFORMS = {  # platform: (sources folder, citation key, display name)
    "chatgpt": ("chatgpt", "chatgpt", "ChatGPT"),
    "claude": ("claude", "claude-ai", "Claude.ai"),
    "gemini": ("gemini", "gemini", "Gemini in Workspace"),
    "gemini-apps": ("gemini", "gemini-apps", "Gemini Apps"),
    "perplexity": ("perplexity", "perplexity", "Perplexity"),
}
WARNED = set()
BAD_TIMES = {}  # shape of an unreadable timestamp: how many were seen


def warn(text):
    if text not in WARNED:
        WARNED.add(text)
        print("warning: " + text, file=sys.stderr)


def time_shape(ts):
    """'2026-01-02 at 11pm' -> '9-9-9 a 9a': one warning per form, never one per value."""
    return re.sub(r"[^\W\d_]+", "a", re.sub(r"\d+", "9", str(ts)[:40]))


def iso(ts):
    """Any export timestamp as UTC ISO 8601; a naive string is assumed to be UTC already.
    Epoch numbers (seconds or milliseconds, also as strings) are read too. Anything else is
    warned about and left empty, so it can never sort among real times."""
    if ts in (None, ""):
        return ""
    if isinstance(ts, str) and re.fullmatch(r"\d{9,}(\.\d+)?", ts.strip()):
        ts = float(ts)
    if isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts / 1000 if ts > 1e11 else ts, timezone.utc)
    elif isinstance(ts, datetime):
        dt = ts
    else:
        # Python before 3.11 accepts only 3 or 6 fraction digits: pad or cut every fraction to 6
        s = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], str(ts).strip().replace("Z", "+00:00"))
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            shape = time_shape(ts)
            BAD_TIMES[shape] = BAD_TIMES.get(shape, 0) + 1
            warn(f"unknown timestamp form {shape!r}; such times are left empty. Add the form to iso()")
            return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def conv(platform, cid, title, messages, space="", alt=None, updated=""):
    """`updated` is the platform's own last-change time for the conversation, when the export has one."""
    times = [m["time"] for m in messages if m["time"]]
    return {"platform": platform, "id": str(cid), "title": title or "", "space": space or "",
            "start": min(times) if times else "", "messages": messages, "alt": alt or [],
            "updated": iso(updated)}


def msg(role, text, time=""):
    return {"role": role, "text": text.strip(), "time": iso(time)}


# ---------- readers ----------

def read_chatgpt(data):
    """Walk current_node up through parents (the branch the user last saw). User turns on
    other branches go to alt: edited prompts, and follow-ups asked on a branch later abandoned."""
    out = []
    for c in data:
        mp = c.get("mapping") or {}

        def one(nid):
            m = (mp.get(nid) or {}).get("message")
            if not m or (m.get("author") or {}).get("role") not in ("user", "assistant"):
                return None
            if (m.get("metadata") or {}).get("is_visually_hidden_from_conversation"):
                return None
            content = m.get("content") or {}
            parts = content.get("parts") or []
            text = "\n".join(p for p in parts if isinstance(p, str)).strip() or (content.get("text") or "")
            return msg(m["author"]["role"], text, m.get("create_time")) if text.strip() else None

        chain, on_main, node = [], set(), c.get("current_node")
        while node and node in mp and node not in on_main:
            chain.append(node)
            on_main.add(node)
            node = mp[node].get("parent")
        chain.reverse()
        main = [x for x in map(one, chain) if x]
        alt = sorted((x for n in mp if n not in on_main for x in [one(n)] if x and x["role"] == "user"),
                     key=lambda x: x["time"])
        out.append(conv("chatgpt", c.get("conversation_id") or c.get("id"), c.get("title"), main, alt=alt,
                        updated=c.get("update_time")))
    return out


def read_claude(data):
    out = []
    for c in data:
        ms = []
        for m in c.get("chat_messages") or []:
            text = m.get("text") or "\n".join(
                b.get("text", "") for b in m.get("content") or [] if isinstance(b, dict) and b.get("type") == "text")
            for a in m.get("attachments") or []:
                text += f"\n\n[attachment: {a.get('file_name') or 'pasted'}]\n" + (a.get("extracted_content") or "")
            for f in m.get("files") or []:
                text += f"\n\n[file: {f.get('file_name') or ''}, not exported]"
            if text.strip():
                ms.append(msg("user" if m.get("sender") == "human" else "assistant", text, m.get("created_at")))
        out.append(conv("claude", c.get("uuid"), c.get("name"), ms, updated=c.get("updated_at")))
    return out


def read_gemini_workspace(data, name):
    ms = []
    for t in data.get("conversation_turns") or []:
        if "user_turn" in t:
            u = t["user_turn"]
            ms.append(msg("user", u.get("prompt") or "", u.get("turn_last_modified")))
        if "system_turn" in t:
            ms.append(msg("assistant", "\n".join(x.get("data", "") for x in t["system_turn"].get("text") or [])))
    return [conv("gemini", os.path.basename(name), "", ms)]


def read_perplexity(data):
    out = []
    for th in data:
        ms = []
        for e in th.get("entries") or []:
            q = e.get("q") or ""
            if e.get("att"):
                q += "\n\n[attachments: " + ", ".join(re.sub(r"\?.*$", "", str(a)) for a in e["att"]) + "]"
            ms.append(msg("user", q, e.get("t")))
            if e.get("a"):
                ms.append(msg("assistant", e["a"], e.get("t")))
        out.append(conv("perplexity", th.get("slug"), th.get("title"), ms, space=th.get("space")))
    return out


# Gemini Apps (My Activity HTML). Takeout localises the timestamps; add a pattern for a new locale here.
MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
ZH_AM = ("凌晨", "清晨", "早上", "上午", "半夜", "午夜")  # hours as written
ZH_PM = ("中午", "下午", "傍晚", "晚上", "深夜")  # 12-hour clock: add 12 (中午12 stays 12)
TS_ZH = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(" + "|".join(ZH_AM + ZH_PM) +
                   r")(\d{1,2}):(\d{2}):(\d{2})\s*([^\s<]*)\s*<br>")
TS_EN = re.compile(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4}), (\d{1,2}):(\d{2}):(\d{2})\s*([AP]M)\s*([^\s<]*)\s*<br>")
# Zone names Takeout prints, as hours from UTC. Ambiguous names (CST, IST) are left out on purpose.
TZ_HOURS = {"UTC": 0, "GMT": 0, "PST": -8, "PDT": -7, "MST": -7, "MDT": -6, "EST": -5, "EDT": -4,
            "AKST": -9, "AKDT": -8, "HST": -10, "BST": 1, "CET": 1, "CEST": 2, "JST": 9, "KST": 9,
            "SGT": 8, "HKT": 8, "AEST": 10, "AEDT": 11}


def to_utc(local, zone):
    m = re.fullmatch(r"(?:GMT|UTC)([+-])(\d{1,2})(?::?(\d{2}))?", zone)
    if m:
        hours = int(m.group(2)) + int(m.group(3) or 0) / 60
        offset = timedelta(hours=hours if m.group(1) == "+" else -hours)
    elif zone in TZ_HOURS:
        offset = timedelta(hours=TZ_HOURS[zone])
    else:
        warn(f"Gemini Apps time zone {zone or '(none)'} is unknown and was read as UTC; add it to TZ_HOURS")
        offset = timedelta(0)
    return local.replace(tzinfo=timezone(offset))


def ts_match(body):
    m = TS_ZH.search(body)
    if m:
        y, mo, d, ap, h, mi, s, zone = m.groups()
        h = int(h) % 12
        # 深夜 also covers just after midnight, and 12 after 晚上 or 深夜 is midnight itself
        if ap in ZH_PM and not (ap == "深夜" and h < 6) and not (ap == "晚上" and h == 0):
            h += 12
        return m, to_utc(datetime(int(y), int(mo), int(d), h, int(mi), int(s)), zone)
    m = TS_EN.search(body)
    if m:
        mon, d, y, h, mi, s, ap, zone = m.groups()
        h = int(h) % 12 + (12 if ap == "PM" else 0)
        return m, to_utc(datetime(int(y), MONTHS[mon], int(d), h, int(mi), int(s)), zone)
    return None, None


def html_text(fragment):
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"</(p|li|h\d|pre|div|tr)>", "\n", fragment)
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


# "Branched" is a prompt the user asked again on a new branch of a chat: also the user's words
PROMPTED = re.compile(r"^(Prompted|Branched|已提示|提示)[:：]?\s*")
CANVAS = re.compile(r"^Created Gemini Canvas titled\s*")


def read_gemini_apps(text):
    """Each activity record is one of: a prompt or a branched re-ask (with Gemini's answer after the timestamp),
    a Canvas Gemini wrote (its body is AI text, so it becomes an assistant turn), or a
    bookkeeping record ("Used Gemini Apps", feedback), which is dropped and counted.
    Returns one card per record, (time, "prompt", prompt, answer) or (time, "canvas", text, ""),
    so an answer never leaves its prompt; gemini_sessions() groups them once every file is read."""
    recs, unparsed, other = [], 0, {}
    for cell in text.split('<div class="outer-cell')[1:]:
        if "content-cell" not in cell:
            continue
        body = cell.split("content-cell", 1)[1].split(">", 1)[1]
        m, when = ts_match(body)
        if not m:
            unparsed += 1
            continue
        head, resp = body[: m.start()], body[m.end():].split('<div class="content-cell')[0]
        head_text = html_text(head)
        if PROMPTED.match(head_text):
            prompt = PROMPTED.sub("", head_text)
            files = re.findall(r'<a href="([^"]+)"', head)
            if files:
                prompt += "\n\n[files: " + ", ".join(os.path.basename(f) for f in files) + "]"
            recs.append((when, "prompt", prompt or "(no text)", html_text(resp)))
        elif CANVAS.match(head_text):
            recs.append((when, "canvas", "[Gemini Canvas] " + CANVAS.sub("", head_text), ""))
        else:
            kind = head_text.split("\n")[0][:40]
            other[kind] = other.get(kind, 0) + 1
    if unparsed:
        warn(f"{unparsed} Gemini Apps records had no recognised timestamp; add the locale to TS_*")
    if other:
        print(f"Gemini Apps records dropped as bookkeeping: {other}", file=sys.stderr)
    return recs


def gemini_sessions(files, gap):
    """Prompts less than `gap` minutes apart form one session. `files` holds one card list per
    activity page. A card repeated across overlapping Takeouts counts once, keyed by its time, kind
    and prompt (or Canvas title); the most recent Takeout's non-empty answer wins, so an answer
    regenerated in between appears once. A later copy never blanks a real answer: when it has the
    same records, each empty answer keeps the earlier one, and when its repeats changed and it lost
    every answer, the earlier answers are kept by position.
    "Most recent" means the page whose newest record is latest, then the one with more records
    (a later Takeout holds everything an earlier one did)."""
    groups = {}  # (time, kind, text): the cards of that record, more than one if it was sent twice in a second
    # Oldest Takeout first; the cards themselves break a full tie, so file order never matters
    for cards in sorted(files, key=lambda cs: (max(c[0] for c in cs), len(cs), cs)):
        page = {}
        for card in reversed(cards):  # My Activity lists newest first; same-second records keep their real order
            page.setdefault(card[:3], []).append(card)
        for key, group in page.items():
            earlier = groups.get(key)
            if earlier is None:
                groups[key] = group
            elif len(earlier) != len(group):
                # A repeat added or deleted since: the later page decides, but if it lost every answer,
                # take the earlier answers by position rather than leave bare prompts
                if not any(c[3] for c in group):
                    group = [(*c[:3], earlier[i][3]) if i < len(earlier) else c for i, c in enumerate(group)]
                groups[key] = group
            else:
                # Same record, same count: take each answer from the later page (a regenerated answer),
                # except where it is empty, since an empty answer never replaces a real one
                groups[key] = [new if new[3] or not old[3] else old for old, new in zip(earlier, group)]
    merged = {(*key, n): card for key, group in groups.items() for n, card in enumerate(group)}
    recs = []
    for when, kind, text, answer in sorted(merged.values(), key=lambda c: c[0]):
        recs.append((when, "user" if kind == "prompt" else "assistant", text))
        if answer:
            recs.append((when, "assistant", answer))
    sessions, cur, last = [], [], None
    for r in recs:
        if last and r[0] - last > timedelta(minutes=gap):
            sessions.append(cur)
            cur = []
        cur.append(r)
        last = r[0]
    if cur:
        sessions.append(cur)
    # The id is the session's first record to the second; with --gap of at least a minute, sessions start
    # more than a minute apart, so two never share one
    return [conv("gemini-apps", "session-" + iso(s[0][0])[:19], "", [msg(role, t, when) for when, role, t in s])
            for s in sessions]


# ---------- discovery ----------

# The Gemini Apps folder inside My Activity, by account language (Takeout localises it).
# Add the folder name for a new language here, lowercase.
GEMINI_FOLDERS = ("gemini apps",)
UPLOAD_SUFFIX = re.compile(r"-[0-9a-f]{16}\.[^./]+$")


def in_gemini_folder(low):
    return any(f"/{name}/" in "/" + low for name in GEMINI_FOLDERS)


def is_upload(path):
    """A file the user uploaded to Gemini. Takeout names every upload with a '-<16 hex>' suffix,
    whatever the folder's language, and no chat export uses one, so the suffix marks an upload
    wherever the file sits, even in a folder unpacked without its Takeout parent.
    In a known Gemini Apps folder, anything but an .html activity page is an upload too."""
    p = path.replace("\\", "/").lower()
    base = p.rsplit("/", 1)[-1]
    if UPLOAD_SUFFIX.search(base):
        return True
    return in_gemini_folder(p) and not base.endswith(".html")


SKIPPED_UPLOADS = {}  # input path: [count, first name, first name that is not an image]
IMAGE = re.compile(r"\.(png|jpe?g|gif|webp|heic|bmp|tiff?)$", re.I)


def skip_upload(top, name):
    base = os.path.basename(name)
    entry = SKIPPED_UPLOADS.setdefault(top, [0, base, None])
    entry[0] += 1
    if entry[2] is None and not IMAGE.search(base):
        entry[2] = base


def read_file(p, n=-1):
    with open(p, "rb") as f:
        return f.read(n)


def read_member(z, info, n=-1):
    with z.open(info) as f:
        return f.read(n)


TAR_EXT = (".tar", ".tgz", ".tar.gz", ".tbz2", ".tar.bz2", ".txz", ".tar.xz")
OTHER_ARCHIVES = (".7z", ".rar")  # bare .gz/.xz files are not exports, so they are not flagged
try:
    import lzma
    READ_ERRORS = (zipfile.BadZipFile, tarfile.TarError, zlib.error, lzma.LZMAError, EOFError, OSError, RuntimeError)
except ImportError:
    READ_ERRORS = (zipfile.BadZipFile, tarfile.TarError, zlib.error, EOFError, OSError, RuntimeError)
JUNK = re.compile(r"(^|/)(__macosx/|\._[^/]*$|\.ds_store$|thumbs\.db$|desktop\.ini$)")
MAX_DEPTH = 3  # archives inside archives, at most this deep
SKIPPED_JUNK = {}  # input path: count of OS leftovers skipped
NESTED = {"dir": None, "n": 0}  # where nested archives are copied while they are read
NESTED_MAX = 8 << 30  # a nested archive larger than this is not copied out
PROBLEM_PATHS = set()  # archives already warned about, so the no-export check does not repeat them
FAILED_MEMBERS = set()  # archive members whose bytes could not be read


class ReadError(Exception):
    """Reading a file's bytes failed (a broken download, an encrypted or truncated archive).
    Only reads raise it, so a bug in a reader is never mistaken for a bad file."""


def guarded(read):
    def r(n=-1):
        try:
            return read(n)
        except READ_ERRORS as e:
            raise ReadError(e) from e
    return r


def archive_kind(low):
    if low.endswith(".zip"):
        return "zip"
    if low.endswith(TAR_EXT):
        return "tar"
    if low.endswith(OTHER_ARCHIVES):
        return "other"
    return None


def is_junk(name):
    return JUNK.search(name.replace("\\", "/").lower()) is not None


def skip_junk(top):
    SKIPPED_JUNK[top] = SKIPPED_JUNK.get(top, 0) + 1


class TarReader:
    """Reads one tar member forward only, keeping what it has read: a compressed tar can seek
    backwards only by decompressing again from the start of the archive."""

    def __init__(self, t, m):
        self.t, self.m, self.f, self.got = t, m, None, b""

    def __call__(self, n=-1):
        if self.f is None:
            self.f = self.t.extractfile(self.m)
        if n < 0:
            self.got += self.f.read()
            return self.got
        if len(self.got) < n:
            self.got += self.f.read(n - len(self.got))
        return self.got[:n]


def files_under(path, top=None, depth=0):
    """Yield (label, name, reader) for every file in a folder, any depth, or in an archive found
    there (.zip, .tar/.tgz), opening archives inside archives up to MAX_DEPTH. reader(n) returns
    the first n bytes, reader() all of them. Uploads are never yielded; they are counted in
    SKIPPED_UPLOADS, so a wrong skip shows. OS leftovers are counted in SKIPPED_JUNK."""
    top = top or path
    if os.path.isdir(path):
        for root, dirs, names in os.walk(path):
            dirs.sort()
            for n in sorted(names):
                full = os.path.join(root, n)
                if is_junk(full):
                    skip_junk(top)
                elif is_upload(full):
                    skip_upload(top, full)
                else:
                    yield from files_under(full, top, depth)
        return
    kind = archive_kind(path.lower())
    if kind is None:
        yield path, path, guarded(lambda n=-1, p=path: read_file(p, n))
    else:
        yield from archive_members(path, path, kind, top, depth)


def problem(label, text):
    PROBLEM_PATHS.add(label.split("!", 1)[0])  # the file on disk the problem is in
    warn(text)


def archive_members(label, path, kind, top, depth):
    if kind == "other":
        problem(label, f"{label}: this kind of archive cannot be opened; extract it into a new folder and index that")
        return
    if depth >= MAX_DEPTH:
        problem(label, f"{label}: archives nested more than {MAX_DEPTH} deep are not opened; extract it and index the result")
        return
    done, last = [0], [None]  # members handled before an error, and the last one reached
    try:
        if kind == "zip":
            with zipfile.ZipFile(path) as z:
                for info in z.infolist():
                    if not info.is_dir():
                        last[0] = f"{label}!{info.filename}"
                        yield from member(label, info.filename, guarded(lambda n=-1, i=info: read_member(z, i, n)),
                                          (lambda i=info: z.open(i)), info.file_size, top, depth)
                        done[0] += 1
        else:
            with tarfile.open(path) as t:
                for m in t:
                    if m.isfile():
                        last[0] = f"{label}!{m.name}"
                        yield from member(label, m.name, guarded(TarReader(t, m)), (lambda m=m: t.extractfile(m)),
                                          m.size, top, depth)
                        done[0] += 1
    except READ_ERRORS as e:
        if last[0] in FAILED_MEMBERS:
            return  # the member being read when the archive broke was already reported: the same damage
        if done[0]:
            problem(label, f"{label}: read {done[0]} file(s), then the rest could not be read ({e}); "
                           "it may be truncated, so download it again")
        else:
            problem(label, f"skipped {label}: not a readable archive ({e})")


class CopyError(Exception):
    pass


def copy_out(src, path):
    """Copy a nested archive out. A failure to read src is the archive's (ReadError);
    a failure to write is ours (CopyError)."""
    try:
        dst = open(path, "wb")
    except OSError as e:
        raise CopyError(e)
    with dst:
        while True:
            try:
                chunk = src.read(1 << 20)
            except READ_ERRORS as e:
                raise ReadError(e) from e
            if not chunk:
                return
            try:
                dst.write(chunk)
            except OSError as e:
                raise CopyError(e)


def member(label, name, read, stream, size, top, depth):
    if is_junk(name):
        skip_junk(top)
        return
    if is_upload(name):
        skip_upload(top, name)
        return
    full = f"{label}!{name}"
    kind = archive_kind(name.lower())
    if kind is None:
        yield full, name, read
        return
    if kind == "other":
        yield from archive_members(full, None, kind, top, depth)
        return
    free = shutil.disk_usage(NESTED["dir"]).free
    if size > NESTED_MAX or size * 1.1 > free:
        problem(full, f"{full}: this nested archive ({size >> 20} MB) is too large to copy into the work dir "
                      f"({free >> 20} MB free); extract it by hand into a new folder and index that")
        return
    NESTED["n"] += 1
    copy = os.path.join(NESTED["dir"], f"{NESTED['n']}.{kind}")
    try:
        with stream() as src:
            copy_out(src, copy)
    except (CopyError, ReadError) as e:
        if isinstance(e, CopyError):
            problem(full, f"{full}: could not copy it into the work dir to open it ({e}); free some space, or extract it by hand")
        else:
            problem(full, f"skipped {full}: this nested archive could not be read ({e}); download the export again")
        if os.path.exists(copy):
            os.remove(copy)
        return
    try:
        yield from archive_members(full, copy, kind, top, depth + 1)
    finally:
        os.remove(copy)


# Files in a known export that are not conversations: never read, never warned about
COMPANIONS = {"shared_conversations.json", "conversation_asset_file_names.json", "sectioned_conversations.json"}
EXPORT_NAME = re.compile(r"conversation|chat|activity|perplexity|capture")


def candidate(low):
    """Worth opening: named like an export. Everything else is skipped unread, so a large
    unrelated JSON (a full Takeout, say) costs nothing."""
    base = low.rsplit("/", 1)[-1]
    if base in COMPANIONS:
        return False
    if low.endswith(".html"):
        return any(f"/{d}/" in "/" + low for d in ("takeout", "my activity", "我的活動")) or in_gemini_folder(low)
    if "conversation history/" in low:
        return low.endswith((".txt", ".json"))
    return low.endswith(".json") and EXPORT_NAME.search(base) is not None


KNOWN_SHAPE = re.compile(rb'"(mapping|chat_messages|conversation_turns)"\s*:')


def renamed_export(low, read):
    """A JSON export under another name: its first bytes show a known shape
    (ChatGPT, Claude.ai, Gemini in Workspace, or a Perplexity capture's slug and entries)."""
    base = low.rsplit("/", 1)[-1]
    if not low.endswith(".json") or base in COMPANIONS:
        return False
    head = read(1 << 16)
    return KNOWN_SHAPE.search(head) is not None or (b'"slug"' in head and b'"entries"' in head)


def detect(name, read):
    """(conversations, Gemini Apps records) from one file."""
    norm = name.replace("\\", "/")
    low = norm.lower()
    is_html = low.endswith(".html")
    if not is_html and not candidate(low) and not renamed_export(low, read):
        return [], []
    if is_html:
        if in_gemini_folder(low):
            text = read().decode("utf-8", "replace")
            if 'class="outer-cell' not in text:
                warn(f"{norm} is in a Gemini Apps folder but has no activity records (no outer-cell); "
                     "the page format may have changed, see the Format notes in import-chats.md")
                return [], []
            return [], read_gemini_apps(text)
        if not candidate(low) and low.rsplit("/", 1)[-1] == "chat.html":
            return [], []  # ChatGPT's own rendering of its export, never an activity page
        head = read(1 << 18 if not candidate(low) else 1 << 20)
        if b'class="outer-cell' not in head:
            return [], []  # not a My Activity page
        records = head.split(b'class="outer-cell')[1:]
        # The brand is not translated, so a Gemini page names it in (nearly) every record;
        # another product's page mentions it at most in the odd record (a search for it, say)
        if sum(b"Gemini" in r for r in records) * 2 < len(records):
            print(f"{norm}: My Activity page for another product, skipped", file=sys.stderr)
            return [], []
        if not candidate(low):
            # Outside any Takeout folder (zipped or moved on its own): only its content can say what it is
            print(f"{norm}: read as the Gemini Apps activity page by its content", file=sys.stderr)
            return [], read_gemini_apps(read().decode("utf-8", "replace"))
        warn(f"{norm} is a My Activity page in a folder not known as Gemini Apps. If it is the Gemini Apps page "
             "in another language, add its folder name to GEMINI_FOLDERS; it was skipped")
        return [], []
    got = read_known(norm, read)
    if got is None:
        warn(f"{norm} looks like an export but matches no known format; check the Format notes in import-chats.md")
    return got or [], []


def read_known(norm, read):
    """Conversations from one JSON file; [] for a recognised file with none; None when unrecognised."""
    try:
        data = json.loads(read().decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as e:
        warn(f"skipped {norm}: not readable JSON ({e})")
        return []
    if isinstance(data, dict) and "conversation_turns" in data:
        return read_gemini_workspace(data, norm)
    if data in ([], {}):
        return []
    if not isinstance(data, list) or not isinstance(data[0], dict):
        return None
    first = data[0]
    if "mapping" in first:
        return read_chatgpt(data)
    if "chat_messages" in first:
        return read_claude(data)
    if "entries" in first and "slug" in first:
        return read_perplexity(data)
    return None


def rank(c, with_updated):
    last = max((m["time"] for m in c["messages"] if m["time"]), default="")
    return ((c["updated"],) if with_updated else ()) + (last, len(c["messages"]))


def content(c):
    return json.dumps(c, sort_keys=True, ensure_ascii=False)


class Best:
    """The best copy so far under one order: rank() first, then the copy's content. The current
    best's rank is kept, and content is serialised only when two ranks tie, each copy at most once."""

    def __init__(self, with_updated):
        self.with_updated, self.copy, self.key, self.text = with_updated, None, None, None

    def offer(self, c):
        key, text = rank(c, self.with_updated), None
        if self.copy is not None:
            if key < self.key:
                return
            if key == self.key:
                if self.text is None:
                    self.text = content(self.copy)
                text = content(c)
                if text <= self.text:
                    return
        self.copy, self.key, self.text = c, key, text


class Pick:
    """The copy to keep when several exports hold one conversation: the later platform update time
    (a rename or an edit moves it), then the later last message, then more messages. Recency comes
    first because an edited prompt can leave the newer branch shorter. The update time counts only
    when every copy has one, so an export without the field never loses for that alone. Both orders
    are total, ending in the copies' content, so the order the exports are given never decides.
    Only the best copy under each order is kept, never every copy."""

    def __init__(self):
        self.all_updated, self.by_updated, self.by_recency = True, Best(True), Best(False)

    def add(self, c):
        self.all_updated = self.all_updated and bool(c["updated"])
        self.by_updated.offer(c)
        self.by_recency.offer(c)

    def best(self):
        return (self.by_updated if self.all_updated else self.by_recency).copy


def group_of(p, label):
    """The first folder or archive under an input path that a file came from."""
    path = label.split("!", 1)[0]
    rel = os.path.relpath(path, p) if os.path.isdir(p) else os.path.basename(p)
    first = rel.replace("\\", "/").split("/", 1)[0]
    return os.path.join(p, first) if os.path.isdir(p) else p


def groups(paths):
    """The folders and archives to report on: each input archive, and each folder or archive
    directly inside an input folder."""
    for p in paths:
        if os.path.isdir(p):
            for n in sorted(os.listdir(p)):
                full = os.path.join(p, n)
                if not is_junk(full) and (os.path.isdir(full) or archive_kind(n.lower())):
                    yield full
        elif os.path.exists(p) and archive_kind(p.lower()):
            yield p


def cmd_index(a):
    picks, gemini_files = {}, []
    os.makedirs(a.out, exist_ok=True)
    NESTED["dir"] = os.path.join(a.out, "nested")
    os.makedirs(NESTED["dir"], exist_ok=True)
    try:
        found = scan(a, picks, gemini_files)
    finally:
        shutil.rmtree(NESTED["dir"], ignore_errors=True)
    for g in groups(a.paths):
        seen, hits = found.get(g, (0, 0))
        if not hits and not any(x == g or x.startswith(g + os.sep) for x in PROBLEM_PATHS):
            warn(f"{g}: no export found ({seen} file(s) read; uploads and OS leftovers are not read). "
                 "If one is an export, see import-chats.md step 2")
    write_index(a, picks, gemini_files)


def scan(a, picks, gemini_files):
    found = {}  # group: [files seen, files with an export]
    for p in a.paths:
        if not os.path.exists(p):
            warn(f"{p}: no such file or folder")
            continue
        for label, name, read in files_under(p):
            try:
                got, recs = detect(name, read)
            except ReadError as e:
                FAILED_MEMBERS.add(label)
                problem(label, f"skipped {label}: could not be read ({e}); download the export again")
                got, recs = [], []
            g = found.setdefault(group_of(p, label), [0, 0])
            g[0] += 1
            g[1] += bool(got or recs)
            if got:
                print(f"{label}: {len(got)} {got[0]['platform']}", file=sys.stderr)
            if recs:
                print(f"{label}: {len(recs)} gemini-apps records", file=sys.stderr)
                gemini_files.append(recs)
            for c in got:
                k = (c["platform"], c["id"])
                picks.setdefault(k, Pick()).add(c)
    return found


def write_index(a, picks, gemini_files):
    best = {k: p.best() for k, p in picks.items()}
    if gemini_files:
        for c in gemini_sessions(gemini_files, a.gap):
            best[(c["platform"], c["id"])] = c
    convs, empty = [], {}
    for c in best.values():
        if c["messages"]:
            convs.append(c)
        else:
            empty[c["platform"]] = empty.get(c["platform"], 0) + 1
    convs.sort(key=lambda c: (c["start"] or "9999", c["platform"]))
    with open(os.path.join(a.out, "conversations.json"), "w", encoding="utf-8") as f:
        json.dump(convs, f, ensure_ascii=False)
    with open(os.path.join(a.out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"gap_minutes": a.gap}, f)
    with open(os.path.join(a.out, "index.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("n\tplatform\tstart_utc\tuser_turns\tspace\ttitle\tfirst_prompt\n")
        for n, c in enumerate(convs):
            users = [m for m in c["messages"] if m["role"] == "user"]
            first = re.sub(r"\s+", " ", users[0]["text"] if users else "")[:160]
            title = re.sub(r"\s+", " ", c["title"])  # outside the f-string: before 3.12, a backslash there is a syntax error
            f.write(f"{n}\t{c['platform']}\t{c['start'][:16]}\t{len(users)}\t{c['space']}\t{title}\t{first}\n")
    by = {}
    for c in convs:
        by[c["platform"]] = by.get(c["platform"], 0) + 1
    for top, (count, first, other) in SKIPPED_UPLOADS.items():
        also = f"; not an image: {other}" if other and other != first else ""
        print(f"{top}: skipped {count} file(s) as Takeout uploads (e.g. {first}{also}); if one is an export, rename it",
              file=sys.stderr)
    for top, count in SKIPPED_JUNK.items():
        print(f"{top}: skipped {count} operating-system leftover(s) (__MACOSX, ._*, .DS_Store)", file=sys.stderr)
    for shape, count in BAD_TIMES.items():
        print(f"{count} timestamp(s) of the form {shape!r} were left empty", file=sys.stderr)
    print(f"{len(convs)} conversations {by} -> {a.out}" + (f"; skipped as empty: {empty}" if empty else ""))


def load(work):
    with open(os.path.join(work, "conversations.json"), encoding="utf-8") as f:
        convs = json.load(f)
    try:
        with open(os.path.join(work, "meta.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except FileNotFoundError:
        meta = {}
    return convs, meta


def cmd_show(a):
    convs, _ = load(a.work)
    bad = [n for n in a.n if not 0 <= n < len(convs)]
    if bad:
        sys.exit(f"show {bad}: index.tsv has conversations 0-{len(convs) - 1}")
    for n in a.n:
        c = convs[n]
        print(f"===== {n} · {c['platform']} · {c['start'][:16]} UTC · {c['space']} · {c['title']}")
        for m in c["messages"]:
            print(f"--- {m['role']} ({m['time'][:16]})\n{m['text']}\n")
        for m in c["alt"]:
            print(f"--- user, other branch ({m['time'][:16]})\n{m['text']}\n")


def parse_pick(s):
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)|(\d+)", part)
        if not m:
            sys.exit(f"--pick: cannot read {part!r}; use numbers and ranges like 3,7,10-12")
        if m.group(3):
            out.append(int(m.group(3)))
        else:
            out += range(int(m.group(1)), int(m.group(2)) + 1)
    return sorted(set(out))


def fence(text):
    ticks = "````"
    while ticks in text:
        ticks += "`"
    return f"{ticks}text\n{text.rstrip()}\n{ticks}\n"


def one_line(text):
    return re.sub(r"\s+", " ", text).strip()


def cmd_extract(a):
    convs, meta = load(a.work)
    picks = parse_pick(a.pick)
    bad = [n for n in picks if not 0 <= n < len(convs)]
    if bad:
        sys.exit(f"--pick {bad}: index.tsv has conversations 0-{len(convs) - 1}")
    by = {}
    for n in picks:
        by.setdefault(convs[n]["platform"], []).append(convs[n])
    bases = {plat: os.path.join(a.out, PLATFORMS[plat][0], f"{a.date}-{a.label}" + ("-apps" if plat == "gemini-apps" else ""))
             for plat in by}
    taken = [f"{b}-{s}.md" for b in bases.values() for s in ("threads", "prompts") if os.path.exists(f"{b}-{s}.md")]
    if taken:
        sys.exit("refusing to overwrite " + ", ".join(taken) + ": sources are never edited; pass a new --label")
    for plat, cs in by.items():
        folder, key, title = PLATFORMS[plat]
        # Each extract numbers its threads from T1, so the key names the extract, not just the platform
        key = f"{key}-{a.date}" + ("" if a.label == "chats" else f"-{a.label}")
        base = bases[plat]
        intro = (f"Picked by the user from a {title} export screened on {a.date} (see `sources/import-log.md`). "
                 "Verbatim; times are UTC. Only **User** turns are the user's own words; **Assistant** turns are "
                 f"AI output and count as leads only. Cite as `{key} T<n>.U<k>` (conversation n, user turn k).")
        if plat == "chatgpt":
            intro += " `T<n>.A<k>`: a user turn on another branch (an edited prompt, or a follow-up on a branch later abandoned)."
        if plat == "gemini-apps":
            gap = meta.get("gap_minutes", "an unknown number of")
            intro += (" The activity log has no conversation ids, so each T is a session: prompts less than "
                      f"{gap} minutes apart. A Canvas Gemini wrote appears as an Assistant turn.")
        full = [f"# {title}: picked conversations (imported {a.date})", "", intro, "",
                f"The user's turns alone are in [{os.path.basename(base)}-prompts.md]({os.path.basename(base)}-prompts.md).", ""]
        prompts = [f"# {title}: the user's prompts (imported {a.date})", "", intro, "",
                   f"Full conversations: [{os.path.basename(base)}-threads.md]({os.path.basename(base)}-threads.md).", ""]
        for t, c in enumerate(cs, 1):
            head = [f"## T{t}: {one_line(c['title']) or '(untitled)'}", "", f"- Platform id: `{c['id']}`",
                    f"- Started: {c['start'][:16]} UTC"] + ([f"- Space: {one_line(c['space'])}"] if c["space"] else []) + [""]
            full += head
            prompts += head
            u = 0
            for m in c["messages"]:
                if m["role"] == "user":
                    u += 1
                    h = f"### T{t}.U{u} — User ({m['time'][:16]})"
                    full += [h, "", fence(m["text"])]
                    prompts += [h, "", fence(m["text"])]
                else:
                    full += ["#### Assistant", "", fence(m["text"])]
            if c["alt"]:
                h = f"### T{t}: user turns on other branches (edited prompts, abandoned follow-ups)"
                full += [h, ""]
                prompts += [h, ""]
                for k, m in enumerate(c["alt"], 1):
                    block = [f"#### T{t}.A{k} — User ({m['time'][:16]})", "", fence(m["text"])]
                    full += block
                    prompts += block
        os.makedirs(os.path.dirname(base), exist_ok=True)
        for suffix, lines in (("threads", full), ("prompts", prompts)):
            with open(f"{base}-{suffix}.md", "x", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(lines))
        print(f"{base}-threads.md / -prompts.md: {len(cs)} conversations; key `{key} T<n>.U<k>`")


# Claude Code session transcripts: excerpts of the perishable sources an entry cites

AGENT = "claude-code"  # the sources folder and the key prefix
# User-role text that is not the user's own words: tool output, app and session events, summaries
NOT_TYPED = re.compile(r"\s*(?:<(?:task-notification|side-sessions-event|ci-monitor-event|cross-session-message"
                       r"|local-command-(?:stdout|stderr|caveat)|bash-(?:stdout|stderr))\b"
                       r"|\[Request interrupted|This session is being continued from a previous conversation)")
# kind, pattern; a match is replaced by [redacted: kind], after the text of a <keep> group. Short values and
# quoted values with spaces get through: the agent reads every kept turn before committing (excerpts.md)
SECRETS = [
    ("private key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)"),
    ("GitHub token", r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    ("API key", r"\b(?:sk|rk)[-_](?:live_|test_|ant-|proj-)?[A-Za-z0-9_-]{20,}"),
    ("GitLab token", r"\bglpat-[A-Za-z0-9_-]{20,}"),
    ("npm token", r"\bnpm_[A-Za-z0-9]{30,}"),
    ("Hugging Face token", r"\bhf_[A-Za-z0-9]{30,}"),
    ("AWS key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("Slack token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    ("Google API key", r"\bAIza[0-9A-Za-z_-]{35}"),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    ("bearer token", r"(?P<keep>(?i:\b(?:bearer|basic))\s+)[A-Za-z0-9._~+/=-]{16,}"),
    ("URL password", r"(?P<keep>://[^/\s:@]+:)[^/\s@]+(?=@)"),
    ("secret value", r"(?P<keep>(?i:\b[A-Za-z0-9_]*(?:password|passwd|secret|token|api[_-]?key|access[_-]?key))"
                     r"['\"]?\s*[:=]\s*)['\"]?[^\s'\",;]{6,}['\"]?"),
]
SECRETS = [(kind, re.compile(p, re.S)) for kind, p in SECRETS]


def redact(text, counts):
    for kind, rx in SECRETS:
        def sub(m):
            counts[kind] = counts.get(kind, 0) + 1
            return (m.group("keep") if "keep" in rx.groupindex else "") + f"[redacted: {kind}]"
        text = rx.sub(sub, text)
    return text


def projects_dir(given):
    if given:
        return given
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "projects")


def fold(name):
    return name.lower() if os.name == "nt" else name  # a Windows drive letter's case varies


def project_folder(projects, cwd):
    """Claude Code's folder for a working directory: every character outside [A-Za-z0-9] becomes '-';
    a long path is cut and given a suffix, so fall back to the folders that start with its first 200."""
    slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(cwd))
    names = os.listdir(projects) if os.path.isdir(projects) else []
    exact = [n for n in names if fold(n) == fold(slug)]
    if exact:
        return os.path.join(projects, exact[0])
    near = sorted(n for n in names if len(slug) > 200 and fold(n).startswith(fold(slug[:200])))
    if near:
        return os.path.join(projects, near[0])
    sys.exit(f"no Claude Code transcripts for {cwd} under {projects}; pass the transcript's path")


def user_text(content):
    """The text of a user-role message the user typed, or None when it is not the user's words."""
    if isinstance(content, str):
        parts = [content]
    else:
        if all(b.get("type") == "tool_result" for b in content):
            return None
        parts = [b.get("text", "") if b.get("type") == "text" else "[image]" if b.get("type") == "image"
                 else "[file]" for b in content if b.get("type") != "tool_result"]
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", "\n\n".join(parts), flags=re.S).strip()
    if not text or NOT_TYPED.match(text):
        return None
    cmd = re.search(r"<command-name>(.*?)</command-name>", text, re.S)
    if cmd:  # a slash command: what the user typed, without the app's wrapper
        args = re.search(r"<command-args>(.*?)</command-args>", text, re.S)
        text = f"{cmd.group(1).strip()} {args.group(1).strip() if args else ''}".strip()
    return text


def read_transcript(path):
    """A Claude Code transcript as {session, start, turns}. U<k> is the session's k-th turn the user typed
    (origin `human`, or no origin in an older transcript; never another session's or the app's message,
    a tool result, a meta or summary message, or a subagent's), each line counted once by its uuid; A<k> is the text the assistant wrote
    after U<k> (A0 before the first), never its thinking or tool calls."""
    start, turns, u, seen = "", [], 0, set()
    with open(path, encoding="utf-8", errors="replace") as f:
        for n, line in enumerate(f, 1):
            try:
                o = json.loads(line)
            except ValueError:
                warn(f"{path}:{n}: not a JSON line, skipped")
                continue
            if not isinstance(o, dict) or o.get("type") not in ("user", "assistant") or o.get("isSidechain"):
                continue
            if o.get("uuid"):  # a resumed or compacted session copies earlier lines again
                if o["uuid"] in seen:
                    continue
                seen.add(o["uuid"])
            t = iso(o.get("timestamp"))
            start = start or t
            m = o.get("message") or {}
            content = m.get("content") or ""
            if o["type"] == "user":
                if (o.get("isMeta") or o.get("isCompactSummary") or o.get("turnOrigin", "human") != "human"
                        or (o.get("origin") or {}).get("kind", "human") != "human"):
                    continue
                text = user_text(content)
                if text is not None:
                    u += 1
                    turns.append({"label": f"U{u}", "time": t, "text": text})
                continue
            if o.get("isApiErrorMessage"):
                continue
            texts = [content] if isinstance(content, str) else [b.get("text", "") for b in content if b.get("type") == "text"]
            text = "\n\n".join(x.strip() for x in texts if x.strip())
            if not text:
                continue
            if turns and turns[-1]["label"] == f"A{u}":
                turns[-1]["text"] += "\n\n" + text
            else:
                turns.append({"label": f"A{u}", "time": t, "text": text})
    if not turns:
        sys.exit(f"{path}: no turns found; is it a Claude Code session transcript?")
    # The file names the session: a forked session copies its parent's sessionId but numbers its own turns
    return {"session": os.path.splitext(os.path.basename(path))[0], "start": start, "turns": turns}


def paragraphs(text):
    """Blank-line separated paragraphs; a fenced code block stays one paragraph."""
    out, cur, fenced = [], [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if not line.strip() and not fenced:
            if cur:
                out.append("\n".join(cur))
            cur = []
        else:
            cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return out


def parse_keep(s, tr):
    """'U3,A3:2-4,U7' -> {label: None (whole turn) or a set of paragraph numbers}."""
    by = {t["label"]: t for t in tr["turns"]}
    keep = {}
    for part in filter(None, (p.strip() for p in s.split(","))):
        m = re.fullmatch(r"([UA]\d+)(?::(\d+)(?:-(\d+))?)?", part)
        if not m:
            sys.exit(f"--keep: cannot read {part!r}; use turns like U3,A3,A5:2-4 (paragraphs of an assistant turn)")
        label = m.group(1)
        if label not in by:
            sys.exit(f"--keep: {label} is not in this transcript; `turns` lists them")
        if m.group(2) is None:
            keep[label] = None
            continue
        if label[0] == "U":
            sys.exit(f"--keep: {part}: a user turn is kept whole, verbatim")
        lo, hi, count = int(m.group(2)), int(m.group(3) or m.group(2)), len(paragraphs(by[label]["text"]))
        if not 1 <= lo <= hi <= count:
            sys.exit(f"--keep: {part}: {label} has paragraphs 1-{count}")
        if label not in keep or keep[label] is not None:
            keep[label] = (keep.get(label) or set()) | set(range(lo, hi + 1))
    if not keep:
        sys.exit("--keep: no turns given")
    return keep


def spans(nums):
    nums, out = sorted(nums), []
    for n in nums:
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return ", ".join(f"{a}-{b}" if a != b else str(a) for a, b in out)


def turn_block(t, paras, counts):
    """One turn as the excerpt holds it; the paragraphs left out of an assistant turn are marked […]."""
    if t["label"][0] == "U":
        return f"## {t['label']} — User ({t['time'][:16].replace('T', ' ')})\n\n" + fence(redact(t["text"], counts))
    ps = paragraphs(t["text"])
    if paras is None or len(paras) == len(ps):
        return f"## {t['label']} — Assistant\n\n" + fence(redact(t["text"], counts))
    parts, last = [], 0
    for n in sorted(paras):
        if n != last + 1:
            parts.append("[…]")
        parts.append(ps[n - 1])
        last = n
    if last < len(ps):
        parts.append("[…]")
    return (f"## {t['label']} — Assistant (paragraphs {spans(paras)} of {len(ps)})\n\n"
            + fence(redact("\n\n".join(parts), counts)))


def split_excerpt(text):
    """An excerpt file as (head, {label: block}); a heading inside a turn's fenced text is not a turn."""
    head, blocks, label, ticks = [], {}, None, None
    for line in text.split("\n"):
        m = re.match(r"## ([UA]\d+) — ", line)
        if ticks is None and m:
            label = m.group(1)
            blocks[label] = []
        elif ticks is None and re.fullmatch(r"`{4,}text", line):
            ticks = line[:-4]
        elif ticks is not None and line == ticks:
            ticks = None
        (blocks[label] if label else head).append(line)
    return "\n".join(head), {k: "\n".join(v).rstrip("\n") + "\n" for k, v in blocks.items()}


def order(label):
    return int(label[1:]), label[0] == "A"


def transcript_path(a):
    if a.transcript:
        return a.transcript
    folder = project_folder(projects_dir(a.projects), a.cwd or os.getcwd())
    found = sorted((os.path.getmtime(p), p) for p in (os.path.join(folder, n) for n in os.listdir(folder)) if p.endswith(".jsonl"))
    if not found:
        sys.exit(f"no transcripts in {folder}")
    print(f"transcript: {found[-1][1]} (the newest of {len(found)} in {folder}; pass another one's path to read it)")
    return found[-1][1]


def cmd_turns(a):
    path = transcript_path(a)
    tr = read_transcript(path)
    print(f"session {tr['session']}, started {tr['start'][:16]} UTC")
    if a.show:
        for label, paras in parse_keep(a.show, tr).items():
            t = next(t for t in tr["turns"] if t["label"] == label)
            ps = paragraphs(t["text"]) if label[0] == "A" else [t["text"]]
            print(f"===== {label} ({t['time'][:16]})")
            for n, p in enumerate(ps, 1):
                if paras is None or n in paras:
                    print((f"[p{n}] " if label[0] == "A" else "") + p + "\n")
        return
    for t in tr["turns"]:
        extra = f"{len(paragraphs(t['text']))} paragraphs" if t["label"][0] == "A" else t["time"][:16]
        print(f"{t['label']}\t{extra}\t{one_line(t['text'])[:200]}")


def excerpt_name(folder, slug, session, start):
    """The excerpt's file name: the session's first day (UTC) and the slug. When the session already has
    files, their date wins, so one session keeps one date even where an earlier rule or a hand-written
    file chose another; and a file with this slug is added to under its own name, never renamed."""
    names = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
    dates = []
    for n in names:
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-([a-z0-9-]+)\.md", n)
        if m:
            with open(os.path.join(folder, n), encoding="utf-8", errors="replace") as f:
                if f"- Session: `{session}`" in f.read():
                    if m.group(2) == slug:
                        return n[:-3]
                    dates.append(m.group(1))
    return f"{min(dates) if dates else start[:10]}-{slug}"


def cmd_excerpt(a):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", a.slug):
        sys.exit("--slug: lowercase letters, digits and single hyphens, like api-retry-design")
    tr = read_transcript(a.transcript)
    keep = parse_keep(a.keep, tr)
    name = excerpt_name(os.path.join(a.out, AGENT), a.slug, tr["session"], tr["start"])  # skills/career-log/excerpts.md
    date = name[:10]
    key = f"{AGENT}-{name}"
    path = os.path.join(a.out, AGENT, name + ".md")
    counts, blocks = {}, {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
        if f"- Session: `{tr['session']}`" not in old:
            sys.exit(f"{path} excerpts another session: pass a new --slug")
        head, blocks = split_excerpt(old)
    else:
        head = (f"# Claude Code session {date}: {redact(one_line(a.title or a.slug), counts)}\n\n"
                f"Excerpted from a Claude Code session transcript by `tools/chat_export.py excerpt`: the transcript is "
                "deleted after about 30 days, and this file keeps the turns entries cite. Turn numbers are the "
                "session's own, so a gap is a turn left out. **User** turns are the user's own words, verbatim; "
                "**Assistant** turns are AI output kept as context, leads only. Times are UTC. Secrets the tool "
                f"recognises are replaced by `[redacted: <kind>]`. Cite as `{key} U<k>` (the k-th turn the user "
                "typed) or `A<k>` (the assistant's reply to it).\n\n"
                f"- Session: `{tr['session']}`\n- Started: {tr['start'][:16].replace('T', ' ')} UTC\n"
                f"- Key date: {'session start (UTC)' if date == tr['start'][:10] else 'another excerpt of the session'}\n\n")
    by = {t["label"]: t for t in tr["turns"]}
    added = []
    for label, paras in keep.items():
        if label in blocks:  # an excerpt's turns are only added to: the file's copy stays, hand redactions included
            print(f"{label} is already in {path}; kept as it is", file=sys.stderr)
            continue
        blocks[label] = turn_block(by[label], paras, counts)
        added.append(label)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(head.rstrip("\n") + "\n\n" + "\n".join(blocks[k] for k in sorted(blocks, key=order)))
    if counts:
        print("redacted: " + ", ".join(f"{n} {k}" for k, n in counts.items()), file=sys.stderr)
    print(f"{path}: added {', '.join(added) or 'nothing (already there)'}; key `{key} U<k>`")


def search_roots(projects, globs):
    """The project folders `find` reads: all of them, or those whose name a --folder glob matches."""
    if not globs:
        return [projects]
    names = sorted(os.listdir(projects)) if os.path.isdir(projects) else []
    roots = [os.path.join(projects, n) for n in names
             if os.path.isdir(os.path.join(projects, n)) and any(fnmatch.fnmatchcase(fold(n), fold(g)) for g in globs)]
    if not roots:
        sys.exit(f"no project folder under {projects} matches {' or '.join(globs)}")
    return roots


# Whitespace in a transcript's raw bytes: as it is (UTF-8), or as JSON escapes it, lowercased
RAW_SPACE = (rb"(?:\s|\\[bfnrt]|\\u[0-9a-f]{4}|\xc2[\x85\xa0]|\xe1\x9a\x80|\xe2\x80[\x80-\x8a\xa8\xa9\xaf]"
             rb"|\xe2\x81\x9f|\xe3\x80\x80)+")


RAW_CHECK_MAX = 4  # phrases: each scans every file, and above this the scans cost more than the parsing they save


def raw_phrases(phrases):
    """For each phrase, (its words' forms, a pattern) that a transcript's raw bytes, ASCII letters
    lowercased, match when a user turn contains it: the words in order, each as it is or as JSON escapes it
    (a quote or backslash, or \\uXXXX when non-ASCII is escaped), with whitespace between them in any form.
    The whole phrase, not one word: a long transcript holds nearly every common word.
    None, so every file is parsed, above RAW_CHECK_MAX phrases, for a phrase the reader may have made (a
    slash command, an [image] or [file] mark), or when a word has a non-ASCII letter with a case (lowering
    bytes leaves its other case as it was). Still missed: a phrase across two content blocks or a removed
    reminder, a turn whose K or İ sign lowers to ASCII, and a writer that escapes '/' (Claude Code writes
    UTF-8, unescaped)."""
    if len(phrases) > RAW_CHECK_MAX or any(one_line(p).startswith("/") or re.search(r"\[(?:image|file)\]", p)
                                           for p in phrases):
        return None
    out = []
    for p in phrases:
        words = one_line(p).lower().split(" ")
        if any(ord(c) > 127 and c.lower() != c.upper() for c in one_line(p)):
            return None
        forms = [{f.encode() for f in (w, json.dumps(w, ensure_ascii=False)[1:-1], json.dumps(w)[1:-1])} for w in words]
        out.append((forms, re.compile(RAW_SPACE.join(b"(?:" + b"|".join(map(re.escape, f)) + b")" for f in forms))))
    return out


def may_hold(low, phrases):
    """Whether lowered raw bytes can hold a phrase; the quick word test runs before the pattern."""
    return any(all(any(f in low for f in forms) for forms in words) and rx.search(low) for words, rx in phrases)


def cmd_find(a):
    wants = [one_line(p).lower() for p in a.phrases]
    raws = raw_phrases(a.phrases)
    projects = projects_dir(a.projects)
    hits, seen = 0, set()
    for root, _, names in (w for r in search_roots(projects, a.folder) for w in os.walk(r)):
        for n in sorted(names):
            if not n.endswith(".jsonl") or os.sep + "subagents" in root:
                continue
            p = os.path.join(root, n)
            if raws is not None:  # parsing is the slow part: skip a file no phrase can be in
                with open(p, "rb") as f:
                    if not may_hold(f.read().lower(), raws):
                        continue
            try:
                tr = read_transcript(p)  # read again, as text: the file is cached by now
            except SystemExit:
                continue
            for t in tr["turns"]:
                if t["label"][0] != "U":
                    continue
                text = one_line(t["text"]).lower()
                for k, want in enumerate(wants, 1):
                    if want in text and (k, t["time"], t["text"]) not in seen:  # a resumed session copies turns
                        seen.add((k, t["time"], t["text"]))
                        hits += 1
                        print(f"{k}\t{p}\t{t['label']}\t{t['time'][:16]}\t{one_line(t['text'])[:120]}")
    if not hits:
        sys.exit(f"no user turn under {projects}{' in the folders --folder matches' if a.folder else ''} "
                 "contains any of the phrases")


def minutes(s):
    n = int(s)
    if n < 1:
        raise argparse.ArgumentTypeError("the session gap is at least 1 minute")
    return n


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("index")
    p.add_argument("paths", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--gap", type=minutes, default=45, help="Gemini Apps session gap in minutes (at least 1)")
    p.set_defaults(fn=cmd_index)
    p = sub.add_parser("show")
    p.add_argument("work")
    p.add_argument("n", nargs="+", type=int)
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("extract")
    p.add_argument("work")
    p.add_argument("--pick", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--label", default="chats")
    p.set_defaults(fn=cmd_extract)
    p = sub.add_parser("turns")
    p.add_argument("transcript", nargs="?")
    p.add_argument("--show")
    p.add_argument("--cwd")
    p.add_argument("--projects")
    p.set_defaults(fn=cmd_turns)
    p = sub.add_parser("excerpt")
    p.add_argument("transcript")
    p.add_argument("--keep", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--title")
    p.set_defaults(fn=cmd_excerpt)
    p = sub.add_parser("find")
    p.add_argument("phrases", nargs="+")
    p.add_argument("--projects")
    p.add_argument("--folder", action="append", help="only project folders whose name matches this glob; "
                   "repeatable; write --folder=<glob> when it starts with '-'")
    p.set_defaults(fn=cmd_find)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
