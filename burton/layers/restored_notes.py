"""`burton restore-notes`: Burton's sidenotes that Gowland's edition leaves out (M8 follow-up; owner,
2026-11-03: "Restore Burton's sidenotes that Gowland cut, but distinguish them") -> data/layers/restored-notes/.

Source: Project Gutenberg #10800 (public domain in the USA; pinned in data/source/BURTON-PG.lock), a
nineteenth-century modernised edition re-checked against the 1638 edition. Its 6,817 notes are numbered through
the book, with their markers [N] in the text. That editor sometimes added an English translation to a note, so a
restored note is labelled as coming from that text, never as Burton's words alone. The base text is not touched.

Rules (`rules/restore-v2`):
1. Each Gutenberg marker is placed in this edition's main text by the words that follow it (5 normalised words,
   then 4, found once in the book), else by the 5 words before it; a place out of reading order is dropped.
2. A marker within one word of one of Gowland's sidenote markers is that note (kept, not restored); so is one
   within six words of an unclaimed note of his with the same text (half its words in common). Each of
   Gowland's notes is claimed once, by the nearest marker. (v2) A note left over that mostly repeats any note of
   his in the same paragraph (>= 60 % of its longer words), claimed or not, is his too: Gutenberg can mark one note
   twice, or far from where Gowland marks it.
3. A note in English, at a foreign passage of this edition or carrying no reference (a number, "lib.", "cap.",
   ...), is most likely that editor's translation of Burton's Latin, not Burton's note: left out, counted and
   listed in state/review/restored-notes-left-out.json.
4. Every other placed marker is restored: a text-quote selector on the word it precedes, and the note's text.
"""

import copy
import json
import re
import unicodedata
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import date

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..tei import XML_ID, T, public_id
from ..textview import is_gowland, public_text

FILE = paths.SOURCE / "burton-pg" / "10800.txt.utf-8"
LAYER = paths.LAYERS / "restored-notes"
RULES = "rules/restore-v2"  # v2 (2026-11-19): a note that repeats one of Gowland's nearby is his, not restored
SOURCE = "Project Gutenberg #10800"
SEP = ""  # a private-use character, never in the text: marks one of Gowland's sidenote anchors
WORD = re.compile(r"[a-z]+|[α-ω]+")


def norm_words(s: str) -> list[tuple[str, int, int]]:
    """(normalised word, start, end) over the original string: lower case, accents dropped, æ/œ spelled out,
    i/j and u/v merged."""
    out = []
    for m in re.finditer(r"[^\W\d_]+", s):
        w = unicodedata.normalize("NFD", m.group(0).lower().replace("æ", "ae").replace("œ", "oe"))
        w = "".join(ch for ch in w if not unicodedata.combining(ch)).replace("j", "i").replace("v", "u")
        w = w.replace("ς", "σ")
        if WORD.fullmatch(w):
            out.append((w, m.start(), m.end()))
    return out


# ---------------------------------------------------------------- the Gutenberg text
def gutenberg() -> tuple[list[tuple[int, list[str]]], dict[int, str]]:
    """(markers in reading order as (note number, the 5 words before, the 5 words after), note bodies)."""
    text = FILE.read_text(encoding="utf-8").replace("\r\n", "\n")
    body = text.split("*** START OF", 1)[1].split("\n", 1)[1].split("*** END OF", 1)[0]
    paras = re.split(r"\n\s*\n", body)
    # the note bodies: from the first paragraph "1. " followed by "2. ", numbered on through the book
    def run_from(i: int) -> int:  # how far "1.", "2.", "3.", ... continue in the paragraphs after i
        want = 1
        for q in paras[i:i + 120]:
            if re.match(rf"{want}\.(?:\s|$)", q):
                want += 1
        return want - 1

    start = next(i for i, p in enumerate(paras) if re.match(r"1\.(?:\s|$)", p) and run_from(i) >= 50)
    notes: dict[int, str] = {}
    want, cur = 1, None
    for p in paras[start:]:
        m = re.match(r"(\d+)\.(?:\s|$)", p)
        if m and want <= int(m.group(1)) <= want + 3:  # the next note (a gap of up to 3 is resynchronised)
            cur = int(m.group(1))
            want = cur + 1
            notes[cur] = p[m.end():]
        elif cur is not None:
            notes[cur] += "\n" + p
    notes = {k: " ".join(v.split()) for k, v in notes.items()}
    main = "\n\n".join(paras[:start])
    markers = []
    for m in re.finditer(r"\[(\d+)\]", main):
        n = int(m.group(1))
        if n not in notes:
            continue
        before = [w for w, _, _ in norm_words(re.sub(r"\[\d+\]", " ", main[max(0, m.start() - 200):m.start()]))][-5:]
        after = [w for w, _, _ in norm_words(re.sub(r"\[\d+\]", " ", main[m.end():m.end() + 200]))][:5]
        markers.append((n, before, after))
    return markers, notes


# ---------------------------------------------------------------- this edition
def _units() -> list[str]:
    from ..site.book import is_gowland_unit, text_units
    return [u for u in text_units() if not is_gowland_unit(u)]


def _blocks(unit: str):
    """(block id, public text, positions of Gowland's sidenote anchors) for the unit's main-text blocks."""
    div = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot().find(f".//{T('div')}")
    for e in div.iter(T("p"), T("lg")):
        if not e.get(XML_ID) or any(is_gowland(a) or a.tag == T("note") for a in e.iterancestors()):
            continue
        c = copy.deepcopy(e)
        texts = [public_text(n) for n in e.iter(T("note"))]
        for n in list(c.iter(T("note"))):
            mark = etree.Element(T("hi"))
            mark.text, mark.tail = SEP, n.tail
            n.getparent().replace(n, mark)
        raw = re.sub(rf" ({SEP}+)(?=[,;:.)])", r"\1", public_text(c))
        out, pos = [], []
        for ch in raw:
            if ch == SEP:
                pos.append(len(out))
            elif not (ch == " " and (not out or out[-1] == " ")):
                out.append(ch)
        text = "".join(out).rstrip(" ")
        if text == public_text(e):
            from .obsolete import _blocked_spans
            yield public_id(e.get(XML_ID)), text, list(zip(pos, texts, strict=False)), _blocked_spans(e, text)


def stream():
    """The book's words in reading order: (word, unit, block, start, end), and Gowland's anchors as (index into
    that list of the word each one precedes, the note's text)."""
    words, anchors = [], []
    for unit in _units():
        for cid, text, pos, foreign in _blocks(unit):
            ws = norm_words(text)
            starts = [s for _, s, _ in ws]
            for p, note in pos:
                anchors.append((len(words) + bisect_left(starts, p), note))
            words += [(w, unit, cid, s, e, text, any(x <= s < y for x, y in foreign)) for w, s, e in ws]
    return words, anchors


def run() -> Counter:
    markers, notes = gutenberg()
    words, anchors = stream()
    seq = [w[0] for w in words]
    grams: dict[tuple, list[int]] = defaultdict(list)
    for n in (5, 4):
        for i in range(len(seq) - n + 1):
            grams[(n, *seq[i:i + n])].append(i)
    stats: Counter = Counter(gutenberg_markers=len(markers), gutenberg_notes=len(notes), gowland_anchors=len(anchors))
    placed = []
    for num, before, after in markers:
        at = None
        for n in (5, 4):
            hits = grams.get((n, *after[:n]), []) if len(after) >= n else []
            if len(hits) == 1:
                at = hits[0]
                break
        if at is None and len(before) == 5:
            hits = grams.get((5, *before), [])
            if len(hits) == 1:
                at = hits[0] + 5
        if at is None or at >= len(words):
            stats["unplaced"] += 1
            continue
        placed.append((num, at))
    # reading order: drop a place that runs backwards against its neighbours
    ordered = []
    for k, (num, at) in enumerate(placed):
        prev_at = placed[k - 1][1] if k else -1
        next_at = placed[k + 1][1] if k + 1 < len(placed) else len(words)
        if prev_at <= at <= next_at:
            ordered.append((num, at))
        else:
            stats["out_of_order"] += 1
    # each of Gowland's anchors is claimed once: first by the nearest marker within one word; then, for a marker
    # left over, by an unclaimed anchor within six words whose note has the same text (half its words in common)
    from ..ids import Registry

    reg = Registry()
    free = sorted(a for a, _ in anchors)
    note_at = dict(anchors)
    claimed = set()
    left = []
    for num, at in ordered:
        k = bisect_left(free, at - 1)
        near = [a for a in free[k:k + 3] if abs(a - at) <= 1 and a not in claimed]
        if near:
            claimed.add(min(near, key=lambda a: abs(a - at)))
            stats["kept_by_gowland"] += 1
        else:
            left.append((num, at))
    out: dict[str, dict] = defaultdict(dict)
    left_out: list[dict] = []
    by_block: dict[str, list[int]] = defaultdict(list)  # paragraph id -> Gowland's anchors in it
    for a in free:
        if a < len(words):
            by_block[words[a][2]].append(a)
    for num, at in left:
        k = bisect_left(free, at - 6)
        near = [a for a in free[k:k + 14] if abs(a - at) <= 6 and a not in claimed
                and similar(note_at[a], notes[num])]
        if near:
            claimed.add(min(near, key=lambda a: abs(a - at)))
            stats["kept_by_gowland_nearby"] += 1
            continue
        # v2 (2026-11-19): Gutenberg may mark one note twice where Gowland keeps it once; the nearer marker claims his
        # note and the other would be "restored" as a copy of it (61 such: 1.1.1.1-r2 repeated note d). A note that
        # mostly repeats any of his notes in the same paragraph, claimed or not, is his (Burton does not give one
        # note twice in a paragraph; Gutenberg's marker can stand far from Gowland's).
        w, unit, cid, s, e, text, in_foreign = words[at]
        if any(repeats(notes[num], note_at[a]) for a in by_block.get(cid, ())):
            stats["repeats_gowland"] += 1
            continue
        while s > 0 and text[s - 1] in "’'‘“(":
            s -= 1
        if english(notes[num]) and (in_foreign or not REFERENCE.search(notes[num])):
            # most likely the 19th-century editor's English for Burton's Latin, not Burton's note: listed, not shown
            stats["english_left_out"] += 1
            left_out.append({"pg_note": num, "unit": unit, "text": notes[num]})
            continue
        sel = _selector(cid, text, s, e)
        if sel is None:
            stats["no_selector"] += 1
            continue
        rid = reg.assign(unit, "r", f"pg10800#{num}")
        out[unit][rid] = {"selector": sel, "pg_note": num, "text": notes[num], "source": SOURCE,
                          "by": "rules", "method": RULES, "date": date.today().isoformat()}
        stats["restored"] += 1
    stats["gowland_anchors_unclaimed"] = len(anchors) - len(claimed)
    LAYER.mkdir(parents=True, exist_ok=True)
    for f in LAYER.glob("*.json"):
        f.unlink()
    for unit, recs in out.items():
        atomic_write_text(LAYER / f"{unit}.json", json.dumps(recs, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    reg.save()
    atomic_write_text(paths.STATE / "review" / "restored-notes-left-out.json",
                      json.dumps(left_out, ensure_ascii=False, indent=1) + "\n")
    stats["units"] = len(out)
    return stats


ENGLISH = {"the", "and", "of", "to", "a", "is", "that", "in", "he", "his", "with", "for", "not", "as", "be", "by",
           "it", "our", "we", "my", "thou", "thy", "are", "what", "but", "who", "her", "she", "they", "their"}


REFERENCE = re.compile(r"\d|\b(?:lib|cap|tom|epist|ep|fol|sect|part|tract|vide|cont|serm|dial)\.", re.I)


def english(s: str) -> bool:
    """Mostly English: at least a fifth of its words are common English words."""
    ws = [w for w, _, _ in norm_words(s)]
    return bool(ws) and sum(w in ENGLISH for w in ws) / len(ws) >= 0.2


def similar(gowland_note: str, pg_note: str) -> bool:
    """At least half the words of Gowland's note occur in the Gutenberg note (spelling normalised)."""
    a = [w for w, _, _ in norm_words(gowland_note)]
    b = {w for w, _, _ in norm_words(pg_note)}
    return bool(a) and sum(w in b for w in a) / len(a) >= 0.5


def repeats(pg_note: str, gowland_note: str) -> bool:
    """The Gutenberg note is mostly Gowland's again: >= 60 % of its words of 4+ letters (at least 3) are in his note."""
    a = {w for w, _, _ in norm_words(pg_note) if len(w) > 3}
    b = {w for w, _, _ in norm_words(gowland_note)}
    return len(a) >= 3 and len(a & b) >= 0.6 * len(a)


def _selector(cid: str, text: str, a: int, b: int) -> dict | None:
    for n in range(8, 41, 4):
        pre, suf = text[max(0, a - n):a], text[b:b + n]
        if text.count(pre + text[a:b] + suf) == 1:
            return {"in": cid, "exact": text[a:b], "prefix": pre, "suffix": suf}
    return None
