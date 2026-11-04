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
from ..tei import T
from ..textview import public_text
from . import authors_pages, fonts, frontispiece, glosses, gowland_notes, names, search, synopsis
from .book import Book, Page, text_units
from .render import attr, esc, render_unit

HERE = Path(__file__).parent
STATIC = ("edition.css", "edition.js", "search.js", "icon.svg")


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
FACING = {"ad-librum": "ad-librum-gowland", "lectori": "lectori-gowland"}  # Burton's Latin poem -> Gowland's page


def toc_html(book: Book, root: str, current: str | None, *, ids: bool, only: Page | None = None) -> str:
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
    return (f'<ol class="toc"><li class="toc-part"{fid}><span class="toc-gl">Front matter</span>'
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
    cite_label = authors_pages.tables_label()["short"]
    titles = {k: f"{k} {pg.title}" for k, pg in book.pages.items() if pg.kind in ("unit", "front", "back")}
    findings = yaml.safe_load((paths.MANUAL / "source-findings.yaml").read_text(encoding="utf-8"))
    findings["names"] = {a: s["name"] for a, s in authors_pages.citations.tables()["authors"].items()}
    images = Images(out)
    jenv = env()
    pages: dict[str, str] = {}
    report = {"profile": profile, "units": {}, "density": {}}
    shown_notes: set[str] = set()  # sidenote ids rendered in this profile, for the author pages' links

    def page(key: str, rel: str, template: str, **kw) -> None:
        root = "../" * rel.count("/")
        pg = book.pages.get(key)
        prev, nxt = book.neighbours(key)
        kw.setdefault("crumbs", book.crumbs(key) if pg else [])
        pages[rel] = jenv.get_template(template).render(
            root=root, profile=profile, key=key, prev=prev, next=nxt,
            toc=Markup(toc_html(book, root, key, ids=False)), **kw)

    back = synopsis.back_links([pg.key for pg in book.partitions], book.units)  # unit -> its node in the synopsis

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
        xml = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        div = xml.find(f".//{T('div')}")
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
                                   names=name_rx, name_ids=name_ids, author_info=author_info)
        if unit == "argument":
            body, counts["panel_links"] = frontispiece.add_back_links(body)
        if (g := FACING.get(unit)) and profile == "private" and g in book.pages:
            # Gowland's translation of a Latin poem, set facing it by edition.js (stage 4); his page stays in the build
            body = (f'<p class="facing-link" data-resp="gowland"><a href="../{g}/" data-facing="../{g}/">'
                    "Gowland’s translation, facing</a></p>\n" + body)
        report["units"][unit] = counts
        shown_notes.update(re.findall(r'<span class="sidenote" id="([^"]+)"', body))  # restored ones: "sidenote sn-…"
        words = len(public_text(div).split())
        if counts["sidenotes"]:
            report["density"][unit] = round(1000 * counts["sidenotes"] / max(words, 1), 1)
        pg = book.pages[unit]
        has_h1 = "<h1" in body
        here = back.get(unit)
        page(unit, f"{unit}/index.html", "unit.html", page=pg, body=Markup(body),
             hidden_h1=None if has_h1 else pg.title,
             synopsis_href=f"../{here[0]}/synopsis/#{here[1]}" if here else None,
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
        arg = book.pages["argument"]
        cap = f'The engraved title page of 1628; <a href="{attr(arg.href)}">{esc(arg.title)}</a> describes its panels'
        front_map = Markup(frontispiece.figure_html(*front, "argument/", here=False, caption=cap))
        stanzas = Markup(frontispiece.stanzas_html())
    # the three synopses, collapsed, on the front page (owner, 2026-11-03: T13, R4 B)
    shown = {u: f"{u} {book.pages[u].title}" for u in book.units if u in book.pages}
    synopses = [{"title": f"The Synopsis of the {part.title.removeprefix('The ')}", "href": f"{part.key}/synopsis/",
                 "tree": Markup(synopsis.tree_html(synopsis.load(part.key), "", shown))}
                for part in book.partitions if (paths.DATA / "synopses" / f"{part.key}.json").exists()]
    pages["index.html"] = jenv.get_template("home.html").render(
        root="", profile=profile, key="home", crumbs=[], prev=None, next=book.pages[book.order[0]],
        toc=Markup(""), contents=Markup(toc_html(book, "", None, ids=True)), frontispiece=front, front_map=front_map,
        argument=book.pages.get("argument"), dedication=book.pages.get("dedication"), stanzas=stanzas,
        synopses=synopses, title="The Anatomy of Melancholy",
        description="A reading edition of Robert Burton’s Anatomy of Melancholy")

    page("about", "about/index.html", "about.html", page=book.pages["about"], crumbs=[("About this edition", None)],
         title="About this edition", description="Sources, provenance labels and rights",
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
    # a name or an expansion links to an author's page only if this build made one (an entry whose author is cited
    # only outside the notes, or only in notes the public build withholds, has none): unwrap the rest
    dead = re.compile(r'<a class="(?:nm|cx-a)" href="\.\./authors/([^/"]+)/"[^>]*>(.*?)</a>', re.S)
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

    # fonts: subset to exactly what the pages and the stylesheet show
    css_src = (HERE / "static" / "edition.css").read_text(encoding="utf-8")
    used = set().union(*(visible_codepoints(p) for p in pages.values())) | css_content_codepoints(css_src)
    used |= search.codepoints(index)
    faces = fonts.build_subsets(used, out / "assets" / "fonts")
    css = []
    for f in faces:
        rng = ""
        if f["fallback"]:
            rng = ";unicode-range:" + ",".join(f"U+{c:04X}" for c in sorted(f["cmap"]))
        weight = "400" if f["fallback"] else "400 800"
        css.append(f'@font-face{{font-family:"{f["family"]}";font-style:{f["style"]};font-weight:{weight};'
                   f'font-display:swap;src:url("fonts/{f["file"]}") format("woff2"){rng};}}\n')
    css.append(f":root{{--font-text:{fonts.STACK};}}\n")
    (out / "assets" / "fonts.css").write_text("".join(css), encoding="utf-8", newline="\n")
    for lic in ("EBGaramond-OFL.txt", "Cardo-OFL.txt"):
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
