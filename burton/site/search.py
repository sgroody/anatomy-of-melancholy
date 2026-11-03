"""Full-text search (M8): one index per profile, loaded by the search page on demand and precached
by the service worker for offline use.

Documents are what the pages show, in reading order: each paragraph and verse group of Burton's text
(without its sidenotes), each sidenote, and each translation of a foreign passage with the same label
the passage box gives it. Gowland's matter enters only the private index, exactly as on the private
pages: his translations as a labelled source; his brackets and interpolations never as Burton's text.
Matching (case, accents, ligatures) is done in the browser; the index stores the text unaltered.
"""

import json
import unicodedata

from lxml import etree

from .. import paths
from ..tei import ED_NS, XML_ID, XML_LANG, T, public_id
from ..textview import public_text
from .render import Renderer, gowland_versions, label_of

KINDS = ("text", "note", "translation")  # document kinds, by index


def _anchor(e) -> str:
    """The page anchor a match inside `e` links to: its own paragraph, verse group or sidenote, else
    (a heading, a list item) the page's article, whose id is the unit's."""
    for x in [e, *e.iterancestors()]:
        if x.tag in (T("p"), T("lg"), T("note"), T("div")) and x.get(XML_ID):
            return public_id(x.get(XML_ID))
    raise ValueError(f"no anchor for {e.get(XML_ID)}")


def _in_gowland(e) -> bool:
    return any(isinstance(a.tag, str) and a.tag.startswith(f"{{{ED_NS}}}") for a in e.iterancestors())


def unit_docs(unit: str, profile: str, layer: dict, djs: dict) -> tuple[list[list], dict]:
    """[kind, anchor, text] for one unit (translations add the original as (lang, text) and their label),
    and counts."""
    div = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot().find(f".//{T('div')}")
    docs: list[list] = []
    counts = {"text": 0, "note": 0, "translation": 0}
    for e in div.iter(T("p"), T("lg"), T("note")):
        if not e.get(XML_ID):
            continue
        if e.tag == T("note"):
            if profile == "public" and _in_gowland(e):
                continue  # a sidenote inside Gowland's bracket is rendered in the private build only
            kind = 1
        elif _in_gowland(e):
            continue  # Gowland's verse translations are verse groups too: never indexed as Burton's text
        else:
            kind = 0
        text = public_text(e)
        if text:
            docs.append([kind, public_id(e.get(XML_ID)), text])
            counts[KINDS[kind]] += 1
    r = Renderer(unit, profile, layer, djs=djs)
    if profile == "private":
        r.gowland = gowland_versions(div)
    by_id = {public_id(f.get(XML_ID)): f for f in div.iter() if isinstance(f.tag, str) and f.get("ana") == "foreign"
             and f.get(XML_ID)}
    for fid, f in by_id.items():
        if profile == "public" and _in_gowland(f):
            continue
        anchor, orig = _anchor(f), (f.get(XML_LANG) or "", public_text(f))
        for v in r.versions(fid):
            docs.append([2, anchor, v["text"], orig, label_of(v)])
            counts["translation"] += 1
    return docs, counts


def build_index(units: list[str], titles: dict[str, str], profile: str, layer_for) -> tuple[dict, dict]:
    """The index as written to assets/search-index.json, and counts for the build report."""
    labels: list[str] = []
    label_ix: dict[str, int] = {}
    origs: list[list[str]] = []  # [lang, text] of each translated passage, stored once for all its versions
    orig_ix: dict[tuple, int] = {}
    out_units, docs = [], []
    totals = {"text": 0, "note": 0, "translation": 0}
    for i, unit in enumerate(units):
        out_units.append([unit, titles[unit]])
        unit_d, counts = unit_docs(unit, profile, layer_for(unit), layer_for(unit, "djs"))
        for k, v in counts.items():
            totals[k] += v
        for d in unit_d:
            row = [i, *d[:3]]
            if d[0] == 2:
                lab, key = d[4], (i, d[1], *d[3])
                if lab not in label_ix:
                    label_ix[lab] = len(labels)
                    labels.append(lab)
                if key not in orig_ix:
                    orig_ix[key] = len(origs)
                    origs.append(list(d[3]))
                row += [orig_ix[key], label_ix[lab]]
            docs.append(row)
    index = {"profile": profile, "kinds": list(KINDS), "units": out_units, "labels": labels, "origs": origs,
             "docs": docs}
    return index, {"docs": len(docs), **totals, "passages": len(origs), "labels": len(labels)}


def write_index(index: dict, out) -> int:
    text = json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    return len(text.encode("utf-8"))


def codepoints(index: dict) -> set[int]:
    """What the search page can draw from the index (for the font subset)."""
    out: set[int] = set()
    for text in [*(d[3] for d in index["docs"]), *(o[1] for o in index["origs"]), *index["labels"],
                 *(u[1] for u in index["units"])]:
        out |= {ord(c) for c in text if not c.isspace() and unicodedata.category(c) != "Cf"}
    return out
