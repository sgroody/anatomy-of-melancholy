"""Dell & Jordan-Smith (1927) alignment (SPEC §6.3), `burton align-djs`.

Dell & Jordan-Smith printed an "All-English" Anatomy: they replaced Burton's Latin with English inside his
text. So the English *between* the stretches of Burton's English that surround a foreign passage is their
rendering of it. For each passage, the last words of Burton's English before it and the first words after it
are located in the OCR text (word-trigram voting, then rapidfuzz on the candidate windows), and the text
between the two anchors becomes the candidate.

Statuses:
  aligned   both anchors score >= THRESHOLD and in order; the words between them are the candidate
  omitted   both anchors found, nothing between them: Dell & Jordan-Smith dropped the foreign words
            (usually because Burton renders them himself)
  below-threshold / not-found / no-anchor
            no candidate is kept (SPEC: below-threshold candidates are never shown)

The OCR text is public domain in the USA; it lives in data/source/djs/ (gitignored, hashes in DJS.lock).
Nothing here reads Gowland's matter: anchors come from `public_text`.
"""

import json
import re
from bisect import bisect_right
from collections import Counter
from functools import lru_cache

from rapidfuzz import fuzz

from .. import paths
from ..fsutil import atomic_write_text

DJS_TXT = paths.ROOT / "data" / "source" / "djs" / "anatomyofmelanch1927burt_djvu.txt"
WHERE = "IA anatomyofmelanch1927burt"
THRESHOLD = 0.85
ANCHOR_WORDS = 12
MIN_ANCHOR = 4
COMMON = 300  # trigrams seen more often than this carry no position information
LAYER = paths.LAYERS / "djs"


def kw(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("&", "and"))


CHUNK = re.compile(r"(?:[^\n]|\n(?![ \t]*\n))+")  # blocks of the OCR text, separated by blank lines
PAGE_NO = re.compile(r"^(\d{1,4})\s*\]|\[\s*(\d{1,4})\s*$")


def _is_furniture(c: str) -> bool:
    """A page number, a running head ("132 ] Anatomy of Melancholy [Part. 1, Sect. 1",
    "Memb. 2, Subs. 3 ] DIGRESSION OF SPIRITS [173"), or OCR debris of one: one short line."""
    if "\n" in c or len(c) > 100:
        return False
    if re.search(r"[\[\]]", c) and len(re.sub(r"[\[\]\s]", "", c)) <= 5:
        return True
    if re.search(r"Anatomy\s+of\s+Melancholy\s*\[", c):
        return True
    # recto heads; the OCR sometimes reads the bracket as "J"
    return bool(re.match(r"\S{0,5}\s*(Memb|Mem|Subs|Sect|Part)\b", c) and re.search(r"[\]J]|[A-Z]{4,}", c))


RUNNING_TITLE = re.compile(r"^(Democritus\s+to\s+the\s+Reader|Anatomy\s+of\s+Melancholy)$")
# a recto head printed inside a line of text: "(horace) Mcmb.3] Remedies Against Discontents [525"
INLINE_HEAD = re.compile(r"M[ce]mb\.\s*\d[^\n\]]{0,12}\]\s+[A-Z][A-Za-z ,'&-]{3,60}\[\s*\d{1,4}")


def _is_debris(c: str) -> bool:
    """A running title, a capitals-only title or stamp of at most two lines ("MARIN COUNTY FREE LIBRARY /
    SAN RAFAEL, CALIFORNIA", a library's stamp in the scanned copy), or a stray mark of a few characters.
    Furniture only when it stands beside furniture."""
    if len(re.sub(r"\s", "", c)) <= 4 or RUNNING_TITLE.match(" ".join(c.split())):
        return True
    letters = [ch for ch in c if ch.isalpha()]
    return c.count("\n") <= 1 and len(c) <= 80 and len(letters) >= 4 and \
        sum(ch.isupper() for ch in letters) >= 0.7 * len(letters)


def furniture(raw: str) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Character ranges of the edition's page furniture, which interrupts the running text: page numbers,
    running heads, and the footnotes printed just above a page break (their own and "Burton's note").
    Returns (ranges, page heads as (offset, page number))."""
    chunks = [(m.start(), m.end(), m.group().strip()) for m in CHUNK.finditer(raw) if m.group().strip()]
    furn = [_is_furniture(c) for _, _, c in chunks]
    changed = True
    while changed:  # titles, stamps and stray marks beside a page number or head
        changed = False
        for i, (_, _, c) in enumerate(chunks):
            if not furn[i] and _is_debris(c) and ((i and furn[i - 1]) or (i + 1 < len(chunks) and furn[i + 1])):
                furn[i] = changed = True
    for i in range(len(chunks) - 1, 0, -1):  # footnotes: marked blocks just before the furniture
        if furn[i] and not furn[i - 1]:
            j = i - 1
            while j >= 0 and chunks[j][2][:1] in "*†‡" and not furn[j]:
                furn[j] = True
                j -= 1
    ranges = sorted([(a, b) for (a, b, _), f in zip(chunks, furn, strict=True) if f] +
                    [m.span() for m in INLINE_HEAD.finditer(raw)])
    heads = []
    for (a, _, c), f in zip(chunks, furn, strict=True):
        m = PAGE_NO.search(c) if f else None
        if m:
            heads.append((a, int(m.group(1) or m.group(2))))
    return ranges, heads


class Djs:
    """The OCR text as words (page furniture skipped, hyphenated line breaks rejoined), with a trigram
    index over key words."""

    def __init__(self, raw: str):
        self.raw = raw
        self.words: list[str] = []
        self.offs: list[int] = []
        skip, self.heads = furniture(raw)
        si = 0
        prev_end = -1
        for m in re.finditer(r"\S+", raw):
            while si < len(skip) and skip[si][1] <= m.start():
                si += 1
            if si < len(skip) and skip[si][0] <= m.start():
                continue
            w = m.group()
            if self.words and self.words[-1].endswith("-") and "\n" in raw[prev_end:m.start()]:
                self.words[-1] = self.words[-1][:-1] + w
            else:
                self.words.append(w)
                self.offs.append(m.start())
            prev_end = m.end()
        self.keys, self.kpos = [], []  # key words and their word indices
        for i, w in enumerate(self.words):
            k = kw(w)
            if k:
                self.keys.append(k)
                self.kpos.append(i)
        self.index: dict[tuple, list[int]] = {}
        for i in range(len(self.keys) - 2):
            self.index.setdefault(tuple(self.keys[i:i + 3]), []).append(i)
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", raw)]

    def locate(self, anchor: list[str], top: int = 6) -> list[tuple[float, int, int]]:
        """Best places for a word sequence: (score 0-1, first key index, end key index)."""
        a = [k for k in (kw(w) for w in anchor) if k]
        if len(a) < MIN_ANCHOR:
            return []
        votes = Counter()
        for i in range(len(a) - 2):
            hits = self.index.get(tuple(a[i:i + 3]), [])
            if len(hits) <= COMMON:
                for pos in hits:
                    votes[pos - i] += 1
        needle = " ".join(a)
        out = []
        for start, _ in votes.most_common(top):
            best = (0.0, start, start)
            for s in range(max(0, start - 2), start + 3):
                for n in range(max(1, len(a) - 2), len(a) + 3):
                    sc = fuzz.ratio(needle, " ".join(self.keys[s:s + n])) / 100
                    if sc > best[0]:
                        best = (sc, s, s + n)
            out.append(best)
        return sorted(out, reverse=True)

    def text(self, k0: int, k1: int) -> str:
        """Raw words between key indices k0 (inclusive) and k1 (exclusive)."""
        if k1 <= k0:
            return ""
        return " ".join(self.words[self.kpos[k0]:self.kpos[k1 - 1] + 1])

    def where(self, k: int) -> str:
        off = self.offs[self.kpos[k]]
        line = bisect_right(self.line_starts, off)
        i = bisect_right([h[0] for h in self.heads], off) - 1
        page = ""
        if i >= 0:
            p0 = self.heads[i][1]
            p1 = self.heads[i + 1][1] - 1 if i + 1 < len(self.heads) else p0
            page = f", p. {p0}" if p1 <= p0 else f", pp. {p0}-{p1}"
        return f"{WHERE} djvu.txt line {line}{page}"


@lru_cache(maxsize=1)
def load() -> Djs:
    return Djs(DJS_TXT.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ anchors from Burton's text

def _cut(left: str, right: str, others: list[str]) -> tuple[str, str]:
    """Keep only Burton's English next to the passage: stop at any other foreign passage."""
    for o in others:
        if o and o in left:
            left = left[left.rindex(o) + len(o):]
        if o and o in right:
            right = right[:right.index(o)]
    return left, right


def anchors(item: dict, others: list[str]) -> tuple[list[str], list[str]]:
    para = item["paragraph"]
    if "⟦" in para and item["location"] == "text":
        left, right = para.split("⟦", 1)[0], para.split("⟧", 1)[-1]
    else:
        left = right = ""
    left, right = _cut(left, right, others)
    lw, rw = left.split(), right.split()
    if len(lw) < MIN_ANCHOR + 2 and item.get("before"):  # the passage opens its block
        b, _ = _cut(item["before"].rstrip("…"), "", others)
        lw = b.split() + lw
    if len(rw) < MIN_ANCHOR + 2 and item.get("after"):
        _, a = _cut("", item["after"].rstrip("…"), others)
        rw = rw + a.split()
    return lw[-ANCHOR_WORDS:], rw[:ANCHOR_WORDS]


def align(item: dict, others: list[str], djs: Djs | None = None) -> dict:
    djs = djs or load()
    words = len(item["text"].split())
    if item["location"] == "sidenote":
        return {"status": "no-anchor", "reason": "sidenote: no English of Burton's around it to anchor on"}
    lw, rw = anchors(item, others)
    L, R = djs.locate(lw), djs.locate(rw)
    if not L or not R:
        return {"status": "no-anchor" if (len(lw) < MIN_ANCHOR or len(rw) < MIN_ANCHOR) else "not-found",
                "left_anchor": " ".join(lw), "right_anchor": " ".join(rw)}
    pairs = [(min(ls, rs), ls, rs, le, rb) for ls, _, le in L for rs, rb, _ in R if 0 <= rb - le <= 6 * words + 80]
    base = {"left_anchor": " ".join(lw), "right_anchor": " ".join(rw)}
    if not pairs:
        return {**base, "status": "not-found", "left_score": L[0][0], "right_score": R[0][0]}
    # prefer anchor pairs whose gap could be a rendering of the passage (or nothing at all)
    score, ls, rs, le, rb = max(pairs, key=lambda p: (_gap_kind(p[4] - p[3], words) != "implausible", p[0]))
    base.update(left_score=round(ls, 3), right_score=round(rs, 3), align_score=round(score, 3))
    if score < THRESHOLD:
        return {**base, "status": "below-threshold"}  # the candidate is discarded, never shown
    kind = _gap_kind(rb - le, words)
    if kind == "omitted":
        return {**base, "status": "omitted", "text": "", "residue": djs.text(le, rb), "where": djs.where(le)}
    if kind == "implausible":
        return {**base, "status": "implausible-length", "gap_words": rb - le}  # discarded, never shown
    text, attribution = split_attribution(djs.text(le, rb))
    out = {**base, "status": "aligned", "text": text, "where": djs.where(le)}
    if re.search(r"[*†‡]$", text):  # their footnote mark; the footnote itself is page furniture
        out.update(text=text.rstrip("*†‡"), footnote_mark=text[-1])
    if attribution:
        out["attribution"] = attribution
    if not _is_words(out["text"]):
        return {**base, "status": "ocr-noise", "gap_words": rb - le}  # discarded, never shown
    if _kept(item["text"], out["text"]):
        # they print the original ("os sacrum", a name): a fact about their edition, not a translation
        return {**out, "status": "kept-original"}
    if _broken_brackets(out["text"]):
        # the span starts or ends inside one of their [bracketed insertions]: the anchors slipped
        return {**base, "status": "broken-span", "gap_words": rb - le}  # discarded, never shown
    return out


def _kept(original: str, candidate: str) -> bool:
    a = " ".join(k for k in (kw(w) for w in original.split()) if k)
    b = " ".join(k for k in (kw(w) for w in candidate.split()) if k)
    return bool(a) and fuzz.ratio(a, b) >= 90


def _broken_brackets(text: str) -> bool:
    depth = 0
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth < 0:
                return True
    return depth != 0


def _is_words(text: str) -> bool:
    """English words, not OCR debris ("E«5,"): mostly letters, with at least one word of 3+ letters."""
    letters = sum(ch.isalpha() or ch.isspace() for ch in text)
    return bool(re.search(r"[A-Za-z]{3,}", text)) and letters >= 0.75 * len(text)


ATTRIBUTION = re.compile(r"\s*\(([a-z][a-z .'-]{2,40})\)\s*([.,;:]?)$")


def split_attribution(text: str) -> tuple[str, str | None]:
    """Their attribution after a verse, "(ovid)" (Burton's sidenote, kept in lower case), is their
    note, not part of the translation: kept apart, as printed."""
    m = ATTRIBUTION.search(text)
    if not m or not text[:m.start()].strip():
        return text, None
    return text[:m.start()] + m.group(2), m.group(1)


def _gap_kind(gap: int, words: int) -> str:
    """Nothing (or a stray word or two) between the anchors means Dell & Jordan-Smith dropped the passage;
    a rendering is assumed to run from 0.3 to 3 times the passage's length (plus a little)."""
    if gap == 0 or (gap <= 3 and gap < 0.3 * words):
        return "omitted"
    if 0.3 * words <= gap <= 3 * words + 8:
        return "aligned"
    return "implausible"


def shown(rec: dict | None, tr: dict | None) -> bool:
    """Does the reader show this alignment as a translation? Only an aligned span (never kept-original,
    omitted or a discarded candidate), current with the passage's text, and not where Burton renders the
    passage in full himself: there his English is shown, they usually drop the passage, and a span found
    there was most often something else (held-out round h1: 3 of 8 correct). Held-out round h2 measured
    exactly this set: 95/100 correct (data/eval/djs-holdout.yaml)."""
    return bool(rec and tr and rec["status"] == "aligned" and rec["text_sha1"] == tr["text_sha1"]
                and tr["self_translation"]["status"] != "full")


def version(rec: dict) -> dict:
    """The translation version the reader shows: their text, with the page in their edition."""
    m = re.search(r"pp?\. ([\d-]+)", rec.get("where", ""))
    v = {"by": "djs1927", "text": rec["text"], "method": rec["method"], "page": m.group(1) if m else None}
    if rec.get("attribution"):
        v["attribution"] = rec["attribution"]
    return v


def sidenote_study(n: int = 60, seed: int = 20261020) -> dict:
    """What did Dell & Jordan-Smith do with Burton's sidenotes? A seeded random sample: find the note's anchor
    in their text (Burton's English on both sides of it), then look from there to 600 characters past the anchor
    for a parenthesis naming the note's first word (their inline attributions, e.g. "(martial)")."""
    import random

    from lxml import etree

    from ..ingest.epub import all_units
    from ..tei import ED_NS, XML_ID, T
    from ..textview import public_text

    notes = []
    for u in all_units():
        root = etree.parse(str(paths.TEXT / f"{u}.xml")).getroot()
        for e in root.iter(T("note")):
            if e.get("type") == "side" and not any(a.tag.startswith(f"{{{ED_NS}}}") for a in e.iterancestors()):
                notes.append((u, e))
    random.Random(seed).shuffle(notes)
    djs, rows, c = load(), [], Counter()
    for _, e in notes[:n]:
        block = e.getparent()
        while block is not None and block.tag not in (T("p"), T("lg"), T("quote"), T("item"), T("head")):
            block = block.getparent()
        if block is None:
            continue
        whole = public_text(block, note_marker=e.get(XML_ID))
        left, _, right = whole.partition("⟦sidenote⟧")
        lw, rw = left.split()[-ANCHOR_WORDS:], right.split()[:ANCHOR_WORDS]
        L, R = djs.locate(lw), djs.locate(rw)
        note = public_text(e, notes=True)
        row = {"note": e.get(XML_ID)[1:], "text": note, "left": " ".join(lw), "right": " ".join(rw)}
        pairs = [(min(a[0], b[0]), a, b) for a in L for b in R if 0 <= b[1] - a[2] <= 40]
        first = next((kw(w) for w in note.split() if len(kw(w)) >= 3 and not kw(w).isdigit()), "")
        if pairs and max(pairs)[0] >= THRESHOLD:
            _, a, b = max(pairs)
            gap, end = djs.text(a[2], b[1]), djs.offs[djs.kpos[min(b[2], len(djs.kpos) - 1)]] + 600
        elif L and L[0][0] >= THRESHOLD:  # Burton's words after the anchor are Latin that they replaced
            a, gap = L[0], None
            end = djs.offs[djs.kpos[min(a[2], len(djs.kpos) - 1)]] + 1500
        else:
            row["finding"] = "anchor-not-found"
            c[row["finding"]] += 1
            rows.append(row)
            continue
        window = djs.raw[djs.offs[djs.kpos[a[2] - 1]]:end]
        parens = [" ".join(p.split()) for p in re.findall(r"\(([a-z][a-z .'-]{2,40})\)", window)]
        row.update(gap=gap, where=djs.where(a[2]), parens=parens)
        if first and any(kw(p).startswith(first[:4]) for p in parens):
            row["finding"] = "inline-attribution"
        elif gap is None:
            row["finding"] = "left-anchor-only, no attribution near"
        elif gap.strip():
            row["finding"] = "something-at-anchor"
        else:
            row["finding"] = "nothing-at-anchor"
        c[row["finding"]] += 1
        rows.append(row)
    return {"sample": n, "seed": seed, "counts": dict(c), "rows": rows}


def run(selection_path=None, units: list[str] | None = None) -> dict:
    """Align the passages of a selection file, or every passage of the given units; write
    data/layers/djs/<unit>.json; return counts. A whole-unit run rewrites the unit's layer, so records keyed
    by retired ids do not linger."""
    import yaml

    from ..translate import packets
    from ..translate.packets import sha1

    by_unit: dict[str, list[str] | None] = {}
    if selection_path:
        sel = yaml.safe_load(open(selection_path, encoding="utf-8"))
        for it in (i for i in sel["items"] if not i.get("retired")):
            if it.get("kind") != "gloss-only":
                by_unit.setdefault(it["id"].rsplit("-", 1)[0], []).append(it["id"])
    for u in units or []:
        by_unit[u] = None
    djs, counts = load(), Counter()
    for unit, ids in by_unit.items():
        ps = packets.passages(unit)
        if not ps:
            continue
        others_all = [p["packet_item"]["text"] for p in ps]
        f = LAYER / f"{unit}.json"
        layer = json.loads(f.read_text(encoding="utf-8")) if f.exists() and ids is not None else {}
        for p in ps:
            item = p["packet_item"]
            if ids is not None and item["id"] not in ids:
                continue
            others = [o for o in others_all if o != item["text"]]
            res = align(item, others, djs)
            counts[res["status"]] += 1
            layer[item["id"]] = {"by": "djs1927", "method": "rules/djs-align-v3", "threshold": THRESHOLD,
                                 "text_sha1": sha1(item["text"]), **res}
        atomic_write_text(f, json.dumps(layer, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return dict(counts)
