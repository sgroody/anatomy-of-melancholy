"""TEI base text + layers -> HTML for one unit.

Profiles: `private` renders Gowland's matter (marked data-resp="gowland", hidden by default where
it duplicates our translations); `public` drops it entirely (SPEC §2). Labels for every translation
come from the layer data, never from the template.
"""

import html
import json
import re

from .. import paths
from ..layers import citations as cit_rules
from ..layers import djs as djs_layer
from ..tei import ED, XML_ID, XML_LANG, T, public_id
from ..textview import public_text
from ..translate.validate import primary_machine
from . import kjv
from .hyphenation import soft_hyphenate

PUNCT_START = re.compile(r"^[,;:.)]")
TRAIL_PUNCT = re.compile(r"^[,;:.!?)’”]+")


def esc(s: str | None) -> str:
    return html.escape(s or "", quote=False)


SCRIPT_RUN = re.compile(r"[Ͱ-Ͽἀ-῿][Ͱ-Ͽἀ-῿̀-ͯʼ’'\s,.;:]*"
                        r"(?<=[Ͱ-Ͽἀ-῿̀-ͯʼ])")


def esc_tagged(s: str | None) -> str:
    """Escape layer text (model notes, translations) and tag any Greek in it with lang="grc"."""
    out, pos = [], 0
    for m in SCRIPT_RUN.finditer(s or ""):
        out.append(esc(s[pos:m.start()]))
        out.append(f'<span lang="grc">{esc(m.group(0))}</span>')
        pos = m.end()
    out.append(esc((s or "")[pos:]))
    return "".join(out)


def attr(s: str | None) -> str:
    return html.escape(s or "", quote=True)


def label_of(t: dict) -> str:
    """The full label of a translation's source, from its data (shown behind the ◇ for machine work)."""
    if t["by"] == "machine":
        return f"Machine translation ({t['model']}, prompt {t['prompt']}, {t['date']})"
    if t["by"] == "djs1927":
        page = f", p. {t['page']}" if t.get("page") else ""
        return f"Dell & Jordan-Smith (1927{page}), aligned by rule"
    if t["by"] == "editor":
        return "Editor's translation"
    if t["by"] == "gowland":
        return "Gowland 2021 (private build)"
    return t["by"]


def model_name(model: str) -> str:
    """The visible name of a model: "Claude" for any Claude model (owner, 2026-11-03); the full id stays in the
    data and behind the ◇."""
    return "Claude" if model.startswith("claude") else model


def short_label(t: dict) -> str:
    """The visible label: the source's name only; a machine label is completed by prov()."""
    return {"machine": model_name(t.get("model", "")), "djs1927": "Dell & Jordan-Smith", "editor": "Editor",
            "gowland": "Gowland"}.get(t["by"], t["by"])


def prov(full: str) -> str:
    """The ◇ that carries a machine item's full provenance (owner, 2026-11-03: a small icon, not a prose line)."""
    return f'<span class="prov" role="img" tabindex="0" aria-label="{attr(full)}" title="{attr(full)}"></span>'


def kjv_html(c: dict, counts: dict) -> str:
    """The KJV text of a Bible citation's verses (stage 6), folded after three lines by edition.js; "" where the
    reference gives no verses, or the book needs a number it lacks (counted)."""
    vs = kjv.verses(c["work"].split(".", 1)[1], c.get("book_n"), c.get("ref"))
    if not vs:
        counts["bible_without_verses"] = counts.get("bible_without_verses", 0) + 1
        return ""
    counts["bible_verses"] = counts.get("bible_verses", 0) + 1
    text = " ".join((f'<sup class="kjv-n">{v}</sup>' if len(vs) > 1 else "") + esc(t) for v, t in vs)
    return (f'<span class="kjv" lang="en"><span class="kjv-t">{text}</span> '
            f'<button type="button" class="kjv-more" hidden>more</button> <span class="kjv-l">KJV</span></span>')


LETTERS = "abcdefghijklmnopqrstuvwxyz"


def letter(n: str | None) -> str:
    """Burton's note number as Gowland letters it: a to z, then a again."""
    return LETTERS[(int(n) - 1) % 26] if n and n.isdigit() else (n or "")


# SPEC §6.3: the default order of translation sources (Burton's own rendering is not a source here:
# where he translates a passage himself his English stays in the text). Gowland first: the private build is
# built on his edition (owner, 2026-11-03); the public build has none. The reader can reorder them.
SOURCE_ORDER = ["gowland", "editor", "djs1927", "machine"]
LANG_NAMES = {"la": ("Latin", "Lat."), "grc": ("Greek", "Gk."), "it": ("Italian", "It."), "fr": ("French", "Fr."),
              "es": ("Spanish", "Sp."), "de": ("German", "Ger."), "nl": ("Dutch", "Du."), "he": ("Hebrew", "Heb."),
              "ar": ("Arabic", "Ar."), "enm": ("Middle English", "ME")}
GOWLAND_SKIP = (T("note"), ED("enref"), T("pb"))


def _flat(x) -> str:
    """Text of a Gowland translation element without the sidenotes, endnote anchors and page breaks
    inside it (their tails are kept)."""
    parts = [x.text or ""]
    for c in x:
        if isinstance(c.tag, str) and c.tag not in GOWLAND_SKIP:
            parts.append(_flat(c))
        parts.append(c.tail or "")
    return "".join(parts)


def gowland_versions(div) -> dict[str, str]:
    """Gowland's translation of each foreign passage (ed:trans / ed:verse-trans @for), read from the base
    text at build time for the private build. Never written to a layer, never sent to a model. His
    brackets and braces are dropped for display only; a bracket that runs over several blocks
    (@part I … M … F) is joined from its pieces."""
    pieces = [t for t in div.iter(ED("trans"), ED("verse-trans"))]
    out = {}
    for i, t in enumerate(pieces):
        target = t.get("for")
        if not target:
            continue
        run = [t]
        if t.get("part") == "I":
            for u in pieces[i + 1:]:
                run.append(u)
                if u.get("part") == "F":
                    break
        texts = []
        for piece in run:
            lines = list(piece.iter(T("l")))
            texts.append(" / ".join(_flat(ln) for ln in lines) if lines else _flat(piece))
        text = re.sub(r"[\[\]{}]", "", " ".join(texts))
        out[public_id(target)] = " ".join(text.split())
    return out


FACING_MIN = 4  # verse passages of this many lines or more are set facing their translation, where it fits (T12 B)
INITIAL_UNITS = re.compile(r"^(?:\d+\.\d+\.\d+\.\d+|djr|abstract)$")
BRACE = ('<span class="hb-brace" aria-hidden="true"><svg viewBox="0 0 10 60" preserveAspectRatio="none" '
         'focusable="false"><path d="M9 1 C4 1 5 6 5 14 C5 24 5 28 1 30 C5 32 5 36 5 46 C5 54 4 59 9 59" '
         'fill="none" stroke="currentColor" stroke-width="1"/></svg></span>')
NUMBER_HEAD = re.compile(r"\bThe (\w+) ((?:Section|Member|Subsection)(?:, (?:Member|Subsection))*\.)")


def penguin_head(seg: str, kind: str | None) -> str:
    """Headings set as on the Penguin page (owner's photo, 2026-11-03: R1 B), by markup only, Burton's words and
    stops unchanged: "The / First Partition." on two lines, and "The First" beside a brace over "Section, /
    Member, / Subsection."."""
    if kind == "partition" and (m := re.search(r"\bThe (\w+ Partition\.)", seg)):
        return (seg[:m.start()] + f'<span class="hp-the">The</span> <span class="hp-n">{m.group(1)}</span>'
                + seg[m.end():])
    if kind == "number" and (m := NUMBER_HEAD.search(seg)):
        parts = " ".join(f"<span>{w}</span>" for w in m.group(2).split(" "))
        return (seg[:m.start()] + f'<span class="hb"><span class="hb-the">The {m.group(1)}</span> {BRACE}'
                f'<span class="hb-stack">{parts}</span></span>' + seg[m.end():])
    return seg


class Renderer:
    def __init__(self, unit: str, profile: str, layer: dict, image=None, h1_head=None, djs: dict | None = None,
                 cites: dict | None = None, cite_label: str = "", verified: dict | None = None,
                 findings: dict | None = None):
        self.unit, self.profile, self.layer = unit, profile, layer
        self.verified = {k: v for k, v in (verified or {}).items() if v["status"] == "verified"}
        self.findings = findings or {}  # data/manual/source-findings.yaml: a finding beside the attribution
        self.cites, self.cite_label = cites or {}, cite_label  # M6 citation layer, shown on request
        self.djs = {k: djs_layer.version(r) for k, r in (djs or {}).items() if djs_layer.shown(r, layer.get(k))}
        self.image = image  # callback: graphic file name -> (src, alt, width, height)
        self.plate = None  # callback: (file name, src, alt, width, height) -> the figure's inner HTML, or None
        self.pagemap: dict[str, str] = {}  # Penguin page number -> the unit where that page begins (the Table)
        self.h1_head = h1_head  # the head element rendered as the page's h1
        self.counts = {"sidenotes": 0, "foreign": 0, "gowland_trans": 0, "enrefs": 0, "pbs": 0,
                       "burton_spans": 0, "burton_spans_unplaced": 0, "soft_hyphens": 0, "images": 0,
                       "gowland_versions": 0, "djs_versions": 0, "cite_expansions": 0, "verified_sources": 0,
                       "pagerefs": 0, "pagerefs_linked": 0}
        self.gowland: dict[str, str] = {}  # passage id -> Gowland's translation (private build only)
        self.cexp: dict = {}  # data/layers/citation-expansions/<unit>.json (model expansions)
        self.out: list[str] = []
        self.hoisted: set[str] = set()
        self.langs: list[str] = []
        self.cards: list[str] = []  # margin items (translations of the text), laid out beside their anchors
        self.in_note = 0
        self.initial = None  # the decorated initial: None, "pending" (after the title), "open", "done"
        self.initials: set[str] = set()  # capitals with an initial in this build (none: no initials)
        self.fp_lang: dict[str, str] = {}  # passage id -> its language, for Burton's own renderings (stage 7)
        self.last_block: tuple[str, int] | None = None  # the previous foreign passage in the text: (id, verse lines)
        self.facing_row: int | None = None  # the line number inside a passage set facing its translation

    # ---------------------------------------------------------------- helpers
    def w(self, s: str) -> None:
        self.out.append(s)

    def text(self, s: str | None) -> None:
        if s:
            if self.initial == "open" and s.strip():
                s = self.open_with_initial(s)
            if self.langs and self.langs[-1] in ("la", "grc"):
                h = soft_hyphenate(s, self.langs[-1])
                self.counts["soft_hyphens"] += len(h) - len(s)
                s = h
            self.w(esc(s))

    def open_with_initial(self, s: str) -> str:
        """The first letter of the unit's first paragraph as a decorated initial (owner, 2026-11-03: T2 B, R1 B, I1
        red), the rest of its first word in small capitals. The letter stays in the text for readers and search;
        the images, one per theme, are drawn beside it (data/source/INITIALS.lock)."""
        self.initial = "done"
        i = len(s) - len(s.lstrip())
        ch = s[i:i + 1]
        if not self.initials or ch.upper() not in self.initials:
            return s
        self.counts["initials"] = self.counts.get("initials", 0) + 1
        up = ch.upper()
        self.counts["initial_letters"] = [up]
        self.w(esc(s[:i]) + '<span class="ini" aria-hidden="true">'
               f'<img class="ini-l" src="../assets/initials/red-light-{up}.webp" alt="" width="300" height="300">'
               f'<img class="ini-d" src="../assets/initials/red-dark-{up}.webp" alt="" width="300" height="300">'
               f'</span><span class="ini-ch">{esc(ch)}</span>')
        rest = s[i + 1:]
        if m := re.match(r"[\w’']+", rest):
            self.w(f'<span class="ini-sc">{esc(m.group(0))}</span>')
            rest = rest[m.end():]
        return rest

    def drop_gowland(self) -> bool:
        return self.profile == "public"

    def tail_after_drop(self, tail: str | None) -> None:
        """When an element is dropped, avoid leaving ' ,' behind."""
        if tail and PUNCT_START.match(tail) and self.out and self.out[-1].endswith(" "):
            self.out[-1] = self.out[-1].rstrip(" ")
        self.text(tail)

    def children(self, e) -> None:
        lang = e.get(XML_LANG)
        if lang:
            self.langs.append(lang)
        self.text(e.text)
        for c in e:
            if c.tag == T("foreign") and c.get("ana") == "foreign" and c.tail and TRAIL_PUNCT.match(c.tail):
                # punctuation right after a passage goes inside its box, after the translation, so
                # interlinear mode cannot open a gap between the word and its comma
                punct = TRAIL_PUNCT.match(c.tail).group(0)
                self.foreign(c, punct)
                self.text(c.tail[len(punct):])
                continue
            dropped = self.node(c)
            if dropped:
                self.tail_after_drop(c.tail)
            else:
                self.text(c.tail)
        if lang:
            self.langs.pop()

    # ---------------------------------------------------------------- dispatcher
    def node(self, e) -> bool:
        """Render e (not its tail). Returns True if e was dropped (for tail spacing)."""
        tag = e.tag
        if not isinstance(tag, str):
            return True
        if tag == T("head"):
            return self.head(e)
        if tag == T("p"):
            if self.initial == "pending" and not self.in_note:
                self.initial = "open"
            self.w(f'<p id="{attr(self.pid(e))}"{self.cls(e.get("rend"))}>')
            self.children(e)
            self.w("</p>\n")
        elif tag == T("quote"):
            if e.get("ana") == "foreign":
                self.foreign_block(e, "blockquote", "bq")
            else:
                self.w('<blockquote class="bq">')
                self.children(e)
                self.w("</blockquote>\n")
        elif tag == T("lg"):
            self.lg(e)
        elif tag == T("l"):
            row = ""
            if self.facing_row is not None:  # a line of a passage set facing its translation: its row in the grid
                self.facing_row += 1
                row = f' data-r="{self.facing_row}" style="--r:{self.facing_row}"'
            self.w(f'<span class="l{" " + attr(e.get("rend")) if e.get("rend") else ""}"{row}>')
            self.children(e)
            self.w("</span>")
        elif tag == T("hi"):
            self.hi(e)
        elif tag == T("foreign"):
            if e.get("ana") == "foreign":
                self.foreign(e)
            else:  # script tagging only (e.g. Greek inside Gowland's braces): a lang span, not a passage
                self.w(f'<span lang="{attr(e.get(XML_LANG))}">')
                self.children(e)
                self.w("</span>")
        elif tag == T("note"):
            if e.get(XML_ID) in self.hoisted:
                return True
            self.note(e)
        elif tag == T("pb"):
            if self.drop_gowland():
                return True
            self.counts["pbs"] += 1
            self.w(f'<span class="pb" id="pg-{attr(e.get("n"))}" data-resp="gowland" data-n="{attr(e.get("n"))}" '
                   'aria-hidden="true"></span>')
        elif tag == T("lb"):
            self.w("<br>")
        elif tag == ED("locs"):  # the Table's Penguin page numbers (M8): private build only
            if self.drop_gowland():
                return True
            self.w('<span class="locs" data-resp="gowland">')
            self.children(e)
            self.w("</span>")
        elif tag == ED("pageref"):
            n = e.get("n")
            self.counts["pagerefs"] += 1
            if n in self.pagemap:
                self.counts["pagerefs_linked"] += 1
                self.w(f'<a class="pageref" href="../{attr(self.pagemap[n])}/#pg-{attr(n)}" '
                       f'aria-label="page {attr(n)}">{esc(e.text)}</a>')
            else:
                self.w(f'<span class="pageref pageref-unlinked">{esc(e.text)}</span>')
        elif tag == ED("enref"):
            if self.drop_gowland():
                return True
            self.counts["enrefs"] += 1
            self.w(f'<span class="enref" data-resp="gowland" data-target="{attr(e.get("target"))}"'
                   f' data-n="{attr(e.get("n"))}" aria-hidden="true"></span>')
        elif tag == ED("trans"):
            if self.drop_gowland():
                return True
            self.counts["gowland_trans"] += 1
            # the space before the bracket belongs with it, so hiding the bracket leaves no " ,"
            lead = ""
            if self.out and self.out[-1].endswith(" "):
                self.out[-1], lead = self.out[-1][:-1], " "
            self.w(f'<span class="gowland-tr" data-resp="gowland" title="Gowland 2021 (private build only)">{lead}')
            self.children(e)
            self.w("</span>")
        elif tag == ED("verse-trans"):
            if self.drop_gowland():
                return True
            self.counts["gowland_trans"] += 1
            self.w('<div class="gowland-tr gowland-verse" data-resp="gowland" '
                   'title="Gowland 2021 (private build only)">')
            self.children(e)
            self.w("</div>")
        elif tag == ED("block"):
            if self.drop_gowland():
                return True
            self.counts["gowland_trans"] += 1
            self.w('<div class="gowland-tr gowland-block" data-resp="gowland" '
                   'title="Gowland 2021 (private build only)">')
            self.children(e)
            self.w("</div>\n")
        elif tag == T("figure"):
            self.figure(e)
        elif tag == T("list"):
            self.w(f'<ul class="list {attr(e.get("rend") or "")}">')
            self.children(e)
            self.w("</ul>\n")
        elif tag == T("item"):
            self.w(f'<li{self.cls(e.get("rend"))}>')
            self.children(e)
            self.w("</li>")
        elif tag == T("supplied"):
            if e.get("resp") == "#gowland" and self.drop_gowland():
                return True
            self.w('<span class="supplied" data-resp="gowland">')
            self.children(e)
            self.w("</span>")
        elif tag == T("choice"):
            sic, corr = e.find(T("sic")), e.find(T("corr"))
            self.w(f'<span class="corr" title="source reads: {attr(public_text(sic))}">')
            self.children(corr)
            self.w("</span>")
        else:
            self.w(f'<span data-tei="{attr(tag)}">')
            self.children(e)
            self.w("</span>")
        return False

    def pid(self, e) -> str:
        return public_id(e.get(XML_ID)) if e.get(XML_ID) else ""

    def cls(self, rend: str | None) -> str:
        return f' class="{attr(rend)}"' if rend else ""

    # ---------------------------------------------------------------- elements
    def figure(self, e) -> None:
        g = e.find(T("graphic"))
        src, alt, w, h = self.image(g.get("url"))
        self.counts["images"] += 1
        if self.plate and (mapped := self.plate(g.get("url"), src, alt, w, h)):  # the frontispiece's panels (M8)
            self.w(f'<figure class="plate plate-mapped">{mapped}</figure>\n')
            return
        self.w(f'<figure class="plate"><a href="{attr(src)}"><img src="{attr(src)}" alt="{attr(alt)}" '
               f'width="{w}" height="{h}" loading="lazy" decoding="async"></a></figure>\n')

    def head(self, e) -> bool:
        t = e.get("type")
        source = ' data-source="image"' if e.get("facs") else ""
        sub = f" head-{attr(e.get('subtype'))}" if e.get("subtype") else ""
        tag, cls = ("h1", f"unit-title head-{attr(t)}") if e is self.h1_head else ("p", f"head-{attr(t)}{sub}")
        if e.get("subtype") == "tableHeadA":  # the Table's letters: real headings, for navigation
            tag = "h2"
        self.w(f'<{tag} class="{cls}"{source}>')
        start = len(self.out)
        if e.get("ana") == "foreign":  # a heading that is itself a foreign passage (Lectori male feriato)
            self.foreign(e)
        else:
            self.children(e)
        self.out[start:] = [penguin_head("".join(self.out[start:]), t)]
        self.w(f"</{tag}>\n")
        if e is self.h1_head and INITIAL_UNITS.match(self.unit):
            self.initial = "pending"  # the next paragraph opens with a decorated initial (stage 3)
        return False

    def hi(self, e) -> None:
        rend = e.get("rend")
        tagmap = {"i": ("<em>", "</em>"), "sup": ("<sup>", "</sup>"), "sup-i": ("<sup><em>", "</em></sup>"),
                  "sc": ('<span class="sc">', "</span>"), "symbol": ('<span class="symbol">', "</span>"),
                  "lucida": ('<span class="lucida">', "</span>")}
        o, c = tagmap.get(rend, (f'<span class="hi-{attr(rend)}">', "</span>"))
        self.w(o)
        self.children(e)
        self.w(c)

    def note(self, e) -> None:
        self.counts["sidenotes"] += 1
        nid, n = self.pid(e), e.get("n")
        lt = letter(n)
        self.w(f'<a class="nref" id="ref-{attr(nid)}" href="#{attr(nid)}" role="doc-noteref" data-n="{attr(n)}" '
               f'aria-label="Note {attr(lt)}">{esc(lt)}</a>')
        self.w(f'<span class="sidenote" id="{attr(nid)}" role="doc-footnote">'
               f'<span class="sn-n">{esc(lt)}</span> ')
        start = len(self.out)
        self.in_note += 1
        if e.find(T("p")) is not None:
            for p in e.iter(T("p")):
                self.w('<span class="sn-p">')
                self.children(p)
                self.w("</span>")
        else:
            self.children(e)
        self.in_note -= 1
        seg, verses = self.expand_citations(nid, "".join(self.out[start:]))
        # the Latin of the note translated after it, one line each, so Burton's punctuation stays with his words
        trs = []
        for fid in dict.fromkeys(re.findall(r'class="fp [^"]*" data-fid="([^"]+)"', seg)):
            if vs := self.versions(fid):
                v = vs[0]
                pl = " " + prov(label_of(v)) if v["by"] == "machine" else ""
                lang = next((x.get(XML_LANG) for x in e.iter() if x.get(XML_ID) and public_id(x.get(XML_ID)) == fid),
                            "la")
                resp = ' data-resp="gowland"' if v["by"] == "gowland" else ""
                trs.append(f'<span class="sn-tr" data-lang="{attr(lang)}" data-src="{attr(v["by"])}"{resp}>'
                           f'<span class="mn-tx">{esc_tagged(v["text"])}</span> '
                           f'<span class="mn-src">{esc(short_label(v))}{pl}</span></span>')
        self.out[start:] = [seg + "".join(trs) + verses]
        self.w("</span>")

    def expansion(self, c: dict) -> tuple[str, str] | None:
        """(HTML, kind) of a citation's expansion: the rules' when they resolved it, else the model's
        (data/layers/citation-expansions/), else the rules' partial reading. "probably" where the model inferred
        the author from the work or from "Idem" (cite-audit a1: the 3 uncertain items were all Idem)."""
        if c.get("author") == "burton":
            return None  # Burton's own divisions: a cross-reference, linked by mark_xrefs
        m = self.cexp.get(c["id"])
        if m and m.get("raw") != c["raw"]:
            # citation ids are `<note>-c<k>` by order: a rules change that finds an earlier citation renumbers the
            # later ones, so a model expansion is used only for the words it was made for
            self.counts["cite_expansions_raw_mismatch"] = self.counts.get("cite_expansions_raw_mismatch", 0) + 1
            m = None
        if c["status"] == "parsed" and c.get("display"):
            return self.cite_link(c.get("author"), c["display"]), "rule"
        if m and m["status"] in ("expanded", "probable") and m.get("display"):
            probably = m["status"] == "probable" or m.get("basis") == "idem-previous"
            full = f"Citation expanded by machine ({m['model']}, prompt {m['prompt']}, {m['date']})"
            html_ = (("probably " if probably else "") + self.cite_link(m.get("author"), m["display"]) +
                     f" {prov(full)}")
            return html_, "model"
        if c.get("display") and c.get("author"):
            return self.cite_link(c["author"], c["display"]), "rule"
        return None

    @staticmethod
    def cite_link(author: str | None, display: str) -> str:
        """The expansion, linked to the author's page where the edition has one (data/authors/)."""
        if not author or author == "bible" or not (paths.DATA / "authors" / f"{author}.yaml").exists():
            return esc(display)
        return f'<a class="cx-a" href="../authors/{attr(author)}/">{esc(display)}</a>'

    def expand_citations(self, nid: str, seg: str) -> tuple[str, str]:
        """Burton's abbreviated citations in a note, each shown expanded in its place, his own words on hover and
        under the reading option "Burton's abbreviations" (owner, 2026-11-03: one expanded form, in place); and the
        KJV verses of its Bible citations, one line each after the note (stage 6)."""
        verses = []
        for c in (self.cites.get(nid) or {}).get("citations", []):
            exp = self.expansion(c)
            if not exp:
                continue
            found = _find_in(seg, c["raw"])
            if found is None:
                self.counts["cite_unplaced"] = self.counts.get("cite_unplaced", 0) + 1
                continue
            if c.get("author") == "bible" and (k := kjv_html(c, self.counts)):
                verses.append(f'<span class="sn-bible">{k}</span>')
            hs, he = found
            if (end := c["raw"].rstrip()[-1:]) in ".,;":  # Burton's stop after the citation stays after it
                exp = (exp[0] + end, exp[1])
            self.counts["cite_expansions"] += 1
            self.counts[f"cite_expansions_{exp[1]}"] = self.counts.get(f"cite_expansions_{exp[1]}", 0) + 1
            seg = (seg[:hs] + f'<span class="cx"><span class="cx-b">{seg[hs:he]}</span>'
                   f'<span class="cx-e" title="{attr("Burton: " + c["raw"])}">{exp[0]}</span></span>' + seg[he:])
        return seg, "".join(verses)

    # ---------------------------------------------------------------- foreign passages
    def versions(self, fid: str) -> list[dict]:
        """Every translation of the passage, in the default source order (SPEC §6.3): the layer's human
        and machine translations (one model shown when several translated it) and, in the private
        build, Gowland's."""
        rec = self.layer.get(fid)
        trs = {t["by"]: t for t in (rec or {}).get("translations", []) if t["by"] != "machine"}
        if rec and (m := primary_machine(rec)) is not None:
            trs["machine"] = m
        if fid in self.djs:
            trs["djs1927"] = self.djs[fid]
        if fid in self.gowland:
            trs["gowland"] = {"by": "gowland", "text": self.gowland[fid]}
        return [trs[s] for s in SOURCE_ORDER if s in trs]

    def has_translation(self, fid: str) -> bool:
        return fid in self.layer or fid in self.gowland

    def tr_markup(self, fid: str, block: bool, lang: str | None) -> str:
        rec = self.layer.get(fid)
        tag = "div" if block else "span"
        vs = self.versions(fid)
        if not vs:
            return (f'<{tag} class="ft ft-missing" id="tr-{attr(fid)}" role="note">'
                    f'<span class="ft-label">No translation yet</span></{tag}>')
        name, abbr = LANG_NAMES.get(lang or "", (lang or "another language", lang or "?"))
        # the source language, shown wherever a translation stands in for the original (owner, 2026-10-26)
        head = (f'<span class="sr-only">Translation from {esc(name)}: </span>'
                f'<span class="ft-from" aria-hidden="true"><span class="ft-from-long">from {esc(name)}</span>'
                f'<span class="ft-from-short">{esc(abbr)}</span></span>')
        st = (rec or {}).get("self_translation") or {"status": "none"}
        burton = ""
        if rec and rec["preferred"] == "burton" and st.get("burton_span"):
            # placeholder: filled in after mark_burton_spans, so the quote is not matched twice
            burton = (f'<span class="ft-burton-own"><span class="ft-text">Burton translates: “\x00Q{fid}\x00”</span>'
                      f'<span class="ft-label">Burton’s own rendering</span></span>')
        elif st["status"] == "partial":
            burton = '<span class="ft-label ft-partial">Completing Burton’s rendering:</span>'
        items = []
        for t in vs:
            src = t["by"]
            extra = ""
            if src == "machine":  # the model's own claims travel with its translation
                s = rec["source"]
                if s["status"] in ("burton-cites", "probable", "identified"):
                    word = {"burton-cites": "Burton cites", "probable": "Probably", "identified": "Source"}[s["status"]]
                    where = ", ".join(x for x in (s.get("author"), s.get("work"), s.get("locus")) if x)
                    unverified = "" if s.get("verified") else " (unverified)"
                    extra += f'<span class="ft-src">{word}: {esc_tagged(where)}{unverified}</span>'
                if t.get("note"):
                    extra += f'<span class="ft-note">{esc_tagged(t["note"])}</span>'
            if src == "djs1927" and t.get("attribution"):  # their own attribution, as they print it
                extra += f'<span class="ft-src">They attribute it: {esc(t["attribution"])}</span>'
            resp = ' data-resp="gowland"' if src == "gowland" else ""
            if src == "gowland":
                self.counts["gowland_versions"] += 1
            if src == "djs1927":
                self.counts["djs_versions"] += 1
            items.append(f'<span class="ft-v ft-{attr(src)}" data-src="{attr(src)}"{resp}>'
                         f'<span class="ft-text">{esc_tagged(t["text"])}</span>'
                         f'<span class="ft-label">{esc(short_label(t))}'
                         f'{" " + prov(label_of(t)) if src == "machine" else ""}</span>{extra}</span>')
        own = " ft-own" if burton.startswith('<span class="ft-burton-own"') else ""
        vsrc = ""
        if fd := self.findings.get("findings", {}).get(fid):
            vsrc = self.finding_line(fd)
        elif v := self.verified.get(fid):  # the only "Source": a verified text match (M6 verifier)
            self.counts["verified_sources"] += 1
            where = ", ".join(x for x in (v.get("author_name"), v.get("title"),
                                          None if v["locus"] == "all" else v["locus"]) if x)
            vsrc = (f'<span class="ft-src ft-verified">Source: {esc(where)} '
                    f'<span class="lbl">text matched by rule in {esc(v["corpus"])} ({esc(v["method"])})</span></span>')
        return (f'<{tag} class="ft{own}" id="tr-{attr(fid)}" role="note" lang="en">{head}{burton}{vsrc}'
                f'<span class="ft-vs">{"".join(items)}</span></{tag}>')

    def finding_line(self, fd: dict) -> str:
        """A source finding shown beside the attribution it differs from (or confirms); both stay visible."""
        self.counts["source_findings"] = self.counts.get("source_findings", 0) + 1
        t = fd["text_found_in"]
        found = ", ".join(x for x in (self.findings["names"].get(t["author"], t["author"]), t.get("work"),
                                      None if t["locus"] == "all" else t["locus"]) if x)
        a = fd["attribution"]
        whose = "Burton’s attribution" if a["by"] == "burton" else "Earlier machine attribution"
        attr_ = ", ".join(x for x in (a.get("author"), a.get("work"), a.get("locus")) if x)
        text = {"agrees": f"Source: {attr_}; the words survive as quoted in {found}",
                "agrees-locus-differs": f"Source: {found} ({whose.lower()}: {attr_})",
                "words-of-transmitter": f"Words: {found}, who gives them to {a.get('author')}",
                "cites-intermediary": f"Words: {found} ({whose.lower()}: {attr_}, where Burton read them)",
                "disagrees": f"Source: {found}. {whose}: {attr_}"}[fd["finding"]]
        d = self.findings["decided"]
        return (f'<span class="ft-src ft-verified" data-finding="{attr(fd["finding"])}">{esc(text)} '
                f'<span class="lbl">finding by {esc(d["by"])}, {esc(d["date"])}; text matched by rule</span></span>')

    def mode_class(self, fid: str) -> str:
        rec = self.layer.get(fid)
        if not self.has_translation(fid):  # nothing to substitute: every mode keeps the original
            return " fp-untranslated"
        st = ((rec or {}).get("self_translation") or {}).get("status", "none")
        return {"full": " st-full", "partial": " st-partial", "paraphrase": " st-paraphrase"}.get(st, "")

    def st_mark(self, fid: str) -> str:
        """The ⁂ that stands for an original Burton translates himself, shown in "Read in English". A real
        character, not CSS content, so a note marker hoisted before the passage keeps a word on its line."""
        return '<span class="st-mark" aria-hidden="true">⁂</span>' if "st-full" in self.mode_class(fid) else ""

    def hoist_notes(self, e) -> None:
        """Burton's notes inside a foreign passage are rendered just before it, so they stay visible
        when the passage is replaced by its translation ("Read in English")."""
        notes = list(e.iter(T("note")))
        if not notes:
            return
        self.w('<span class="hoisted">')
        for n in notes:
            self.note(n)
            self.hoisted.add(n.get(XML_ID))
        self.w("</span>")

    def card(self, fid: str, lang: str | None) -> None:
        """A translation of a passage in the main text, for the margin (owner, 2026-11-03, T6 A / T8 D): the
        preferred version in the passage's colour, labelled with its source; the other versions, the source and
        the notes folded under it. Where Burton translates the passage himself, the card says so instead
        (R2 A + C). Its anchor stands before the passage; edition.js lays it beside that line."""
        if self.in_note:
            return
        rec = self.layer.get(fid)
        st = ((rec or {}).get("self_translation") or {})
        vs = self.versions(fid)
        cid = f"mt-{fid}"
        name, _ = LANG_NAMES.get(lang or "", (lang or "another language", ""))
        if rec and rec.get("preferred") == "burton" and st.get("burton_span"):
            head = '<span class="mn-k">Burton’s own</span> '
            body = f'“\x00Q{fid}\x00”'
            if t := next((v for v in vs if v["by"] != "gowland" and v.get("note")), None):
                body += f'<span class="mn-sub">{esc_tagged(t["note"])} {prov(label_of(t))}</span>'
            kind = "own"
        elif vs:
            v0, rest = vs[0], vs[1:]
            lab = short_label(v0) + (" " + prov(label_of(v0)) if v0["by"] == "machine" else "")
            head = '<span class="mn-k">trans.</span> '
            body = (f'<span class="mn-v" data-src="{attr(v0["by"])}">'
                    f'<span class="mn-tx">{esc_tagged(v0["text"])}</span> <span class="mn-src">{lab}</span></span>')
            more = []
            for t in rest:
                pl = " " + prov(label_of(t)) if t["by"] == "machine" else ""
                more.append(f'<span class="mn-alt" data-src="{attr(t["by"])}">'
                            f'<span class="mn-tx">{esc_tagged(t["text"])}</span> '
                            f'<span class="mn-src">{esc(short_label(t))}{pl}</span></span>')
            src = (rec or {}).get("source") or {}
            if src.get("status") in ("burton-cites", "probable", "identified"):
                word = {"burton-cites": "Burton cites", "probable": "Probably", "identified": "Source"}[src["status"]]
                where = ", ".join(x for x in (src.get("author"), src.get("work"), src.get("locus")) if x)
                more.append(f'<span class="mn-alt"><span class="mn-h">Source</span> {word} {esc_tagged(where)}'
                            f'{"" if src.get("verified") else " (unverified)"}</span>')
            notes = [t for t in vs if t["by"] == "machine" and t.get("note")]
            if notes:
                more.append(f'<span class="mn-alt"><span class="mn-h">Notes</span> {esc_tagged(notes[0]["note"])} '
                            f'{prov(label_of(notes[0]))}</span>')
            if more:
                body += f'<details class="mn-more"><summary>more</summary>{"".join(more)}</details>'
            kind = "tr"
        else:
            return
        resp = ' data-resp="gowland"' if vs and vs[0]["by"] == "gowland" else ""
        self.w(f'<span class="mref" data-for="{attr(cid)}" data-fo="{attr(fid)}" aria-hidden="true"></span>')
        self.cards.append(f'<span class="mn mn-{kind}" id="{attr(cid)}" data-lang="{attr(lang)}"{resp} role="note" '
                          f'aria-label="Translation from {attr(name)}">{head}{body}</span>')
        self.counts["margin_translations"] = self.counts.get("margin_translations", 0) + 1

    def foreign(self, e, punct: str = "") -> None:
        self.counts["foreign"] += 1
        self.hoist_notes(e)
        fid, lang = self.pid(e), e.get(XML_LANG)
        self.fp_lang[fid] = lang
        if not self.in_note:
            self.last_block = (fid, 0)
        size = "short" if len(public_text(e)) <= 40 else "long"
        self.card(fid, lang)
        self.w(f'<span class="fp fp-{size}{self.mode_class(fid)}" data-fid="{attr(fid)}" data-lang="{attr(lang)}">'
               f'{self.st_mark(fid)}'
               f'<span class="fo" lang="{attr(lang)}" tabindex="0" aria-describedby="tr-{attr(fid)}">')
        self.children(e)
        self.w("</span>")
        self.w(self.tr_markup(fid, block=False, lang=lang))
        if punct:
            self.w(f'<span class="fp-p">{esc(punct)}</span>')
        self.w("</span>")

    def facing_lines(self, e, fid: str) -> tuple[list[str], dict] | None:
        """The preferred translation of a verse passage of FACING_MIN lines or more, line for line, where it has as
        many " / " lines as the passage (owner, 2026-11-03: T12 B). Gowland's bracket sometimes runs on from the
        verse passage before, which has no version of his own (the Plautus in 1.2.2.6): where his version has exactly
        that passage's lines more, his last lines are this passage's."""
        n = len(list(e.iter(T("l"))))
        if self.in_note or n < FACING_MIN or e.tag != T("lg") or not (vs := self.versions(fid)):
            return None
        v, lines = vs[0], vs[0]["text"].split(" / ")
        prev = self.last_block
        if len(lines) > n and v["by"] == "gowland" and prev and prev[0] not in self.gowland and \
                prev[1] == len(lines) - n:
            lines = lines[-n:]
            self.counts["facing_run_on"] = self.counts.get("facing_run_on", 0) + 1
        return (lines, v) if len(lines) == n else None

    def foreign_block(self, e, tag: str, cls: str) -> None:
        """A block-level foreign passage (verse group or block quotation) with its translation: in the margin, or,
        for a long verse passage that has one line for line, set facing it."""
        fid = self.pid(e)
        self.counts["foreign"] += 1
        self.hoist_notes(e)
        lang = e.get(XML_LANG)
        self.fp_lang[fid] = lang
        facing = self.facing_lines(e, fid)
        if not self.in_note:
            self.last_block = (fid, len(list(e.iter(T("l")))))
        if facing:
            cls += " fp-facing"
            self.counts["facing"] = self.counts.get("facing", 0) + 1
            self.facing_row = 0
        else:
            self.card(fid, lang)
        self.w(f'<{tag} class="{cls} fp fp-block{self.mode_class(fid)}" id="{attr(fid)}" data-fid="{attr(fid)}" '
               f'data-lang="{attr(lang)}">{self.st_mark(fid)}'
               f'<div class="fo" lang="{attr(lang)}" tabindex="0" aria-describedby="tr-{attr(fid)}">')
        self.children(e)
        self.w("</div>")
        self.facing_row = None
        if facing:
            lines, v = facing
            name, _ = LANG_NAMES.get(lang or "", (lang or "another language", ""))
            pl = " " + prov(label_of(v)) if v["by"] == "machine" else ""
            resp = ' data-resp="gowland"' if v["by"] == "gowland" else ""
            rows = "".join(f'<span class="ftr-l" data-r="{k}" style="--r:{k}">{esc_tagged(t)}</span>'
                           for k, t in enumerate(lines, 1))
            self.w(f'<div class="ftr" lang="en" data-src="{attr(v["by"])}"{resp} role="note" '
                   f'aria-label="Translation from {attr(name)}">{rows}<span class="ftr-src" '
                   f'style="--r:{len(lines) + 1}">{esc(short_label(v))}{pl}</span></div>')
        self.w(self.tr_markup(fid, block=True, lang=lang))
        self.w(f"</{tag}>\n")

    def lg(self, e) -> None:
        lgid = self.pid(e)
        if e.get("ana") == "foreign":
            self.foreign_block(e, "div", "lg")
            return
        kind = " burton-verse-tr" if e.get("type") == "translation-block" else ""
        self.w(f'<div class="lg{kind}" id="{attr(lgid)}">')
        self.children(e)
        self.w("</div>")


def mark_burton_spans(html_text: str, layer: dict, counts: dict, langs: dict | None = None) -> str:
    """Wrap Burton's own renderings (text-quote selectors) so they can be linked to their originals, each with its
    original's language, whose colour it takes in the line (owner, 2026-11-03: R2 A + C).
    Only exact matches inside one text run are wrapped; others are counted as unplaced."""
    for fid, rec in layer.items():
        sel = rec["self_translation"].get("burton_span")
        if not sel:
            continue
        q = esc(sel["exact"])
        parts = q.split(" / ")  # verse renderings span several lines; mark each line
        placed = 0
        lang = (langs or {}).get(fid) or ""
        for part in parts:
            if html_text.count(part) == 1:
                html_text = html_text.replace(
                    part, f'<span class="burton-tr" data-for="{attr(fid)}" data-lang="{attr(lang)}">{part}</span>', 1)
                placed += 1
        if placed == len(parts):
            counts["burton_spans"] += 1
        else:
            counts["burton_spans_unplaced"] += 1
    return html_text


SKIP_MAIN = ("nref", "sidenote", "ft", "sn-cite", "gowland-tr", "gowland-verse", "gowland-block", "pb", "mn",
             "cx-e", "prov", "ic-m", "ftr")
SKIP_NOTES = ("nref", "ft", "sn-cite", "gowland-tr", "gowland-verse", "gowland-block", "pb", "mn", "cx-e", "prov",
              "ftr")


def _visible(html_text: str, skip: tuple[str, ...] = ()) -> tuple[str, list[int]]:
    """The page's visible text and, for each of its characters, the index in the HTML where it starts (tags
    and soft hyphens skipped, an entity counted as one character). Elements whose class is in `skip` are left
    out with their content (note markers, sidenotes, translation boxes), so they do not interrupt a phrase."""
    out, pos, i = [], [], 0
    skipping: list[str] = []  # tag names open inside a skipped element
    while i < len(html_text):
        ch = html_text[i]
        if ch == "<":
            j = html_text.index(">", i) + 1
            m = re.match(r"<(/?)([a-zA-Z0-9]+)([^>]*)>", html_text[i:j])
            if m and not m.group(3).endswith("/") and m.group(2) not in ("br", "img", "wbr"):
                close, tag, rest = m.groups()
                if skipping:
                    if close:
                        skipping.pop()
                    else:
                        skipping.append(tag)
                elif not close and (c := re.search(r'class="([^"]*)"', rest)) and \
                        set(c.group(1).split()) & set(skip):
                    skipping.append(tag)
            i = j
            continue
        if skipping:
            i += 1
            continue
        if ch == "&" and (m := re.match(r"&(#?\w+);", html_text[i:])):
            out.append(html.unescape(m.group(0)))
            pos.append(i)
            i += len(m.group(0))
            continue
        if ch != "\u00ad":  # soft hyphen
            out.append(ch)
            pos.append(i)
        i += 1
    return "".join(out), pos


def _balanced(fragment: str) -> bool:
    stack = []
    for m in re.finditer(r"<(/?)([a-zA-Z0-9]+)[^>]*?(/?)>", fragment):
        close, tag, selfclose = m.groups()
        if selfclose or tag in ("br", "img", "wbr"):
            continue
        if tag == "a":
            return False  # never nest a link
        if close:
            if not stack or stack.pop() != tag:
                return False
        else:
            stack.append(tag)
    return not stack


def _locate(html_text: str, sel: dict, skips=(SKIP_MAIN, SKIP_NOTES), views=None) -> tuple | None:
    """Where a selector's words stand in the page: (index in the visible text, the visible text's positions,
    HTML start, HTML end), or None. The words must occur once in the visible text, tried with their context,
    then shorter; the main text first, then with the sidenotes. `views` caches the visible texts."""
    pre, ex, suf = (sel.get("prefix", "").split(" ¶ ")[-1], sel["exact"], sel.get("suffix", "").split(" ¶ ")[0])
    at = None
    for skip in skips:
        text, pos = views[skip] if views is not None else _visible(html_text, skip)
        for a, b in ((pre, suf), ("", suf), (pre, ""), ("", "")):
            if text.count(a + ex + b) == 1:
                at = text.index(a + ex + b) + len(a)
                break
        if at is not None:
            break
    if at is None:
        return None
    hs, he = pos[at], pos[at + len(ex) - 1]
    he = html_text.index(";", he) + 1 if html_text[he] == "&" else he + 1
    while (m := re.search(r"<[a-zA-Z][^>]*>$", html_text[:hs])) and not m.group(0).startswith("<a "):
        hs = m.start()  # take in opening tags right before the first word ...
    while (m := re.match(r"</[a-zA-Z0-9]+>", html_text[he:])) and m.group(0) != "</a>":
        he += len(m.group(0))  # ... and closing tags right after the last
    return at, pos, hs, he


def _find_in(seg: str, raw: str) -> tuple[int, int] | None:
    """Where a citation's words stand in a note's HTML (Burton's token-by-token italics and any Latin box between
    them taken in): (start, end) of a balanced fragment with no link inside, or None."""
    text, pos = _visible(seg, ("ft", "gowland-tr", "gowland-verse", "gowland-block", "cx", "prov"))
    pat = r"\s*".join(re.escape(t) for t in raw.split())
    ms = list(re.finditer(pat, text))
    if len(ms) != 1:
        return None
    a, b = ms[0].start(), ms[0].end()
    hs, he = pos[a], pos[b - 1]
    he = seg.index(";", he) + 1 if seg[he] == "&" else he + 1
    while (m := re.search(r"<[a-zA-Z][^>]*>$", seg[:hs])) and not m.group(0).startswith("<a "):
        hs = m.start()
    while (m := re.match(r"</[a-zA-Z0-9]+>", seg[he:])) and m.group(0) != "</a>":
        he += len(m.group(0))
    frag = seg[hs:he]
    if not _balanced(frag):  # the words end inside an element that opened before them: keep the tags outside
        hs, he = pos[a], pos[b - 1] + 1
        frag = seg[hs:he]
        if not _balanced(frag):
            return None
    return (hs, he) if "<a " not in frag else None


GW_LABELS = {"gloss": "gloss", "source": "source", "identity": "about", "explanation": "note", "pointer": "see"}


def gowland_card(e: dict, notes, cid: str) -> str:
    """One of Gowland's endnote entries as a margin item, labelled by its kind (private build only). A pointer
    shows the note it points to, in place."""
    text = notes.note_text(e["endnote"], e["seg"])
    kind = e["kind"]
    if kind == "pointer" and e.get("targets"):
        t = e["targets"][0]
        if t in notes.endnotes():
            segs = notes.segments(notes.endnotes()[t])
            k = next((i for i, (lem, _) in enumerate(segs) if lem.lower() == e["lemma"].lower()), 0)
            text = segs[k][1] if segs else text
            kind = notes.kind(segs[k][0], segs[k][1]) if segs else kind
        elif re.fullmatch(r"\d\.\d\.\d(?:\.\d+)?", t):
            text = f'<a class="xref" href="../{attr(t)}/">{esc(t)}</a>'
            return (f'<span class="mn mn-gw" id="{attr(cid)}" data-kind="pointer" data-resp="gowland" role="note">'
                    f'<span class="mn-k">see</span> {text}</span>')
    lem = f'<em class="mn-lem">{esc_tagged(e["lemma"])}</em> ' if e["lemma"] else ""
    return (f'<span class="mn mn-gw" id="{attr(cid)}" data-kind="{attr(kind)}" data-resp="gowland" role="note">'
            f'<span class="mn-k">{GW_LABELS.get(kind, "note")}</span> {lem}{esc_tagged(text)}</span>')


def mark_gowland(html_text: str, entries: list[dict], counts: dict) -> tuple[str, list[str]]:
    """Gowland's endnote entries in the margin (private build; burton/site/gowland_notes.py): an anchor before the
    words each is on (`data-len` of them, for the highlight), or, where the words are not found, after his own
    endnote anchor; the items themselves are returned to be laid out beside their anchors."""
    from . import gowland_notes as notes
    views = {SKIP_MAIN: _visible(html_text, SKIP_MAIN)}
    edits, cards = [], []
    for e in entries:
        cid = f"gw-{e['endnote']}-{e['seg']}"
        hs = None
        if e["selector"] and (found := _locate(html_text, e["selector"], (SKIP_MAIN,), views)):
            at, pos = found[0], found[1]
            hs = pos[at]
            ln = len(e["selector"]["exact"])
        if hs is None:
            m = re.search(rf'<span class="enref"[^>]*data-target="{re.escape(e["endnote"])}"[^>]*></span>', html_text)
            if not m:
                counts["gowland_notes_unplaced"] = counts.get("gowland_notes_unplaced", 0) + 1
                continue
            hs, ln = m.end(), 0
        edits.append((hs, f'<span class="mref" data-for="{attr(cid)}" data-len="{ln}" aria-hidden="true"></span>'))
        cards.append(gowland_card(e, notes, cid))
        counts["gowland_notes"] = counts.get("gowland_notes", 0) + 1
        counts[f"gowland_notes_{e['kind']}"] = counts.get(f"gowland_notes_{e['kind']}", 0) + 1
    for hs, mark in sorted(edits, key=lambda x: x[0], reverse=True):
        html_text = html_text[:hs] + mark + html_text[hs:]
    return html_text, cards


SKIP_NAMES = (*SKIP_MAIN, "xref", "xref-unresolved", "unit-title", "pageref", "cx", "gl-s", "nm", "cx-b")


def mark_names(html_text: str, names: re.Pattern | None, ids: dict[str, str], counts: dict) -> tuple[str, set[str]]:
    """The names of cited authors in Burton's running text, linked to their index entries (owner, 2026-11-03: a
    window on the entry, R5 C hairline). Only a form the abbreviation tables give to one author with an entry is
    linked (`names`, built by the caller); it must stand as whole words in one text run, outside links, notes and
    the margin. Returns the page and the ids linked."""
    if names is None:
        return html_text, set()
    text, pos = _visible(html_text, SKIP_NAMES)
    edits, used = [], set()
    for m in names.finditer(text):
        hs, he = pos[m.start()], pos[m.end() - 1] + 1
        if "<" in html_text[hs:he] or "&" in html_text[hs:he]:
            continue  # the name runs over markup (a soft hyphen is not markup; an entity is left alone)
        aid = ids[m.group(0).replace("­", "")]
        edits.append((hs, he, aid))
        used.add(aid)
    for hs, he, aid in reversed(edits):
        html_text = (html_text[:hs] + f'<a class="nm" href="../authors/{attr(aid)}/" data-author="{attr(aid)}">'
                     + html_text[hs:he] + "</a>" + html_text[he:])
    counts["names_linked"] = counts.get("names_linked", 0) + len(edits)
    return html_text, used


def mark_glosses(html_text: str, items: list[dict], counts: dict) -> str:
    """Obsolete-word glosses (M8): the word is wrapped, and its sense follows it, hidden until the reader turns
    glosses on. Placed like cross-references, in the main text only (all found on the page as it is, then
    inserted from the end); a gloss that cannot be placed, is split by other markup or overlaps another is
    counted and left out."""
    views = {SKIP_MAIN: _visible(html_text, SKIP_MAIN)}
    edits = []
    for it in items:
        found = _locate(html_text, it["selector"], (SKIP_MAIN,), views)
        why = None
        if found is None:
            why = "notfound"
        else:
            at, pos, hs, he = found
            inner = html_text[hs:he]
            if not _balanced(inner) or "<a " in inner:
                # the tags taken in around the words do not balance (a word that ends an italic run): wrap the
                # word's own characters instead, if no tag stands inside them
                n = len(it["selector"]["exact"])
                hs, he = pos[at], pos[at + n - 1]
                he = html_text.index(";", he) + 1 if html_text[he] == "&" else he + 1
                if "<" in html_text[hs:he]:
                    why = "markup"
        if why:
            counts["glosses_unplaced"] = counts.get("glosses_unplaced", 0) + 1
            counts[f"glosses_unplaced_{why}"] = counts.get(f"glosses_unplaced_{why}", 0) + 1
            continue
        edits.append((hs, he, it))
    edits.sort(key=lambda x: x[0])
    keep, end = [], -1
    for hs, he, it in edits:
        if hs < end:
            counts["glosses_unplaced"] = counts.get("glosses_unplaced", 0) + 1
            counts["glosses_unplaced_overlap"] = counts.get("glosses_unplaced_overlap", 0) + 1
            continue
        keep.append((hs, he, it))
        end = he
    for hs, he, it in reversed(keep):
        src = attr(it["source"])
        note = (f'<span class="gl-s" data-src="{src}"><span class="sr-only">gloss: </span>{esc(it["sense"])}'
                f'<span class="gl-l"> · {esc(it["label"])}</span></span>')
        resp = ' data-resp="gowland"' if it["source"] == "gowland" else ""
        word = f'<span class="gl gl-{src}"{resp}><span class="gl-w">{html_text[hs:he]}</span>{note}</span>'
        html_text = html_text[:hs] + word + html_text[he:]
        counts["glosses"] = counts.get("glosses", 0) + 1
        counts[f"glosses_{it['source']}"] = counts.get(f"glosses_{it['source']}", 0) + 1
    return html_text


RESTORED_LABEL = "Not in Gowland’s edition: restored from"
TAG = re.compile(r"<(/?)([a-zA-Z0-9]+)([^>]*)>")


def _outside_passage(html_text: str, at: int) -> int:
    """`at`, or the start of the outermost foreign-passage box (class "fp") open there: a note inside the box
    would be laid out against it and vanish with it in "Read in English", so it goes before it, as Gowland's
    notes in a quotation are lifted out of it."""
    stack: list[tuple[str, int, bool]] = []
    for m in TAG.finditer(html_text, 0, at):
        close, tag, rest = m.groups()
        if rest.endswith("/") or tag in ("br", "img", "wbr"):
            continue
        if close:
            while stack and stack.pop()[0] != tag:
                pass
        else:
            c = re.search(r'class="([^"]*)"', rest)
            stack.append((tag, m.start(), bool(c) and "fp" in c.group(1).split()))
    outer = [start for _, start, fp in stack if fp]
    return outer[0] if outer else at


def mark_restored(html_text: str, notes: dict, counts: dict) -> str:
    """Burton's sidenotes that Gowland's edition leaves out (data/layers/restored-notes/): a marker ° before the
    word and the note beside it, styled apart and labelled with its source; placed like glosses, found on the
    page as it is and inserted from the end. One that cannot be placed is counted."""
    views = {SKIP_MAIN: _visible(html_text, SKIP_MAIN)}
    edits = []
    for rid, rec in notes.items():
        found = _locate(html_text, rec["selector"], (SKIP_MAIN,), views)
        if found is None:
            counts["restored_unplaced"] = counts.get("restored_unplaced", 0) + 1
            continue
        at, pos = found[0], found[1]
        word = pos[at]  # at the word itself, inside its paragraph and any italics (not before the tags around it)
        hs = _outside_passage(html_text, word)
        counts["restored_hoisted"] = counts.get("restored_hoisted", 0) + (hs != word)
        edits.append((hs, rid, rec, hs != word))
    for hs, rid, rec, hoisted in sorted(edits, key=lambda x: x[0], reverse=True):
        note = (f'<a class="nref nref-restored" id="ref-{attr(rid)}" href="#{attr(rid)}" role="doc-noteref" '
                f'aria-label="Note not in Gowland’s edition">°</a>'
                f'<span class="sidenote sn-restored" id="{attr(rid)}" role="doc-footnote">'
                f'<span class="sn-n">°</span> {esc_tagged(rec["text"])} '
                + prov(f'{RESTORED_LABEL} {rec["source"]}, note {rec["pg_note"]} '
                       f'(a 19th-century text checked against the 1638 edition)') + '</span>')
        if hoisted:  # before a passage box, held to its first line as Gowland's lifted-out notes are
            note = f'<span class="hoisted">{note}</span>'
        html_text = html_text[:hs] + note + html_text[hs:]
        counts["restored_notes"] = counts.get("restored_notes", 0) + 1
    return html_text


def _runs(html_text: str, pos: list[int], a: int, b: int) -> list[tuple[int, int]]:
    """The HTML ranges that hold the visible characters a..b-1, one per run of text between tags (a soft hyphen
    does not break a run; an entity is taken whole)."""
    def end(k):
        return html_text.index(";", pos[k]) + 1 if html_text[pos[k]] == "&" else pos[k] + 1

    runs, k = [], a
    while k < b:
        j = k
        while j + 1 < b and not html_text[end(j):pos[j + 1]].strip("­"):
            j += 1
        runs.append((pos[k], end(j)))
        k = j + 1
    return runs


SKIP_IC = (*SKIP_MAIN, "gl-s")
CLOSE_STOPS = ",;:"


def mark_inline_cites(html_text: str, recs: dict, counts: dict) -> tuple[str, list[str]]:
    """Burton's citations in his running text (data/layers/citations-inline/; owner, 2026-11-03: C1 C). The author's
    name stays; the reference words are wrapped in a `cx-b` span, shown only under "Burton's abbreviations"; a raised
    § after them stands for the citation, whose margin card gives the expansion and, for the Bible, the KJV verses.
    A Bible reference has no name to keep, so only the § stays, and a comma it would leave doubled goes with it
    ("sins, Hag. 1. 9, 10, God" -> "sins,§ God"; "the 1st, Jer. 7. God" -> "the 1st§. God"). Burton's stop at the
    end stays where a sentence follows. Placed like glosses (found on the page as it is, inserted from the end); one
    that cannot be placed is counted."""
    views = {SKIP_IC: _visible(html_text, SKIP_IC)}
    text = views[SKIP_IC][0]
    edits: dict[int, list[str]] = {}
    cards = []
    for key, rec in sorted(recs.items()):
        sel = rec["selector"]
        found = _locate(html_text, sel, (SKIP_IC,), views)
        if found is None:
            counts["inline_cites_unplaced"] = counts.get("inline_cites_unplaced", 0) + 1
            continue
        at, pos = found[0], found[1]
        ex, bible = sel["exact"], rec["author"] == "bible"
        name = 0
        if not bible:
            toks = list(cit_rules.TOKEN.finditer(ex))
            m = cit_rules._match_author([t.group(0) for t in toks], 0)
            name = toks[m[0] - 1].end() if m else 0
        a, b = at + name, at + len(ex)
        if ex.endswith(".") and (not sel["suffix"] or sel["suffix"].lstrip()[:1].isupper()):
            b -= 1  # "… Laurentius cap. 20 lib. 1. Similar, or Homogeneal": the stop ends Burton's sentence
        if bible:
            if a > 0 and text[a - 1] == " ":
                a -= 1
            if text[b:b + 1] == "," and text[a - 1:a] in CLOSE_STOPS:
                b += 1
            elif text[b:b + 1] in ".;:" and text[a - 1:a] == ",":
                a -= 1  # "the 1st, Jer. 7. God is angry" -> "the 1st§. God is angry"
        if b <= a:
            counts["inline_cites_unplaced"] = counts.get("inline_cites_unplaced", 0) + 1
            continue
        runs = _runs(html_text, pos, a, b)
        for hs, he in runs:
            edits.setdefault(hs, []).append('<span class="cx-b">')
            edits.setdefault(he, []).append("</span>")
        cid = f"ic-{key}"
        kind = "bible" if bible else "cites"
        mark = (f'<span class="ic-m" data-kind="{kind}" role="img" aria-label="{attr("citation: " + rec["display"])}" '
                f'title="{attr("Burton: " + rec["raw"])}">§</span>')
        anchor_at, length = (runs[-1][1], 1) if bible else (pos[at], name + 1)
        if (outside := _outside_passage(html_text, anchor_at)) != anchor_at:
            anchor_at, length = outside, 0  # in a quotation: the card is held to the box, which "Read in English" hides
            counts["inline_cites_in_passage"] = counts.get("inline_cites_in_passage", 0) + 1
        edits.setdefault(anchor_at, []).append(f'<span class="mref" data-for="{attr(cid)}" data-len="{length}" '
                                               'aria-hidden="true"></span>')
        edits.setdefault(runs[-1][1], []).append(mark)
        body = Renderer.cite_link(rec["author"], rec["display"])
        if bible:
            body += kjv_html(rec, counts)
        label = "Bible" if bible else "cites"
        cards.append(f'<span class="mn mn-ic" id="{attr(cid)}" data-kind="{kind}" role="note" '
                     f'aria-label="Citation"><span class="mn-k">{label}</span> '
                     f'<span class="ic-e" title="{attr("Burton: " + rec["raw"])}">{body}</span></span>')
        counts["inline_cites"] = counts.get("inline_cites", 0) + 1
        counts[f"inline_cites_{kind}"] = counts.get(f"inline_cites_{kind}", 0) + 1
    for p in sorted(edits, reverse=True):  # at one place, a span that ends there closes before anything opens
        html_text = html_text[:p] + "".join(sorted(edits[p], key=lambda s: not s.startswith("</"))) + html_text[p:]
    return html_text, cards


def mark_xrefs(html_text: str, refs: list[dict], counts: dict) -> str:
    """Link Burton's cross-references: explicit ones resolved by rule (M2) and relative ones confirmed on review
    (M6). The selector's words are found in the page's visible text, where they must occur once (tried with
    their context, then shorter), so token-by-token italics in a sidenote do not hide them. The link is
    inserted only where the tags inside it balance; a reference that cannot be placed is counted, never
    guessed. Unresolved explicit references are marked, not linked."""
    for r in refs:
        sel = r["selector"]
        ex = sel["exact"]
        found = _locate(html_text, sel)
        if found is None:
            counts["xrefs_unplaced"] = counts.get("xrefs_unplaced", 0) + 1
            continue
        at, pos, hs, he = found
        if r.get("target"):
            title = f' title="{attr(r["title"])}"' if r.get("title") else ""
            o, c, key = f'<a class="xref" href="../{attr(r["target"])}/"{title}>', "</a>", "xrefs_linked"
        else:
            o, c, key = '<span class="xref-unresolved">', "</span>", "xrefs_unresolved_marked"
        inner = html_text[hs:he]
        if _balanced(inner):
            html_text = html_text[:hs] + o + inner + c + html_text[he:]
        else:
            # a note or a translation box stands between the words: wrap each run of words, leave it alone
            runs, k = [], at
            while k < at + len(ex):
                j = k
                while j + 1 < at + len(ex) and pos[j + 1] == pos[j] + 1:
                    j += 1
                runs.append((pos[k], pos[j] + 1))
                k = j + 1
            for a_, b_ in reversed(runs):
                html_text = html_text[:a_] + o + html_text[a_:b_] + c + html_text[b_:]
            key += "_split"
        counts[key] = counts.get(key, 0) + 1
    return html_text


def h1_head(div):
    """The head that becomes the page's only h1: the title, else the first heading."""
    heads = list(div.iter(T("head")))
    return next((h for h in heads if h.get("type") == "title"), heads[0] if heads else None)


def render_unit(div, unit: str, profile: str, layer: dict, image=None, djs: dict | None = None,
                cites: dict | None = None, cite_label: str = "", verified: dict | None = None,
                findings: dict | None = None, xrefs: list[dict] | None = None, plate=None,
                pagemap: dict | None = None, glosses: list[dict] | None = None,
                restored: dict | None = None, gowland_entries: list[dict] | None = None,
                cexp: dict | None = None, initials: set[str] | None = None, names: re.Pattern | None = None,
                name_ids: dict | None = None, author_info: dict | None = None,
                inline_cites: dict | None = None) -> tuple[str, dict]:
    r = Renderer(unit, profile, layer, image=image, h1_head=h1_head(div), djs=djs, cites=cites, cite_label=cite_label,
                 verified=verified, findings=findings)
    r.plate, r.pagemap, r.cexp, r.initials = plate, pagemap or {}, cexp or {}, initials or set()
    if profile == "private":
        r.gowland = gowland_versions(div)
    r.w(f'<article class="unit" id="{attr(unit)}">\n')
    r.children(div)
    r.w("</article>\n")
    body = mark_burton_spans("".join(r.out), layer, r.counts, r.fp_lang)
    body = mark_xrefs(body, xrefs or [], r.counts)
    body = mark_glosses(body, glosses or [], r.counts)
    body = mark_restored(body, restored or {}, r.counts)
    body, ic_cards = mark_inline_cites(body, inline_cites or {}, r.counts)
    body, used = mark_names(body, names, name_ids or {}, r.counts)
    if used and author_info:  # what the name windows show, for the authors named on this page (edition.js)
        data = json.dumps({a: author_info[a] for a in sorted(used) if a in author_info}, ensure_ascii=False)
        script = f'<script type="application/json" class="authors-data">{data.replace("</", "<\\/")}</script>'
        body = body.replace("</article>\n", script + "\n</article>\n")
    cards = list(r.cards) + ic_cards
    if profile == "private" and gowland_entries:
        body, gw = mark_gowland(body, gowland_entries, r.counts)
        cards += gw
    if cards:  # the margin items, laid out by edition.js beside their anchors (in reading order for no-script)
        body = body.replace("</article>\n", f'<div class="mn-pool">{"".join(cards)}</div>\n</article>\n')
    for fid, rec in layer.items():
        sel = rec["self_translation"].get("burton_span")
        if sel:
            body = body.replace(f"\x00Q{fid}\x00", esc(sel["exact"]))
    return body, r.counts


def inline_html(e) -> str:
    """A heading as inline HTML for contents, breadcrumb and pager labels: Burton's words with their
    italics and lang, without notes, Gowland's matter, page breaks or translations."""
    out: list[str] = []

    def walk(x, top=False):
        tag = x.tag if isinstance(x.tag, str) else ""
        skip = tag in (T("note"), T("pb"), ED("enref"), ED("trans"), ED("verse-trans")) or \
            (tag == T("supplied") and x.get("resp") == "#gowland")
        if not skip:
            close = ""
            if not top and x.get(XML_LANG):
                out.append(f'<span lang="{attr(x.get(XML_LANG))}">')
                close = "</span>"
            if tag == T("hi") and x.get("rend") in ("i", "sc"):
                out.append("<em>" if x.get("rend") == "i" else '<span class="sc">')
                close = ("</em>" if x.get("rend") == "i" else "</span>") + close
            if tag == T("lb"):
                out.append(" ")
            out.append(esc(x.text))
            for c in x:
                walk(c)
            out.append(close)
        if not top:
            out.append(esc(x.tail))

    walk(e, top=True)
    lang = e.get(XML_LANG)
    body = re.sub(r"\s+", " ", "".join(out)).strip()
    return f'<span lang="{attr(lang)}">{body}</span>' if lang else body
