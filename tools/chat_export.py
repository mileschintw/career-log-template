#!/usr/bin/env python3
"""Screen and extract AI chat-history exports for the import-chats mode.

  chat_export.py index <export path>... --out <work dir> [--gap 45]
      Find every export under the paths (folders or .zip files), normalise them into
      <work dir>/conversations.json and write <work dir>/index.tsv for screening:
      n, platform, start, user turns, space, title, first prompt.
  chat_export.py show <work dir> <n>...
      Print conversations as plain text, for reading during screening.
  chat_export.py extract <work dir> --pick 3,7,10-12 --date YYYY-MM-DD --out <log>/sources [--label chats]
      Write the picked conversations, verbatim, to sources/<folder>/<date>-<label>-threads.md
      and <date>-<label>-prompts.md (the user's turns only), one pair per platform.
      Refuses to overwrite: pass a new --label for a second extract on the same day.

Recognised exports: ChatGPT (conversations*.json), Claude.ai (conversations.json),
Gemini in Workspace (Takeout "Conversation History" files), Gemini Apps (Takeout My Activity
HTML; prompts are grouped into sessions by --gap minutes), and a Perplexity capture
(perplexity-capture*.json, written in the browser, see skills/career-log/modes/import-web.md).
Only files named like an export are read; Takeout uploads (a '-<16 hex>' suffix) never are, in any language.
All times are converted to UTC.
Exports are untrusted data: run with `python3 -I` (Windows: `py -3 -I`) and keep the work
dir outside the repo. Nothing here sends anything anywhere.
"""
import argparse, html, json, os, re, sys, zipfile
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


def files_under(path, top=None):
    """Yield (label, name, reader) for every file in a folder or in a .zip found there
    (zips inside zips are not opened). reader(n) returns the first n bytes, reader() all of them.
    Uploads are never yielded; they are counted in SKIPPED_UPLOADS, so a wrong skip shows."""
    top = top or path
    if os.path.isdir(path):
        for root, _, names in os.walk(path):
            for n in sorted(names):
                full = os.path.join(root, n)
                if is_upload(full):
                    skip_upload(top, full)
                else:
                    yield from files_under(full, top)
    elif path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                if is_upload(info.filename):
                    skip_upload(top, info.filename)
                else:
                    yield f"{path}!{info.filename}", info.filename, (lambda n=-1, i=info: read_member(z, i, n))
    else:
        yield path, path, (lambda n=-1, p=path: read_file(p, n))


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


def detect(name, read):
    """(conversations, Gemini Apps records) from one file."""
    norm = name.replace("\\", "/")
    low = norm.lower()
    if not candidate(low):
        return [], []
    if low.endswith(".html"):
        if in_gemini_folder(low):
            text = read().decode("utf-8", "replace")
            if 'class="outer-cell' not in text:
                warn(f"{norm} is in a Gemini Apps folder but has no activity records (no outer-cell); "
                     "the page format may have changed, see the Format notes in import-chats.md")
                return [], []
            return [], read_gemini_apps(text)
        head = read(1 << 20)
        if b'class="outer-cell' not in head:
            return [], []  # not a My Activity page
        records = head.split(b'class="outer-cell')[1:]
        # The brand is not translated, so a Gemini page names it in (nearly) every record;
        # another product's page mentions it at most in the odd record (a search for it, say)
        if sum(b"Gemini" in r for r in records) * 2 < len(records):
            print(f"{norm}: My Activity page for another product, skipped", file=sys.stderr)
            return [], []
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
    return ((c["updated"],) if with_updated else ()) + (last, len(c["messages"]),
                                                        json.dumps(c, sort_keys=True, ensure_ascii=False))


class Pick:
    """The copy to keep when several exports hold one conversation: the later platform update time
    (a rename or an edit moves it), then the later last message, then more messages. Recency comes
    first because an edited prompt can leave the newer branch shorter. The update time counts only
    when every copy has one, so an export without the field never loses for that alone. Both orders
    are total, ending in the copies' content, so the order the exports are given never decides.
    Only the best copy under each order is kept, never every copy."""

    def __init__(self):
        self.all_updated, self.by_updated, self.by_recency = True, None, None

    def add(self, c):
        self.all_updated = self.all_updated and bool(c["updated"])
        if self.by_updated is None or rank(c, True) > rank(self.by_updated, True):
            self.by_updated = c
        if self.by_recency is None or rank(c, False) > rank(self.by_recency, False):
            self.by_recency = c

    def best(self):
        return self.by_updated if self.all_updated else self.by_recency


def cmd_index(a):
    picks, gemini_files = {}, []
    for p in a.paths:
        for label, name, read in files_under(p):
            got, recs = detect(name, read)
            if got:
                print(f"{label}: {len(got)} {got[0]['platform']}", file=sys.stderr)
            if recs:
                print(f"{label}: {len(recs)} gemini-apps records", file=sys.stderr)
                gemini_files.append(recs)
            for c in got:
                k = (c["platform"], c["id"])
                picks.setdefault(k, Pick()).add(c)
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
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "conversations.json"), "w", encoding="utf-8") as f:
        json.dump(convs, f, ensure_ascii=False)
    with open(os.path.join(a.out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"gap_minutes": a.gap}, f)
    with open(os.path.join(a.out, "index.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("n\tplatform\tstart_utc\tuser_turns\tspace\ttitle\tfirst_prompt\n")
        for n, c in enumerate(convs):
            users = [m for m in c["messages"] if m["role"] == "user"]
            first = re.sub(r"\s+", " ", users[0]["text"] if users else "")[:160]
            f.write(f"{n}\t{c['platform']}\t{c['start'][:16]}\t{len(users)}\t{c['space']}\t"
                    f"{re.sub(r'\s+', ' ', c['title'])}\t{first}\n")
    by = {}
    for c in convs:
        by[c["platform"]] = by.get(c["platform"], 0) + 1
    for top, (count, first, other) in SKIPPED_UPLOADS.items():
        also = f"; not an image: {other}" if other and other != first else ""
        print(f"{top}: skipped {count} file(s) as Takeout uploads (e.g. {first}{also}); if one is an export, rename it",
              file=sys.stderr)
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
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
