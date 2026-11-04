"""`burton citations-inline`: citations Burton gives in his running text, not in a sidenote ("saith Avicenna,
lib. 3 Fen 1 Tract. 4 cap. 18", "’Tis all for your sins, Hag. 1. 9, 10") -> data/layers/citations-inline/<unit>.json.

Rules only, with the sidenote parser's tables (burton/layers/citations.py, data/abbreviations.yaml). A run of
the main text counts as a citation only where it is anchored twice over:
* it opens with an author form from the tables, and a locator with a number ("lib. 3", "cap. 18") follows within
  four tokens; or
* it opens with a Bible book form followed by a chapter number, after a stop, a comma or the start of the block.
A name alone ("as Plato saith") is not a citation, and an unknown name is never read as an author: what the
tables do not know stays out of this layer (the sidenote layer's model pass, `expand-citations`, is where unknown
forms are taken up).

Each record points into the text with a text-quote selector {in, exact, prefix, suffix} that must match exactly
once in the block's public text (Gowland's matter removed, so his brackets never reach a layer). Keys are the
block's public id and the run's character offset in that text (as in data/layers/xrefs-relative/).
"""

import json
import re
from collections import Counter

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..ingest.epub import all_units
from ..tei import XML_ID, T, public_id
from ..textview import public_text
from . import citations as cit

METHOD = "rules/inline-v1"
LAYER = "citations-inline"
BLOCKS = (T("p"), T("l"), T("item"), T("head"), T("quote"))
SPAN_TOKENS = 30  # a citation in the text is short; the parser reads at most this many tokens from its head


def _token_spans(text: str) -> list[tuple[int, int]]:
    return [m.span() for m in cit.TOKEN.finditer(text)]


ROMAN = re.compile(r"^(?:x{0,3})(?:ix|iv|v?i{0,3})$|^(?:X{0,3})(?:IX|IV|V?I{0,3})$")


def _real_number(n: str) -> bool:
    """An Arabic number, or a well-formed Roman one below 40: in running text a lower-case word such as "ill"
    or "civil" also matches the parser's loose numeral pattern."""
    return bool(n) and (any(ch.isdigit() for ch in n) or bool(ROMAN.match(n)))


def _heads(toks: list[str]) -> list[int]:
    """Token indices where an in-text citation may start (see the module docstring)."""
    t = cit.tables()
    out = []
    for i, tok in enumerate(toks):
        prev = toks[i - 1] if i else "."
        b = cit._bare(tok)
        if b in t["bible"] and i + 1 < len(toks) and toks[i + 1][:1].isdigit() and \
                (i == 0 or prev.endswith(".") or prev in {",", ";", ":", "("}):
            out.append(i)
        elif (m := cit._match_author(toks, i)) and len(m[1]["candidates"]) == 1 and \
                cit._locus_soon(toks, i + m[0] - 1, within=4):
            out.append(i)
    return out


def scan_block(text: str) -> list[dict]:
    """In-text citations in one block's public text: [{start, end, citation}], in order, not overlapping."""
    spans = _token_spans(text)
    toks = [text[a:b] for a, b in spans]
    found, taken = [], -1
    for i in _heads(toks):
        if i <= taken:
            continue
        window = toks[i:i + SPAN_TOKENS]
        parsed = cit.parse_note(" ".join(window))
        if not parsed or parsed[0]["kind"] not in ("author", "bible") or not parsed[0]["locus"]:
            continue
        c = parsed[0]
        if not c.get("author"):
            continue
        if c["author"] == "bible" and (c["work_words"] or c["odd"] or c.get("part_title")):
            continue  # a Bible book takes only numbers: "Tit. 10 de Horol." is Pancirollus's title 10
        if not all(_real_number(n) for _, ns in c["locus"] for n in ns.split(", ")):
            continue  # "Gellius, an ill habit of the body": "an ill" is prose, not "year ill"
        n = len(cit.tokenize(c["raw"]))  # the citation's own tokens, from its head
        j = min(i + n, len(toks)) - 1
        if ":" in toks[i:j + 1]:  # "Austin ep. 52 …, cap. 61 ad Dulcitium Tribunum: so doth Jerome": prose follows
            j = i + toks[i:j + 1].index(":") - 1
        while j > i and (toks[j] in {",", ";", ":", "(", "&"} or toks[j].lower() in {"and", "et"}):
            j -= 1  # "Montaltus cap. 26 and Jason Pratensis": the joining word is not the citation's
        start, end = spans[i][0], spans[j][1]
        found.append({"start": start, "end": end, "citation": c})
        taken = j
    return found


def build(units: list[str] | None = None) -> Counter:
    stats: Counter = Counter()
    for unit in units or all_units():
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        div = root.find(f".//{T('div')}")
        records = {}
        if div is not None and div.get("resp") != "#gowland":
            for b in div.iter(*BLOCKS):
                if b.get(XML_ID) is None or any(a.tag == T("note") for a in b.iterancestors()) or \
                        any(a.tag in BLOCKS for a in b.iterancestors()):
                    continue
                text = public_text(b)
                bid = public_id(b.get(XML_ID))
                for f in scan_block(text):
                    c, exact = f["citation"], text[f["start"]:f["end"]]
                    pre, suf = text[max(0, f["start"] - 30):f["start"]], text[f["end"]:f["end"] + 30]
                    if text.count(pre + exact + suf) != 1:
                        stats["dropped_selector_not_unique"] += 1
                        continue
                    if c.get("author") != "bible" and not c.get("work"):
                        c["work"] = cit._work(c["author"], c["work_words"])
                    rec = {"selector": {"in": bid, "exact": exact, "prefix": pre, "suffix": suf},
                           "raw": exact, "author": c["author"], "work": c.get("work"), "locus": c["locus"],
                           "status": cit._status(c), "method": METHOD, "display": cit._display(c)}
                    if c.get("ambiguous_with"):
                        rec["ambiguous_with"], rec["resolved_by"] = c["ambiguous_with"], c.get("resolved_by")
                    records[f"{bid}-ic{f['start']}"] = rec
                    stats[f"inline_{rec['status']}"] += 1
                    stats["inline_bible" if c["author"] == "bible" else "inline_author"] += 1
        out = paths.LAYERS / LAYER / f"{unit}.json"
        if records:
            out.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(out, json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            stats["units_with_inline"] += 1
        elif out.exists():
            out.unlink()
    return stats


if __name__ == "__main__":  # pragma: no cover
    print(dict(build()))
