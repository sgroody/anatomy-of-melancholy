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
from . import fonts
from .book import Book, Page, text_units
from .render import attr, esc, render_unit

HERE = Path(__file__).parent
STATIC = ("edition.css", "edition.js", "icon.svg")


def env() -> Environment:
    e = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html"]),
                    keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=True)
    return e


def layer_for(unit: str) -> dict:
    f = paths.LAYERS / "translations" / f"{unit}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


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
    return (f'<ol class="toc"><li class="toc-part"{fid}><span class="toc-gl">Front matter</span>'
            f'<ol>{front}</ol></li>{parts}</ol>')


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
    book = Book(profile, units)
    images = Images(out)
    jenv = env()
    pages: dict[str, str] = {}
    report = {"profile": profile, "units": {}, "density": {}}

    def page(key: str, rel: str, template: str, **kw) -> None:
        root = "../" * rel.count("/")
        pg = book.pages.get(key)
        prev, nxt = book.neighbours(key)
        kw.setdefault("crumbs", book.crumbs(key) if pg else [])
        pages[rel] = jenv.get_template(template).render(
            root=root, profile=profile, key=key, prev=prev, next=nxt,
            toc=Markup(toc_html(book, root, key, ids=False)), **kw)

    # units and front matter
    for unit in book.units:
        xml = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        div = xml.find(f".//{T('div')}")
        body, counts = render_unit(div, unit, profile, layer_for(unit),
                                   image=lambda n: images.get(n, "../"))
        report["units"][unit] = counts
        words = len(public_text(div).split())
        if counts["sidenotes"]:
            report["density"][unit] = round(1000 * counts["sidenotes"] / max(words, 1), 1)
        pg = book.pages[unit]
        has_h1 = "<h1" in body
        page(unit, f"{unit}/index.html", "unit.html", page=pg, body=Markup(body),
             hidden_h1=None if has_h1 else pg.title,
             title=pg.title if pg.kind == "front" else f"{unit} {pg.title}",
             description=f"Burton, The Anatomy of Melancholy, {pg.title}")

    # Partition landings: title, synopsis sheets, contents of the Partition
    for part in book.partitions:
        p = int(part.key[1:])
        first = next(c for c in book.units if c.startswith(f"{p}."))
        div = etree.parse(str(paths.TEXT / f"{first}.xml")).getroot().find(f".//{T('div')}")
        sub = next((public_text(h) for h in div.iter(T("head")) if h.get("subtype") == "part_title3"), None)
        page(part.key, f"{part.key}/index.html", "partition.html", page=part, subtitle=sub,
             sheets=images.synopsis(p, "../", part.title),
             contents=Markup(toc_html(book, "../", None, ids=True, only=part)),
             title=part.title, description=f"Burton, The Anatomy of Melancholy: {part.title}")

    # home
    front = images.get("pg003.png", "")
    pages["index.html"] = jenv.get_template("home.html").render(
        root="", profile=profile, key="home", crumbs=[], prev=None, next=book.pages[book.order[0]],
        toc=Markup(""), contents=Markup(toc_html(book, "", None, ids=True)), frontispiece=front,
        argument=book.pages.get("argument"), title="Contents",
        description="A reading edition of Robert Burton’s Anatomy of Melancholy")

    page("about", "about/index.html", "about.html", page=book.pages["about"], crumbs=[("About this edition", None)],
         title="About this edition", description="Sources, provenance labels and rights",
         labels=machine_labels(), source_hash=source_hash(), n_units=len(book.units),
         built=date.today().isoformat())
    page("settings", "settings/index.html", "settings.html", page=book.pages["settings"],
         crumbs=[("Reading options", None)], title="Reading options",
         description="Language mode, theme and type size")

    # fonts: subset to exactly what the pages and the stylesheet show
    css_src = (HERE / "static" / "edition.css").read_text(encoding="utf-8")
    used = set().union(*(visible_codepoints(p) for p in pages.values())) | css_content_codepoints(css_src)
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
