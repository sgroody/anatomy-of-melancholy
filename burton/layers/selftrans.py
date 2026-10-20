"""`burton selftrans`: self-translation signals per foreign passage -> data/layers/selftrans/<unit>.json.

Signals only (SPEC §6.2); verdicts come from the M5 translation pass. Rules, no model. For each passage:

* Gowland's bracket: `none`, `present`, or `short` (much shorter than the passage). Only its presence and
  its word count are used; its text never enters the layer (CLAUDE.md rule 5).
* Candidate spans of Burton's own English, each a text-quote selector into the public text of the
  nearest element with an id (paragraph, sidenote, verse group, or the unit):
  * `following`: the next clause, or the next sentence when the passage ends one. A short attribution
    in between ("saith Seneca,") is stepped over;
  * `preceding`: the clause before the passage, unless it is only an attribution;
  * `note-anchor`: for a passage in a sidenote, the clause the note's anchor precedes in the main text;
  * `verse-following`: Burton's own English verse group (`lg[@type=translation-block]`) after a verse.

  A prose span needs lowercase words and must not be Latin or a citation by the language rules. Each span
  also records its cognates with the passage (`infinita`/`infinite`) and any gloss cue ("that is").

Candidate text comes from `public_text`, so Gowland's marked matter cannot reach it. A few of his brackets
were not separated by ingest and remain as plain `[…]` text; a candidate whose selector touches one is
dropped and counted. Every selector is checked to match exactly once before it is written; one that cannot
be made unique is dropped and counted.
"""

import copy
import json
import re
from collections import Counter

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..ingest import langid
from ..ingest.epub import all_units
from ..tei import ED, XML_ID, XML_LANG, T, public_id
from ..textview import public_text
from ..translate.packets import sha1

METHOD = "rules/selftrans-v1"
SHORT_RATIO = 0.8  # bracket words < 0.8 x passage words (the book's median ratio is about 1.5)
SHORT_MIN_WORDS = 4  # only passages of 4+ words are judged "short-bracketed"
MAX_WORDS = 40  # a candidate span is cut at this many words
CONTEXT = 32  # prefix/suffix length, extended up to CONTEXT_MAX until the selector is unique
CONTEXT_MAX = 160
SENTINEL = 0xF0000  # private-use code points: mark n opens (2n) or closes (2n+1) a passage, or is a note anchor
NO_COGNATES = ("grc", "he", "ar")

WORD = re.compile(r"[^\W\d_]+(?:[’'][^\W\d_]+)*")
LOWER_WORD = re.compile(r"(?<![\w’'])[a-z]+(?:[’'][a-z]+)*(?![\w’'])")
# a short clause that only says who is quoted: "saith Seneca", "as the Poet hath it", "quoth he"
ATTRIBUTION = re.compile(r"\b(?:saith|says|say|said|sayeth|quoth|writes|wrote|hath it|have it|observes|"
                         r"tells us|inquit|ait|as (?:he|she|one|they|the [a-z]+)|in [A-Z][a-z]+)\b")
ATTRIBUTION_MAX_WORDS = 8
CUE = re.compile(r"^(?:that is|i\.e\.|id est|to wit|as much as to say|which is|or as)(?!\w)", re.I)
# a stop that is not a sentence end: initials and common locators ("&c." before a capital is one)
ABBREV = re.compile(r"(?:(?<![&\w])[A-Za-z]|\bviz|\bcap|\blib|\bfol|\btom|\bSt|\bMr|\bDr|\bvid|\bib|\bibid|"
                    r"\bsect|\bmemb|\bsubs|\bpart|\bi\.e|\be\.g)\.$")
LEAD = re.compile(r"[\s,;:.?!)\]—–-]*")  # punctuation between a passage and the English after it


def _container(e):
    """The nearest ancestor with an id that is not a foreign passage: paragraph, sidenote, verse group or unit."""
    return next(a for a in e.iterancestors() if a.get(XML_ID) and not _foreign(a))


def _nested(e) -> bool:
    """Is e inside another foreign passage (within its own note, if it is in one)?"""
    for a in e.iterancestors():
        if a.tag == T("note"):
            return False
        if _foreign(a):
            return True
    return False


def _view(container) -> str:
    return public_text(container, notes=container.tag == T("note"))


def _foreign(e) -> bool:
    return isinstance(e.tag, str) and e.get("ana") == "foreign"


def spans_in(container) -> tuple[str, dict[str, tuple[int, int]], dict[str, int]] | None:
    """The container's public text, the (start, end) of every foreign passage in it, and the position of
    every sidenote anchor in it (the note itself is not part of a paragraph's text).

    Found by rendering a copy with sentinels at those points and aligning that text with the plain view
    (they differ only in spaces next to the sentinels). None if the alignment fails."""
    plain = _view(container)
    if any(ord(ch) >= SENTINEL for ch in plain):
        return None
    marked_copy = copy.deepcopy(container)
    ids: list[tuple[str, str]] = []  # sentinel n names ids[n]: passages in a dropped note never reach the view
    for f in marked_copy.iter():
        if f is marked_copy:
            continue
        if f.tag == T("note"):
            ids.append(("note", f.get(XML_ID)))
            f.tail = chr(SENTINEL + 2 * len(ids) - 2) + (f.tail or "")  # just after the anchor
        elif _foreign(f):
            ids.append(("foreign", f.get(XML_ID)))
            n = len(ids) - 1
            f.text = chr(SENTINEL + 2 * n) + (f.text or "")
            last = f[-1] if len(f) else None
            if last is None:
                f.text += chr(SENTINEL + 2 * n + 1)
            else:
                last.tail = (last.tail or "") + chr(SENTINEL + 2 * n + 1)
    marked = _view(marked_copy)
    spans: dict[str, tuple[int, int]] = {}
    anchors: dict[str, int] = {}
    starts: dict[int, int] = {}
    j = 0
    for ch in marked:
        if ord(ch) >= SENTINEL:
            n, closing = divmod(ord(ch) - SENTINEL, 2)
            kind, xid = ids[n]
            if closing:
                spans[public_id(xid)] = (starts.pop(n), j)
            elif kind == "note":
                anchors[public_id(xid)] = j
            else:
                starts[n] = j
        elif j < len(plain) and ch == plain[j]:
            j += 1
        elif ch == " ":
            continue  # a space the plain view collapsed or dropped
        else:
            return None
    if j != len(plain) or starts:
        return None
    # a sentinel can sit outside a space the plain view trimmed: tighten each span to its text
    for k, (s, e) in spans.items():
        while s < e and plain[s] == " ":
            s += 1
        while e > s and plain[e - 1] == " ":
            e -= 1
        spans[k] = (s, e)
    return plain, spans, anchors


def _sentence_end(text: str, i: int) -> bool:
    """Is text[i] ('.', '?' or '!') the end of a sentence?"""
    if text[i] in "?!":
        return True
    rest = text[i + 1:].lstrip()
    if rest and not (rest[0].isupper() or rest[0] in "“‘\"'("):
        return False
    return not ABBREV.search(text[max(0, i - 8):i + 1])


def _clause_end(text: str, start: int, stop: int) -> int:
    for i in range(start, stop):
        if text[i] in ";:?!" or (text[i] == "." and _sentence_end(text, i)):
            return i
    return stop


def _clause_start(text: str, end: int, floor: int) -> int:
    for i in range(end - 1, floor - 1, -1):
        if text[i] in ";:?!" or (text[i] == "." and _sentence_end(text, i)):
            return i + 1
    return floor


def _cap_words(text: str, s: int, e: int, keep: str) -> tuple[int, int]:
    """Cut [s, e) to MAX_WORDS words, keeping its start ('head') or its end ('tail')."""
    words = list(re.finditer(r"\S+", text[s:e]))
    if len(words) <= MAX_WORDS:
        return s, e
    if keep == "head":
        return s, s + words[MAX_WORDS - 1].end()
    return s + words[-MAX_WORDS].start(), e


def _trim(text: str, s: int, e: int) -> tuple[int, int]:
    while s < e and text[s] in " ,;:(—–-":
        s += 1
    while e > s and text[e - 1] in " ,;:(—–-":
        e -= 1
    if e > s and text[e - 1] == "." and not text[s:e].endswith("&c."):
        e -= 1
    return s, e


def _english(span: str, minimum: int) -> bool:
    """Enough lowercase words, and not untagged Latin or a citation by the language rules
    ("Mille mei Siculis errant in", "Plin. lib. 7 cap. 31")."""
    if len(LOWER_WORD.findall(span)) < minimum:
        return False
    body = CUE.sub("", span).lstrip(" ,")  # "i.e." is Latin evidence to the rules; the words after it are not
    return langid.classify(body or span, False)[0] not in ("la", "citation")


def _attribution(span: str) -> bool:
    return len(WORD.findall(span)) <= ATTRIBUTION_MAX_WORDS and bool(ATTRIBUTION.search(span))


def following(text: str, fe: int, stop: int) -> dict | None:
    """The clause (or next sentence) after a passage ending at fe; `stop` is where the next passage starts."""
    i = LEAD.match(text, fe, stop).end()
    ended = any(text[k] in ".?!" and _sentence_end(text, k) for k in range(max(0, fe - 1), i))
    relation = "sentence" if ended else "clause"
    after_attribution = False
    end = _clause_end(text, i, stop)
    comma = text.find(",", i, end)
    first_end = comma if comma > i else end
    if first_end > i and _attribution(text[i:first_end]):  # "*Latin*, saith Seneca, his English"
        i = LEAD.match(text, first_end, stop).end()
        after_attribution = True
    end = _clause_end(text, i, stop)
    if text.startswith("&c.", end - 2):
        end += 1  # keep the stop of a closing "&c."
    s, e = _trim(text, *_cap_words(text, i, end, "head"))
    if not _english(text[s:e], 2):
        return None
    return {"position": "following", "span": (s, e), "relation": relation, "after_attribution": after_attribution}


def preceding(text: str, fs: int, floor: int) -> dict | None:
    """The clause before a passage starting at fs; `floor` is where the previous passage ends."""
    s = _clause_start(text, fs, floor)
    s, e = _trim(text, *_cap_words(text, s, fs, "tail"))
    span = text[s:e]
    if not _english(span, 3) or _attribution(span):
        return None
    return {"position": "preceding", "span": (s, e)}


def selector(text: str, s: int, e: int, in_id: str) -> dict | None:
    """A text-quote selector for text[s:e] that matches exactly once in `text`, or None."""
    n = CONTEXT
    while True:
        prefix, suffix = text[max(0, s - n):s], text[e:e + n]
        if text.count(prefix + text[s:e] + suffix) == 1:
            return {"in": in_id, "exact": text[s:e], "prefix": prefix, "suffix": suffix}
        if n >= CONTEXT_MAX or (s - n <= 0 and e + n >= len(text)):
            return None
        n *= 2


def unseparated(text: str) -> list[tuple[int, int]]:
    """Regions of `[…]` and `{…}` left in a public view. Burton uses neither, so they are Gowland's matter that
    ingest did not separate; an unclosed one runs to the end, a stray close from the start."""
    out, stack = [], []
    for i, ch in enumerate(text):
        if ch in "[{":
            stack.append(i)
        elif ch in "]}":
            out.append((stack.pop() if stack else 0, i + 1))
    out += [(s, len(text)) for s in stack]
    return out


def _gowland_overlap(regions: list[tuple[int, int]], a: int, b: int) -> bool:
    return any(s < b and a < e for s, e in regions)


def _norm(w: str) -> str:
    return w.lower().replace("æ", "e").replace("œ", "e").replace("ae", "e").replace("oe", "e").replace("j", "i")


def cognates(foreign: str, english: str) -> int:
    """Words of the passage (5+ letters) that share their first five letters with a word of the span:
    `infinita`/`infinite`, `melancholia`/`melancholy`."""
    stems = {_norm(w)[:5] for w in WORD.findall(english) if len(w) >= 5}
    return len({w.lower() for w in WORD.findall(foreign) if len(w) >= 5 and _norm(w)[:5] in stems})


def bracket(e, trans_words: dict[str, int]) -> str:
    """Only the presence and the word count of Gowland's bracket are used, never its text."""
    if e.get(XML_ID) not in trans_words:
        return "none"
    n = len(WORD.findall(public_text(e)))
    if n >= SHORT_MIN_WORDS and trans_words[e.get(XML_ID)] < SHORT_RATIO * n:
        return "short"
    return "present"


def _verse_group(e):
    """The verse group a passage is (or sits in), if any."""
    if e.tag == T("lg"):
        return e
    return next((a for a in e.iterancestors() if a.tag == T("lg")), None)


def verse_following(lg) -> object | None:
    """Burton's English verse group after a verse, stepping over Gowland's verse translation and further
    foreign stanzas."""
    x = lg.getnext()
    while x is not None and (x.tag == ED("verse-trans") or (x.tag == T("lg") and _foreign(x))):
        x = x.getnext()
    if x is not None and x.tag == T("lg") and x.get("type") == "translation-block" and x.get(XML_ID):
        return x
    return None


def unit_records(root, stats: Counter) -> dict:
    div = root.find(f".//{T('div')}")
    if div is None or div.get("resp") == "#gowland":
        return {}
    trans_words: dict[str, int] = Counter()
    for t in root.iter(ED("trans"), ED("verse-trans")):
        if t.get("for"):
            trans_words[t.get("for")] += len(WORD.findall("".join(t.itertext())))
    views: dict = {}
    regions: dict[str, list[tuple[int, int]]] = {}

    def view(container):
        key = container.get(XML_ID)
        if key not in views:
            views[key] = spans_in(container)
        return views[key]

    records = {}
    for e in div.iter():
        if not _foreign(e):
            continue
        pid = public_id(e.get(XML_ID))
        text = public_text(e)
        note = next((a for a in e.iterancestors() if a.tag == T("note")), None)
        lg = _verse_group(e)
        location = "sidenote" if note is not None else "verse" if lg is not None else "text"
        rec = {"by": "rules", "method": METHOD, "lang": e.get(XML_LANG), "location": location,
               "text_sha1": sha1(text), "bracket": bracket(e, trans_words), "candidates": []}
        stats["passages"] += 1
        stats[f"bracket-{rec['bracket']}"] += 1
        found = []  # (candidate, container text, container id)
        inline = e.tag == T("foreign") and e.getparent().tag != T("div")
        if inline and _nested(e):
            inline = False  # inside a longer passage: Burton's English, if any, renders that one
            stats["nested-in-passage"] += 1
        if inline:
            container = _container(e)
            v = view(container)
            if v is None or pid not in v[1]:
                stats["container-text-unaligned"] += 1
            else:
                ctext, spans, _ = v
                fs, fe = spans[pid]
                nxt = min((s for s, _ in spans.values() if s >= fe), default=len(ctext))
                prv = max((x for _, x in spans.values() if x <= fs), default=0)
                in_id = public_id(container.get(XML_ID))
                found += [(c, ctext, in_id) for c in (following(ctext, fe, nxt), preceding(ctext, fs, prv)) if c]
        if inline and note is not None:
            # Latin in a sidenote is often rendered by the words the note's anchor precedes
            outer = _container(note)
            v = view(outer)
            nid = public_id(note.get(XML_ID))
            if v is None or nid not in v[2]:
                stats["container-text-unaligned"] += 1
            else:
                otext, ospans, anchors = v
                at = anchors[nid]
                nxt = min((s for s, _ in ospans.values() if s >= at), default=len(otext))
                c = following(otext, at, nxt)
                if c:
                    c["position"] = "note-anchor"
                    found.append((c, otext, public_id(outer.get(XML_ID))))
        cands = []
        for c, ctext, in_id in found:
            s, x = c.pop("span")
            sel = selector(ctext, s, x, in_id)
            if sel is None:
                stats["selector-not-unique"] += 1
                continue
            if in_id not in regions:
                regions[in_id] = unseparated(ctext)
            if _gowland_overlap(regions[in_id], s - len(sel["prefix"]), x + len(sel["suffix"])):
                stats["skipped-unseparated-gowland"] += 1  # never copy Gowland's text, even unmarked
                continue
            c["selector"] = sel
            cands.append(c)
        if lg is not None and note is None and lg.get("type") != "translation-block":
            tb = verse_following(lg)
            ttext = public_text(tb) if tb is not None else ""
            if tb is not None and unseparated(ttext):
                stats["skipped-unseparated-gowland"] += 1  # a bracketed "translation block" is Gowland's
            elif tb is not None:
                cands.append({"position": "verse-following",
                              "selector": {"in": public_id(tb.get(XML_ID)), "exact": ttext,
                                           "prefix": "", "suffix": ""}})
        for c in cands:
            c["by"] = "rules"
            c["words"] = len(WORD.findall(c["selector"]["exact"]))
            c["cognates"] = 0 if rec["lang"] in NO_COGNATES else cognates(text, c["selector"]["exact"])
            if c["position"] in ("following", "note-anchor"):
                m = CUE.match(c["selector"]["exact"])
                c["cue"] = m.group().lower() if m else None
            stats[f"candidate-{c['position']}"] += 1
        rec["candidates"] = cands
        rec["signals"] = signals(rec)
        for s in rec["signals"]:
            stats[f"signal:{s}"] += 1
        records[pid] = rec
    return records


def signals(rec: dict) -> list[str]:
    out = {"none": ["no-gowland-bracket"], "short": ["short-gowland-bracket"], "present": []}[rec["bracket"]]
    positions = {c["position"] for c in rec["candidates"]}
    out += [{"following": "english-follows", "preceding": "english-precedes", "note-anchor": "english-at-anchor",
             "verse-following": "burton-verse-follows"}[p] for p in positions]
    if any(c.get("cue") for c in rec["candidates"]):
        out.append("gloss-cue")
    if any(c["cognates"] for c in rec["candidates"]):
        out.append("cognate-overlap")
    return sorted(out)


def build(units: list[str] | None = None) -> Counter:
    stats: Counter = Counter()
    for unit in units or all_units():
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        records = unit_records(root, stats)
        out = paths.LAYERS / "selftrans" / f"{unit}.json"
        atomic_write_text(out, json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        stats["units"] += 1
    return stats
