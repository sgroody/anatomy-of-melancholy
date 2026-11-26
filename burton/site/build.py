"""`burton build --profile private|public`: data/text + layers -> site/<profile>/.

Page types (SPEC §7.1): home with frontispiece and contents, front matter, Partition landings,
units, About this edition, and Reading options. Navigation (breadcrumbs, previous/next, contents
tree) comes from burton.site.book, which derives it from data/text.
"""

import hashlib
import html
import json
import re
import shutil
import struct
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from lxml import etree
from markupsafe import Markup

from .. import paths
from ..layers import names_sweep, sweep_audit
from ..tei import T
from ..textview import public_text
from . import (
    authors_pages,
    facing,
    fonts,
    frontispiece,
    glossary_page,
    glosses,
    gowland_notes,
    labyrinth,
    names,
    search,
    synopsis,
)
from .book import Book, Page, text_units
from .render import attr, esc, render_unit

HERE = Path(__file__).parent
STATIC = ("edition.css", "edition.js", "search.js", "icon.svg")


# The reading options' live sample (round 8, D1 A; owner, 2026-11-19): a few lines of Burton at the head of the
# options, changing as the options change. Its words are checked against the base text, and its translation,
# citation and gloss come from their layers with their provenance (never written here).
SAMPLE_UNIT, SAMPLE_P = "3.2.3.1", "3.2.3.1-p35"
SAMPLE_TEXT = ["but fear and sorrow may justly challenge the chief place. Though ", "Hercules de Saxonia",
               " cap. 3 tract. de melanch.", " will exclude fear from Love-Melancholy, yet I am otherwise persuaded. ",
               "Res est solliciti plena timoris amor",
               ". ’Tis full of fear, anxiety, doubt, care, peevishness, suspicion, it turns a man into a woman, "
               "which made ",
               "Hesiod", " ", "belike", ", put fear and paleness Venus’ daughters"]


def options_sample() -> Markup:
    from .render import label_of, prov, src_mark

    root = etree.parse(str(paths.TEXT / f"{SAMPLE_UNIT}.xml")).getroot()
    p = next(e for e in root.iter(T("p")) if e.get("{http://www.w3.org/XML/1998/namespace}id") == "u" + SAMPLE_P)
    plain = public_text(p, notes=False)
    if "".join(SAMPLE_TEXT) not in plain:
        raise SystemExit(f"options sample: its words are no longer in {SAMPLE_P}")
    tr = json.loads((paths.LAYERS / "translations" / f"{SAMPLE_UNIT}.json").read_text(encoding="utf-8"))
    rec = next(r for r in tr.values() if r["text"] == SAMPLE_TEXT[4])
    mt = next(t for t in rec["translations"] if t["by"] == "machine")
    ic = json.loads((paths.LAYERS / "citations-inline" / f"{SAMPLE_UNIT}.json").read_text(encoding="utf-8"))
    cite = next(c for c in ic.values() if c["selector"]["in"] == SAMPLE_P and c["raw"].startswith("Hercules"))
    gl = next(g for g in glosses.layer_items(SAMPLE_UNIT)
              if g["headword"] == "belike" and g["selector"]["in"] == SAMPLE_P)
    t = [esc(x) for x in SAMPLE_TEXT]
    la = esc(rec["text"])
    en = esc(mt["text"])
    en_in = esc(mt["text"].rstrip(" ."))  # in the line, before Burton's own full stop
    pv = prov(label_of(mt))
    html_ = (
        '<div class="opt-sample" role="group" aria-label="A few lines of Burton, as these options show them">'
        f'<p class="os-h">Example passage <span class="os-where">Burton, {SAMPLE_UNIT}</span></p>'
        f'<div class="os-body"><p class="os-text">… {t[0]}<i class="os-ul">{t[1]}</i>'
        f'<span class="os-abbr"><i>{t[2]}</i></span><span class="os-ic" aria-hidden="true">§</span>{t[3].rstrip()}'
        '<sup class="os-ref" aria-hidden="true">e</sup> '
        f'<i class="os-la" lang="la">{la}</i><span class="os-il">{en_in}</span><span class="os-en">{en_in}</span>'
        f'{t[5]}<span class="os-ul">{t[6]}</span>{t[7]}<span class="os-glw">{t[8]}</span>{t[9]} …</p>'
        '<div class="os-m">'
        '<p class="os-card os-sn"><span class="os-n">e</span> <span class="os-k">cites</span> '
        '<span class="os-abbr-n"><i>Ovid</i>.</span><span class="os-exp-n os-ul">Ovid</span></p>'
        f'<p class="os-card os-tr"><span class="os-k">trans.</span> {en} {pv}</p>'
        f'<p class="os-card os-icc"><span class="os-k os-k-c">§ cites</span> {esc(cite["display"])}</p>'
        f'<p class="os-card os-gl"><span class="os-k">gloss</span> <i>belike</i> {esc(gl["sense"])} '
        f'<span class="mn-src">{src_mark("webster1913")}</span> '
        f'{prov("Sense chosen from Webster 1913 by machine: " + gl["label"])}</p>'
        "</div></div></div>")
    return Markup(html_)


def front_specimen(unit_html: str, author_info: dict) -> Markup:
    """The front page's "How a page looks" (owner, 2026-11-21: "a representative text that responds in the same way
    when you interact with it"): the options' sample lines of Burton set as a page of this reader sets them, his text
    and its margin, each sign lighting its pair as in the reader, the names opening who they were. The translation
    is the one the reader shows first (Gowland's in the private build), taken from the rendered page; the citation
    and the names from their layers. No machine's sign: the front page shows none (owner, 2026-11-21, recorded in
    CLAUDE.md); each item carries its sign on its own page."""
    from lxml import html as lhtml

    from .render import esc as resc
    from .render import src_mark
    tr = json.loads((paths.LAYERS / "translations" / f"{SAMPLE_UNIT}.json").read_text(encoding="utf-8"))
    fid = next(k for k, r in tr.items() if r["text"] == SAMPLE_TEXT[4])
    tree = lhtml.fromstring(unit_html)
    ft = tree.xpath(f'//*[@id="tr-{fid}"]')
    v = ft[0].xpath('.//span[contains(concat(" ", @class, " "), " ft-v ")]')[0] if ft else None
    if v is None:
        raise SystemExit(f"front specimen: no translation of {fid} on the {SAMPLE_UNIT} page")
    en = " ".join(v.xpath('.//span[@class="ft-text"]')[0].text_content().split()).strip("[] ")
    mark = f' <span class="mn-src">{src_mark(v.get("data-src"))}</span>' if v.get("data-src") != "machine" else ""
    ic = json.loads((paths.LAYERS / "citations-inline" / f"{SAMPLE_UNIT}.json").read_text(encoding="utf-8"))
    cite = next(c for c in ic.values() if c["selector"]["in"] == SAMPLE_P and c["raw"].startswith("Hercules"))
    root = etree.parse(str(paths.TEXT / f"{SAMPLE_UNIT}.xml")).getroot()
    p = next(e for e in root.iter(T("p")) if e.get("{http://www.w3.org/XML/1998/namespace}id") == "u" + SAMPLE_P)
    notes = [" ".join(public_text(n).split()) for n in p.iter(T("note"))]
    if "Ovid." not in notes:
        raise SystemExit(f"front specimen: Burton's note \"Ovid.\" is no longer in {SAMPLE_P}")

    def name(key: str, shown: str) -> str:
        a = author_info[key]
        return (f'<span class="sp-nm" tabindex="0">{resc(shown)}<span class="sp-who" role="tooltip">'
                f'<b>{resc(a["name"])}</b> <span class="sp-dates">{resc(a.get("dates") or "")}</span> '
                f'{resc(a.get("about") or "")}</span></span>')
    t = [resc(x) for x in SAMPLE_TEXT]
    html_ = (
        '<div class="sp" role="group" aria-label="A few lines of Burton as a page of this reader shows them">'
        f'<p class="sp-h">Burton, {SAMPLE_UNIT} <span class="sp-hint">point at the marked words, or tap them</span></p>'
        f'<div class="sp-body"><p class="sp-text">… {t[0]}<i>{t[1]}</i>'
        '<span class="sp-ic" data-k="c" tabindex="0" aria-label="citation">§</span>'
        f'{t[3].rstrip()}<sup class="sp-ref" data-k="n" tabindex="0" aria-label="Note e">e</sup> '
        f'<i class="sp-la" data-k="t" tabindex="0" lang="la">{t[4]}</i>{t[5]}<i>{name("hesiod", SAMPLE_TEXT[6])}</i>'
        f'{t[7]}{t[8]}{t[9]} …</p>'
        '<div class="sp-m">'
        f'<p class="sp-card sp-sn" data-k="n"><span class="sp-n">e</span> <span class="sp-k">cites</span> '
        f'<i>{name("ovid", "Ovid")}</i>.</p>'
        f'<p class="sp-card sp-tr" data-k="t"><span class="sp-k">trans.</span> {resc(en)}{mark}</p>'
        f'<p class="sp-card sp-cc" data-k="c"><span class="sp-k sp-k-c">§ cites</span> {resc(cite["display"])}</p>'
        "</div></div></div>")
    return Markup(html_)

def env() -> Environment:
    e = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html"]),
                    keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=True)
    return e


def layer_for(unit: str, layer: str = "translations") -> dict:
    f = paths.LAYERS / layer / f"{unit}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def xrefs_for(unit: str, titles: dict) -> list[dict]:
    """Cross-references to show: explicit ones (linked when resolved, marked when not) and relative ones the
    owner (or a delegated reviewer) confirmed. Proposals awaiting review are not shown."""
    out = []
    for rec in layer_for(unit, "xrefs").values():
        ok = rec["status"] == "explicit-resolved"
        out.append({"selector": rec["selector"], "target": rec["target"] if ok else None,
                    "title": titles.get(rec["target"]) if ok else None})
    for rec in layer_for(unit, "xrefs-relative").values():
        if rec["status"] == "relative-confirmed":
            out.append({"selector": rec["selector"], "target": rec["target"], "title": titles.get(rec["target"])})
    return out


def visible_codepoints(html_text: str) -> set[int]:
    """Code points a page shows: its text, attribute text a user can see (alt, title, aria-label),
    and CSS generated content. Format characters (soft hyphen, joiners) draw no glyph."""


    attrs = " ".join(m.group(2) for m in re.finditer(r'\s(alt|title|aria-label|placeholder)="([^"]*)"', html_text))
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", html_text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text) + " " + attrs
    return {ord(c) for c in html.unescape(text) if not c.isspace() and unicodedata.category(c) != "Cf"}


def css_content_codepoints(css: str) -> set[int]:
    out = set()
    for m in re.finditer(r'content:\s*((?:"[^"]*"\s*|attr\([^)]*\)\s*)+)', css):
        for s in re.findall(r'"([^"]*)"', m.group(1)):
            s = re.sub(r"\\([0-9a-fA-F]{1,6}) ?", lambda x: chr(int(x.group(1), 16)), s)
            out |= {ord(c) for c in s if not c.isspace() and unicodedata.category(c) != "Cf"}
    return out


# ---------------------------------------------------------------- images
def png_size(p: Path) -> tuple[int, int]:
    with p.open("rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


class Images:
    def __init__(self, out: Path):
        self.dir = out / "assets" / "images"
        self.used: dict[str, Path] = {}
        self.alt = yaml.safe_load((paths.MANUAL / "alt-text.yaml").read_text(encoding="utf-8"))

    def get(self, name: str, root: str, alt: str | None = None) -> tuple[str, str, int, int]:
        src = paths.IMAGES / name
        if not src.exists():
            raise SystemExit(f"image {name} missing from the unpacked EPUB: run `burton unpack`")
        if alt is None:
            if name not in self.alt:
                raise SystemExit(f"image {name} has no entry in data/manual/alt-text.yaml")
            alt = " ".join(self.alt[name]["alt"].split())
        self.used[name] = src
        w, h = png_size(src)
        return f"{root}assets/images/{name}", alt, w, h

    def synopsis(self, p: int, root: str, label: str) -> list[tuple]:
        xhtml = (paths.XHTML / f"chapter00{p}.xhtml").read_text(encoding="utf-8")
        names = re.findall(r'src="\.\./images/(pg\d+_\d+\.png)"', xhtml)
        tpl = " ".join(self.alt["synopsis-sheets"]["alt"].split())
        return [self.get(n, root, tpl.format(partition=label, i=i, n=len(names))) for i, n in enumerate(names, 1)]

    def copy(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        for name, src in self.used.items():
            shutil.copy(src, self.dir / name)


# ---------------------------------------------------------------- contents tree


def toc_html(book: Book, root: str, current: str | None, *, ids: bool, only: Page | None = None,
             extras: str = "") -> str:
    """Nested contents list. `ids` puts anchor ids on groups (home and landing pages only)."""

    def link(pg: Page) -> str:
        cur = ' aria-current="page"' if pg.key == current else ""
        num = f'<span class="toc-n">{esc(pg.number)}</span> ' if pg.number else ""
        gow = ' <span class="toc-tag">Gowland’s translation</span>' if pg.gowland else ""
        return f'<a href="{root}{pg.href}"{cur}>{num}<span class="toc-t">{pg.title_html}</span>{gow}</a>'

    def group(pg: Page, depth: int) -> str:
        gid = f' id="toc-{attr(pg.key)}"' if ids else ""
        kids = "".join(item(c, depth + 1) for c in pg.children)
        return f'<li class="toc-g toc-d{depth}"{gid}><span class="toc-gl">{esc(pg.title)}</span><ol>{kids}</ol></li>'

    def item(pg: Page, depth: int) -> str:
        if pg.gowland and pg.key != current:  # Gowland's translation pages: shown facing their original (stage 4)
            return ""
        if pg.kind == "group":
            return group(pg, depth)
        if pg.kind == "partition":
            pid = f' id="toc-{attr(pg.key)}"' if ids else ""
            kids = "".join(item(c, depth + 1) for c in pg.children)
            return f'<li class="toc-part"{pid}>{link(pg)}<ol>{kids}</ol></li>'
        return f"<li>{link(pg)}</li>"

    if only is not None:
        return f'<ol class="toc">{"".join(item(c, 1) for c in only.children)}</ol>'
    fid = ' id="toc-front"' if ids else ""
    front = "".join(item(p, 1) for p in book.front)
    parts = "".join(item(p, 0) for p in book.partitions)
    back = ""
    if book.back:
        bid = ' id="toc-back"' if ids else ""
        back = (f'<li class="toc-part"{bid}><span class="toc-gl">Back matter</span>'
                f'<ol>{"".join(item(p, 1) for p in book.back)}</ol></li>')
    return (f'{extras}<ol class="toc"><li class="toc-part"{fid}><span class="toc-gl">Front matter</span>'
            f'<ol>{front}</ol></li>{parts}{back}</ol>')


# ---------------------------------------------------------------- about page data
def machine_labels() -> dict:
    """Who made the machine-produced records, read from the layers (never hard-coded)."""
    tr = Counter()
    for f in (paths.LAYERS / "translations").glob("*.json"):
        for rec in json.loads(f.read_text(encoding="utf-8")).values():
            for t in rec.get("translations", []):
                if t.get("by") == "machine":
                    tr[(t["model"], t["prompt"], t["date"])] += 1
    adj = Counter()
    f = paths.LAYERS / "langid-adjudication.json"
    if f.exists():
        data = json.loads(f.read_text(encoding="utf-8"))
        rows = data.get("rulings", data) if isinstance(data, dict) else data
        for r in (rows.values() if isinstance(rows, dict) else rows):
            if isinstance(r, dict) and r.get("model"):
                adj[(r["model"], r.get("prompt", "?"), r.get("date", "?"))] += 1
    return {"translations": sorted(tr.items()), "adjudication": sorted(adj.items())}


def gloss_model() -> str:
    """The model that ruled on the obsolete-word glosses, read from the layer."""
    models = sorted({rec["ruling"]["model"] for f in (paths.LAYERS / "obsolete").glob("*.json")
                     for rec in json.loads(f.read_text(encoding="utf-8")).values()})
    return ", ".join(models) or "none yet"


def source_hash() -> str:
    for line in paths.SOURCE_LOCK.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            return line.split()[0]
    return "?"


# ---------------------------------------------------------------- build
def build(units: list[str] | None, *, profile: str) -> dict:
    units = units or text_units()
    out = paths.SITE / profile
    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    # the decorated initials (stage 3; data/source/INITIALS.lock): the red set, light and dark, where both exist
    ini_src = paths.DATA / "source" / "initials"
    initials = {f.stem[-1] for f in ini_src.glob("red-light-?.webp")
                if (ini_src / f"red-dark-{f.stem[-1]}.webp").exists()}
    book = Book(profile, units)
    name_rx, name_ids, author_info = names.index()  # the name windows (stage 5)
    # the stage-14 sweeps, each shown only if its blind audit passed (data/eval/sweep-audit.yaml)
    obscure_rx, obscure_info = names_sweep.reader_index() if sweep_audit.passed("names") else ({}, {})
    show_cites, show_restored = sweep_audit.passed("cites"), sweep_audit.passed("restored")
    # what the full blind pass or the first sample judged wrong or doubtful is withheld (2026-11-20)
    cites_withheld = {i.split(":", 1)[1] for i in sweep_audit.withheld("cites")} if show_cites else set()
    # the translator notes cleared for the margin (stage 14; owner's remedy, 2026-11-19): rated 3, not doubtful, judged
    # sound by the blind auditor, and only once the fresh spot check passed; keyed by the hash of the very note
    from ..translate import notes_rate
    note_hashes = ({pid: r["note_hash"] for pid, r in notes_rate._layer().items()
                    if notes_rate.shown(r, notes_rate._audits().get(pid))} if notes_rate.passed() else {})
    cite_label = authors_pages.tables_label()["short"]
    titles = {k: f"{k} {pg.title}" for k, pg in book.pages.items() if pg.kind in ("unit", "front", "back")}
    findings = yaml.safe_load((paths.MANUAL / "source-findings.yaml").read_text(encoding="utf-8"))
    findings["names"] = {a: s["name"] for a, s in authors_pages.citations.tables()["authors"].items()}
    images = Images(out)
    jenv = env()
    jenv.globals["opt_sample"] = options_sample()
    pages: dict[str, str] = {}
    report = {"profile": profile, "units": {}, "density": {}}
    shown_notes: set[str] = set()  # sidenote ids rendered in this profile, for the author pages' links

    parsed_units = {}
    words_by_unit: dict[str, int] = {}
    for u in book.units:
        div = etree.parse(str(paths.TEXT / f"{u}.xml")).getroot().find(f".//{T('div')}")
        parsed_units[u] = div
        words_by_unit[u] = len(public_text(div).split())

    def page(key: str, rel: str, template: str, **kw) -> None:
        root = "../" * rel.count("/")
        pg = book.pages.get(key)
        prev, nxt = book.neighbours(key)
        kw.setdefault("crumbs", book.crumbs(key) if pg else [])
        extras = labyrinth.contents_extras_html(root, book, words_by_unit)
        pages[rel] = jenv.get_template(template).render(
            root=root, profile=profile, key=key, prev=prev, next=nxt,
            toc=Markup(toc_html(book, root, key, ids=False, extras=extras)), **kw)

    def front_nav(current: str) -> Markup:
        """Every page of the front matter, the reader's own marked (owner, 2026-11-18): after "Enter, gentle Reader"
        the front matter has its own contents at the head of each of its pages."""
        # one markup for round 8's three designs (A a ruled tablet, B Roman numerals, D a thumb index), chosen by CSS:
        # A by default (owner, 2026-11-19), B and D for comparison on the real pages (?fm=B, ?fm=D; edition.js)
        roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
        fronts = [fp for fp in book.front if not fp.gowland]
        items = "".join(f'<li><a href="../{attr(fp.key)}/" title="{attr(fp.title)}"'
                        f'{' aria-current="page"' if fp.key == current else ""}><span class="fn-n">{roman[i]}</span> '
                        f'<span class="fn-t">{fp.title_html}</span></a></li>' for i, fp in enumerate(fronts))
        return Markup(f'<nav class="front-nav" aria-label="The front matter"><ol>{items}</ol></nav>')

    back = synopsis.back_links([pg.key for pg in book.partitions], book.units)  # unit -> its node in the synopsis
    plain = {u: book.pages[u].title for u in book.units if u in book.pages}  # for the synopsis mark (N1 D)
    shown_titles = {u: f"{u} {book.pages[u].title}" for u in book.units if u in book.pages}
    part_first = {next(u for u in book.units if u.startswith(f"{pt.key[1:]}.")): pt for pt in book.partitions
                  if any(u.startswith(f"{pt.key[1:]}.") for u in book.units)}

    # where each Penguin page begins, for the Table's locators (private build only: the numbers are Gowland's)
    pagemap = {}
    if profile == "private":
        for u in book.units:
            for pb in etree.parse(str(paths.TEXT / f"{u}.xml")).getroot().iter(T("pb")):
                pagemap[pb.get("n")] = u

    def plate(name, src, alt, w, h):  # the frontispiece on the Argument page, its panels linked to the stanzas
        return frontispiece.figure_html(src, alt, w, h, "", here=True) if name == frontispiece.load()["image"] else None

    gstats: dict = {}  # Gowland's glosses found and placed (private build)

    # units and front matter
    for unit in book.units:
        div = parsed_units[unit]
        body, counts = render_unit(div, unit, profile, layer_for(unit),
                                   image=lambda n: images.get(n, "../"), djs=layer_for(unit, "djs"),
                                   cites=layer_for(unit, "citations"), cite_label=cite_label,
                                   verified=layer_for(unit, "source-verification"), findings=findings,
                                   xrefs=xrefs_for(unit, titles), plate=plate if unit == "argument" else None,
                                   # Gowland's own glosses are margin items now (gowland_notes), so the optional
                                   # in-line glosses keep only Webster's and the machine ones
                                   pagemap=pagemap, glosses=glosses.items_for(unit, "public", gstats),
                                   restored=layer_for(unit, "restored-notes"),
                                   gowland_entries=(gowland_notes.entries(unit, gstats)
                                                    if profile == "private" else None),
                                   cexp=layer_for(unit, "citation-expansions"), initials=initials,
                                   inline_cites=layer_for(unit, "citations-inline"),
                                   psalms=layer_for(unit, "psalm-check"),
                                   # Gowland's translation pages, set facing Burton's Latin (stage 9)
                                   facing_src=facing.sources(unit) if profile == "private" else None,
                                   names=name_rx, name_ids=name_ids, author_info=author_info,
                                   restored_read=layer_for(unit, "restored-read") if show_restored else None,
                                   inline_cites_model=({k: v for k, v in layer_for(unit, "citations-inline-model")
                                                        .items() if k not in cites_withheld} if show_cites else None),
                                   note_hashes=note_hashes,
                                   name_extra=(obscure_rx.get(unit), obscure_info))
        if unit == "argument":
            body, counts["panel_links"] = frontispiece.add_back_links(body)
        if unit in part_first and (tree := synopsis.load(part_first[unit].key)):
            # the Partition's synopsis at the head of its first page, folded (owner, 2026-11-04): the click-through goes
            # from the front matter straight into the text, past the landing and synopsis pages
            # Folded wholly, as on the front page, with no heading or link of its own (owner, 2026-11-20: just
            # "I The First Partition {&c."): resting on it opens its sheets, each folded to its opening line
            pt = part_first[unit]
            of = esc(pt.title.removeprefix("The "))
            body = (f'<section class="part-syn" aria-label="Burton’s synopsis of the {of}">'
                    f'{synopsis.front_html([(pt.key, pt.title, tree)], "../", shown_titles)}</section>\n' + body)
        report["units"][unit] = counts
        shown_notes.update(re.findall(r'<span class="sidenote" id="([^"]+)"', body))  # restored ones: "sidenote sn-…"
        words = words_by_unit[unit]
        if counts["sidenotes"]:
            report["density"][unit] = round(1000 * counts["sidenotes"] / max(words, 1), 1)
        pg = book.pages[unit]
        has_h1 = "<h1" in body
        here = back.get(unit)
        signposts = synopsis.extract_signposts(body) if words >= 2500 else []
        place = (Markup(synopsis.branch_html(unit, here[0], here[1], "../", plain, signposts=signposts))
                 if here else (Markup(synopsis.compass_html(pg.title, signposts)) if signposts else None))
        page(unit, f"{unit}/index.html", "unit.html", page=pg, body=Markup(body),
             hidden_h1=None if has_h1 else pg.title,
             place=place,
             front_nav=front_nav(unit) if pg.kind == "front" else None,
             title=pg.title if pg.kind in ("front", "back") else f"{unit} {pg.title}",
             description=f"Burton, The Anatomy of Melancholy, {pg.title}")

    # Partition landings: title, synopsis sheets, contents of the Partition
    for part in book.partitions:
        p = int(part.key[1:])
        first = next(c for c in book.units if c.startswith(f"{p}."))
        div = etree.parse(str(paths.TEXT / f"{first}.xml")).getroot().find(f".//{T('div')}")
        sub = next((public_text(h) for h in div.iter(T("head")) if h.get("subtype") == "part_title3"), None)
        syn_key = f"{part.key}-synopsis"
        page(part.key, f"{part.key}/index.html", "partition.html", page=part, subtitle=sub,
             sheets=images.synopsis(p, "../", part.title),
             synopsis=book.pages.get(syn_key),
             contents=Markup(toc_html(book, "../", None, ids=True, only=part)),
             title=part.title, description=f"Burton, The Anatomy of Melancholy: {part.title}")

        # the synopsis as a tree (M7): Burton's words, the branching read from the sheets, links both ways
        if syn_key in book.pages:
            tree = synopsis.load(part.key)
            built = {u: f"{u} {book.pages[u].title}" for u in book.units if u in book.pages}
            spg = book.pages[syn_key]
            page(syn_key, f"{part.key}/synopsis/index.html", "synopsis.html", page=spg,
                 tree=Markup(synopsis.tree_html(tree, "../../", built)), label=synopsis.label(tree),
                 sheets=images.synopsis(p, "../../", part.title), title=spg.title,
                 description=f"Burton, The Anatomy of Melancholy: {spg.title}, as a linked tree")

    # home
    front = images.get("pg003.png", "")
    front_map = stanzas = None
    if "argument" in book.pages:
        # no caption and no machine's sign on the front page (owner, 2026-11-21); the Argument page carries the label
        front_map = Markup(frontispiece.figure_html(*front, "argument/", here=False, caption=None,
                                                       zoom_title=True))
        # beside each stanza its margin items as the Argument page has them; beside the first, the hint, which goes
        # once the reader has pointed at a panel (owner, 2026-11-21)
        arg = book.pages["argument"]
        hint = (f'<p class="fs-hint">Select a panel to the left to read the associated stanza from '
                f'<a href="{attr(arg.href)}">{esc(arg.title)}</a>.</p>')
        stanzas = Markup(frontispiece.stanzas_html(frontispiece.glosses_from(pages.get("argument/index.html", "")),
                                                   hint))
    # the three synopses on the front page, folded so the page fits one screen; resting on a Partition's name opens
    # it onto its sheets (owner, 2026-11-19: rubric numerals, "&c.")
    shown = {u: f"{u} {book.pages[u].title}" for u in book.units if u in book.pages}
    have = [p for p in book.partitions if (paths.DATA / "synopses" / f"{p.key}.json").exists()]
    synopses = {"sheet": Markup(synopsis.front_html([(p.key, p.title, synopsis.load(p.key)) for p in have], "", shown)),
                "pages": [{"n": synopsis.ROMAN.get(p.key, p.key), "href": f"{p.key}/synopsis/"} for p in have]
                } if have else None

    page("about", "about/index.html", "about.html", page=book.pages["about"], crumbs=[("About", None)],
         title="About", description="How to read this edition, where each part comes from, and its rights",
         labels=machine_labels(), source_hash=source_hash(), n_units=len(book.units), gloss_model=gloss_model(),
         built=date.today().isoformat())
    page("settings", "settings/index.html", "settings.html", page=book.pages["settings"],
         crumbs=[("Reading options", None)], title="Reading options",
         description="Language mode, theme and type size")

    # full-text search (M8): the index is a file of its own, fetched by the search page when used
    labels = {u: (f"{u} {book.pages[u].title}" if book.pages[u].kind == "unit" else book.pages[u].title)
              for u in book.units}
    index, sstats = search.build_index(book.units, labels, profile, layer_for)
    sstats["bytes"] = search.write_index(index, out / "assets" / "search-index.json")
    report["search"] = sstats
    report["restored_notes"] = {k: sum(c.get(k, 0) for c in report["units"].values())
                                for k in ("restored_notes", "restored_unplaced")}
    report["glosses"] = {**gstats, **{k: sum(c.get(k, 0) for c in report["units"].values())
                                      for k in ("glosses", "glosses_gowland", "glosses_webster1913", "glosses_machine",
                                                "glosses_unplaced", "glosses_unplaced_notfound",
                                                "glosses_unplaced_markup", "glosses_unplaced_overlap")}}
    report["citations"] = {k: sum(c.get(k, 0) for c in report["units"].values())  # stage 6
                           for k in ("cite_expansions", "cite_expansions_rule", "cite_expansions_model",
                                     "cite_expansions_raw_mismatch", "cite_unplaced", "inline_cites",
                                     "inline_cites_cites", "inline_cites_bible", "inline_cites_unplaced",
                                     "inline_cites_in_passage", "bible_verses", "bible_without_verses")}
    print("citations:", ", ".join(f"{k} {v}" for k, v in report["citations"].items()))
    page("search", "search/index.html", "search.html", page=book.pages["search"], crumbs=[("Search", None)],
         title="Search", description="Search Burton’s text, sidenotes and translations", stats=sstats)

    # the author index and one page per cited author (M6)
    apages, astats = authors_pages.collect(book.units, shown_notes)
    alpha = sorted(apages.values(), key=lambda a: a["name"].lower())
    page("authors", "authors/index.html", "authors.html", page=book.pages["authors"],
         crumbs=[("Authors cited", None)], title="Authors cited",
         description="The authors Burton cites in his sidenotes", authors=alpha, stats=astats,
         tables=authors_pages.tables_label())
    for a in alpha:
        page(f"author:{a['id']}", f"authors/{a['id']}/index.html", "author.html", page=None,
             crumbs=[("Authors cited", "authors/"), (a["name"], None)], title=a["name"],
             description=f"{a['name']}, as cited by Burton in The Anatomy of Melancholy", a=a)
    report["authors"] = {"pages": len(alpha), **astats}
    labyrinth.write_sortes(labyrinth.sortes_pool(book, words_by_unit), out / "assets" / "sortes.json")
    page("glossary", "glossary/index.html", "glossary.html", page=book.pages["glossary"],
         crumbs=[("Glossary", None)], title="Glossary",
         description=("Humoral terms, apothecary signs, citation locators, and recurring authorities "
                      "in The Anatomy of Melancholy"),
         glossary=glossary_page.collect(apages))
    # a name or an expansion links to an author's page only if this build made one (an entry whose author is cited
    # only outside the notes, or only in notes the public build withholds, has none): unwrap the rest
    dead = re.compile(r'<a class="(?:nm|cx-a|cx-a nm)" href="\.\./authors/([^/"]+)/"[^>]*>(.*?)</a>', re.S)
    unwrapped = 0
    for rel in pages:
        def keep(m):
            nonlocal unwrapped
            if m.group(1) in apages:
                return m.group(0)
            unwrapped += 1
            return m.group(2)
        pages[rel] = dead.sub(keep, pages[rel])
    report["authors"]["links_without_page_unwrapped"] = unwrapped
    home_extras = labyrinth.contents_extras_html("", book, words_by_unit)
    pages["index.html"] = jenv.get_template("home.html").render(
        root="", profile=profile, key="home", crumbs=[], prev=None, next=book.pages[book.order[0]],
        toc=Markup(""), contents=Markup(toc_html(book, "", None, ids=True, extras=home_extras)),
        frontispiece=front, front_map=front_map,
        argument=book.pages.get("argument"), dedication=book.pages.get("dedication"), stanzas=stanzas,
        synopses=synopses,
        specimen=front_specimen(pages["3.2.3.1/index.html"], author_info) if "3.2.3.1/index.html" in pages else "",
        title="The Anatomy of Melancholy",
        description="A reading edition of Robert Burton’s Anatomy of Melancholy")

    # fonts: subset to exactly what the pages and the stylesheet show
    css_src = (HERE / "static" / "edition.css").read_text(encoding="utf-8")
    used = set().union(*(visible_codepoints(p) for p in pages.values())) | css_content_codepoints(css_src)
    used |= search.codepoints(index)
    faces = fonts.build_subsets(used, out / "assets" / "fonts")
    css = []
    for f in faces:
        rng = ""
        if f["ranged"]:  # the symbols' fallback, and Greek (GFS Didot) for its letters only
            rng = ";unicode-range:" + ",".join(f"U+{c:04X}" for c in sorted(f["cmap"]))
        weight = "400" if f["ranged"] else "400 800"
        css.append(f'@font-face{{font-family:"{f["family"]}";font-style:{f["style"]};font-weight:{weight};'
                   f'font-display:swap;src:url("fonts/{f["file"]}") format("woff2"){rng};}}\n')
    css.append(f":root{{--font-text:{fonts.STACK};}}\n")
    (out / "assets" / "fonts.css").write_text("".join(css), encoding="utf-8", newline="\n")
    for lic in ("EBGaramond-OFL.txt", "Cardo-OFL.txt", "GFSDidot-OFL.txt"):
        shutil.copy(paths.FONTS_SRC / lic, out / "assets" / "fonts" / lic)
    for name in STATIC:
        shutil.copy(HERE / "static" / name, out / "assets" / name)
    images.copy()
    used_initials = sorted({c for u in report["units"].values() for c in u.get("initial_letters", [])})
    if used_initials:
        (out / "assets" / "initials").mkdir()
        for c in used_initials:
            for theme in ("light", "dark"):
                shutil.copy(ini_src / f"red-{theme}-{c}.webp", out / "assets" / "initials" / f"red-{theme}-{c}.webp")
    report["initials"] = {"letters": len(used_initials), "units": sum(1 for u in report["units"].values()
                                                                      if u.get("initials"))}

    for rel, text in pages.items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8", newline="\n")

    manifest = {"name": "The Anatomy of Melancholy", "short_name": "Anatomy", "start_url": "./",
                "scope": "./", "display": "standalone", "background_color": "#f7f3ea",
                "theme_color": "#23201b", "lang": "en",
                "icons": [{"src": "assets/icon.svg", "sizes": "any", "type": "image/svg+xml"}]}
    (out / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")

    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    h = hashlib.sha256()
    for f in files:
        h.update((out / f).read_bytes())
    precache = ["./"] + [f.removesuffix("index.html") for f in files]
    sw = (HERE / "static" / "sw.js").read_text(encoding="utf-8")
    sw = sw.replace("__VERSION__", f"{profile}-{h.hexdigest()[:12]}")
    sw = sw.replace("__FILES__", json.dumps(precache, indent=1))
    (out / "sw.js").write_text(sw, encoding="utf-8", newline="\n")

    fallback = sorted(c for f in faces if f["fallback"] for c in f["cmap"] if c in used)
    report["fonts"] = {f["file"]: len(f["cmap"]) for f in faces}
    report["fallback_glyphs"] = "".join(chr(c) for c in fallback)
    report["codepoints_used"] = len(used)
    report["pages"] = len(pages)
    report["files"] = len(files) + 1
    report["densest"] = sorted(report["density"].items(), key=lambda kv: -kv[1])[:5]
    rep = paths.STATE / "build" / f"{profile}.json"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    kinds = Counter(book.pages[k].kind for k in book.order)
    fb = " ".join(f"U+{c:04X}" for c in fallback) or "none"
    print(f"built site/{profile}: {len(pages)} pages ({dict(kinds)} + home, about, settings), "
          f"{report['files']} files, {len(used)} distinct glyphs, fallback glyphs {fb}; "
          f"densest notes per 1,000 words {report['densest'][:3]}")
    return report
