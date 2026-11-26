"""Gowland's endnotes in the margin (private build only), sorted by what each entry does and tied to Burton's words.

An endnote holds one or more entries, each an italic lemma (Burton's words), ": " and Gowland's note on it
(`glosses.note_segments`). Every entry is classed by rule (`gowland-kind-v1`):
* `pointer`: the whole note sends the reader to another of his notes ("See above, n. 38 (1.2.1)."); the target is
  resolved to its endnote id, so the reader can open it in place;
* `gloss`: a short sense of an English word ("Margin.", rule gowland-gloss-v2 in glosses.py);
* `source`: where a quotation or reference comes from: a Bible verse ("1 Corinthians 7:9."), a numbered locus in
  parentheses ("Amores (2.4.32)"), or a note opening "A quotation from", "From", "Quoted from" …;
* `identity`: who or what a name is: a capitalised lemma, or a note giving life dates ("(1261–1333)");
* `explanation`: everything else.
Each entry is anchored on its lemma, found as whole words in Burton's text before the endnote's anchor (as Gowland's
glosses are placed), else on the anchor alone. Only ids, kinds, selectors on Burton's words and counts come out of
here; Gowland's own wording is read from the base text when the page is built and is never written to a layer
(CLAUDE.md rule 5).
"""

import re
from collections import Counter
from functools import cache

from lxml import etree

from .. import paths
from ..layers import obsolete
from ..tei import ED, XML_ID, T, public_id
from ..textview import public_text
from . import glosses

RULE = "gowland-kind-v1"
KINDS = ("gloss", "source", "identity", "explanation", "pointer")
# "n. 38 (1.2.1)", "note 32 (DJR)", "nn. 181, 187 (1.2.3)"
REF = r"(?:notes?|nn?\.) ?(\d+(?:(?:, | and | or )\d+)*) \(([^)]+)\)"
# the whole note only points elsewhere: "See above, n. 38 (1.2.1).", "… n. 175 (DJR) and n. 30 (2.2.4)."
POINTER = re.compile(rf"^(?:In note ‘\w’, )?[Ss]ee (?:above|below),? {REF}(?:,? (?:and|or) {REF})*\.?$")
POINTER_ANY = re.compile(REF)
BIBLE_REF = re.compile(r"\b\d+:\d+")
LOCUS = re.compile(r"\(\s*(?:[IVXL]+\.|\d+)(?:\.\d+[A-F]?)+(?:[–-]\d*[A-F]?)?\s*\)")  # "(2.4.32)", "(6.249D–E)"
# a place in the Anatomy itself: "See above, 1.1.2.4."
BOOK_REF = re.compile(r"^[Ss]ee (?:above|below),? (\d\.\d\.\d(?:\.\d+)?)\.?$")
TITLE_LOCUS = re.compile(r"\b[A-Z][a-z]+(?: [A-Za-z][a-z]+){0,4} \d+\.\d+")  # "(Histories 5.13)", "Satires 1.1"
SOURCE_OPEN = re.compile(r"^(?:A quotation|This quotation|The quotation|Quoted|Quoting|From |Adapted from|"
                         r"A paraphrase of|Paraphrasing|"
                         r"Translated from|A line from|In this line from|Lines from|A version of|Cited from|"
                         r"According to|Burton quotes|Burton’s source)")
LIFE = re.compile(r"\((?:c\. |d\. |b\. |fl\. )?\d{3,4}\s*(?:BCE|CE)?\s*[–-]")
# a second entry run into the first where Gowland's lemma is not set in italics: "… kept down. Prima fere … &c.: The"
TAIL = re.compile(r"(?<=[.?!’”)])\s+([^.:;]{1,60}?\s*…)\s*$")
RUN_IN = re.compile(r"(?<=[.?!’”])\s+(?=[^.:;]{2,80}?(?:…|&c\.)[^.:;]{0,40}: [A-Z‘])")


@cache
def endnotes() -> dict:
    root = etree.parse(str(paths.TEXT / "gowland-endnotes.xml")).getroot()
    return {e.get(XML_ID): e for e in root.iter(ED("endnote"))}


@cache
def prefixes() -> dict[str, str]:
    """Gowland's chapter labels ("DJR", "1.2.1") -> endnote id prefixes ("pre6", "chc1"), from where each
    prefix's anchors stand."""
    where: dict[str, set] = {}
    for f in paths.TEXT.glob("*.xml"):
        if f.stem == "gowland-endnotes":
            continue
        for a in etree.parse(str(f)).getroot().iter(ED("enref")):
            where.setdefault(re.sub(r"_en_\d+$", "", a.get("target")), set()).add(f.stem)
    out = {}
    for p, units in where.items():
        if units == {"djr"}:
            out["DJR"] = p
        elif units and units <= {"argument", "ad-librum-gowland", "dedication", "ad-librum", "abstract", "lectori",
                                 "lectori-gowland", "heraclite"}:
            out["Preliminaries"] = p
        elif all(re.fullmatch(r"\d+\.\d+\.\d+\.\d+", u) for u in units):
            members = {".".join(u.split(".")[:3]) for u in units}
            if len(members) == 1:
                out[members.pop()] = p
    return out


def pointer_target(num: str, label: str) -> str | None:
    p = prefixes().get(label.strip())
    tid = f"{p}_en_{num}" if p else None
    return tid if tid in endnotes() else None


@cache
def endnote_locations() -> dict[str, tuple[str, str]]:
    """Target endnote id -> (unit id, enclosing block public id) where that endnote is anchored."""
    out: dict[str, tuple[str, str]] = {}
    block_tags = {T("p"), T("lg"), T("item"), T("head"), T("quote")}
    for f in paths.TEXT.glob("*.xml"):
        if f.stem == "gowland-endnotes":
            continue
        root = etree.parse(str(f)).getroot()
        for a in root.iter(ED("enref")):
            tid = a.get("target")
            if not tid or tid in out:
                continue
            blk = next((anc for anc in a.iterancestors() if anc.tag in block_tags and anc.get(XML_ID)), None)
            if blk is not None:
                out[tid] = (f.stem, public_id(blk.get(XML_ID)))
    return out


def resolve_ref_items(target_id: str, hint_clause: str, fallback_lemma: str = "") -> list[tuple[int, str, str]]:
    """Resolve the specific segment(s) of `target_id` referenced by an embedded cross-note citation."""
    en = endnotes().get(target_id)
    if en is None:
        return []
    segs = segments(en)
    if len(segs) <= 1:
        return [(0, segs[0][0], segs[0][1])] if segs else []
    q = re.findall(r"[‘']([^’']+)[’']", hint_clause)
    for cand in (*q, hint_clause, fallback_lemma):
        cand = cand.strip()
        if not cand:
            continue
        idxs = match_pointer_segments(cand, segs)
        if idxs:
            return [(i, segs[i][0], segs[i][1]) for i in idxs]
    return [(i, lem, txt) for i, (lem, txt) in enumerate(segs)]


def segments(en) -> list[tuple[str, str]]:
    """The endnote's (lemma, note) entries; one without an italic lemma is split at its first ": "."""
    segs = glosses.note_segments(en)
    if not segs:
        text = " ".join("".join(en.itertext()).split())
        lemma, sep, note = text.partition(": ")
        segs = [(lemma, note)] if sep else [("", text)]
    # a lemma that runs over an ellipsis is italic only after it ("Suidas … in Pindar"): its opening stays at the end
    # of the previous note ("See above, n. 249 (1.2.3). Suidas …"); it goes back to its lemma
    fixed = []
    for lemma, note in segs:
        if fixed and (m := TAIL.search(fixed[-1][1])):
            fixed[-1] = (fixed[-1][0], fixed[-1][1][:m.start()].rstrip())
            lemma = f"{m.group(1)} {lemma}".strip()
        fixed.append((lemma, note))
    if fixed and (m := TAIL.search(fixed[-1][1])):  # the last note cannot hand on its tail: leave it
        pass
    out = []
    for lemma, note in fixed:
        parts = RUN_IN.split(note)
        out.append((lemma, parts[0]))
        for p in parts[1:]:
            lem, _, rest = p.partition(": ")
            out.append((lem, rest))
    return out


_STOP_WORDS = frozenset({
    "the", "and", "for", "with", "from", "that", "this", "his", "her", "into",
    "after", "see", "above", "below", "note", "kind", "new", "their", "them",
})


def _norm_plain(s: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", s.lower()).split())


def _content_words(s: str) -> list[str]:
    return [_norm(w) for w in WORD.findall(s) if len(w) >= 3 and w.lower() not in _STOP_WORDS]


def _shares_stem(wa: list[str], wb: list[str]) -> bool:
    for x in wa:
        need = max(4, -(-len(x) * 3 // 5))
        if any(len(_common(x, y)) >= need for y in wb):
            return True
    return False


def match_pointer_segments(lemma: str, segs: list[tuple[str, str]]) -> list[int]:
    """Find which segment(s) of a target endnote a pointer's lemma refers to.
    Never falls back to segment 0 when a multi-segment target has no match.
    """
    if len(segs) <= 1:
        return [0] if segs else []
    nl = _norm_plain(lemma)
    if nl:
        exact = [i for i, (lem, _) in enumerate(segs) if _norm_plain(lem) == nl]
        if exact:
            return exact
        if len(nl) >= 4:
            sub = [
                i for i, (lem, _) in enumerate(segs)
                if len(_norm_plain(lem)) >= 4 and (
                    re.search(rf"(?<!\w){re.escape(nl)}(?!\w)", _norm_plain(lem))
                    or re.search(rf"(?<!\w){re.escape(_norm_plain(lem))}(?!\w)", nl)
                )
            ]
            if sub:
                return sub
    wa = _content_words(lemma)
    if wa:
        stem_hits = [i for i, (lem, _) in enumerate(segs) if _shares_stem(wa, _content_words(lem))]
        if stem_hits:
            return stem_hits
        txt_hits = [i for i, (_, txt) in enumerate(segs) if _shares_stem(wa, _content_words(txt))]
        if len(txt_hits) == 1:
            return txt_hits
    return []


def _short_sense(lemma: str, note: str) -> bool:
    """A sense of an English word even where it opens "A …" or "That is, …" ("A very ugly person."), or where
    the word is one of Burton's capitalised common nouns ("Schools: Universities.", "Chemist: Alchemist.")."""
    note = re.sub(r";? ?(?:cf\.|see) (?:above|below),? " + REF + r"\.?", "", note)  # "…character; cf. above, n. 1"
    words = note.split()
    plain = not re.search(r"\d", note) and not note.startswith(("See ", "Cf.")) and \
        not any(w[:1].isupper() and w != "I" for w in words[1:])
    if not plain or not words or len(lemma.split()) > 5:
        return False
    if glosses.LEMMA.match(lemma.replace(",", "")):
        return len(words) <= 14
    return bool(re.fullmatch(r"[A-Z][a-z’'\- ]*", lemma)) and len(words) <= 4


@cache
def _bible_books() -> re.Pattern:
    from ..layers import citations
    names = sorted({b["name"] for b in citations.tables()["bible_books"].values()} | {"Psalm"}, key=len, reverse=True)
    return re.compile(rf"^(?:(?:An allusion to|See|Cf\.) )?(?:[123] )?(?:{'|'.join(map(re.escape, names))}) \d+")


def _bible_chapter(note: str) -> bool:
    """A note that opens with a Bible chapter without a verse ("Judges 16.")."""
    return bool(_bible_books().match(note))


def kind(lemma: str, note: str) -> str:
    if POINTER.match(note) or BOOK_REF.match(note):
        return "pointer"
    if glosses.is_word_gloss(lemma, note) or _short_sense(lemma, note):
        return "gloss"
    bare = POINTER_ANY.sub("", note)  # "see above, n. 107 (1.2.4)": his chapter label is not a locus
    if BIBLE_REF.search(bare) or LOCUS.search(bare) or SOURCE_OPEN.match(bare) or _bible_chapter(bare) or \
            TITLE_LOCUS.search(bare):
        return "source"
    if (lemma[:1].isupper() and not lemma.endswith(("…", "&c.")) and len(lemma.split()) <= 5) or LIFE.search(note):
        return "identity"
    return "explanation"


def _anchor_words(lemma: str) -> list[str]:
    """The words to look for: the lemma, or for "Some die suddenly … the battle at Cannae, &c." its opening."""
    first = re.split(r"\s*…\s*", lemma)[0].replace("&c.", "").strip(" ,.;:")
    return [w for w in (lemma, first) if w]


def _norm(w: str) -> str:
    return w.lower().replace("j", "i").replace("v", "u").replace("æ", "ae").replace("œ", "oe")


WORD = re.compile(r"[^\W\d_]+")


def _stem_hit(text: str, lemma: str, start: int, end: int) -> int:
    """A single-word lemma met in another form, as Latin declines a name ("Praxiteles": "Praxitilem", "Dionysus":
    "Dionysio"): the one word in text[start:end] sharing its first letters (five at least, and three fifths of the
    lemma), or -1 where there is none or more than one."""
    lw = _norm(lemma)
    need = max(5, -(-len(lw) * 3 // 5))
    hits = {(m.start(), m.group(0)) for m in WORD.finditer(text, start, end)
            if len(m.group(0)) >= 5 and len(_common(lw, _norm(m.group(0)))) >= need}
    return hits.pop()[0] if len({w for _, w in hits}) == 1 and len(hits) == 1 else -1


def _common(a: str, b: str) -> str:
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return a[:n]


def _fallback(e, cid: str, text: str, start: int, at: int, lemma: str) -> tuple[dict | None, str | None]:
    """Where the lemma's words are not found before the endnote's anchor (stage 11, 2026-11-04: 280 of 4,392 entries
    stood at the marker): (1) once only anywhere in the paragraph; (2) as one word in another form, before the anchor;
    (3) in one of Burton's sidenotes in the paragraph, once only (Gowland annotates the notes too: "Otho Nicholson").
    Returns the selector and how it was found, or (None, None)."""
    for words in _anchor_words(lemma):
        ms = list(re.finditer(rf"(?<![\w’'-]){re.escape(words)}(?![\w’'-])", text, re.I))
        if len(ms) == 1 and (sel := obsolete._selector(cid, text, ms[0].start(), ms[0].end())):
            return sel, "block"
    if len(WORD.findall(lemma)) == 1 and len(lemma.strip(" ,.;:")) >= 5:
        i = _stem_hit(text, lemma.strip(" ,.;:"), start, at)
        if i >= 0 and (sel := obsolete._selector(cid, text, i, WORD.match(text, i).end())):
            return sel, "stem"
    found = []
    for note in e.iter(T("note")):
        if note.get("type") != "side" or not note.get(XML_ID):
            continue
        ntext = public_text(note, notes=True)
        for words in _anchor_words(lemma):
            ms = list(re.finditer(rf"(?<![\w’'-]){re.escape(words)}(?![\w’'-])", ntext, re.I))
            if ms:
                found.append((note, ntext, ms))
                break
    if len(found) == 1 and len(found[0][2]) == 1:
        note, ntext, ms = found[0]
        if sel := obsolete._selector(public_id(note.get(XML_ID)), ntext, ms[0].start(), ms[0].end()):
            return {**sel, "on": "note"}, "sidenote"
    return None, None


def entries(unit: str, stats: Counter | dict) -> list[dict]:
    """Every Gowland entry on this unit's paragraphs and verse groups: {endnote, n, seg, kind, lemma, selector,
    target (pointers)}. The selector spans the lemma's words where they are found, else it is None and the entry
    stands at its anchor (`at`: the endnote's anchor in the block, by its endnote id)."""
    notes = endnotes()
    div = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot().find(f".//{T('div')}")
    out = []
    for e in div.iter(T("p"), T("lg"), T("l"), T("item"), T("head"), T("quote")):
        if not e.get(XML_ID) or e.find(f".//{ED('enref')}") is None:
            continue
        if any(a.tag in (T("p"), T("lg"), T("item"), T("head"), T("quote")) for a in e.iterancestors()) or \
                any(a.tag == T("note") for a in e.iterancestors()):
            continue
        cid = public_id(e.get(XML_ID))
        text, anchors = glosses._text_with_anchors(e)
        if text != public_text(e):
            stats["gowland_text_mismatch"] = stats.get("gowland_text_mismatch", 0) + 1
            continue
        start = 0
        for target, at in anchors:
            en = notes.get(target)
            if en is None:
                stats["gowland_endnote_missing"] = stats.get("gowland_endnote_missing", 0) + 1
                continue
            for k, (lemma, note) in enumerate(segments(en)):
                kd = kind(lemma, note)
                rec = {"endnote": target, "n": en.get("n"), "seg": k, "kind": kd, "lemma": lemma,
                       "selector": None, "rule": RULE}
                if kd == "pointer":
                    refs = refs_in(note)
                    rec["targets"] = [t for num, lab in refs if (t := pointer_target(num, lab))]
                    if m := BOOK_REF.match(note):  # a place in the Anatomy, linked as a cross-reference
                        refs, rec["unit"] = [m.group(1)], m.group(1)
                        rec["targets"] = [m.group(1)] if (paths.TEXT / f"{m.group(1)}.xml").exists() else []
                    key = "gowland_pointer_resolved" if len(rec["targets"]) == len(refs) else \
                        "gowland_pointer_unresolved"
                    stats[key] = stats.get(key, 0) + 1
                elif refs := other_pointers(note):
                    rec["see"] = refs  # a longer note that sends the reader on its way ("on whom, see above, n. 10")
                for words in _anchor_words(lemma):
                    i = glosses._last_word(text, words, start, at)
                    if i >= 0 and (sel := obsolete._selector(cid, text, i, i + len(words))):
                        rec["selector"] = sel
                        break
                if rec["selector"] is None and kd != "pointer" and lemma:
                    rec["selector"], how = _fallback(e, cid, text, start, at, lemma)
                    if how:
                        stats[f"gowland_placed_by_{how}"] = stats.get(f"gowland_placed_by_{how}", 0) + 1
                stats[f"gowland_{kd}"] = stats.get(f"gowland_{kd}", 0) + 1
                stats["gowland_anchored_on_words" if rec["selector"] else "gowland_anchored_at_marker"] = \
                    stats.get("gowland_anchored_on_words" if rec["selector"] else "gowland_anchored_at_marker", 0) + 1
                out.append(rec)
            start = at
    return out


def note_text(endnote: str, seg: int) -> str:
    """Gowland's wording of one entry, for the private page only (never for a layer)."""
    segs = segments(endnotes()[endnote])
    return segs[seg][1] if seg < len(segs) else ""


def other_pointers(note: str) -> list[str]:
    """Endnote ids that a longer note sends the reader to on the way ("on whom, see above, n. 10 (3.2.2)")."""
    return [t for num, lab in refs_in(note) if (t := pointer_target(num, lab))]


def refs_in(note: str) -> list[tuple[str, str]]:
    """(number, chapter label) for every note Gowland points to, "nn. 181, 187 (1.2.3)" giving two."""
    return [(n, lab) for nums, lab in POINTER_ANY.findall(note) for n in re.split(r", | and | or ", nums)]
