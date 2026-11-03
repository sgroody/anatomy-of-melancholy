"""Synopsis source text (M7): the hidden tables behind the 20 synopsis images (SURVEY §6).

The images carry the tree; the hidden table carries the words, flattened and partly reordered. The edition takes
the words only from here, verbatim (code points unchanged), and the tree shape from a hand-made structure file
(data/manual/synopses/<pN>.yaml) that names these paragraphs by id. `burton synopses --checklist` writes the
word-level checklist the transcriber works against: state/m7/<pN>-checklist.tsv.
"""

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text

FILES = {"p1": "chapter001", "p2": "chapter002", "p3": "chapter003"}
GLYPHS = {"⎧", "⎨", "⎩"}  # brace pieces: drawing, not text


def hidden(part: str) -> list[dict]:
    """The hidden table's paragraphs in document order: id, text (verbatim), and whether it is a brace glyph."""
    d = etree.parse(str(paths.XHTML / f"{FILES[part]}.xhtml"))
    out = []
    for p in (p for t in d.iter("{*}table") for p in t.iter("{*}p")):
        text = "".join(p.itertext())
        out.append({"id": p.get("id"), "text": text, "glyph": text.strip() in GLYPHS})
    return out


def images(part: str) -> list[str]:
    d = etree.parse(str(paths.XHTML / f"{FILES[part]}.xhtml"))
    return [i.get("src").rsplit("/", 1)[-1] for i in d.iter("{*}img") if "penguin_logo" not in i.get("src", "")]


def checklist() -> dict:
    out = {}
    for part in FILES:
        rows = [r for r in hidden(part) if not r["glyph"]]
        dest = paths.STATE / "m7" / f"{part}-checklist.tsv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(dest, "id\ttext\n" + "".join(f"{r['id']}\t{' '.join(r['text'].split())}\n" for r in rows))
        out[part] = {"strings": len(rows), "images": images(part)}
    return out
