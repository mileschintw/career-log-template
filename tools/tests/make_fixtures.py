#!/usr/bin/env python3
"""Build anonymised test fixtures for chat_export.py from real exports.

  make_fixtures.py [--chatgpt <file or folder>] [--claude <conversations.json or .zip>]
                   [--gemini-apps <the activity page, or the Takeout folder>] --out <dir> [--seed N]

Keeps an export's structure: schema keys (SCHEMA_KEYS), nesting, value types, conversation trees,
record kinds, timestamp forms (period words, zones), link kinds and attachment shapes. Replaces
everything written by a person or a model with words from VOCAB, every id with a made-up one,
every URL and file name with a placeholder, and every key outside SCHEMA_KEYS with key_<n>.
Times are made up too: each conversation is moved by its own random amount (only the gaps inside
it survive), and Gemini Apps records get a made-up clock, so no real timing or time of day is left.

Two proofs run before anything is kept: check() (every key is a schema key or a placeholder, every
string a kept label, a placeholder shape or VOCAB words), and crosscheck(), which needs no rules
at all: no word of the source may appear in the output unless it is a schema key, a kept label, a
kept enum value (listed for review), or a made-up word.

A sample, not everything, is kept: the conversations and records that cover the features found,
plus a few more. With --madeup, cases a real export may lack are added from made-up data: English
timestamps and rarer period words (always), and a Perplexity capture, Gemini in Workspace files,
ChatGPT edited prompts with hidden, tool and mid-thread cases, and zh-prefixed prompts.

Takeout uploads are never opened: the activity page is the only Takeout file read. Run with
`python3 -I`, like chat_export.py. The output is safe to commit only after check() passes; the
test suite runs check() again on every run.
"""
import argparse, json, os, random, re, shutil, sys, tempfile, uuid, zipfile
from datetime import datetime, timedelta

# Made-up words. Nothing in a fixture may be a word outside this list or KEEP.
VOCAB_EN = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november "
            "oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu amber basil "
            "cedar dune ember fern grove harbor iris jade kelp lumen maple nectar onyx pebble quartz "
            "river sage thistle umber vale willow yarrow zephyr").split()
VOCAB_ZH = "甲 乙 丙 丁 戊 己 庚 辛 壬 癸 子 丑 寅 卯 辰 巳 午 未 申 酉 戌 亥".split()
VOCAB = set(VOCAB_EN) | set(VOCAB_ZH)

# Labels written by the platform, kept as they are (the parser keys on some of them)
KEEP = {
    "Gemini Apps", "&emsp;Gemini Apps", "產品：", "為什麼有這項活動記錄？", "這裡", "控管這些設定。", "詳細資料：",
    "&emsp;由於您開啟了下列設定，因此系統將這個活動儲存到您的 Google 帳戶中：&nbsp;Gemini Apps Activity.&nbsp;您可以前往",
    "Manage your Gems.", "我的活動記錄", "Products:", "Why is this here?", "Details:",
}
KEEP_PREFIX = re.compile(r"^(Prompted|Branched|已提示|提示|Created Gemini Canvas titled)(\xa0|&nbsp;|[:：]?\s+|$)")
# Whole records the platform writes for bookkeeping, as found; anything longer is not kept
KEEP_WHOLE = re.compile(
    r"^(Used(\xa0| )Gemini Apps|Gave feedback: (Good|Bad) response( \(Unspecified\))?|Selected preferred draft"
    r"|Used an Assistant feature|Cleared previous feedback|Attached \d+ files?\.|\s*)$")
# Keys of the exports' own schemas, as found. A key outside it (front matter, a user-defined
# field) becomes key_<n>; a new format's key is added here by hand after a look at it.
SCHEMA_KEYS = set("""
account alt alternative_display_type approval_key approval_key_legacy approval_options asset_pointer
asset_pointer_link attachments attribution attribution_segments attributions author bidi_voice_fem_message
bidi_voice_mode_message body body_has_rewritten_wikilinks chat_messages chunks citations
container_pixel_height container_pixel_width content content_references content_type context
context_connector context_connector_info conversation_id conversation_template_id create_time created_at
current_node custom_symbol_offsets cut_off dalle decoding_id default_model_slug description direction
display_content documents domain emu_omit_glimpse_image emu_patches_override end endIndex end_index entries
extracted_content fallback_items fileTokenSize file_name file_path file_size file_token_size file_type
file_uuid files files_list finished flags fovea generation gizmo has_images height hidden hidden_in_chat hue
icon_name icon_type icon_url id if_version image_results initial_turn_only injection_source input
integration_icon_url integration_name is_archived is_big_paste is_do_not_remember is_error is_mcp_app
is_no_auth_placeholder is_read_only is_starred is_study_mode items library_file_id lpe_delta_encoding_channel
lpe_keep_patch_ijhw mapping mcp_server_url memory_scope message message_locale meta metadata mimeType
mime_type model_slug name new_str old_str output_format_category parent parent_id parent_message_uuid parsed
parts path path_segments pinned_time plugin_ids prefix prompt prompt_text pub_date ref_index ref_type refs
resource_type role sanitized search_result_groups segmentation sender serialization_metadata signature size
size_bytes skip_on_truncated_continuation snippet source source_analysis_msg_id source_name source_url
sources start startIndex start_index start_timestamp stop_timestamp structured_content subtitles summaries
summary supporting_websites symbol synthetic_extension target targeted_reply_label
targeted_reply_source_message_id targeted_reply_source_range text thinking thinking_hidden thoughts title
tool_icons tool_identifier tool_origin tool_use_id truncated turn_index type update_time updated_at url uuid
version voice watermarked_asset_pointer width wikilink_refs wikilinks
is_visually_hidden_from_conversation slug space t q a att
children conversation_turns user_turn system_turn turn_last_modified data
""".split())
KEY_PLACEHOLDER = re.compile(r"^key_\d+$")
# HTML attributes: class names and alignment as found; every other attribute is checked as text
CSS_CLASSES = set("""content-cell header-cell image-preview mdl-cell mdl-cell--12-col mdl-cell--6-col mdl-grid
mdl-typography--body-1 mdl-typography--caption mdl-typography--text-right mdl-typography--title
mdl-shadow--2dp outer-cell""".split())
ALIGN = {"left", "center", "right"}
# Strings kept in JSON when they sit under one of these keys and look like an identifier
ENUM_KEYS = {"role", "sender", "content_type", "type", "model_slug", "default_model_slug", "memory_scope",
             "mime_type", "mimeType", "file_type", "resource_type", "recipient", "status", "ref_type",
             "icon_type", "display_type", "alternative_display_type", "voice"}
ENUM = re.compile(r"^[A-Za-z0-9_.\-/]{1,40}$")
# Values kept under ENUM_KEYS (and as tool names beside a role): only these, reviewed by hand.
# Any other value becomes made-up words and is listed, so a new one can be looked at and added.
KNOWN_ENUMS = set("""
assistant user system tool human auto global_enabled text multimodal_text code execution_output
thoughts reasoning_recap thinking tool_use tool_result injected_prompt_block image_asset_pointer
webpage_extended tether_quote tether_browsing_display image/jpeg image/png image/gif image/webp
application/pdf text/plain txt pdf png jpg
gpt-4 gpt-4o gpt-4-browsing gpt-4-code-interpreter gpt-4-gizmo gpt-4-plugins gpt-4-dalle gpt-5-6-thinking
gpt-5.6-sol-wm o1 o1-preview text-davinci-002-render-sha browser python dalle.text2im
""".split())
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
HEXID = re.compile(r"^[0-9a-f]{12,}$|^client-created-root$")
ISO = re.compile(r"^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(\.\d+)?(Z|[+-]\d\d:\d\d)?$")
# File types a placeholder name may keep; any other extension becomes .bin, since it is text the user chose
KNOWN_EXT = ("pdf png jpg jpeg gif webp heic bmp tif tiff svg txt md csv tsv json xml yaml yml html htm "
             "doc docx xls xlsx ppt pptx odt rtf tex bib zip gz tar wav mp3 m4a ogg flac mp4 mov webm "
             "py js ts java c cpp h hpp cs go rs rb sh ipynb sql bin").split()
EXT = "(?:" + "|".join(KNOWN_EXT) + ")"
PLACEHOLDER = re.compile(r"^(https://example\.com/\d+|file-\d+(-[0-9a-f]{16})?\." + EXT + "|"
                         r"https://gemini\.google\.com/app/[0-9a-f]+|https://myaccount\.google\.com/activitycontrols.*|"
                         r"https://gemini\.google\.com/gems/view)$")
EPOCH = (1.0e9, 2.2e9)  # a number in this range under a time or date key is a timestamp
DAY = re.compile(r"^(\d{4})-(\d\d)-(\d\d)$")
TS_ZH = re.compile(r"^(\s*)(\d{4})年(\d{1,2})月(\d{1,2})日(\s*)(\S{2})(\d{1,2}):(\d\d):(\d\d)(\s*)(\S*?)(\s*)$")
TS_EN = re.compile(r"^(\s*)([A-Z][a-z]{2}) (\d{1,2}), (\d{4}), (\d{1,2}):(\d\d):(\d\d)(\s*)([AP]M)(\s*)(\S*?)(\s*)$")
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
UPLOAD = re.compile(r"-[0-9a-f]{16}\.[^./]+$")
# Zones the parser knows (chat_export.TZ_HOURS); the fixture page uses one at random, not the account's
PAGE_ZONES = ("UTC", "PST", "PDT", "EST", "EDT", "CET", "CEST", "JST", "SGT", "AEST")
# Numbers under these keys are file sizes and image dimensions: scaled at random, not kept
MEASURES = {"size", "size_bytes", "file_size", "fileTokenSize", "file_token_size", "width", "height",
            "container_pixel_height", "container_pixel_width"}


def ext_of(name):
    ext = os.path.splitext(name.split("?", 1)[0])[1].lower().lstrip(".")
    return "." + (ext if ext in KNOWN_EXT else "bin")


class Anon:
    def __init__(self):
        # The OS's generator, with no state: a seeded one (even a secret seed) could be replayed, or
        # cloned from the fake ids it prints, to recover the shifts below and so the real times.
        # Only the sampler (build's rng) takes --seed.
        self.rng, self.ids, self.keys, self.n = random.SystemRandom(), {}, {}, 0
        self.unknown = set()  # identifier-like values under ENUM_KEYS that are not KNOWN_ENUMS, replaced
        self.base = self.rng.randrange(1500, 3500)  # days, unknown too, so a fixture date bounds no real one
        self.shift = None  # set per conversation; a time read outside one is an error, never shifted by a stale amount
        self.clock = datetime(2030, 6, 30, 23, 0)  # the made-up Gemini Apps clock, running backwards
        self.zone = self.rng.choice(PAGE_ZONES)  # the made-up zone every Gemini Apps record is written in

    def new_item(self):
        """Each conversation moves by its own random amount, down to the microsecond, so no real date,
        time of day or seconds survive; the gaps inside it do."""
        self.shift = timedelta(days=self.base + self.rng.randrange(700), seconds=self.rng.randrange(86400),
                               microseconds=self.rng.randrange(10 ** 6))

    def moved(self, t):
        if self.shift is None:
            raise AssertionError("a time outside any conversation would be shifted by a stale amount")
        return t + self.shift

    def words(self, original, cap=160):
        """Made-up text about as long as the original (capped). Its first six lines are kept as
        lines, blank ones blank, so whitespace handling is still tested."""
        if not original.strip():
            return original
        zh = re.search(r"[\u4e00-\u9fff]", original) is not None
        lines = original.split("\n")[:6]
        per = max(cap // len(lines), 4)
        out = []
        for ln in lines:
            if not ln.strip():
                out.append(ln if not ln.strip() and len(ln) < 8 else "")
                continue
            line = []
            while sum(len(w) + 1 for w in line) < min(len(ln) + 1, per):
                line.append(self.rng.choice(VOCAB_ZH if zh and self.rng.random() < 0.5 else VOCAB_EN))
            out.append(" ".join(line))
        return "\n".join(out)

    def key(self, k):
        if k in SCHEMA_KEYS or KEY_PLACEHOLDER.match(k):
            return k
        if UUID.match(k) or HEXID.match(k):
            return self.fake_id(k)
        if k not in self.keys:
            self.keys[k] = f"key_{len(self.keys) + 1}"
        return self.keys[k]

    def fake_id(self, real, shape=None):
        if real not in self.ids:
            self.n += 1
            h = "%032x" % self.rng.getrandbits(128)
            if UUID.match(real):
                self.ids[real] = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
            elif real == "client-created-root":
                self.ids[real] = real
            else:
                self.ids[real] = (h * 4)[:len(real)]
        return self.ids[real]

    def counter(self):
        self.n += 1
        return self.n

    def iso(self, m):
        """The fraction is shifted too and written with as many digits as it had (6 at most), so order holds."""
        return iso_plus(m.group(0), self.moved(timedelta(0)))

    def day(self, m):
        return self.moved(datetime(*map(int, m.groups()))).strftime("%Y-%m-%d")

    def text(self, s, key=None, tool_name=False):
        if s == "" or s is None:
            return s
        if key in ENUM_KEYS or tool_name:
            if s in KNOWN_ENUMS:
                return s
            if ENUM.match(s):
                self.unknown.add(s)
        if UUID.match(s) or HEXID.match(s):
            return self.fake_id(s)
        m = ISO.match(s)
        if m:
            return self.iso(m)
        m = DAY.match(s)
        if m:
            return self.day(m)
        if re.match(r"^https?://", s):
            return f"https://example.com/{self.counter()}"
        if key in ("file_name", "name") and re.search(r"\.[A-Za-z0-9]{1,5}$", s) and "\n" not in s and len(s) < 120:
            return f"file-{self.counter()}{ext_of(s)}"
        return self.words(s)

    def json(self, o, key=None):
        if isinstance(o, dict):
            author = "role" in o
            return {self.key(k): (self.text(v, k, tool_name=True) if author and k == "name" and isinstance(v, str)
                                  else self.json(v, k))
                    for k, v in o.items()}
        if isinstance(o, list):
            return [self.json(v, key) for v in o]
        if isinstance(o, str):
            return self.text(o, key)
        if isinstance(o, (int, float)) and not isinstance(o, bool) and key:
            if re.search(r"time|date", key) and EPOCH[0] <= o <= EPOCH[1]:
                return o + self.moved(timedelta(0)).total_seconds()
            if key in MEASURES and o > 0:  # a file's real size or an image's real dimensions are a fingerprint
                return type(o)(max(1, round(o * self.rng.uniform(0.5, 1.5))))
        return o

    def tick(self):
        """The next (earlier) made-up time: Takeout lists the newest record first. Steps are mostly
        minutes, sometimes hours, so sessions form and break, and every hour of the day comes up."""
        self.clock -= timedelta(minutes=self.rng.choice((2, 3, 5, 8, 13, 21)) if self.rng.random() < 0.8
                                else self.rng.randrange(60, 600))
        return self.clock.replace(second=self.rng.randrange(60))

    @staticmethod
    def zh_clock(t):
        """Hour and period word as the zh-TW Takeout writes them (12-hour clock)."""
        h = t.hour
        word = ("凌晨" if h < 5 else "清晨" if h < 6 else "上午" if h < 12 else "中午" if h == 12
                else "下午" if h < 18 else "晚上")
        return word, (h % 12 or 12)

    def zh_ts(self, m):
        a, y, mo, d, sp, period, h, mi, s, sp2, zone, b = m.groups()
        t = self.tick()
        word, hh = self.zh_clock(t)
        return f"{a}{t.year}年{t.month}月{t.day}日{sp}{word}{hh}:{t.minute:02d}:{t.second:02d}{sp2}{self.zone if zone else ''}{b}"

    def en_ts(self, m):
        a, mon, d, y, h, mi, s, sp, ap, sp2, zone, b = m.groups()
        t = self.tick()
        return (f"{a}{MONTHS[t.month - 1]} {t.day}, {t.year}, {t.hour % 12 or 12}:{t.minute:02d}:{t.second:02d}"
                f"{sp}{'AM' if t.hour < 12 else 'PM'}{sp2}{self.zone if zone else ''}{b}")

    def node(self, t):
        """One HTML text node of an activity record."""
        if t in KEEP or KEEP_WHOLE.match(t):
            return t
        m = TS_ZH.match(t)
        if m:
            return self.zh_ts(m)
        m = TS_EN.match(t)
        if m:
            return self.en_ts(m)
        m = re.match(r"^(.*) was used in this chat\.(\s*)$", t, re.S)
        if m:
            return self.words(m.group(1), 40) + " was used in this chat." + m.group(2)
        m = KEEP_PREFIX.match(t)
        if m:
            return t[:m.end()] + self.words(t[m.end():])
        return self.words(t, 120)

    def href(self, h):
        if h.startswith("https://myaccount.google.com/activitycontrols") or h == "https://gemini.google.com/gems/view":
            return h
        m = re.match(r"^https://gemini\.google\.com/app/([0-9a-f]+)$", h)
        if m:
            return "https://gemini.google.com/app/" + self.fake_id(m.group(1))
        if re.match(r"^https?://", h):
            return f"https://example.com/{self.counter()}"
        return f"file-{self.counter()}-{self.rng.getrandbits(64):016x}{ext_of(h)}"  # an upload's Takeout name

    def attr(self, m):
        name, value = m.group(1), m.group(2)
        if name in ("href", "src"):
            return f'{name}="{self.href(value)}"'
        if name == "class" and set(value.split()) <= CSS_CLASSES or name == "align" and value in ALIGN:
            return f'{name}="{value}"'
        return f'{name}="{self.words(value, 30)}"'

    def cell(self, c):
        c = re.sub(r'\s([a-zA-Z][\w:-]*)="([^"]*)"', lambda m: " " + self.attr(m), c)
        return re.sub(r">([^<>]+)<", lambda m: ">" + self.node(m.group(1)) + "<", c)


# ---- sampling: the items that cover the most features, then some more ----

def pick(items, features, want, rng, cost=len):
    chosen, covered = [], set()
    pool = sorted(range(len(items)), key=lambda i: cost(items[i]))
    for i in pool:
        new = features(items[i]) - covered
        if new:
            chosen.append(i)
            covered |= new
    rest = [i for i in pool[: max(len(pool) // 2, 1)] if i not in chosen]
    rng.shuffle(rest)
    chosen += rest[: max(want - len(chosen), 0)]
    return sorted(chosen), covered


def chatgpt_features(c):
    f, mp = set(), c.get("mapping") or {}
    kids = {}
    for nid, n in mp.items():
        kids.setdefault(n.get("parent"), []).append(nid)
        m = n.get("message")
        if not m:
            f.add("null-message")
            continue
        f.add("role:" + str((m.get("author") or {}).get("role")))
        ct = (m.get("content") or {}).get("content_type")
        f.add("content:" + str(ct))
        meta = m.get("metadata") or {}
        for k in ("attachments", "content_references", "is_visually_hidden_from_conversation"):
            if meta.get(k):
                f.add("meta:" + k)
        if any(not isinstance(p, str) for p in (m.get("content") or {}).get("parts") or []):
            f.add("non-text-part")
    if any(len(v) > 1 for k, v in kids.items() if k):
        f.add("branch")
    return f


def claude_features(c):
    f = set() if c.get("chat_messages") else {"empty"}
    for m in c.get("chat_messages") or []:
        f.add("sender:" + str(m.get("sender")))
        for part in m.get("content") or []:
            f.add("part:" + str(part.get("type")))
        if m.get("attachments"):
            f.add("attachments")
        if m.get("files"):
            f.add("files")
    return f


def record_kind(cell):
    body = cell.split("content-cell", 1)[1].split(">", 1)[1]
    first = (re.findall(r"([^<>]+)<", body) or [""])[0]
    m = KEEP_PREFIX.match(first)
    f = {"kind:" + (m.group(1) if m else first[:24])}
    zh = re.search(r"\d{4}年\d{1,2}月\d{1,2}日\s*(\S{2})\d", body)
    if zh:
        f.add("period:" + zh.group(1))
    zone = re.search(r":\d\d:\d\d\s*([A-Z]{2,5})\s*<br>", body)
    if zone:
        f.add("zone:" + zone.group(1))
    if '<a href="' in body.split("mdl-typography--caption")[0] and "file-" not in body:
        f.add("link")
    if "<img" in cell:
        f.add("img")
    if "was used in this chat" in cell:
        f.add("gem")
    return f


# ---- made-up additions for features the real export may lack ----

def add_synthetic_cells(cells, anon):
    """English-format and rare-period copies of anonymised prompt records."""
    prompts = [c for c in cells if "Prompted" in c and re.search(r"\d{4}年", c)][:12]
    out = []
    for i, c in enumerate(prompts):
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\S{2})(\d{1,2}):(\d\d):(\d\d)\s*([A-Z]{2,5})", c)
        if not m:
            continue
        y, mo, d, period, h, mi, s, zone = m.groups()
        t = anon.tick()
        if i < 6:  # the English form Takeout uses for an English-language account
            new = (f"{MONTHS[t.month - 1]} {t.day}, {t.year}, {t.hour % 12 or 12}:{t.minute:02d}:{t.second:02d}"
                   f"\u202f{'AM' if t.hour < 12 else 'PM'} {'PST' if i % 2 else 'PDT'}")
        else:  # period words this account never produced, with an hour each one is used for
            word, hour = [("早上", 7), ("傍晚", 6), ("深夜", 11), ("半夜", 1), ("午夜", 12), ("深夜", 1)][i - 6]
            new = f"{t.year}年{t.month}月{t.day}日 {word}{hour}:{t.minute:02d}:{t.second:02d} {zone}"
        out.append(c[: m.start()] + new + c[m.end():])
    return out


def synthetic_chatgpt(anon):
    """Made-up conversations for paths the real sample lacks: an edited prompt (a user turn on
    an abandoned branch), a hidden system message, a tool message with content.text, and a
    current_node that is not a leaf."""
    def node(nid, parent, role, text, t, children, hidden=False, ctype="text", as_text=False):
        content = {"content_type": ctype, "text": text} if as_text else {"content_type": ctype, "parts": [text]}
        meta = {"is_visually_hidden_from_conversation": True} if hidden else {}
        return nid, {"id": nid, "parent": parent, "children": children,
                     "message": {"id": nid, "author": {"role": role, "name": None}, "content": content,
                                 "create_time": t, "metadata": meta}}
    base, ids = 2051222400.0, [anon.fake_id("%032x" % (900 + i)) for i in range(8)]
    r, sysm, u1, a1, u1b, a1b, tool, u2 = ids
    nodes = dict([
        (r, {"id": r, "parent": None, "children": [sysm], "message": None}),
        node(sysm, r, "system", anon.words("x" * 40), base, [u1, u1b], hidden=True),
        node(u1, sysm, "user", anon.words("x" * 80), base + 10, [a1]),          # the first wording, later edited
        node(a1, u1, "assistant", anon.words("y" * 200), base + 20, []),
        node(u1b, sysm, "user", anon.words("x" * 90), base + 60, [a1b]),        # the edit the user kept
        node(a1b, u1b, "assistant", anon.words("y" * 200), base + 70, [tool]),
        node(tool, a1b, "tool", anon.words("z" * 60), base + 80, [u2], ctype="execution_output", as_text=True),
        node(u2, tool, "user", anon.words("x" * 50), base + 90, []),
    ])
    first = {"title": anon.words("t" * 30), "create_time": base, "update_time": base + 90, "mapping": nodes,
             "current_node": u2, "conversation_id": anon.fake_id("%032x" % 950), "id": anon.fake_id("%032x" % 950)}
    # The same shape, but current_node points mid-thread (the user went back up the branch)
    second = json.loads(json.dumps(first))
    second["conversation_id"] = second["id"] = anon.fake_id("%032x" % 951)
    second["current_node"], second["title"] = a1b, anon.words("t" * 30)
    return [first, second]


def synthetic_workspace(anon, n=2):
    """Made-up Gemini in Workspace files (Takeout "Conversation History"), one conversation each."""
    out = {}
    for i in range(n):
        turns = []
        for k in range(1 + i):
            turns.append({"user_turn": {"prompt": anon.words("x" * 70), "turn_last_modified": f"2031-02-0{3 + i}T1{k}:00:00Z"}})
            turns.append({"system_turn": {"text": [{"data": anon.words("y" * 150)}, {"data": anon.words("y" * 50)}]}})
        out[f"conversation-{i + 1}.json"] = {"conversation_turns": turns}
    return out


def zh_prefix_cells(cells, anon):
    """Copies of a prompt record in the fully localised forms 已提示 and 提示, each at a new time, so
    a parser that dropped them would lose records instead of falling back on the originals."""
    out = []
    for c, word in zip([c for c in cells if "Prompted\xa0" in c][:2], ("已提示\xa0", "提示： ")):
        c = c.replace("Prompted\xa0", word, 1)
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\S{2})(\d{1,2}):(\d\d):(\d\d)\s*([A-Z]{2,5})", c)
        if m:
            t = anon.tick()
            period, hh = anon.zh_clock(t)
            c = c[: m.start()] + f"{t.year}年{t.month}月{t.day}日 {period}{hh}:{t.minute:02d}:{t.second:02d} {m.group(8)}" + c[m.end():]
        out.append(c)
    return out


def synthetic_perplexity(anon, n=6):
    out = []
    for i in range(n):
        entries = [{"t": f"2031-0{1 + i % 9}-1{i % 9}T0{k}:00:00.000000", "q": anon.words("x" * 60),
                    "a": anon.words("y" * 300 + "\n" * 3), "att": [] if k else [f"file-{anon.counter()}.pdf"]}
                   for k in range(1 + i % 3)]
        out.append({"slug": anon.fake_id("%016x" % (i + 1)),
                    "title": anon.words("t" * 30), "space": anon.words("s" * 10) if i % 2 else "", "entries": entries})
    return out


# ---- the proof ----

def check_string(s, where):
    if s in KEEP or not s.strip() or PLACEHOLDER.match(s) or UUID.match(s) or HEXID.match(s) or ISO.match(s) or DAY.match(s):
        return
    if TS_ZH.match(s) or TS_EN.match(s):
        return
    rest = KEEP_PREFIX.sub("", s)
    rest = re.sub(r" was used in this chat\.\s*$", "", rest)
    if KEEP_WHOLE.match(rest) or rest in KNOWN_ENUMS and where.endswith(tuple(f".{k}" for k in ENUM_KEYS | {"author.name"})):
        return
    for w in re.findall(r"[A-Za-z]+|[\u4e00-\u9fff]", rest):
        if w not in VOCAB:
            raise AssertionError(f"{where}: {w!r} is not a made-up word")


def check_json(o, where="$"):
    if isinstance(o, dict):
        for k, v in o.items():
            if not (k in SCHEMA_KEYS or KEY_PLACEHOLDER.match(k) or UUID.match(k) or HEXID.match(k)):
                raise AssertionError(f"{where}: key {k!r} is neither a schema key, a placeholder nor an id")
            check_json(v, f"{where}.{k}")
    elif isinstance(o, list):
        for v in o:
            check_json(v, where + "[]")
    elif isinstance(o, str):
        check_string(o, where)


def check_html(text, where):
    body = text[text.find('<div class="outer-cell'):] if '<div class="outer-cell' in text else text
    head = text[: len(text) - len(body)]
    skeleton = re.sub(r"<style[^>]*>.*?</style>", "<style></style>", head, flags=re.S)
    if skeleton not in ('<html><head><title>我的活動記錄</title><style></style></head><body><div class="mdl-grid">',
                        '<html><head><title>My Activity</title><style></style></head><body><div class="mdl-grid">'):
        raise AssertionError(f"{where}: the page header holds more than the title and the stylesheet")
    for attr, v in re.findall(r'\s([a-zA-Z][\w:-]*)="([^"]*)"', body):
        if attr in ("href", "src"):
            if not PLACEHOLDER.match(v):
                raise AssertionError(f"{where}: {attr} {v!r} is not a placeholder")
        elif attr == "class":
            if not set(v.split()) <= CSS_CLASSES:
                raise AssertionError(f"{where}: class {v!r} is not a known class")
        elif attr == "align":
            if v not in ALIGN:
                raise AssertionError(f"{where}: align {v!r}")
        else:
            check_string(v, f"{where} {attr}")
    for t in re.findall(r">([^<>]+)<", body):
        check_string(t, where)


def check(folder):
    """Raise unless every fixture under folder holds only kept labels, placeholders and made-up words."""
    for root, _, names in os.walk(folder):
        for n in names:
            p = os.path.join(root, n)
            if UPLOAD.search(n):
                continue  # a made-up upload; check_uploads() vouches for its bytes
            if n.endswith(".json"):
                check_json(read_json(p), p)
            elif n.endswith(".html"):
                check_html(read_text(p), p)
            else:
                raise AssertionError(f"{p}: unexpected fixture file")
    check_uploads(folder)


def tokens(s):
    return {w.lower() for w in re.findall(r"[A-Za-z]{3,}", s)} | set(re.findall(r"[\u4e00-\u9fff]{2,}", s))


def made_up_shape(s):
    """An id or a placeholder: random or fixed by construction, never text."""
    return bool(UUID.match(s) or HEXID.match(s) or PLACEHOLDER.match(s) or KEY_PLACEHOLDER.match(s))


def json_tokens(o, out, skip_ids=False):
    if isinstance(o, dict):
        for k, v in o.items():
            if not (skip_ids and made_up_shape(k)):
                out |= tokens(k)
            json_tokens(v, out, skip_ids)
    elif isinstance(o, list):
        for v in o:
            json_tokens(v, out, skip_ids)
    elif isinstance(o, str) and not (skip_ids and made_up_shape(o)):
        out |= tokens(o)
    return out


def html_tokens(text, out, skip_ids=False):
    body = text[text.find('<div class="outer-cell'):]
    for t in re.findall(r">([^<>]+)<", body) + re.findall(r'="([^"]*)"', body):
        if not (skip_ids and made_up_shape(t)):
            out |= tokens(t)
    return out


def crosscheck(source, folder):
    """Rule-free proof: a word of the source found in the output's text must be a schema key, a
    kept label, a known enum value or a made-up word. Ids and placeholders are left out of the
    output's words: they are random or fixed by construction, so a hex run in one is no leak."""
    out = set()
    for root, _, names in os.walk(folder):
        for n in names:
            p = os.path.join(root, n)
            if n.endswith(".json"):
                json_tokens(read_json(p), out, skip_ids=True)
            elif n.endswith(".html") and not UPLOAD.search(n):
                html_tokens(read_text(p), out, skip_ids=True)
    allowed = {w.lower() for w in VOCAB_EN} | set(VOCAB_ZH)
    for k in SCHEMA_KEYS | KEEP | KNOWN_ENUMS | CSS_CLASSES | ALIGN:
        allowed |= tokens(k)
    allowed |= tokens("Prompted Branched Created Gemini Canvas titled Used Apps Gave feedback Good Bad response "
                      "Unspecified Selected preferred draft Assistant feature Cleared previous Attached file files "
                      "was used in this chat https example com gemini google myaccount activitycontrols gems view "
                      "app key client-created-root " + " ".join(PAGE_ZONES) + " "
                      " 已提示 提示 凌晨 清晨 早上 上午 中午 下午 傍晚 晚上 深夜 半夜 午夜 " + " ".join(MONTHS))
    shared = (source & out) - allowed
    if shared:
        raise AssertionError(f"words of the real export left in the fixtures: {sorted(shared)[:40]}")


def check_uploads(folder):
    for root, _, names in os.walk(folder):
        for n in names:
            if UPLOAD.search(n):
                with open(os.path.join(root, n), "rb") as f:
                    data = f.read()
                if n.endswith(".zip"):
                    with zipfile.ZipFile(os.path.join(root, n)) as z:
                        for i in z.infolist():
                            check_json(json.loads(z.read(i)), f"{n}!{i.filename}")
                elif data not in (b"made-up upload\n",):
                    raise AssertionError(f"{n}: an upload fixture must be made up")


# ---- main ----

def read_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def read_text(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def dump(obj, *parts, indent=1):
    p = os.path.join(*parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)


def is_fixture_dir(path):
    """True for a folder an earlier run wrote: it holds only what check() accepts."""
    try:
        check(path)
        return True
    except (AssertionError, ValueError, OSError, zipfile.BadZipFile):
        return False


CHATGPT_FILE = re.compile(r"^conversations(-\d+)?\.json$")


def load_chatgpt(path):
    """The export as downloaded (a .zip), its folder at any depth, or one conversations*.json."""
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            names = sorted(n for n in z.namelist() if CHATGPT_FILE.match(n.rsplit("/", 1)[-1]))
            if not names:
                sys.exit(f"no conversations*.json in {path}")
            return [c for n in names for c in json.loads(z.read(n))]
    if not os.path.isdir(path):
        return read_json(path)
    files = sorted(os.path.join(r, n) for r, _, ns in os.walk(path) for n in ns if CHATGPT_FILE.match(n))
    if not files:
        sys.exit(f"no conversations*.json under {path}")
    return [c for f in files for c in read_json(f)]


def load_claude(path):
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.rsplit("/", 1)[-1] == "conversations.json"]
            if len(names) != 1:
                sys.exit(f"expected one conversations.json in {path}, found {len(names)}")
            return json.loads(z.read(names[0]))
    if os.path.isdir(path):
        files = [os.path.join(r, "conversations.json") for r, _, ns in os.walk(path) if "conversations.json" in ns]
        if len(files) != 1:
            sys.exit(f"expected one conversations.json under {path}, found {len(files)}")
        path = files[0]
    return read_json(path)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chatgpt")
    ap.add_argument("--claude")
    ap.add_argument("--gemini-apps")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=452,
                    help="picks which conversations are kept; ids, words and time shifts come from the OS")
    ap.add_argument("--want", type=int, default=30, help="conversations per platform, at least")
    ap.add_argument("--madeup", action="store_true",
                    help="add made-up cases the real exports may lack: a Perplexity capture, Gemini in Workspace files, "
                         "ChatGPT edits, hidden and tool messages, zh-prefixed prompts (the repo's own fixtures have them; "
                         "an upstream sample does not need them)")
    a = ap.parse_args()
    final = os.path.abspath(a.out)
    if os.path.exists(final) and os.listdir(final) and not is_fixture_dir(final):
        sys.exit(f"{final} is not empty and is not a fixture folder; pick an empty or new folder")
    # Built and checked in the system's temp folder, never inside the repo, so an interrupted run
    # cannot leave unchecked files where `git add` would find them
    a.out = tempfile.mkdtemp(prefix="make_fixtures-")
    try:
        build(a)
        if os.path.isdir(final):  # a platform this run did not build keeps its current fixtures
            for name in os.listdir(final):
                if not os.path.exists(os.path.join(a.out, name)):
                    shutil.copytree(os.path.join(final, name), os.path.join(a.out, name))
        check(a.out)
        install(a.out, final)
    finally:
        shutil.rmtree(a.out, ignore_errors=True)
    print("checks passed:", final)


def install(checked, final):
    """Copy the checked fixtures beside final, then swap: the old fixtures are removed only once the
    new ones are in place, and are put back if the swap fails."""
    parent = os.path.dirname(final)
    os.makedirs(parent, exist_ok=True)
    # Fresh names nobody else uses (.gitignore ignores .make_fixtures-*), so no existing folder is touched
    tag = uuid.uuid4().hex[:12]
    incoming = os.path.join(parent, f".make_fixtures-incoming-{tag}")
    old = os.path.join(parent, f".make_fixtures-old-{tag}")
    moved_old = swapped = False
    try:
        shutil.copytree(checked, incoming)  # already checked, so safe to have beside --out for a moment
        if os.path.exists(final):
            replace(final, old)
            moved_old = True
        replace(incoming, final)
        swapped = True
    except BaseException:
        if moved_old and not os.path.exists(final):
            try:
                replace(old, final)
            except OSError:
                print(f"could not put the old fixtures back; they are in {old}", file=sys.stderr)
        raise
    finally:
        shutil.rmtree(incoming, ignore_errors=True)
        if swapped and moved_old:  # the old copy goes only once the new one is in place
            shutil.rmtree(old, ignore_errors=True)


replace = os.replace  # install()'s one way to move a folder, so a test can make it fail


def iso_plus(s, delta):
    """An ISO time from the output plus delta, written in the same form."""
    y, mo, d, h, mi, sec, frac, zone = ISO.match(s).groups()
    t = datetime(int(y), int(mo), int(d), int(h), int(mi), int(sec), int((frac or ".0")[1:7].ljust(6, "0"))) + delta
    return t.strftime("%Y-%m-%dT%H:%M:%S") + ("." + f"{t.microsecond:06d}"[: len(frac) - 1] if frac else "") + (zone or "")


def chatgpt_times(c):
    return [n["message"]["create_time"] for n in (c.get("mapping") or {}).values()
            if n.get("message") and isinstance(n["message"].get("create_time"), (int, float))]


def claude_times(c):
    return [m["created_at"] for m in c.get("chat_messages") or [] if ISO.match(m.get("created_at") or "")]


def build(a):
    anon, rng = Anon(), random.Random(a.seed)
    report, source = {}, set()

    def each(items, update_key, message_times):
        out = []
        for c in items:
            anon.new_item()
            c = anon.json(c)
            # The real gap from creation to the last update would survive the shift, and gaps that
            # cluster can line conversations up again: the update is a few minutes after the last message
            times = message_times(c)
            if c.get(update_key) is not None and times:
                last = max(times)
                later = timedelta(seconds=anon.rng.uniform(1, 600))
                c[update_key] = last + later.total_seconds() if isinstance(last, (int, float)) else iso_plus(last, later)
            out.append(c)
        anon.shift = None  # the last conversation's shift must not reach anything built after it
        anon.rng.shuffle(out)  # the export's own order follows the real dates
        return out

    if a.chatgpt:
        data = load_chatgpt(a.chatgpt)
        small = [c for c in data if len(c.get("mapping") or {}) <= 80]
        idx, cov = pick(small, chatgpt_features, a.want, rng, cost=lambda c: len(c.get("mapping") or {}))
        json_tokens(data, source)
        out = each((small[i] for i in idx), "update_time", chatgpt_times)
        if a.madeup:
            out += synthetic_chatgpt(anon)
        half = len(out) // 2  # two files, as a large export arrives
        for k, part in enumerate((out[:half], out[half:])):
            dump(part, a.out, "chatgpt", f"conversations-{k:03d}.json")
        dump([{"id": anon.fake_id("0" * 32), "conversation_id": out[0]["conversation_id"], "title": anon.words("x" * 20)}],
             a.out, "chatgpt", "shared_conversations.json", indent=None)
        report["chatgpt"] = (len(out), sorted(cov))

    if a.claude:
        data = load_claude(a.claude)
        empty = [c for c in data if not c.get("chat_messages")][:3]  # a few: the parser must skip them
        small = empty + [c for c in data if 0 < len(c.get("chat_messages") or []) <= 40]
        idx, cov = pick(small, claude_features, a.want, rng, cost=lambda c: len(json.dumps(c)))
        json_tokens(data, source)
        out = each((small[i] for i in idx), "updated_at", claude_times)
        dump(out, a.out, "claude", "conversations.json")
        report["claude"] = (len(out), sorted(cov))

    if a.gemini_apps:
        page_path = a.gemini_apps
        if os.path.isdir(page_path):  # a Takeout folder: its one Gemini Apps page, never an upload
            pages = [os.path.join(r, n) for r, _, ns in os.walk(page_path) for n in ns
                     if n.endswith(".html") and not UPLOAD.search(n) and os.path.basename(r).lower() == "gemini apps"]
            if len(pages) != 1:
                sys.exit(f"expected one Gemini Apps activity page under {page_path}, found {len(pages)}")
            page_path = pages[0]
        if UPLOAD.search(os.path.basename(page_path)):
            sys.exit("that is a Takeout upload, not the activity page")
        text = open(page_path, encoding="utf-8").read()
        html_tokens(text, source)
        start = text.index('<div class="outer-cell')
        head, cells = text[:start], text[start:].split('<div class="outer-cell')[1:]
        tail = cells[-1][cells[-1].rindex("</div></div></div>") + len("</div></div></div>"):]
        cells[-1] = cells[-1][: len(cells[-1]) - len(tail)]
        kinds = [record_kind(c) for c in cells]
        chosen, cov = set(), set()
        for i, f in sorted(enumerate(kinds), key=lambda x: len(cells[x[0]])):
            if f - cov:
                chosen.add(i)
                cov |= f
        for _ in range(8):  # runs of consecutive records, so sessions form as they do in real use
            s = rng.randrange(0, max(len(cells) - 20, 1))
            chosen |= set(range(s, min(s + 20, len(cells))))
        kept = [anon.cell(cells[i]) for i in sorted(chosen)]
        extra = add_synthetic_cells(kept, anon) + (zh_prefix_cells(kept, anon) if a.madeup else [])
        head = re.sub(r"<title>[^<]*</title>", "<title>我的活動記錄</title>", head)
        folder = os.path.join(a.out, "takeout", "Takeout", "我的活動", "Gemini Apps")
        os.makedirs(folder, exist_ok=True)
        page = head + "".join('<div class="outer-cell' + c for c in kept + extra) + tail
        with open(os.path.join(folder, "我的活動.html"), "w", encoding="utf-8", newline="") as f:
            f.write(page)
        linked = sorted(set(re.findall(r'(?:href|src)="(file-\d+-[0-9a-f]{16}\.[a-z0-9]+)"', page)))
        for n in linked[:6]:  # made-up uploads beside the page, which the parser must skip unread
            with open(os.path.join(folder, n), "wb") as f:
                f.write(b"made-up upload\n")
        trap = os.path.join(folder, f"file-{anon.counter()}-{anon.rng.getrandbits(64):016x}.zip")
        anon.shift = timedelta(0)  # made-up times, kept as written: a shift here would give one away
        with zipfile.ZipFile(trap, "w") as z:  # an upload that looks like an export: never to be read
            z.writestr(zipfile.ZipInfo("conversations.json", (2030, 1, 1, 0, 0, 0)), json.dumps(anon.json([{
                "uuid": "a" * 32, "name": "trap", "created_at": "2030-01-01T00:00:00Z", "updated_at": "2030-01-01T00:00:00Z",
                "chat_messages": [{"uuid": "b" * 32, "sender": "human", "text": "trap", "created_at": "2030-01-01T00:00:00Z",
                                   "content": [], "attachments": [], "files": []}]}])))
        anon.shift = None
        report["gemini-apps"] = (len(kept), sorted(cov), f"+{len(extra)} made-up")

    if a.madeup:
        for name, data in synthetic_workspace(anon).items():
            dump(data, a.out, "workspace", "Takeout", "Gemini", "Conversation History", name)
        dump(synthetic_perplexity(anon), a.out, "perplexity", "perplexity-capture-madeup.json")
    check(a.out)
    crosscheck(source, a.out)
    for k, v in report.items():
        print(k, v)
    if anon.unknown:
        print("identifier-like values not in KNOWN_ENUMS, replaced (add one only after a look):", sorted(anon.unknown))
    if anon.keys:
        print("keys outside SCHEMA_KEYS, replaced:", sorted(anon.keys.values()))


if __name__ == "__main__":
    main()
