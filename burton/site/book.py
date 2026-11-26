"""The book as the reader sees it: pages in reading order, titles, and the contents tree.

Everything is derived from data/text (and the front-matter order in burton.ingest.epub), so a
re-ingest that changes a title changes the contents, breadcrumbs and pager with it.
"""

from dataclasses import dataclass, field
from functools import cache

from lxml import etree
from markupsafe import Markup, escape

from .. import paths
from ..ingest.epub import BACK, FRONT, MATTER
from ..tei import T
from ..textview import public_text
from .render import inline_html

ORDINAL = ["First", "Second", "Third"]
SYNOPSIS = ["Synopsis", "Synopsis", "Analysis"]  # the source's own word for each


def partition_label(p: int) -> str:
    return f"The {ORDINAL[p - 1]} Partition"


@dataclass
class Page:
    key: str  # unit id, "p1"…, or "home" / "about" / "settings"
    kind: str  # home | front | partition | synopsis | unit | about | settings
    title: str  # plain-text title (source text where the source has one)
    href: str  # directory URL relative to the site root ("" for home)
    gowland: bool = False  # a whole page of Gowland's matter (private build only)
    children: list = field(default_factory=list)
    html: str | None = None  # the title as inline HTML (italics, lang), for contents and pager

    @property
    def title_html(self) -> Markup:
        return Markup(self.html) if self.html is not None else escape(self.title)

    @property
    def number(self) -> str:
        return self.key if self.kind == "unit" else ""


def unit_sort_key(unit: str) -> tuple:
    return tuple(int(x) for x in unit.split("."))


@cache
def unit_title(unit: str) -> tuple[str, str | None]:
    """(plain title, inline HTML title) from the unit's title head; front matter without one
    uses its editorial title."""
    root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
    div = root.find(f".//{T('div')}")
    for h in div.iter(T("head")):
        if h.get("type") == "title":
            return public_text(h), inline_html(h)
    return (MATTER[unit][1] if unit in MATTER else unit), None


def is_gowland_unit(unit: str) -> bool:
    return unit in FRONT and FRONT[unit][2] == "#gowland"


def text_units() -> list[str]:
    """Every unit with a base-text file, in reading order (front matter, the Partitions, back matter)."""
    have = {p.stem for p in paths.TEXT.glob("*.xml")}
    front = [u for u in FRONT if u in have]
    subs = sorted((u for u in have if u[:1].isdigit()), key=unit_sort_key)
    return front + subs + [u for u in BACK if u in have]


@dataclass
class Book:
    profile: str
    units: list[str]  # the units being built, in reading order

    def __post_init__(self):
        self.units = [u for u in self.units if not (self.profile == "public" and is_gowland_unit(u))]
        self.pages: dict[str, Page] = {}
        self.order: list[str] = []  # reading order of front, partition and unit pages
        self.front: list[Page] = []
        self.partitions: list[Page] = []
        self.back: list[Page] = []
        for u in self.units:
            if u in FRONT:
                pg = Page(u, "front", FRONT[u][1], f"{u}/", gowland=is_gowland_unit(u))
                self.front.append(pg)
                self._add(pg)
        subs = [u for u in self.units if u not in MATTER]
        for u in subs:
            p, s, m, _ = (int(x) for x in u.split("."))
            if not self.partitions or self.partitions[-1].key != f"p{p}":
                self._add(Page(f"p{p}", "partition", partition_label(p), f"p{p}/"))
                self.partitions.append(self.pages[f"p{p}"])
                if (paths.DATA / "synopses" / f"p{p}.json").exists():  # Burton prints it after the title
                    self._add(Page(f"p{p}-synopsis", "synopsis", f"{SYNOPSIS[p - 1]} of the {ORDINAL[p - 1]} Partition",
                                   f"p{p}/synopsis/"))
            part = self.partitions[-1]
            sec = self._group(part, f"{p}.{s}", f"Section {s}")
            mem = self._group(sec, f"{p}.{s}.{m}", f"Member {m}")
            pg = Page(u, "unit", *unit_title(u)[:1], f"{u}/", html=unit_title(u)[1])
            mem.children.append(pg)
            self._add(pg)
        for u in self.units:
            if u in BACK:
                pg = Page(u, "back", BACK[u][1], f"{u}/")
                self.back.append(pg)
                self._add(pg)
        self.extra = [Page("about", "about", "About", "about/"),
                      Page("glossary", "glossary", "Glossary", "glossary/"),
                      Page("settings", "settings", "Reading options", "settings/"),
                      Page("authors", "authors", "Authors cited", "authors/"),
                      Page("search", "search", "Search", "search/")]
        for pg in self.extra:
            self.pages[pg.key] = pg

    def _add(self, pg: Page) -> None:
        self.pages[pg.key] = pg
        self.order.append(pg.key)

    def _group(self, parent: Page, key: str, title: str) -> Page:
        if not parent.children or parent.children[-1].key != key:
            parent.children.append(Page(key, "group", title, f"{parent.href}#toc-{key}"))
        return parent.children[-1]

    # ------------------------------------------------------------ navigation
    def reading(self, pg: Page) -> bool:
        """A page on the way through the book by "Next" (owner, 2026-11-04): not the Partition landings or the synopsis
        pages (each Partition's first page opens with its synopsis instead), nor Gowland's translation pages (they face
        their originals)."""
        return pg.kind not in ("partition", "synopsis") and not pg.gowland

    def neighbours(self, key: str) -> tuple[Page | None, Page | None]:
        if key not in self.order:
            return None, None
        i = self.order.index(key)
        prev = next((self.pages[k] for k in reversed(self.order[:i]) if self.reading(self.pages[k])), None)
        nxt = next((self.pages[k] for k in self.order[i + 1:] if self.reading(self.pages[k])), None)
        return prev, nxt

    def crumbs(self, key: str) -> list[tuple[str, str | None]]:
        """(label, href or None for the current page), from the Partition down."""
        pg = self.pages[key]
        if pg.kind == "unit":
            p, s, m, u = pg.key.split(".")
            land = f"p{p}/"
            return [(partition_label(int(p)), land), (f"Section {s}", f"{land}#toc-{p}.{s}"),
                    (f"Member {m}", f"{land}#toc-{p}.{s}.{m}"), (f"Subsection {u}", None)]
        if pg.kind == "partition":
            return [(pg.title, None)]
        if pg.kind == "synopsis":
            p = int(pg.key[1])
            return [(partition_label(p), f"p{p}/"), (SYNOPSIS[p - 1], None)]
        if pg.kind == "front":
            return [("Front matter", "#toc-front"), (pg.title, None)]
        if pg.kind == "back":
            return [("Back matter", "#toc-back"), (pg.title, None)]
        return [(pg.title, None)]

    def partition_of(self, key: str) -> Page | None:
        if key.startswith("p") and key in self.pages:
            return self.pages[key]
        if key[:1].isdigit():
            return self.pages.get(f"p{key.split('.')[0]}")
        return None
