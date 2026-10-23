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


class Djs:
    """The OCR text as words (hyphenated line breaks rejoined), with a trigram index over key words."""

    def __init__(self, raw: str):
        self.raw = raw
        self.words: list[str] = []
        self.offs: list[int] = []
        prev_end = -1
        for m in re.finditer(r"\S+", raw):
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
        self.heads = [(m.start(), int(m.group(1) or m.group(2))) for m in re.finditer(
            r"(?m)^\s*(\d{1,4})\]|\[(\d{1,4})\s*$", raw)]

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
    return {**base, "status": "aligned", "text": djs.text(le, rb), "where": djs.where(le)}


def _gap_kind(gap: int, words: int) -> str:
    """Nothing (or a stray word or two) between the anchors means Dell & Jordan-Smith dropped the passage;
    a rendering is assumed to run from 0.3 to 3 times the passage's length (plus a little)."""
    if gap == 0 or (gap <= 3 and gap < 0.3 * words):
        return "omitted"
    if 0.3 * words <= gap <= 3 * words + 8:
        return "aligned"
    return "implausible"


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


def run(selection_path) -> dict:
    """Align the passages of a selection file; write data/layers/djs/<unit>.json; return counts."""
    import yaml

    from ..translate import packets
    from ..translate.packets import sha1

    sel = yaml.safe_load(open(selection_path, encoding="utf-8"))
    by_unit: dict[str, list[str]] = {}
    for it in sel["items"]:
        if it.get("kind") != "gloss-only":
            by_unit.setdefault(it["id"].rsplit("-", 1)[0], []).append(it["id"])
    djs, counts = load(), Counter()
    for unit, ids in by_unit.items():
        ps = packets.passages(unit)
        others_all = [p["packet_item"]["text"] for p in ps]
        f = LAYER / f"{unit}.json"
        layer = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        for p in ps:
            item = p["packet_item"]
            if item["id"] not in ids:
                continue
            others = [o for o in others_all if o != item["text"]]
            res = align(item, others, djs)
            counts[res["status"]] += 1
            layer[item["id"]] = {"by": "djs1927", "method": "rules/djs-align-v1", "threshold": THRESHOLD,
                                 "text_sha1": sha1(item["text"]), **res}
        atomic_write_text(f, json.dumps(layer, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return dict(counts)
