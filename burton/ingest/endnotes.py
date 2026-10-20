"""Gowland's Explanatory Notes -> data/text/gowland-endnotes.xml (private build only).

Every element here is Gowland's editorial matter (resp=#gowland): it is never rendered in the public
build and never sent to a model. The texts are kept as in the EPUB; only the backlink number is dropped
(it is the note number, kept in @n).
"""

from collections import Counter

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..tei import ED, XML_ID, XML_LANG, T, el
from . import convert, epub
from .run import wrap_document

FILES = ["notes001", "notes002", "notes003"]
OUT = paths.TEXT / "gowland-endnotes.xml"


def ingest() -> Counter:
    stats: Counter = Counter()
    div = el("div", {"type": "front", "n": "gowland-endnotes", "resp": "#gowland"})
    div.set(XML_ID, "ugowland-endnotes")
    for f in FILES:
        ctx = convert.Ctx("gowland-endnotes", f)
        body = epub.load(f).getroot().find(f"{{{epub.XH}}}body")
        for aside in body.iter(f"{{{epub.XH}}}aside"):
            p = aside.find(f"{{{epub.XH}}}p")
            note = el(ED("endnote"), {"n": None, "src": f"{f}.xhtml#{aside.get('id')}"})
            note.set(XML_ID, aside.get("id"))
            back = p.find(f"{{{epub.XH}}}a")
            note.set("n", "".join(back.itertext()).rstrip(".") if back is not None else "")
            convert.inline_into(p, note, ctx, f)
            convert._drop_backlink(note, note.get("n"))
            note.tail = "\n"
            div.append(note)
            stats["endnotes"] += 1
        stats.update({f"unknown:{k}": v for k, v in ctx.unknown.items()})
    tree = wrap_document(div, "gowland-endnotes", "notes001-003")
    xml = etree.tostring(tree, encoding="unicode")
    atomic_write_text(OUT, "<?xml version='1.0' encoding='UTF-8'?>\n" + xml + "\n")
    return stats


def bodies() -> dict[str, str]:
    """{endnote id: plain text} from the generated file."""
    if not OUT.exists():
        return {}
    root = etree.parse(str(OUT)).getroot()
    return {e.get(XML_ID): " ".join("".join(e.itertext()).split()) for e in root.iter(ED("endnote"))}


__all__ = ["ingest", "bodies", "T", "XML_LANG"]
