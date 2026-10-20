"""Independent EPUB counter.

This module deliberately shares NO code with burton.ingest. It reads the unzipped EPUB with
plain lxml and its own simple rules, so that a bug in the ingest code cannot hide itself
from verification (CLAUDE.md, "Verifiers are independent of the code they verify").
"""

import re
from functools import lru_cache
from pathlib import Path

from lxml import etree

XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_TYPE = "{http://www.idpf.org/2007/ops}type"

BURTON_FILES = [
    "preface001", "preface002", "preface003", "preface005", "preface006", "preface007",
    "preface010", "chapter001", "chapter001-01", "chapter001-02", "chapter001-03", "chapter002",
    "chapter002-01", "chapter002-02", "chapter003", "chapter003-01", "chapter003-02",
    "chapter003-03", "chapter003-04",
]
# Gowland's whole-page translations (preface004, preface008) are counted separately.
GOWLAND_PAGES = ["preface004", "preface008"]
SIDENOTE_FILES = ["footnotes", "footnotesa", "footnotesb", "footnotesc"]
ENDNOTE_FILES = ["notes001", "notes002", "notes003"]

BLOCK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "blockquote", "div", "section",
         "figure", "aside", "table", "tr", "ol", "ul"}
GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")


def local(tag) -> str:
    return tag.split("}", 1)[1] if isinstance(tag, str) and "}" in tag else str(tag)


@lru_cache(maxsize=64)
def doc(xhtml_dir: Path, name: str):
    return etree.parse(str(xhtml_dir / f"{name}.xhtml"))


def is_noteref(el) -> bool:
    return local(el.tag) == "a" and el.get(EPUB_TYPE) == "noteref"


def note_kind(el) -> str:
    target = el.get("href", "").split("#")[0].replace(".xhtml", "")
    if target in SIDENOTE_FILES:
        return "side"
    if target in ENDNOTE_FILES:
        return "end"
    return "other"


def plain(el) -> str:
    """Visible text of an element: note-marker text dropped, block boundaries as newlines."""
    out: list[str] = []

    def walk(e):
        tag = local(e.tag)
        if not isinstance(e.tag, str):  # comments, PIs
            if e.tail:
                out.append(e.tail)
            return
        if is_noteref(e) or (tag == "a" and e.get("class") == "backlink"):
            pass
        else:
            if tag in BLOCK:
                out.append("\n")
            if tag == "br":
                out.append("\n")
            if e.text:
                out.append(e.text)
            for c in e:
                walk(c)
            if tag in BLOCK:
                out.append("\n")
        if e.tail:
            out.append(e.tail)

    tail = el.tail
    el.tail = None
    try:
        walk(el)
    finally:
        el.tail = tail
    return "".join(out)


# ---------------------------------------------------------------- whole book

def book_counts(xhtml_dir: Path) -> dict[str, int]:
    c = {"sidenote_refs": 0, "endnote_refs": 0, "pagebreaks": 0,
         "sidenote_refs_on_gowland_pages": 0, "endnote_refs_on_gowland_pages": 0,
         "pagebreaks_on_gowland_pages": 0,
         "sidenote_bodies": 0, "endnote_bodies": 0, "greek_chars_text": 0, "greek_chars_sidenotes": 0}
    for name in BURTON_FILES + GOWLAND_PAGES:
        suffix = "_on_gowland_pages" if name in GOWLAND_PAGES else ""
        root = doc(xhtml_dir, name).getroot()
        for el in root.iter():
            if is_noteref(el):
                k = note_kind(el)
                if k in ("side", "end"):
                    c[("sidenote_refs" if k == "side" else "endnote_refs") + suffix] += 1
            if el.get(EPUB_TYPE) == "pagebreak":
                c["pagebreaks" + suffix] += 1
        if not suffix:
            body = root.find(f"{{{XHTML_NS}}}body")
            c["greek_chars_text"] += len(GREEK.findall(plain(body)))
    for name in SIDENOTE_FILES:
        root = doc(xhtml_dir, name).getroot()
        c["sidenote_bodies"] += sum(1 for el in root.iter(f"{{{XHTML_NS}}}aside"))
        c["greek_chars_sidenotes"] += len(GREEK.findall(plain(root.find(f"{{{XHTML_NS}}}body"))))
    for name in ENDNOTE_FILES:
        root = doc(xhtml_dir, name).getroot()
        c["endnote_bodies"] += sum(1 for el in root.iter(f"{{{XHTML_NS}}}aside"))
    c["nav_units"] = len(nav_units(xhtml_dir))
    return c


def print_book_counts(xhtml_dir: Path) -> None:
    for k, v in book_counts(xhtml_dir).items():
        print(f"{k:24} {v:>7,}")


# ---------------------------------------------------------------- units

NAV_RE = re.compile(r"^(\d+\.\d+\.\d+\.\d+)\s+(.*)$", re.S)


def nav_units(xhtml_dir: Path) -> list[tuple[str, str, str, str]]:
    """[(unit, file, fragment, title)] in nav order, from the EPUB's own navigation document."""
    root = doc(xhtml_dir, "nav").getroot()
    out = []
    for a in root.iter(f"{{{XHTML_NS}}}a"):
        text = re.sub(r"\s+", " ", "".join(a.itertext())).strip()
        m = NAV_RE.match(text)
        if m:
            f, _, frag = a.get("href").partition("#")
            out.append((m.group(1), f.replace(".xhtml", ""), frag, m.group(2)))
    return out


def _is_heading_like(el) -> bool:
    tag = local(el.tag)
    return tag in ("h2", "h3", "h4") or (tag == "figure" and el.get("class") == "landscape_small")


def _unit_start(el):
    """Walk back from the nav anchor over the run of headings/heading-images that precede it."""
    start = el
    prev = el.getprevious()
    while prev is not None and _is_heading_like(prev):
        start = prev
        prev = prev.getprevious()
    return start


# Front-matter pages: one page = one unit (an independent copy of the mapping; not imported from ingest)
FRONT_FILES = {"argument": "preface001", "dedication": "preface002", "ad-librum": "preface003",
               "ad-librum-gowland": "preface004", "abstract": "preface005", "djr": "preface006",
               "lectori": "preface007", "lectori-gowland": "preface008", "heraclite": "preface010"}
PARTITION_FILES = ["chapter001-01", "chapter001-02", "chapter001-03", "chapter002-01", "chapter002-02",
                   "chapter003-01", "chapter003-02", "chapter003-03", "chapter003-04"]


def section_children(xhtml_dir: Path, fname: str) -> list:
    sec = doc(xhtml_dir, fname).getroot().find(f"{{{XHTML_NS}}}body/{{{XHTML_NS}}}section")
    return [k for k in sec if isinstance(k.tag, str)]


def file_text(xhtml_dir: Path, fname: str) -> str:
    """All visible text of a page's section, with no unit boundaries involved (coverage check)."""
    return "\n".join(plain(k) for k in section_children(xhtml_dir, fname))


def units_by_file(xhtml_dir: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {f: [u] for u, f in FRONT_FILES.items()}
    for unit, fname, _, _ in nav_units(xhtml_dir):
        out.setdefault(fname, []).append(unit)
    return out


def unit_elements(xhtml_dir: Path, unit: str) -> tuple[str, list]:
    """Top-level elements belonging to a unit, by the counter's own boundary rule."""
    if unit in FRONT_FILES:
        return FRONT_FILES[unit], section_children(xhtml_dir, FRONT_FILES[unit])
    units = nav_units(xhtml_dir)
    keys = [u[0] for u in units]
    i = keys.index(unit)
    _, fname, frag, _ = units[i]
    root = doc(xhtml_dir, fname).getroot()
    anchor = root.xpath(f"//*[@id='{frag}']")[0]
    start = _unit_start(anchor)
    stop = None
    if i + 1 < len(units) and units[i + 1][1] == fname:
        nxt = root.xpath(f"//*[@id='{units[i + 1][2]}']")[0]
        stop = _unit_start(nxt)
    els = []
    el = start
    while el is not None and el is not stop:
        els.append(el)
        el = el.getnext()
    return fname, els


def unit_counts(xhtml_dir: Path, unit: str) -> dict:
    fname, els = unit_elements(xhtml_dir, unit)
    c = {"sidenote_refs": 0, "endnote_refs": 0, "pagebreaks": 0, "paragraphs": 0, "verse_lines": 0,
         "greek_chars": 0, "heading_images": 0}
    sidenote_ids: list[str] = []
    sidenote_numbers: list[int] = []
    for top in els:
        for el in top.iter():
            if not isinstance(el.tag, str):
                continue
            tag, cls = local(el.tag), (el.get("class") or "")
            if is_noteref(el):
                k = note_kind(el)
                if k == "side":
                    c["sidenote_refs"] += 1
                    sidenote_ids.append(el.get("href"))
                    sidenote_numbers.append(int(re.sub(r"\D", "", "".join(el.itertext()))))
                elif k == "end":
                    c["endnote_refs"] += 1
            elif el.get(EPUB_TYPE) == "pagebreak":
                c["pagebreaks"] += 1
            elif tag == "p":
                if cls.startswith(("verse", "poetry_line", "poemverse")):
                    c["verse_lines"] += 1
                else:
                    c["paragraphs"] += 1
            elif tag == "figure" and cls == "landscape_small":
                c["heading_images"] += 1
        c["greek_chars"] += len(GREEK.findall(plain(top)))
    c["sidenote_numbers"] = sidenote_numbers
    c["main_text"] = "\n".join(plain(e) for e in els)
    notes = []
    for href in sidenote_ids:
        f, _, frag = href.partition("#")
        aside = doc(xhtml_dir, f.replace(".xhtml", "")).getroot().xpath(f"//*[@id='{frag}']")
        notes.append(plain(aside[0]) if aside else None)
    c["sidenote_texts"] = notes
    c["sidenote_greek_chars"] = sum(len(GREEK.findall(t or "")) for t in notes)
    c["file"] = fname
    return c
