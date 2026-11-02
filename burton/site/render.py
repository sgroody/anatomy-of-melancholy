"""TEI base text + layers -> HTML for one unit.

Profiles: `private` renders Gowland's matter (marked data-resp="gowland", hidden by default where
it duplicates our translations); `public` drops it entirely (SPEC §2). Labels for every translation
come from the layer data, never from the template.
"""

import html
import re

from ..layers import djs as djs_layer
from ..tei import ED, XML_ID, XML_LANG, T, public_id
from ..textview import public_text
from ..translate.validate import primary_machine
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


# SPEC §6.3: the default order of translation sources (Burton's own rendering is not a source here:
# where he translates a passage himself his English stays in the text). The reader can reorder them.
SOURCE_ORDER = ["editor", "djs1927", "machine", "gowland"]
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


class Renderer:
    def __init__(self, unit: str, profile: str, layer: dict, image=None, h1_head=None, djs: dict | None = None,
                 cites: dict | None = None, cite_label: str = "", verified: dict | None = None):
        self.unit, self.profile, self.layer = unit, profile, layer
        self.verified = {k: v for k, v in (verified or {}).items() if v["status"] == "verified"}
        self.cites, self.cite_label = cites or {}, cite_label  # M6 citation layer, shown on request
        self.djs = {k: djs_layer.version(r) for k, r in (djs or {}).items() if djs_layer.shown(r, layer.get(k))}
        self.image = image  # callback: graphic file name -> (src, alt, width, height)
        self.h1_head = h1_head  # the head element rendered as the page's h1
        self.counts = {"sidenotes": 0, "foreign": 0, "gowland_trans": 0, "enrefs": 0, "pbs": 0,
                       "burton_spans": 0, "burton_spans_unplaced": 0, "soft_hyphens": 0, "images": 0,
                       "gowland_versions": 0, "djs_versions": 0, "cite_expansions": 0, "verified_sources": 0}
        self.gowland: dict[str, str] = {}  # passage id -> Gowland's translation (private build only)
        self.out: list[str] = []
        self.hoisted: set[str] = set()
        self.langs: list[str] = []

    # ---------------------------------------------------------------- helpers
    def w(self, s: str) -> None:
        self.out.append(s)

    def text(self, s: str | None) -> None:
        if s:
            if self.langs and self.langs[-1] in ("la", "grc"):
                h = soft_hyphenate(s, self.langs[-1])
                self.counts["soft_hyphens"] += len(h) - len(s)
                s = h
            self.w(esc(s))

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
            self.w(f'<span class="l{" " + attr(e.get("rend")) if e.get("rend") else ""}">')
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
            self.w(f'<span class="pb" data-resp="gowland" data-n="{attr(e.get("n"))}" aria-hidden="true"></span>')
        elif tag == T("lb"):
            self.w("<br>")
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
        self.w(f'<figure class="plate"><a href="{attr(src)}"><img src="{attr(src)}" alt="{attr(alt)}" '
               f'width="{w}" height="{h}" loading="lazy" decoding="async"></a></figure>\n')

    def head(self, e) -> bool:
        t = e.get("type")
        source = ' data-source="image"' if e.get("facs") else ""
        sub = f" head-{attr(e.get('subtype'))}" if e.get("subtype") else ""
        tag, cls = ("h1", f"unit-title head-{attr(t)}") if e is self.h1_head else ("p", f"head-{attr(t)}{sub}")
        self.w(f'<{tag} class="{cls}"{source}>')
        if e.get("ana") == "foreign":  # a heading that is itself a foreign passage (Lectori male feriato)
            self.foreign(e)
        else:
            self.children(e)
        self.w(f"</{tag}>\n")
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
        self.w(f'<a class="nref" id="ref-{attr(nid)}" href="#{attr(nid)}" role="doc-noteref" '
               f'aria-label="Note {attr(n)}">{esc(n)}</a>')
        self.w(f'<span class="sidenote" id="{attr(nid)}" role="doc-footnote">'
               f'<span class="sn-n">{esc(n)}</span> ')
        if e.find(T("p")) is not None:
            for p in e.iter(T("p")):
                self.w('<span class="sn-p">')
                self.children(p)
                self.w("</span>")
        else:
            self.children(e)
        self.cite_expansion(nid)
        self.w("</span>")

    def cite_expansion(self, nid: str) -> None:
        """The note's resolved citations, hidden unless the reader asks for them ("Expand citations"). Only
        what the rules resolved is shown; an author links to the author page, Scripture to nothing."""
        shown = [c for c in (self.cites.get(nid) or {}).get("citations", [])
                 if c.get("display") and c.get("author") and c["author"] != "burton"]
        if not shown:
            return
        self.counts["cite_expansions"] += 1
        items = [esc(c["display"]) if c["author"] == "bible" else
                 f'<a href="../authors/{attr(c["author"])}/">{esc(c["display"])}</a>' for c in shown]
        self.w(f'<span class="sn-cite" data-method="{attr(shown[0]["method"])}">'
               f'<span class="lbl">{esc(self.cite_label)}:</span> {"; ".join(items)}</span>')

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
                         f'<span class="ft-label">{esc(label_of(t))}</span>{extra}</span>')
        own = " ft-own" if burton.startswith('<span class="ft-burton-own"') else ""
        vsrc = ""
        if v := self.verified.get(fid):  # the only "Source": a verified text match (M6 verifier)
            self.counts["verified_sources"] += 1
            where = ", ".join(x for x in (v.get("author_name"), v.get("title"),
                                          None if v["locus"] == "all" else v["locus"]) if x)
            vsrc = (f'<span class="ft-src ft-verified">Source: {esc(where)} '
                    f'<span class="lbl">text matched by rule in {esc(v["corpus"])} ({esc(v["method"])})</span></span>')
        return (f'<{tag} class="ft{own}" id="tr-{attr(fid)}" role="note" lang="en">{head}{burton}{vsrc}'
                f'<span class="ft-vs">{"".join(items)}</span></{tag}>')

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

    def foreign(self, e, punct: str = "") -> None:
        self.counts["foreign"] += 1
        self.hoist_notes(e)
        fid, lang = self.pid(e), e.get(XML_LANG)
        size = "short" if len(public_text(e)) <= 40 else "long"
        self.w(f'<span class="fp fp-{size}{self.mode_class(fid)}" data-fid="{attr(fid)}">{self.st_mark(fid)}'
               f'<span class="fo" lang="{attr(lang)}" tabindex="0" aria-describedby="tr-{attr(fid)}">')
        self.children(e)
        self.w("</span>")
        self.w(self.tr_markup(fid, block=False, lang=lang))
        if punct:
            self.w(f'<span class="fp-p">{esc(punct)}</span>')
        self.w("</span>")

    def foreign_block(self, e, tag: str, cls: str) -> None:
        """A block-level foreign passage (verse group or block quotation) with its translation."""
        fid = self.pid(e)
        self.counts["foreign"] += 1
        self.hoist_notes(e)
        lang = e.get(XML_LANG)
        self.w(f'<{tag} class="{cls} fp fp-block{self.mode_class(fid)}" id="{attr(fid)}" data-fid="{attr(fid)}">'
               f'{self.st_mark(fid)}'
               f'<div class="fo" lang="{attr(lang)}" tabindex="0" aria-describedby="tr-{attr(fid)}">')
        self.children(e)
        self.w("</div>")
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


def mark_burton_spans(html_text: str, layer: dict, counts: dict) -> str:
    """Wrap Burton's own renderings (text-quote selectors) so they can be linked to their originals.
    Only exact matches inside one text run are wrapped; others are counted as unplaced."""
    for fid, rec in layer.items():
        sel = rec["self_translation"].get("burton_span")
        if not sel:
            continue
        q = esc(sel["exact"])
        parts = q.split(" / ")  # verse renderings span several lines; mark each line
        placed = 0
        for part in parts:
            if html_text.count(part) == 1:
                html_text = html_text.replace(
                    part, f'<span class="burton-tr" data-for="{attr(fid)}">{part}</span>', 1)
                placed += 1
        if placed == len(parts):
            counts["burton_spans"] += 1
        else:
            counts["burton_spans_unplaced"] += 1
    return html_text


def h1_head(div):
    """The head that becomes the page's only h1: the title, else the first heading."""
    heads = list(div.iter(T("head")))
    return next((h for h in heads if h.get("type") == "title"), heads[0] if heads else None)


def render_unit(div, unit: str, profile: str, layer: dict, image=None, djs: dict | None = None,
                cites: dict | None = None, cite_label: str = "", verified: dict | None = None) -> tuple[str, dict]:
    r = Renderer(unit, profile, layer, image=image, h1_head=h1_head(div), djs=djs, cites=cites, cite_label=cite_label,
                 verified=verified)
    if profile == "private":
        r.gowland = gowland_versions(div)
    r.w(f'<article class="unit" id="{attr(unit)}">\n')
    r.children(div)
    r.w("</article>\n")
    body = mark_burton_spans("".join(r.out), layer, r.counts)
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
