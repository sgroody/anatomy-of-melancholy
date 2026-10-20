"""Reading the unzipped EPUB: documents, navigation, and unit boundaries."""

import re
from functools import cache, lru_cache

import yaml
from lxml import etree

from .. import paths

XH = "http://www.w3.org/1999/xhtml"
OPS_TYPE = "{http://www.idpf.org/2007/ops}type"

SIDENOTE_FILES = {"footnotes", "footnotesa", "footnotesb", "footnotesc"}
ENDNOTE_FILES = {"notes001", "notes002", "notes003"}
NUMBER_HEAD = re.compile(r"\b(SUBSECT|SECT|MEMB)\b\.?\s*(\d+)", re.I)


def xlocal(e) -> str:
    t = e.tag
    return t.split("}", 1)[1] if isinstance(t, str) and "}" in t else str(t)


@cache
def load(name: str):
    return etree.parse(str(paths.XHTML / f"{name}.xhtml"))


def by_id(name: str, ident: str):
    found = load(name).getroot().xpath("//*[@id=$i]", i=ident)
    if len(found) != 1:
        raise LookupError(f"{name}#{ident}: found {len(found)} elements")
    return found[0]


def resolve(href: str, here: str):
    f, _, frag = href.partition("#")
    return (f.removesuffix(".xhtml") or here), frag


@lru_cache(maxsize=1)
def heading_images() -> dict:
    with (paths.MANUAL / "heading-images.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def is_heading_image(e) -> str | None:
    if xlocal(e) != "figure":
        return None
    img = e.find(f"{{{XH}}}img")
    if img is None:
        return None
    name = img.get("src", "").rsplit("/", 1)[-1]
    return name if name in heading_images() else None


@lru_cache(maxsize=1)
def nav() -> list[dict]:
    """Units from the EPUB navigation document, in order."""
    out = []
    for a in load("nav").getroot().iter(f"{{{XH}}}a"):
        text = " ".join("".join(a.itertext()).split())
        m = re.match(r"(\d+\.\d+\.\d+\.\d+) (.*)", text)
        if m:
            f, frag = resolve(a.get("href"), "nav")
            out.append({"unit": m.group(1), "file": f, "anchor": frag, "title": m.group(2)})
    return out


def _belongs_before(e) -> bool:
    """Headings and heading images directly before a unit's title belong to that unit."""
    return xlocal(e) in {"h2", "h3", "h4"} or is_heading_image(e) is not None


def unit_range(unit: str) -> tuple[str, list]:
    units = nav()
    idx = next(i for i, u in enumerate(units) if u["unit"] == unit)
    u = units[idx]

    def first_of(entry):
        e = by_id(entry["file"], entry["anchor"])
        while (p := e.getprevious()) is not None and _belongs_before(p):
            e = p
        return e

    start = first_of(u)
    end = None
    if idx + 1 < len(units) and units[idx + 1]["file"] == u["file"]:
        end = first_of(units[idx + 1])
    out, e = [], start
    while e is not None and e is not end:
        if isinstance(e.tag, str):
            out.append(e)
        e = e.getnext()
    return u["file"], out
