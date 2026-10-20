"""Shared vocabulary for the TEI-flavoured base text (data/text/*.xml)."""

from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
ED_NS = "https://burton-edition.local/ns/gowland"  # Gowland's editorial matter
XML_NS = "http://www.w3.org/XML/1998/namespace"
NSMAP = {None: TEI_NS, "ed": ED_NS}

XML_ID = f"{{{XML_NS}}}id"
XML_LANG = f"{{{XML_NS}}}lang"


def T(tag: str) -> str:
    """Clark name for a TEI element."""
    return f"{{{TEI_NS}}}{tag}"


def ED(tag: str) -> str:
    return f"{{{ED_NS}}}{tag}"


def el(tag: str, attrib: dict | None = None, text: str | None = None):
    qname = tag if tag.startswith("{") else T(tag)
    e = etree.Element(qname, {k: v for k, v in (attrib or {}).items() if v is not None}, nsmap=NSMAP)
    if text:
        e.text = text
    return e


def local(tag) -> str:
    return tag.split("}", 1)[1] if isinstance(tag, str) and "}" in tag else str(tag)


def is_ed(e) -> bool:
    return isinstance(e.tag, str) and e.tag.startswith(f"{{{ED_NS}}}")


# --- the one place where XML ids and HTML/layer ids are converted (CLAUDE.md, rule 4)

def xml_id(public_id: str) -> str:
    return "u" + public_id


def public_id(xmlid: str) -> str:
    if not xmlid.startswith("u"):
        raise ValueError(f"not a project xml:id: {xmlid!r}")
    return xmlid[1:]


# --- mixed-content helpers

def take_items(e) -> list:
    """Detach an element's mixed content as a list of str | element (tails become str items)."""
    items: list = []
    if e.text:
        items.append(e.text)
    for c in list(e):
        tail = c.tail
        c.tail = None
        e.remove(c)
        items.append(c)
        if tail:
            items.append(tail)
    e.text = None
    return items


def put_items(e, items: list) -> None:
    last = None
    for it in items:
        if isinstance(it, str):
            if not it:
                continue
            if last is None:
                e.text = (e.text or "") + it
            else:
                last.tail = (last.tail or "") + it
        else:
            e.append(it)
            last = it
