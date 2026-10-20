"""`burton build --profile private|public`: data/text + layers -> site/<profile>/."""

import hashlib
import json
import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from lxml import etree
from markupsafe import Markup

from .. import paths
from ..tei import T
from ..textview import public_text
from . import fonts
from .render import render_unit

HERE = Path(__file__).parent
ORDINAL = ["First", "Second", "Third"]


def env() -> Environment:
    return Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html"]),
                       keep_trailing_newline=True)


def crumbs(unit: str) -> list[str]:
    p, s, m, u = unit.split(".")
    return [f"The {ORDINAL[int(p) - 1]} Partition", f"Section {s}", f"Member {m}", f"Subsection {u}"]


def layer_for(unit: str) -> dict:
    f = paths.LAYERS / "translations" / f"{unit}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def visible_codepoints(html_text: str) -> set[int]:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", html_text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    import html as h

    return {ord(c) for c in h.unescape(text) if not c.isspace()}


def build(units: list[str], *, profile: str) -> dict:
    out = paths.SITE / profile
    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    tpl = env().get_template("page.html")
    pages: dict[str, str] = {}
    report = {"profile": profile, "units": {}}

    titles = {}
    for unit in units:
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        div = root.find(f".//{T('div')}")
        title = next((public_text(h) for h in div.iter(T("head")) if h.get("type") == "title"), unit)
        titles[unit] = title
        body, counts = render_unit(div, unit, profile, layer_for(unit))
        report["units"][unit] = counts
        i = units.index(unit)
        prev = {"href": f"../{units[i - 1]}/", "label": units[i - 1]} if i > 0 else None
        nxt = {"href": f"../{units[i + 1]}/", "label": units[i + 1]} if i + 1 < len(units) else None
        pages[f"{unit}/index.html"] = tpl.render(
            title=f"{unit} {title}", description=f"Burton, The Anatomy of Melancholy, {unit}: {title}",
            root="../", profile=profile, crumbs=crumbs(unit), body=Markup(body), prev=prev, next=nxt)

    items = "".join(f'<li><a href="{u}/">{u} <em>{titles[u]}</em></a></li>' for u in units)
    home = (f'<div class="home-page"><h1>The Anatomy of Melancholy</h1>'
            f'<p class="sub">Robert Burton · a reading edition in progress</p>'
            f'<h2 class="sr-only">Contents</h2><ol>{items}</ol></div>')
    pages["index.html"] = tpl.render(title="Contents", description="A reading edition of Burton’s Anatomy",
                                     root="", profile=profile, crumbs=None, body=Markup(home))

    # fonts: subset to exactly what the pages show
    used = set().union(*(visible_codepoints(p) for p in pages.values()))
    faces = fonts.build_subsets(used, out / "assets" / "fonts")
    css = "".join(
        f'@font-face{{font-family:"{f["family"]}";font-style:{f["style"]};font-weight:400 800;'
        f'font-display:swap;src:url("fonts/{f["file"]}") format("woff2");}}\n' for f in faces)
    (out / "assets" / "fonts.css").write_text(css, encoding="utf-8")
    shutil.copy(paths.FONTS_SRC / "EBGaramond-OFL.txt", out / "assets" / "fonts" / "OFL.txt")
    for name in ("edition.css", "edition.js", "icon.svg"):
        shutil.copy(HERE / "static" / name, out / "assets" / name)

    for rel, text in pages.items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")

    manifest = {"name": "The Anatomy of Melancholy", "short_name": "Anatomy", "start_url": "./",
                "scope": "./", "display": "standalone", "background_color": "#f7f3ea",
                "theme_color": "#23201b", "lang": "en",
                "icons": [{"src": "assets/icon.svg", "sizes": "any", "type": "image/svg+xml"}]}
    (out / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    digest = hashlib.sha256("".join((out / f).read_text("latin-1") for f in files).encode("latin-1")).hexdigest()[:12]
    precache = ["./"] + [f.removesuffix("index.html") for f in files]
    sw = (HERE / "static" / "sw.js").read_text(encoding="utf-8")
    sw = sw.replace("__VERSION__", f"{profile}-{digest}").replace("__FILES__", json.dumps(precache, indent=1))
    (out / "sw.js").write_text(sw, encoding="utf-8")

    report["fonts"] = {f["file"]: len(f["cmap"]) for f in faces}
    report["codepoints_used"] = len(used)
    report["files"] = len(files) + 1
    rep = paths.STATE / "build" / f"{profile}.json"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"built site/{profile}: {len(units)} unit page(s), {report['files']} files, "
          f"{len(used)} distinct glyphs; counts {report['units']}")
    return report
