"""XHTML (Gowland EPUB) -> TEI-flavoured elements. Structure and typography only.

No text is altered here. Gowland's bracketed material and language tagging are later passes.
"""

import re
from collections import Counter

from ..tei import ED, el, put_items
from .epub import (
    ENDNOTE_FILES,
    NUMBER_HEAD,
    OPS_TYPE,
    SIDENOTE_FILES,
    XH,
    by_id,
    heading_images,
    is_heading_image,
    resolve,
    xlocal,
)

SPAN_REND = {"small_caps": "sc", "lucida": "lucida", "arial_bold": "symbol", "sup": "sup",
             "sup_it": "sup-i", "small_caps100": "sc"}
VERSE_PREFIXES = ("verse", "poetry_line", "poemverse")


def link_fixes() -> dict:
    """Recorded corrections of mis-targeted note links (data/manual/link-fixes.yaml)."""
    import yaml

    from .. import paths

    f = paths.MANUAL / "link-fixes.yaml"
    rows = yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else []
    return {r["ref"]: r for r in rows or []}


class Ctx:
    def __init__(self, unit: str, file: str):
        self.unit = unit
        self.file = file
        self.unknown: Counter = Counter()
        self.note_ordinal = 0
        self.ignored: Counter = Counter()


def src(file: str, e) -> str | None:
    return f"{file}.xhtml#{e.get('id')}" if e.get("id") else None


# ------------------------------------------------------------------ inline

def inline_into(source, target, ctx: Ctx, file: str) -> None:
    items: list = []
    if source.text:
        items.append(source.text)
    for c in source:
        if isinstance(c.tag, str):
            items.extend(inline(c, ctx, file))
        if c.tail:
            items.append(c.tail)
    put_items(target, items)


def inline(e, ctx: Ctx, file: str) -> list:
    tag, cls = xlocal(e), (e.get("class") or "")
    if e.get(OPS_TYPE) == "pagebreak":
        return [el("pb", {"n": e.get("id", "").removeprefix("pg"), "ed": "penguin2021"})]
    if tag == "a" and e.get(OPS_TYPE) == "noteref":
        f, frag = resolve(e.get("href"), file)
        marker = "".join(e.itertext())
        if f in SIDENOTE_FILES:
            return [sidenote(f, frag, marker, ctx)]
        if f in ENDNOTE_FILES:
            ref_src = f"{file}.xhtml#{e.get('id')}"
            fix = link_fixes().get(ref_src)
            if fix and fix["wrong"] == frag:
                ctx.ignored["link-fix-applied"] += 1
                return [el(ED("enref"), {"target": fix["right"], "n": marker, "src": ref_src, "sic": frag})]
            return [el(ED("enref"), {"target": frag, "n": marker, "src": ref_src})]
        ctx.unknown[f"noteref->{f}"] += 1
    if tag == "img":  # small inline images in Gowland's notes are glyphs (astrological signs)
        return [el("g", {"ref": "img:" + e.get("src", "").rsplit("/", 1)[-1]})]
    if tag == "a" and cls == "backlink":
        return [el("hi", {"rend": "src:a.backlink"})]  # removed again by _drop_backlink
    if tag in ("em", "i"):
        out = el("hi", {"rend": "i"})
    elif tag == "span" and cls in SPAN_REND:
        out = el("hi", {"rend": SPAN_REND[cls]})
    elif tag == "sup":
        out = el("hi", {"rend": "sup"})
    elif tag == "br":
        return [el("lb")]
    else:
        ctx.unknown[f"inline:{tag}.{cls}"] += 1
        out = el("hi", {"rend": f"src:{tag}.{cls}"})
    inline_into(e, out, ctx, file)
    return [out]


def sidenote(f: str, frag: str, marker: str, ctx: Ctx):
    aside = by_id(f, frag)
    ctx.note_ordinal += 1
    note = el("note", {"type": "side", "n": str(ctx.note_ordinal), "src": f"{f}.xhtml#{frag}",
                       "srcN": re.sub(r"\D", "", marker)})
    paras = [p for p in aside if xlocal(p) == "p"]
    if len(paras) != len([c for c in aside if isinstance(c.tag, str)]):
        ctx.unknown["sidenote:non-p child"] += 1
    holders = []
    for i, p in enumerate(paras):
        holder = el("p", {"src": src(f, p)}) if len(paras) > 1 else note
        inline_into(p, holder, ctx, f)
        if i == 0:
            _drop_backlink(holder, marker)
        if holder is not note:
            holders.append(holder)
    for h in holders:
        note.append(h)
    return note


def _drop_backlink(holder, marker: str) -> None:
    """The backlink ("55.") was converted as an unknown <hi>; remove it and the following space."""
    first = holder[0] if len(holder) else None
    if first is None or first.get("rend") != "src:a.backlink":
        raise ValueError(f"sidenote {marker}: expected a backlink first")
    rest = (first.tail or "").removeprefix(" ")
    holder.remove(first)
    holder.text = (holder.text or "") + rest


# ------------------------------------------------------------------ blocks

def head_type(e) -> tuple[str, str | None]:
    cls = e.get("class") or ""
    text = "".join(e.itertext())
    if cls.startswith("chapter_title"):
        return "partition", None
    if NUMBER_HEAD.search(text):
        levels = [m.group(1).lower() for m in NUMBER_HEAD.finditer(text)]
        return "number", " ".join(levels)
    if cls.startswith(("HeadA", "booktitle", "poem_title")):
        return "title", None
    return "other", cls


def block(e, ctx: Ctx, file: str):
    tag, cls = xlocal(e), (e.get("class") or "")
    if tag == "hr":
        ctx.ignored["hr"] += 1
        return None
    if tag == "figure":
        img = e.find(f"{{{XH}}}img")
        src_img = img.get("src", "") if img is not None else ""
        if "prh_core_assets" in src_img:  # publisher's logo: not part of the book
            ctx.ignored["publisher-logo"] += 1
            return None
    if (img := is_heading_image(e)) is not None:
        spec = heading_images()[img]
        h = el("head", {"type": spec["role"], "facs": img, "resp": "#editor", "src": src(file, e)})
        if spec.get("italic"):
            text = spec["text"]
            body, dot = (text[:-1], ".") if text.endswith(".") else (text, "")
            h.append(el("hi", {"rend": "i"}, body))
            if dot:
                h[-1].tail = dot
        else:
            h.text = spec["text"]
        return h
    if tag in ("h2", "h3", "h4"):
        t, sub = head_type(e)
        h = el("head", {"type": t, "subtype": sub, "src": src(file, e)})
        inline_into(e, h, ctx, file)
        return h
    if tag == "p":
        if cls.startswith(VERSE_PREFIXES):
            lg = el("lg")
            lg.append(line(e, ctx, file))
            return lg
        p = el("p", {"rend": cls or None, "src": src(file, e)})
        inline_into(e, p, ctx, file)
        return p
    if tag == "blockquote":
        return quote(e, ctx, file)
    if tag in ("ol", "ul"):
        lst = el("list", {"rend": cls or None, "src": src(file, e)})
        for li in e:
            if not isinstance(li.tag, str):
                continue
            if xlocal(li) != "li":
                ctx.unknown[f"list-child:{xlocal(li)}"] += 1
            item = el("item", {"rend": li.get("class") or None, "src": src(file, li)})
            inline_into(li, item, ctx, file)
            lst.append(item)
        return lst
    if tag == "figure" and is_heading_image(e) is None:
        img = e.find(f"{{{XH}}}img")
        fig = el("figure", {"src": src(file, e)})
        fig.append(el("graphic", {"url": img.get("src", "").rsplit("/", 1)[-1]}))
        return fig
    if tag == "div" and cls.startswith("poetry_stanza"):
        lg = el("lg", {"src": src(file, e)})
        for c in e:
            if isinstance(c.tag, str):
                lg.append(line(c, ctx, file))
        return lg
    ctx.unknown[f"block:{tag}.{cls}"] += 1
    p = el("p", {"rend": f"src:{tag}.{cls}", "src": src(file, e)})
    inline_into(e, p, ctx, file)
    return p


def line(e, ctx: Ctx, file: str):
    cls = e.get("class") or ""
    rend = " ".join(t for t in cls.split() if t not in ("verse",)) or None
    ln = el("l", {"rend": rend, "src": src(file, e)})
    inline_into(e, ln, ctx, file)
    return ln


def is_ts(e) -> bool:
    return any(t.startswith("TS") for t in (e.get("class") or "").split())


def quote(e, ctx: Ctx, file: str):
    """blockquote -> quote; consecutive verse lines -> lg, a new lg starting at each TS line."""
    q = el("quote", {"type": "block", "src": src(file, e)})
    current = None
    for c in e:
        if not isinstance(c.tag, str):
            continue
        cls = c.get("class") or ""
        if xlocal(c) == "p" and cls.startswith(VERSE_PREFIXES):
            opens_bracket = "".join(c.itertext()).lstrip().startswith("[")
            if current is None or is_ts(c) or (opens_bracket and len(current)):
                # a new group starts at a TS line, or at a line opening a bracketed translation
                current = el("lg", {"type": "translation-block" if is_ts(c) else None})
                q.append(current)
            current.append(line(c, ctx, file))
        else:
            current = None
            q.append(block(c, ctx, file))
    _mark_gowland_verse(q)
    return q


def _mark_gowland_verse(q) -> None:
    """A verse group whose first line opens '[' and last line closes ']' is Gowland's translation."""
    for lg in list(q):
        if xlocal(lg) != "lg" or len(lg) == 0:
            continue
        first = "".join(lg[0].itertext()).lstrip()
        last = "".join(lg[-1].itertext()).rstrip()
        if first.startswith("[") and last.endswith("]"):
            wrapper = el(ED("verse-trans"))
            q.replace(lg, wrapper)
            wrapper.append(lg)
            lg.attrib.pop("type", None)


def convert_unit(unit: str, file: str, elements: list, *, front: bool = False, resp: str | None = None) -> tuple:
    ctx = Ctx(unit, file)
    div = el("div", {"type": "front" if front else "subsection", "n": unit, "resp": resp})
    for e in elements:
        b = block(e, ctx, file)
        if b is None:
            continue
        b.tail = "\n"
        div.append(b)
    return div, ctx
