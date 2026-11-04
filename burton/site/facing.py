"""Burton's Latin front matter set facing Gowland's translation on its own page (stage 9; private build).

Owner, 2026-11-04: pointing at a line lights its translation; no "[Translation]" heading and no divider; Gowland's
explanatory notes between the two columns, each lighting both; and his translation not a page of its own when it
already faces the original. Ad librum (90 lines) and Heraclite fleas (10) pair line for line; Lectori male feriato is
prose and pairs by paragraph, a block of his that is not a paragraph (a quoted line) joining the paragraph before.

His words are read from the base text at build time and shown labelled as his; nothing here is written to a layer.
"""

import re

from lxml import etree

from .. import paths
from ..tei import ED, XML_ID, T, public_id
from ..textview import public_text
from . import gowland_notes
from .render import gowland_card

# Burton's page -> (Gowland's translation page, or None where it is a block on the same page; the passage it faces)
SOURCES = {"ad-librum": ("ad-librum-gowland", "ad-librum-f2"), "lectori": ("lectori-gowland", "lectori-f2"),
           "heraclite": (None, "heraclite-f1")}
# the passage heading Burton's page, translated by Gowland's own heading (without his "[Translation]")
HEADS = {"lectori": "lectori-f1"}


def _clean(text: str) -> str:
    return " ".join(re.sub(r"[\[\]{}]", "", text).split())


def _div(unit: str):
    return etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot().find(f".//{T('div')}")


def rows_of(div, block=None, verse: bool = True) -> list[str]:
    """Gowland's translation as rows: its verse lines where Burton's passage is verse, else its paragraphs (a block
    of his that is not a paragraph, such as a quoted line, joined to the one before)."""
    src = block if block is not None else div
    if verse:
        return [_clean(public_text(x)) for x in src.iter(T("l"))]
    rows: list[str] = []
    for x in src:
        if not isinstance(x.tag, str) or x.tag == T("head"):
            continue
        t = _clean(public_text(x))
        if x.tag == T("p") or not rows:
            rows.append(t)
        elif t:
            rows[-1] += " " + t
    return rows


ASIDES = {"dedication": "dedication-f1"}  # an inscription with Gowland's translation beside it, not line for line


def sources(unit: str) -> dict:
    """{fid: {"rows": [...], "notes": {row: [html]}}, "heads": {fid: text}, "consumed": bool} for Burton's page."""
    if unit in ASIDES:  # the Dedication: his translation block, set beside the inscription (stage 9)
        block = next((b for b in _div(unit).iter(ED("block"))), None)
        lines = [_clean(public_text(x)) for x in (block.iter(T("p")) if block is not None else [])]
        lines = [x for x in lines if x and x != "Translation"]
        return {"asides": {ASIDES[unit]: lines}, "consumed": bool(lines)} if lines else {}
    if unit not in SOURCES:
        return {}
    gunit, fid = SOURCES[unit]
    notes: dict[int, list[str]] = {}
    heads = {}
    if gunit:
        gdiv = _div(gunit)
        rows = rows_of(gdiv, verse=_is_verse(unit, fid))
        if unit in HEADS and (h := gdiv.find(f".//{T('head')}")) is not None:
            heads[HEADS[unit]] = _clean(public_text(h).replace("[Translation]", ""))
        for e in gowland_notes.entries(gunit, {}):  # his notes on his own English, each on the row of its words
            words = (e.get("selector") or {}).get("exact")
            hits = [k for k, r in enumerate(rows) if words and words in r]
            if len(hits) == 1:
                html = gowland_card(e, gowland_notes, f"fn-{e['endnote']}-{e['seg']}")
                html = html.replace('class="mn mn-gw"', 'class="ftr-note"', 1)
                html = re.sub(r' id="[^"]*"', "", html, count=1)
                if len(re.sub(r"<[^>]+>", "", html)) > 200:  # a long note is shortened, with "more" to read it
                    html = html.replace('class="ftr-note"', 'class="ftr-note ftr-long"', 1)
                    html = html[:-len("</span>")] + '<button type="button" class="ftr-more">more</button></span>'
                notes.setdefault(hits[0] + 1, []).append(html)
    else:
        div = _div(unit)
        block = next((b for b in div.iter(ED("block"))), None)
        rows = rows_of(div, block, verse=_is_verse(unit, fid)) if block is not None else []
    return {"facing": {fid: {"rows": rows, "notes": notes}} if rows else {},
            "heads": heads, "from": gunit, "consumed": gunit is None and bool(rows)}


def _is_verse(unit: str, fid: str) -> bool:
    e = next((x for x in _div(unit).iter() if x.get(XML_ID) and public_id(x.get(XML_ID)) == fid), None)
    return e is not None and e.tag == T("lg")


def target_rows(div, fid: str) -> int:
    """How many rows Burton's passage has: its verse lines, or its paragraphs."""
    e = next((x for x in div.iter() if x.get(XML_ID) and public_id(x.get(XML_ID)) == fid), None)
    if e is None:
        return 0
    return len(list(e.iter(T("l")))) if e.tag == T("lg") else len(list(e.iter(T("p"))))
