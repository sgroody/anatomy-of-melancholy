"""Glosses of obsolete English shown by the reader (M8; off by default, "Obsolete-word glosses").

Sources, first preferred (SPEC §4.2, D6):
1. Gowland's own glosses, private build only, read from his endnotes when the site is built and never
   written to a layer (rule `gowland-gloss-v1` below). His lemma must stand in Burton's sentence before the
   endnote anchor; the gloss is placed on those words.
2. Webster 1913 senses and model-drafted senses from data/layers/obsolete/ (`burton obsolete`).
3. The M5 Chaucer glosses (data/layers/glosses/, by the translation runner).
Each item names its source; machine involvement is named with the model.
"""

import copy
import json
import re

from lxml import etree

from .. import paths
from ..layers import obsolete
from ..tei import ED, XML_ID, T, public_id
from ..textview import public_text

GOWLAND_RULE = "gowland-gloss-v2"
NOT_A_GLOSS = re.compile(r"^(?:A |An |The |See |Cf\.|I\.e\.|That is|Literally|Burton|Here |Or |Probably|Possibly"
                         r"|Perhaps|Presumably|Translated|Quoted|Proverbial|[‘“'\"(\[])")
LEMMA = re.compile(r"^[a-z][a-z’'\- ]*$")
SEP = ""  # a private-use character, never in the text: marks an endnote anchor's place


def _endnotes() -> dict:
    root = etree.parse(str(paths.TEXT / "gowland-endnotes.xml")).getroot()
    return {e.get(XML_ID): e for e in root.iter(ED("endnote"))}


def note_segments(en) -> list[tuple[str, str]]:
    """An endnote's (lemma, note) pairs: an italic lemma followed by ': ' and the note on it."""
    out, kids = [], list(en)
    for i, h in enumerate(kids):
        if h.tag == T("hi") and h.get("rend") == "i" and (h.tail or "").startswith(": "):
            buf, j = [h.tail[2:]], i + 1
            while j < len(kids) and not (kids[j].tag == T("hi") and (kids[j].tail or "").startswith(": ")):
                buf.append("".join(kids[j].itertext()) + (kids[j].tail or ""))
                j += 1
            out.append((" ".join("".join(h.itertext()).split()), " ".join("".join(buf).split())))
    return out


def is_word_gloss(lemma: str, note: str) -> bool:
    """Gowland's note is a gloss of an English word (rule gowland-gloss-v1): a lower-case lemma of at most
    three words, a note of at most ten words with no digits, no capitalised word after its first, and not
    opening as a reference, a paraphrase or a quotation."""
    if not LEMMA.match(lemma) or len(lemma.split()) > 3:
        return False
    words = note.split()
    if not words or len(words) > 10 or re.search(r"\d", note) or NOT_A_GLOSS.match(note):
        return False
    return not any(w[:1].isupper() and w != "I" for w in words[1:])


def _text_with_anchors(e) -> tuple[str, list[tuple[str, int]]]:
    """The container's public text and, for each endnote anchor in it, (endnote id, position)."""
    c = copy.deepcopy(e)
    targets = []
    for a in list(c.iter(ED("enref"))):
        targets.append(a.get("target"))
        mark = etree.Element(T("hi"))  # an ordinary element, so public_text keeps its text
        mark.text, mark.tail = SEP, a.tail
        a.getparent().replace(a, mark)
    raw = public_text(c)
    raw = re.sub(rf" ({SEP}+)(?=[,;:.)])", r"\1", raw)  # as public_text drops the space before punctuation
    out, pos = [], []
    for ch in raw:
        if ch == SEP:
            pos.append(len(out))
        elif not (ch == " " and (not out or out[-1] == " ")):  # the anchor's removal leaves one space, not two
            out.append(ch)
    text = "".join(out).rstrip(" ")
    return text, [(t, p) for t, p in zip(targets, pos, strict=False)]


def _last_word(text: str, lemma: str, start: int, end: int) -> int:
    """Where the lemma last occurs as whole words in text[start:end], or -1 (case-insensitive)."""
    ms = list(re.finditer(rf"(?<![\w’'-]){re.escape(lemma)}(?![\w’'-])", text[start:end], re.I))
    return start + ms[-1].start() if ms else -1


def gowland_items(unit: str, stats: dict) -> list[dict]:
    """Gowland's glosses on this unit's paragraphs and verse groups (private build only). Rule gowland-gloss-v2:
    his endnote anchor closes the stretch the note covers, so the lemma is looked for, as whole words, between
    the previous anchor (or the start of the block) and this one, nearest first; failing that, in the previous
    block after its last anchor."""
    notes = _endnotes()
    div = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot().find(f".//{T('div')}")
    out = []
    prev = None  # (block id, text, position after its last anchor)
    for e in div.iter(T("p"), T("lg")):
        if not e.get(XML_ID) or any(a.tag == T("note") for a in e.iterancestors()):
            continue
        cid = public_id(e.get(XML_ID))
        if e.find(f".//{ED('enref')}") is None:
            prev = (cid, public_text(e), 0)
            continue
        text, anchors = _text_with_anchors(e)
        if text != public_text(e):
            stats["gowland_text_mismatch"] = stats.get("gowland_text_mismatch", 0) + 1
            prev = None
            continue
        start = 0
        for target, at in anchors:
            en = notes.get(target)
            for lemma, note in note_segments(en) if en is not None else []:
                if not is_word_gloss(lemma, note):
                    continue
                stats["gowland_glosses"] = stats.get("gowland_glosses", 0) + 1
                where, k = (cid, text), _last_word(text, lemma, start, at)
                if k < 0 and start == 0 and prev is not None:
                    where, k = (prev[0], prev[1]), _last_word(prev[1], lemma, prev[2], len(prev[1]))
                if k < 0:
                    stats["gowland_lemma_not_found"] = stats.get("gowland_lemma_not_found", 0) + 1
                    continue
                sel = obsolete._selector(where[0], where[1], k, k + len(lemma))
                if sel is None:
                    stats["gowland_no_selector"] = stats.get("gowland_no_selector", 0) + 1
                    continue
                sense = re.split(r"\.\s+(?=[a-z])", note)[0]  # not the next lemma, where it is not set in italics
                out.append({"selector": sel, "headword": lemma, "sense": sense.rstrip(" ."), "source": "gowland",
                            "label": "Gowland 2021"})
            start = at
        prev = (cid, text, anchors[-1][1] if anchors else 0)
    return out


def layer_items(unit: str) -> list[dict]:
    """Webster and machine glosses (data/layers/obsolete/) and the Chaucer glosses (data/layers/glosses/)."""
    out = []
    for rec in obsolete.load_layer(unit).values():
        if rec["verdict"] == "webster" and rec["sense"].startswith("See "):
            continue  # Webster's cross-reference ("See Lickerish."), not a sense: no gloss (round o1)
        if rec["verdict"] == "webster":
            r = rec["ruling"]
            out.append({"selector": rec["selector"], "headword": rec["headword"], "sense": rec["sense"].rstrip(" ."),
                        "source": "webster1913", "label": f"Webster 1913; sense chosen by {r['model']}"})
        elif rec["verdict"] == "other-obsolete":
            out.append({"selector": rec["selector"], "headword": rec["headword"], "sense": rec["sense"].rstrip(" ."),
                        "source": "machine", "label": f"drafted by {rec['model']} ({rec['prompt']}, {rec['date']})"})
    f = paths.LAYERS / "glosses" / f"{unit}.json"
    for rec in (json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}).values():
        for g in rec["glosses"]:
            for it in g["items"]:
                out.append({"selector": it["selector"], "headword": it["headword"], "sense": it["sense"],
                            "source": "machine", "label": f"drafted by {g['model']} ({g['prompt']}, {g['date']})"})
    return out


def items_for(unit: str, profile: str, stats: dict) -> list[dict]:
    """One gloss per place, the preferred source first: Gowland (private), then the layers."""
    def place(i):  # the same word in the same block, whatever context length each selector chose
        s = i["selector"]
        return s["in"], s["exact"], s["prefix"][-8:], s["suffix"][:8]

    items = gowland_items(unit, stats) if profile == "private" else []
    seen = {place(i) for i in items}
    for i in layer_items(unit):
        if place(i) not in seen:
            seen.add(place(i))
            items.append(i)
    return items
