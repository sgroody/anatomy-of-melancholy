"""Build translation packets from the base text. No Gowland matter ever enters a packet."""

import hashlib
import json
import unicodedata

from lxml import etree

from .. import paths
from ..tei import ED, XML_ID, XML_LANG, T, public_id
from ..textview import public_text

BLOCKS = (T("p"), T("quote"), T("head"))


def sha1(text: str) -> str:
    return hashlib.sha1(" ".join(unicodedata.normalize("NFC", text).split()).encode()).hexdigest()


def load(unit: str):
    return etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()


def _block_of(e):
    """The paragraph, block quote or heading that contains e."""
    x = e
    while x is not None and x.tag not in BLOCKS:
        x = x.getparent()
    if x is None:  # verse or list items standing outside any paragraph: the outermost lg or item
        x = [a for a in (e, *e.iterancestors()) if a.tag in (T("lg"), T("item"))][-1]
    return x


def _sibling_text(block, step: int, limit: int = 700) -> str:
    x = block.getnext() if step > 0 else block.getprevious()
    if x is None or not isinstance(x.tag, str):
        return ""
    t = public_text(x)
    return t[:limit] + ("…" if len(t) > limit else "")


def _selftrans(unit: str) -> dict:
    f = paths.LAYERS / "selftrans" / f"{unit}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _title(div) -> str:
    return next((public_text(h) for h in div.iter(T("head")) if h.get("type") == "title"), "")


def passages(unit: str) -> list[dict]:
    root = load(unit)
    div = root.find(f".//{T('div')}")
    title = _title(div)
    signals = _selftrans(unit)
    out = []
    for e in div.iter():
        if not isinstance(e.tag, str) or e.get("ana") != "foreign":
            continue
        pid = public_id(e.get(XML_ID))
        in_note = any(a.tag == T("note") for a in e.iterancestors())
        container = next(a for a in e.iterancestors() if a.tag == T("note")) if in_note else _block_of(e)
        text = public_text(e)
        item = {
            "id": pid,
            "lang": e.get(XML_LANG),
            "kind": "verse" if e.tag == T("lg") else "phrase",
            "location": "sidenote" if in_note else "text",
            "text": text,
            "paragraph": public_text(container, mark=e.get(XML_ID), notes=in_note),
            "sidenotes": [] if in_note else [public_text(n, notes=True) for n in container.iter(T("note"))],
        }
        block = _block_of(e)
        if in_note:
            # Burton's text around the point where the note is anchored (often his own rendering)
            whole = public_text(block, note_marker=container.get(XML_ID))
            at = whole.find("⟦sidenote⟧")
            item["main_text_at_note"] = whole[max(0, at - 450): at + 450]
        else:
            item["before"] = _sibling_text(block, -1)
            item["after"] = _sibling_text(block, +1)
        if e.tag == T("lg"):
            nxt = e.getnext()
            if nxt is not None and nxt.get("type") == "translation-block":
                item["burton_english_following"] = public_text(nxt)
        st = signals.get(pid)
        if st and st.get("text_sha1") == sha1(text):
            # rules-only hints (SPEC §6.2): Burton's English spans that may render the passage
            item["selftrans_signals"] = st["signals"]
            item["burton_english_candidates"] = [{"position": c["position"], "text": c["selector"]["exact"]}
                                                 for c in st["candidates"]]
        out.append({"packet_item": item, "text_sha1": sha1(text),
                    "bracket_follows": _gowland_follows(e)})
    return [dict(o, unit=unit, title=title) for o in out]


def gloss_item(unit: str, element_id: str) -> dict:
    """A gloss-only item (Chaucer): an element of Burton's English, keyed by its own id, that gets
    glosses of obsolete words and no translation."""
    root = load(unit)
    div = root.find(f".//{T('div')}")
    e = next(x for x in root.iter() if isinstance(x.tag, str) and x.get(XML_ID) == f"u{element_id}")
    text = public_text(e)
    block = _block_of(e)
    item = {"id": element_id, "lang": "enm", "kind": "gloss-only", "location": "text", "text": text,
            "paragraph": public_text(block, mark=e.get(XML_ID)),
            "before": _sibling_text(block, -1), "after": _sibling_text(block, +1), "sidenotes": []}
    return {"packet_item": item, "text_sha1": sha1(text), "bracket_follows": False, "unit": unit,
            "title": _title(div)}


def _gowland_follows(e) -> bool:
    """Only a yes/no signal derived from the presence of a Gowland bracket; its text is never used."""
    nxt = e.getnext()
    return nxt is not None and nxt.tag in (ED("trans"), ED("verse-trans"))


def input_hash(item: dict, prompt: str, model: str, glossary_version: int) -> str:
    blob = json.dumps({"item": item, "prompt": prompt, "model": model, "glossary": glossary_version},
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def render_packet(unit: str, title: str, items: list[dict]) -> str:
    head = {"subsection": unit, "subsection_title": title, "passages": items}
    return (
        "Translate the passages in this packet. Return one entry per passage id, in order.\n\n"
        + json.dumps(head, ensure_ascii=False, indent=2)
    )
