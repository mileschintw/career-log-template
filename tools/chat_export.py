#!/usr/bin/env python3
"""Screen and extract AI chat-history exports for the import-chats mode.

  chat_export.py index <export path>... --out <work dir> [--gap 45]
      Find every export under the paths, normalise them into <work dir>/conversations.json and write
      <work dir>/index.tsv for screening: n, platform, start, user turns, space, title, first prompt.
      It looks through folders at any depth and inside .zip and .tar/.tgz archives, archives inside
      archives too, up to {depth} deep (each nested archive is copied into <work dir>/nested while it
      is read, and deleted afterwards). It opens files named like an export, and any other JSON whose
      first bytes show a known shape, so a renamed export is still found; an activity page outside any
      Takeout folder is recognised by its content. It never opens Takeout uploads, zipped or not, in any
      language (Takeout names every upload with a '-<16 hex>' suffix), nor what operating systems leave
      in archives: {junk}. It prints how many of each it skipped.
      All times are converted to UTC.
      When the same conversation is in two exports, it keeps the copy the platform changed last (its own
      update time, when every copy has one), then the one with the later last message, then the one
      with more messages; overlapping Takeouts keep each Gemini Apps record once, and an empty answer
      never replaces a real one. Each warning ends with the kind of problem: [packing] (how the files
      were packed or downloaded), [disk] (the work dir's disk) or [parser] (part of an export was
      skipped: the parser needs a fix).
  chat_export.py show <work dir> <n>...
      Print conversations as plain text, for reading during screening.
  chat_export.py tally <work dir> [--groups] [--date YYYY-MM-DD]
      Read <work dir>/marks.tsv, the screening's marks: one row per conversation, its n, a tab, and
      either a group, G<k>, or one of the leave-out categories:
{categories}
      A group's row adds a tab and its status once the user has answered: picked, not picked, or
      dropped (the user said it is not theirs or does not count). A conversation with no row counts as
      "other, not career-relevant". Prints the three lines the import log records for what was not
      picked (`Dropped:` dated --date, default today); with --groups, each group's conversation
      numbers and date range instead.
  chat_export.py extract <work dir> --pick 3,7,10-12 --date YYYY-MM-DD --out <log>/sources [--label chats]
                         [--keys <log>/sources/keys.md]
      Write the picked conversations, verbatim, to sources/<folder>/<date>-<label>-threads.md
      and <date>-<label>-prompts.md (the user's turns only), one pair per platform, numbered T<n>.U<k>
      in date order; Gemini Apps sessions go to sources/gemini/<date>-<label>-apps-*.md. Each extract
      has its own key, printed: <platform>-<date>, plus -<label> for a label other than chats, since
      every extract numbers its threads from T1. Refuses to overwrite: pass a new --label for a second
      extract on the same day. --keys adds each extract's row to the table in that keys.md, unless its
      key is there already.
  chat_export.py cut <threads or prompts file> T3.U2,T5,...
      Remove those turns (T<n>.U<k>, a user turn with the answers after it; T<n>.A<k>, a user turn on
      another branch) or whole conversations (T<n>) from both files of an extract; every other number
      stays as it is.
  chat_export.py leaks <work dir> --pick 3,7,10-12 <import log>
      Search the import log's last section (from its last level-2 heading) for the title and the first
      {words} words of the first prompt of every conversation not picked, as fixed text, ignoring case
      and spacing. Prints each hit with its line; whether a hit describes an unpicked conversation is
      the reader's call.
  chat_export.py manifest <claude-manifest-*.json> [--memories]
      Print the download links of a Claude.ai link file as Markdown links: every part of the
      conversations, and of the memories with --memories. It writes nothing. A file of another shape
      prints `unknown shape:` and why.

Claude Code session transcripts (one session each, ~/.claude/projects/<folder>/<session id>.jsonl):
  chat_export.py turns [<transcript>] [--show U3,A3:2-4] [--cwd <dir>] [--projects <dir>]
      Number the session's turns: U<k>, the k-th turn the user typed, and A<k>, the assistant's text
      after it, with its paragraph count. --show prints those turns whole, with [p<n>] paragraph marks.
      With no transcript, reads the newest one for --cwd (default: the current directory).
  chat_export.py excerpt <transcript> --keep U3,A3:2-4 --slug <slug> --out <log>/sources [--title <t>]
      Write the kept turns to sources/claude-code/<date>-<slug>.md: user turns whole, assistant turns
      whole or only the paragraphs given, secrets redacted (a count goes to stderr). Run again with the
      same transcript and slug to add turns; a turn already there never changes. Prints the key and,
      for each kept user turn, its citation with the turn's day in this machine's time zone,
      `(user, YYYY-MM-DD)`, which can be a day off the key's date.
  chat_export.py quote --agent <name> --slug <slug> --session <id|unknown> [--started 'YYYY-MM-DD HH:MM']
                       --turns <file> --note <text> --out <log>/sources [--title <t>]
      Write an excerpt of a session this tool cannot read (another agent's, or one whose transcript is
      gone) to sources/<agent>/<date>-<slug>.md, in the excerpt format, secrets redacted. --turns holds
      the turns, each after a line `--- U<k> YYYY-MM-DD HH:MM` (a user turn, its time in UTC), `--- A<k>`
      (an assistant turn) or `--- Q<n> YYYY-MM-DD` (a quote copied from an entry, dated as its
      `(user, ...)`); an unknown session takes one quote, Q1, per file. --note is the paragraph saying
      where the turns came from. --started is the session's first turn, in UTC. A slug the session
      already has is refused.
  chat_export.py find <phrase>... [--root <log>] [--projects <dir>] [--folder=<glob>]...
      List the user turns that contain a phrase (case and spacing ignored), one line each: the phrase's
      number, the transcript, the turn, its time, its text, and where it was found: `log` (the project
      folders of the Log's main checkout and its worktrees, searched first) or `elsewhere` (every
      folder, searched for the phrases the first round did not find). Then a line for each phrase found
      nowhere. --root is the Log (default: the one this tool is in). With --folder, only the project
      folders a glob matches are searched, in one round (found in: `folder`). Give every phrase in one run.

An excerpt's key is <agent>-<YYYY-MM-DD>-<slug>, its file's name, and one session keeps one date in all
its files: a session that already has a file in sources/<agent>/ (its `- Session:` line) keeps that
file's name for the same slug, and a new slug takes the earliest of its files' dates (`- Key date:
another excerpt of the session`); a known session with no file yet takes its first day in UTC
(`session start (UTC)`); otherwise (the transcript gone and no file naming the session), the quote's
own day (`quote (session unknown)`). A key without a `- Key date:` line was named before this rule.

Recognised exports: ChatGPT (conversations*.json), Claude.ai (conversations.json),
Gemini in Workspace (Takeout "Conversation History" files), Gemini Apps (Takeout My Activity
HTML; prompts are grouped into sessions by --gap minutes), and a Perplexity capture
(perplexity-capture*.json, written in the browser, see skills/career-log/modes/import-web.md).
Exports are untrusted data: run with `python3 -I` (Windows: `py -3 -I`) and keep the work
dir outside the repo. Nothing here sends anything anywhere.
"""
import argparse, fnmatch, html, json, os, re, shutil, sys, tarfile, zipfile, zlib
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I leaves this folder off sys.path
sys.dont_write_bytecode = True   # no tools/__pycache__ left in the Log
import logfiles  # noqa: E402

PLATFORMS = {  # platform: (sources folder, citation key, display name)
    "chatgpt": ("chatgpt", "chatgpt", "ChatGPT"),
    "claude": ("claude", "claude-ai", "Claude.ai"),
    "gemini": ("gemini", "gemini", "Gemini in Workspace"),
    "gemini-apps": ("gemini", "gemini-apps", "Gemini Apps"),
    "perplexity": ("perplexity", "perplexity", "Perplexity"),
}
WARNED = set()
BAD_TIMES = {}  # shape of an unreadable timestamp: how many were seen


def warn(text, kind=None):
    """kind, for the index's warnings: packing, disk or parser (the docstring's index)."""
    text += f" [{kind}]" if kind else ""
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
            warn(f"unknown timestamp form {shape!r}; such times are left empty. Add the form to iso()", "parser")
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
        warn(f"Gemini Apps time zone {zone or '(none)'} is unknown and was read as UTC; add it to TZ_HOURS", "parser")
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
        warn(f"{unparsed} Gemini Apps records had no recognised timestamp; add the locale to TS_*", "parser")
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
JUNK_NAMES = ("__MACOSX/", "._*", ".DS_Store", "Thumbs.db", "desktop.ini")  # operating-system leftovers in archives
JUNK = re.compile(r"(^|/)(" + "|".join(re.escape(n.lower()).replace(r"\*", "[^/]*") + ("" if n.endswith("/") else "$")
                                      for n in JUNK_NAMES) + ")")
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


def problem(label, text, kind="packing"):
    PROBLEM_PATHS.add(label.split("!", 1)[0])  # the file on disk the problem is in
    warn(text, kind)


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
                      f"({free >> 20} MB free); extract it by hand into a new folder and index that", "disk")
        return
    NESTED["n"] += 1
    copy = os.path.join(NESTED["dir"], f"{NESTED['n']}.{kind}")
    try:
        with stream() as src:
            copy_out(src, copy)
    except (CopyError, ReadError) as e:
        if isinstance(e, CopyError):
            problem(full, f"{full}: could not copy it into the work dir to open it ({e}); free some space, or extract it by hand", "disk")
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
                     "the page format may have changed, see the Format notes in import-chats.md", "parser")
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
             "in another language, add its folder name to GEMINI_FOLDERS; it was skipped", "parser")
        return [], []
    got = read_known(norm, read)
    if got is None:
        warn(f"{norm} looks like an export but matches no known format; check the Format notes in import-chats.md", "parser")
    return got or [], []


def read_known(norm, read):
    """Conversations from one JSON file; [] for a recognised file with none; None when unrecognised."""
    try:
        data = json.loads(read().decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as e:
        warn(f"skipped {norm}: not readable JSON ({e})", "parser")
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
                 "If one is an export, see import-chats.md step 2", "packing")
    write_index(a, picks, gemini_files)


def scan(a, picks, gemini_files):
    found = {}  # group: [files seen, files with an export]
    for p in a.paths:
        if not os.path.exists(p):
            warn(f"{p}: no such file or folder", "packing")
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
        print(f"{top}: skipped {count} file(s) as Takeout uploads (e.g. {first}{also}); if one is an export, "
              "copy it under another name into a new folder in the scratch space and index that too",
              file=sys.stderr)
    for top, count in SKIPPED_JUNK.items():
        print(f"{top}: skipped {count} operating-system leftover(s) ({', '.join(JUNK_NAMES)})", file=sys.stderr)
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
    keys = read_keys(a.keys) if a.keys else None
    rows = []
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
        rel = "sources/" + os.path.relpath(base, a.out).replace(os.sep, "/")
        unit = "session" if plat == "gemini-apps" else "conversation"
        rows.append((key, f"| `{key} T<n>.U<k>` | `{rel}-prompts.md`: {unit} n, user turn k (full exchange: "
                          f"`{os.path.basename(base)}-threads.md`"
                          + ("; `T<n>.A<k>`: a user turn on another branch" if plat == "chatgpt" else "") + ") |"))
    if keys is not None:
        add_keys(a.keys, keys, rows)


def read_keys(path):
    """keys.md's lines and where its table's last row is; checked before an extract writes anything."""
    try:
        lines = logfiles.read_text(path).split("\n")
    except (OSError, UnicodeDecodeError) as e:
        sys.exit(f"--keys: cannot read {path} ({e}); nothing was written")
    head = next((i for i, l in enumerate(lines) if logfiles.md_cells(l)[:1] == ["Key"]), None)
    if head is None:
        sys.exit(f"--keys: {path} has no table with a Key column; nothing was written")
    end = head
    while end + 1 < len(lines) and lines[end + 1].lstrip().startswith("|"):
        end += 1
    return lines, end


def add_keys(path, keys, rows):
    lines, end = keys
    have = [l.lstrip() for l in lines if l.lstrip().startswith("|")]   # the table's rows, not a citation in its prose
    new = [row for key, row in rows if not any(l.startswith(f"| `{key} ") for l in have)]
    for key, _ in rows:
        print(f"{path}: " + ("added" if any(f"`{key} " in r for r in new) else "already has") + f" the row of `{key}`")
    if new:
        logfiles.write_text(path, "\n".join(lines[:end + 1] + new + lines[end + 1:]))


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


projects_dir = logfiles.projects_dir
fold = logfiles.fold


def project_folder(projects, cwd):
    """Claude Code's folder for a working directory (logfiles.find_project_folder: the rule's one copy)."""
    found = logfiles.find_project_folder(projects, cwd)
    if found:
        return found
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


def session_files(folder, session):
    """The excerpts in folder whose `- Session:` line names the session, as (date, slug) pairs."""
    names = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
    out = []
    for n in names:
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-([a-z0-9-]+)\.md", n)
        if m:
            with open(os.path.join(folder, n), encoding="utf-8", errors="replace") as f:
                if f"- Session: `{session}`" in f.read():
                    out.append((m.group(1), m.group(2)))
    return out


def excerpt_name(folder, slug, session, start):
    """The excerpt's file name: the session's first day (UTC) and the slug. When the session already has
    files, their date wins, so one session keeps one date even where an earlier rule or a hand-written
    file chose another; and a file with this slug is added to under its own name, never renamed."""
    files = session_files(folder, session)
    for date, s in files:
        if s == slug:
            return f"{date}-{s}"
    return f"{min(d for d, _ in files) if files else start[:10]}-{slug}"


def local_day(time):
    """A UTC ISO time's day in this machine's time zone: the date a `(user, YYYY-MM-DD)` citation gives."""
    return datetime.fromisoformat(time).astimezone().date().isoformat() if time else "unknown"


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
    for label in sorted(keep, key=order):
        if label[0] == "U":
            print(f"`{key} {label}` (user, {local_day(by[label]['time'])})")


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


claude_folder = logfiles.claude_folder
folder_of = logfiles.folder_of


def log_folders(projects, root):
    """The project folders of the Log's checkouts: its main checkout's, each worktree's that git lists, and any
    for a folder under one of the main checkout's hidden folders (.claude/worktrees/, .worktrees/), since a
    worktree's transcripts outlive it."""
    try:
        paths = logfiles.checkouts(root)
    except logfiles.LogError:
        paths = [os.path.abspath(root)]
    slugs = [claude_folder(p) for p in paths]
    names = sorted(os.listdir(projects)) if os.path.isdir(projects) else []
    return [os.path.join(projects, n) for n in names if os.path.isdir(os.path.join(projects, n))
            and (any(folder_of(n, s) for s in slugs)
                 or any(fold(n).startswith(fold(slugs[0] + h)) for h in ("--claude-worktrees-", "--worktrees-")))]


def transcripts(roots, skip=()):
    """The session transcripts under the folders, subagents' left out, and none under a folder in skip."""
    for root, _, names in (w for r in roots for w in os.walk(r)):
        if os.sep + "subagents" in root or any(root == s or root.startswith(s + os.sep) for s in skip):
            continue
        for n in sorted(names):
            if n.endswith(".jsonl"):
                yield os.path.join(root, n)


def search(files, wants, where, found, seen):
    """Print each user turn of the files that holds one of wants ({phrase number: lowered phrase}), and note the
    numbers found."""
    raws = raw_phrases(list(wants.values()))
    for p in files:
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
            for k, want in wants.items():
                if want in text and (k, t["time"], t["text"]) not in seen:  # a resumed session copies turns
                    seen.add((k, t["time"], t["text"]))
                    found.add(k)
                    print(f"{k}\t{p}\t{t['label']}\t{t['time'][:16]}\t{one_line(t['text'])[:120]}\t{where}")


def cmd_find(a):
    wants = {k: one_line(p).lower() for k, p in enumerate(a.phrases, 1)}
    projects = projects_dir(a.projects)
    found, seen = set(), set()
    if a.folder:
        search(transcripts(search_roots(projects, a.folder)), wants, "folder", found, seen)
    else:
        mine = log_folders(projects, a.root or logfiles.default_root(__file__))
        search(transcripts(mine), wants, "log", found, seen)
        rest = {k: w for k, w in wants.items() if k not in found}
        if rest:
            search(transcripts([projects], skip=mine), rest, "elsewhere", found, seen)
    where = f"{projects}{' in the folders --folder matches' if a.folder else ''}"
    for k in wants:
        if k not in found:
            print(f"{k}\tnot found under {where}")
    if not found:
        sys.exit(f"no user turn under {where} contains any of the phrases")


# Screening marks (marks.tsv), the import log's three lines, and its leak check (import-chats.md steps 3 and 7)

CATEGORIES = ("health", "finances and investing", "relationships", "housing", "shopping", "travel", "entertainment",
              "called unimportant by the user", "other, not career-relevant")
STATUSES = ("picked", "not picked", "dropped")
LEAK_WORDS = 5  # of a first prompt, searched for as one phrase
LEAK_SHORTEST = 3  # characters: a shorter title would match nearly every line


def index_rows(work):
    """index.tsv's rows as {n: {column: value}}."""
    path = os.path.join(work, "index.tsv")
    if not os.path.isfile(path):
        sys.exit(f"no {path}: run index first (and keep the work dir until the import is committed)")
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    cols = lines[0].split("\t")
    return {int(r.split("\t")[0]): dict(zip(cols, r.split("\t"))) for r in lines[1:] if r.strip()}


def read_marks(work, rows):
    """marks.tsv as {n: (category or group, status)}; every conversation it leaves out is 'other, not career-relevant'."""
    path = os.path.join(work, "marks.tsv")
    if not os.path.isfile(path):
        sys.exit(f"no {path}: write it while screening (the docstring's tally says how)")
    marks, bad = {}, []
    with open(path, encoding="utf-8-sig") as f:
        for i, line in enumerate(f, 1):
            cells = [c.strip() for c in line.rstrip("\r\n").split("\t")]
            if not line.strip() or (i == 1 and not cells[0].isdigit()):
                continue  # a blank line, or a header row
            n, mark, status = (cells + ["", ""])[:3]
            group = re.fullmatch(r"G\d+", mark)
            why = ("n is not a number" if not n.isdigit() else
                   "not in index.tsv" if int(n) not in rows else
                   "marked twice" if int(n) in marks else
                   f"not a category or a group (categories: {', '.join(CATEGORIES)}; groups: G1, G2, ...)"
                   if not group and mark not in CATEGORIES else
                   "only a group's row has a status" if status and not group else
                   f"status is one of {', '.join(STATUSES)}" if status and status not in STATUSES else
                   "more than three columns" if len(cells) > 3 else "")
            if why:
                bad.append(f"{path}:{i}: {why}: {line.strip()}")
            else:
                marks[int(n)] = (mark, status)
    if bad:
        sys.exit("\n".join(bad))
    for n in rows:
        marks.setdefault(n, ("other, not career-relevant", ""))
    return marks


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def cmd_tally(a):
    rows = index_rows(a.work)
    marks = read_marks(a.work, rows)
    groups = {}
    for n, (mark, status) in sorted(marks.items()):
        if mark not in CATEGORIES:
            groups.setdefault(mark, []).append((n, status))
    if a.groups:
        for g in sorted(groups, key=lambda g: int(g[1:])):
            ns = [n for n, _ in groups[g]]
            days = sorted(rows[n]["start_utc"][:10] for n in ns if rows[n]["start_utc"])
            span = "no dates" if not days else days[0] if days[0] == days[-1] else f"{days[0]} to {days[-1]}"
            print(f"{g}: {plural(len(ns), 'conversation')} ({spans(ns)}), {span} (UTC)")
        if not groups:
            print("no groups in marks.tsv")
        return
    open_rows = [f"{g}: {n}" for g, rs in groups.items() for n, status in rs if not status]
    if open_rows:
        sys.exit("conversations of a group with no status (picked, not picked or dropped): " + ", ".join(open_rows))
    counts = {c: sum(m == c for m, _ in marks.values()) for c in CATEGORIES}
    left = ", ".join(f"{c} {counts[c]}" for c in CATEGORIES if counts[c])
    unpicked = [g for g, rs in groups.items() if any(s == "not picked" for _, s in rs)]
    convs = sum(s == "not picked" for _, s in marks.values())
    dropped = sum(s == "dropped" for _, s in marks.values())
    print(f"Left out by category: {left or 'none'}")
    print(f"Groups not picked: {plural(len(unpicked), 'group')}, {plural(convs, 'conversation')}" if unpicked
          else "Groups not picked: none")
    print(f"Dropped: {plural(dropped, 'conversation')} (user, {a.date or datetime.now().date().isoformat()})" if dropped
          else "Dropped: none")


def last_section(path):
    """(line number, lines) of the file's last level-2 section, or of the whole file when it has none."""
    try:
        lines = logfiles.read_text(path).split("\n")
    except (OSError, UnicodeDecodeError) as e:
        sys.exit(f"cannot read {path}: {e}")
    starts = [i for i, l in enumerate(lines) if l.startswith("## ")]
    first = starts[-1] if starts else 0
    return first + 1, lines[first:]


def cmd_leaks(a):
    rows = index_rows(a.work)
    picks = parse_pick(a.pick)
    bad = [n for n in picks if n not in rows]
    if bad:
        sys.exit(f"--pick {bad}: index.tsv has conversations 0-{max(rows, default=-1)}")
    start, lines = last_section(a.log)
    norm = [one_line(l).lower() for l in lines]
    hits, short = 0, 0
    for n, r in sorted(rows.items()):
        if n in picks:
            continue
        needles = [("title", one_line(r.get("title", ""))),
                   ("first prompt", " ".join(one_line(r.get("first_prompt", "")).split(" ")[:LEAK_WORDS]))]
        for what, needle in needles:
            if not needle:
                continue
            if len(needle) < LEAK_SHORTEST:
                short += 1
                continue
            for i, l in enumerate(norm):
                if needle.lower() in l:
                    hits += 1
                    print(f"{start + i}: conversation {n}'s {what} \"{needle}\": {one_line(lines[i])[:160]}")
    where = f"{a.log} from line {start}" + (f" ({one_line(lines[0])[:80]})" if lines and lines[0].startswith("## ") else "")
    also = f"; {short} title(s) under {LEAK_SHORTEST} characters not searched" if short else ""
    print(f"{plural(hits, 'hit')} in {where}{also}")


def cmd_manifest(a):
    def unknown(why):
        print(f"unknown shape: {why}; read {a.file} by hand (import-chats.md step 1)")
        sys.exit(1)
    try:
        data = json.loads(logfiles.read_text(a.file))
    except (OSError, ValueError, UnicodeDecodeError) as e:
        unknown(f"not readable JSON ({e})")
    items = data.get("data_files") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        unknown("no data_files list")
    for i, item in enumerate(items):
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k] for k in ("category", "filename", "export_url")) \
                or "part" not in item:
            unknown(f"data_files[{i}] lacks one of category, part, filename, export_url")
        if not item["export_url"].startswith("https://"):
            unknown(f"data_files[{i}]'s export_url is not an https link")
    want = ("conversations", "memories") if a.memories else ("conversations",)
    got = sorted((want.index(i["category"]), str(i["part"]).zfill(6), i["filename"], i["export_url"])
                 for i in items if i["category"] in want)
    if not any(w == 0 for w, *_ in got):
        unknown("no conversations item")
    for _, _, name, url in got:
        print(f"- [{name}]({url})")
    rest = sorted(i["filename"] for i in items if i["category"] not in want)
    if rest:
        print(f"Not needed: {', '.join(rest)}")
    print("Give the user these links to open in the browser signed in to the same Claude account and save into "
          "sources/inbox/claude/: each expires 24 hours after the export was made and may work only once. Never "
          "open or download them yourself, and never write them into the repo or the import log.")


# An extract's turns, cut before it is committed (import-chats.md step 5)

EXTRACT_HEADING = re.compile(r"(?:## (T\d+): |### (T\d+\.U\d+) — |### (T\d+): user turns on other branches|#### (T\d+\.A\d+) — )")


def extract_blocks(text):
    """An extract as [label, lines] blocks: the head (None), each conversation's heading (T3), each user turn
    with the answers after it (T3.U2), the heading of its other branches (T3:other) and each turn on them (T3.A1).
    A heading inside a turn's fenced text is text."""
    blocks, ticks = [[None, []]], None
    for line in text.split("\n"):
        m = EXTRACT_HEADING.match(line) if ticks is None else None
        if m:
            label = m.group(1) or m.group(2) or m.group(4) or m.group(3) + ":other"
            blocks.append([label, []])
        elif ticks is None and re.fullmatch(r"`{4,}text", line):
            ticks = line[:-4]
        elif ticks is not None and line == ticks:
            ticks = None
        blocks[-1][1].append(line)
    return blocks


def conversation(label):
    return re.match(r"T\d+", label).group(0) if label else None


def cmd_cut(a):
    m = re.fullmatch(r"(.*)-(threads|prompts)\.md", a.file)
    if not m:
        sys.exit(f"{a.file}: give an extract's -threads.md or -prompts.md file")
    files = [m.group(1) + "-threads.md", m.group(1) + "-prompts.md"]
    labels = [p.strip() for p in a.turns.split(",") if p.strip()]
    if not labels or any(not re.fullmatch(r"T\d+(?:\.[UA]\d+)?", x) for x in labels):
        sys.exit(f"{a.turns}: give turns and conversations like T3.U2,T3.A1,T5")
    out = {}
    for path in files:
        try:
            blocks = extract_blocks(logfiles.read_text(path))
        except (OSError, UnicodeDecodeError) as e:
            sys.exit(f"cannot read {path}: {e}")
        have = {b[0] for b in blocks}
        missing = [x for x in labels if x not in have]
        if missing:
            sys.exit(f"{path} has no {', '.join(missing)}; nothing was cut")
        kept = [b for b in blocks if b[0] not in labels and conversation(b[0]) not in labels]
        branches = {conversation(b[0]) for b in kept if b[0] and ".A" in b[0]}
        kept = [b for b in kept if not (b[0] or "").endswith(":other") or conversation(b[0]) in branches]
        out[path] = "\n".join(line for b in kept for line in b[1])
    for path, text in out.items():
        logfiles.write_text(path, text)
    print(f"cut {', '.join(labels)} from {files[0]} and {files[1]}; every other number is unchanged")


def quote_turns(path):
    """The --turns file of `quote` as [{label, time, text}]."""
    head = re.compile(r"--- (?:(U\d+) (\d{4}-\d{2}-\d{2} \d{2}:\d{2})|(A\d+)|(Q\d+) (\d{4}-\d{2}-\d{2}))")
    try:
        lines = logfiles.read_text(path).split("\n")
    except (OSError, UnicodeDecodeError) as e:
        sys.exit(f"cannot read {path}: {e}")
    turns = []
    for i, line in enumerate(lines, 1):
        m = head.fullmatch(line.rstrip())
        if m:
            turns.append({"label": m.group(1) or m.group(3) or m.group(4), "time": m.group(2) or m.group(5) or "",
                          "lines": []})
        elif re.match(r"--- [UAQ]\d", line):
            sys.exit(f"{path}:{i}: write `--- U<k> YYYY-MM-DD HH:MM`, `--- A<k>` or `--- Q<n> YYYY-MM-DD`")
        elif turns:
            turns[-1]["lines"].append(line)
        elif line.strip():
            sys.exit(f"{path}:{i}: text before the first `--- ` turn line")
    for t in turns:
        t["text"] = "\n".join(t.pop("lines")).strip()
    labels = [t["label"] for t in turns]
    problems = (["no turns"] if not turns else []) + [f"{t['label']} is empty" for t in turns if not t["text"]] + \
        [f"{x} twice" for x in sorted(set(labels)) if labels.count(x) > 1]
    if problems:
        sys.exit(f"{path}: " + "; ".join(problems))
    return turns


def cmd_quote(a):
    folder_name = re.sub(r"[^a-z0-9]+", "-", a.agent.lower()).strip("-")
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)*", folder_name):
        sys.exit(f"--agent {a.agent!r}: name the agent in letters and digits, starting with a letter (codex, cursor)")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", a.slug):
        sys.exit("--slug: lowercase letters, digits and single hyphens, like api-retry-design")
    if a.started and not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", a.started):
        sys.exit("--started: the session's first turn as 'YYYY-MM-DD HH:MM', in UTC")
    unknown = a.session == "unknown"
    if unknown and a.started:
        sys.exit("--started: an unknown session has no known start; leave it out")
    turns = quote_turns(a.turns)
    if unknown and [t["label"] for t in turns] != ["Q1"]:
        sys.exit("--session unknown: each quote gets its own file, so --turns holds one turn, `--- Q1 YYYY-MM-DD`")
    folder = os.path.join(a.out, folder_name)
    files = [] if unknown else session_files(folder, a.session)
    if any(s == a.slug for _, s in files):
        sys.exit(f"the session already has a file with the slug {a.slug}: pass a new --slug")
    if files:
        date, key_date = min(d for d, _ in files), "another excerpt of the session"
    elif a.started:
        date, key_date = a.started[:10], "session start (UTC)"
    else:
        first = turns[0]
        date = first["time"][:10] if first["label"][0] == "Q" else \
            local_day(first["time"].replace(" ", "T") + ":00+00:00") if first["time"] else ""
        if not date:
            sys.exit("--turns: the first turn has no date, and neither the session's files nor --started give one")
        key_date = "quote (session unknown)"
    name = f"{date}-{a.slug}"
    path = os.path.join(folder, name + ".md")
    if os.path.exists(path):
        sys.exit(f"{path} exists already (another session's): pass a new --slug")
    key = f"{folder_name}-{name}"
    counts = {}
    times = any(t["label"][0] == "U" for t in turns)
    text = (f"# {one_line(a.agent)} session {date}: {redact(one_line(a.title or a.slug), counts)}\n\n"
            f"{one_line(a.note)} Only **User** turns are the user's own words; **Assistant** turns are AI output, "
            f"leads only.{' Times are UTC.' if times else ''} Cite a turn as `{key} <turn>`, such as "
            f"`{key} {turns[0]['label']}`.\n\n- Session: `{a.session}`\n"
            + (f"- Started: {a.started} UTC\n" if a.started else "") + f"- Key date: {key_date}\n\n")
    for t in turns:
        head = {"U": f"User ({t['time']})", "A": "Assistant", "Q": f"User ({t['time']})"}[t["label"][0]]
        text += f"## {t['label']} — {head}\n\n" + fence(redact(t["text"], counts)) + "\n"
    os.makedirs(folder, exist_ok=True)
    logfiles.write_text(path, text.rstrip("\n") + "\n")
    if counts:
        print("redacted: " + ", ".join(f"{n} {k}" for k, n in counts.items()), file=sys.stderr)
    print(f"{path}: written; key `{key}`")
    for t in turns:
        if t["label"][0] == "U":
            print(f"`{key} {t['label']}` (user, {local_day(t['time'].replace(' ', 'T') + ':00+00:00')})")
        elif t["label"][0] == "Q":
            print(f"`{key} {t['label']}` (user, {t['time']})")


def minutes(s):
    n = int(s)
    if n < 1:
        raise argparse.ArgumentTypeError("the session gap is at least 1 minute")
    return n


__doc__ = __doc__.format(depth=MAX_DEPTH, junk=", ".join(JUNK_NAMES), words=LEAK_WORDS,
                         categories="\n".join("        " + c for c in CATEGORIES))


def main():
    logfiles.utf8_stdout()
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
    p.add_argument("--keys", help="the Log's sources/keys.md: add each extract's row to its table")
    p.set_defaults(fn=cmd_extract)
    p = sub.add_parser("cut")
    p.add_argument("file")
    p.add_argument("turns")
    p.set_defaults(fn=cmd_cut)
    p = sub.add_parser("tally")
    p.add_argument("work")
    p.add_argument("--groups", action="store_true")
    p.add_argument("--date", help="the day the user dropped conversations (default: today)")
    p.set_defaults(fn=cmd_tally)
    p = sub.add_parser("leaks")
    p.add_argument("work")
    p.add_argument("--pick", required=True)
    p.add_argument("log", help="sources/import-log.md, its new section last")
    p.set_defaults(fn=cmd_leaks)
    p = sub.add_parser("manifest")
    p.add_argument("file")
    p.add_argument("--memories", action="store_true")
    p.set_defaults(fn=cmd_manifest)
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
    p = sub.add_parser("quote")
    p.add_argument("--agent", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--session", required=True, help="the session's id, or unknown")
    p.add_argument("--started", help="the session's first turn, 'YYYY-MM-DD HH:MM' in UTC")
    p.add_argument("--turns", required=True)
    p.add_argument("--note", required=True, help="where the turns came from")
    p.add_argument("--out", required=True)
    p.add_argument("--title")
    p.set_defaults(fn=cmd_quote)
    p = sub.add_parser("find")
    p.add_argument("phrases", nargs="+")
    p.add_argument("--root", help="the Log (default: the one this tool is in)")
    p.add_argument("--projects")
    p.add_argument("--folder", action="append", help="only project folders whose name matches this glob; "
                   "repeatable; write --folder=<glob> when it starts with '-'")
    p.set_defaults(fn=cmd_find)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
