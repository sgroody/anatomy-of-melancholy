"""Site-side checks on the generated HTML (SPEC §9): V2/V3 on HTML, V4 on HTML, V6 links,
V8 profile leak, V9 font coverage, V10 HTML validity and basic accessibility.

Reads only site/ and data/text (never the renderer), so a renderer bug cannot hide itself.
"""

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import html5lib
from fontTools.ttLib import TTFont
from lxml import etree

from .. import paths
from .checks import ARABIC, ED, GREEK, HEBREW, TEI, Result

XH = "{http://www.w3.org/1999/xhtml}"


def parse(path: Path):
    """Strict HTML5 parse; returns (tree, parse errors)."""
    parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"), strict=False)
    tree = parser.parse(path.read_bytes())
    return tree, parser.errors


def pages(profile: str) -> list[Path]:
    return sorted((paths.SITE / profile).rglob("*.html"))


def by_class(tree, cls: str) -> list:
    return tree.xpath(f"//*[contains(concat(' ', normalize-space(@class), ' '), ' {cls} ')]")


def lang_of(e) -> str | None:
    while e is not None:
        if e.get("lang"):
            return e.get("lang")
        e = e.getparent()
    return None


def site_results(units: list[str]) -> list[Result]:
    v2 = Result("V2h", "per-unit counts XML = HTML")
    v3 = Result("V3h", "every note marker resolves")
    v4 = Result("V4h", "HTML foreign scripts carry lang")
    v6 = Result("V6", "links resolve")
    v8 = Result("V8", "public build has no Gowland matter")
    v9 = Result("V9", "font coverage")
    v10 = Result("V10", "HTML validity and basic accessibility")
    tot = {k: 0 for k in ("markers", "resolved", "script_chars", "untagged", "links", "broken",
                          "parse_errors", "a11y_issues", "leaks", "uncovered")}

    for profile in ("private", "public"):
        site = paths.SITE / profile
        for page in pages(profile):
            tree, errors = parse(page)
            rel = page.relative_to(site).as_posix()
            ids = {e.get("id") for e in tree.iter() if isinstance(e.tag, str) and e.get("id")}
            tot["parse_errors"] += len(errors)
            for pos, code, _data in errors[:5]:
                v10.fail(f"{profile}/{rel}: HTML parse error {code} at {pos}")

            # V3h: markers -> notes
            for a in by_class(tree, "nref"):
                tot["markers"] += 1
                target = a.get("href", "")[1:]
                note = tree.xpath(f"//*[@id='{target}']")
                if note and "sidenote" in (note[0].get("class") or ""):
                    tot["resolved"] += 1
                else:
                    v3.fail(f"{profile}/{rel}: marker {a.get('id')} -> {target} unresolved")

            # V4h: script characters must sit under a matching lang
            for e in tree.iter():
                if not isinstance(e.tag, str) or e.tag in (f"{XH}script", f"{XH}style"):
                    continue
                for text, owner in ((e.text, e), (e.tail, e.getparent())):
                    if not text or owner is None:
                        continue
                    for rx, langs in ((GREEK, ("grc", "el")), (HEBREW, ("he",)), (ARABIC, ("ar",))):
                        for m in rx.finditer(text):
                            tot["script_chars"] += 1
                            if lang_of(owner) not in langs:
                                tot["untagged"] += 1
                                v4.fail(f"{profile}/{rel}: {m.group(0)!r} without lang")

            # V6: every local href/src resolves (file and fragment)
            for e in tree.iter():
                if not isinstance(e.tag, str):
                    continue
                for att in ("href", "src"):
                    url = e.get(att)
                    if not url or re.match(r"^[a-z]+:", url):
                        continue
                    tot["links"] += 1
                    parts = urlsplit(url)
                    target = (page.parent / unquote(parts.path)).resolve() if parts.path else page
                    if target.is_dir():
                        target = target / "index.html"
                    ok = target.exists()
                    if ok and parts.fragment:
                        t_ids = ids if target == page else {
                            x.get("id") for x in parse(target)[0].iter() if isinstance(x.tag, str)}
                        ok = parts.fragment in t_ids
                    if not ok:
                        tot["broken"] += 1
                        v6.fail(f"{profile}/{rel}: {att}={url!r} does not resolve")

            # V10: basic accessibility facts that do not need a browser
            html_el = tree.getroot()
            if html_el.get("lang") != "en":
                tot["a11y_issues"] += 1
                v10.fail(f"{profile}/{rel}: <html> lacks lang=en")
            if len(tree.findall(f".//{XH}h1")) != 1:
                tot["a11y_issues"] += 1
                v10.fail(f"{profile}/{rel}: expected exactly one h1")
            for img in tree.iter(f"{XH}img"):
                if img.get("alt") is None:
                    tot["a11y_issues"] += 1
                    v10.fail(f"{profile}/{rel}: img without alt")
            for b in tree.iter(f"{XH}button"):
                if not "".join(b.itertext()).strip() and not b.get("aria-label"):
                    tot["a11y_issues"] += 1
                    v10.fail(f"{profile}/{rel}: button without a label")
            for fo in by_class(tree, "fo"):
                if not fo.get("lang"):
                    tot["a11y_issues"] += 1
                    v10.fail(f"{profile}/{rel}: foreign passage without lang")

            # V8: public leak check
            if profile == "public":
                raw = page.read_text(encoding="utf-8")
                for needle in ('data-resp="gowland"', "gowland-tr", 'class="pb"', 'class="enref"', 'class="supplied"'):
                    if needle in raw:
                        tot["leaks"] += 1
                        v8.fail(f"public/{rel}: contains {needle}")

        # V2h: per-unit counts, XML vs HTML
        for unit in units:
            root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
            tree, _ = parse(site / unit / "index.html")
            xml = {"sidenotes": len(root.findall(f".//{TEI}note")),
                   "foreign": len(root.xpath("//*[@ana='foreign']")),
                   "enrefs": len(root.findall(f".//{ED}enref")) if profile == "private" else 0,
                   "pbs": len(root.findall(f".//{TEI}pb")) if profile == "private" else 0}
            htm = {"sidenotes": len(by_class(tree, "sidenote")), "foreign": len(by_class(tree, "fp")),
                   "enrefs": len(by_class(tree, "enref")), "pbs": len(by_class(tree, "pb"))}
            for k in xml:
                v2.counts[f"{profile}:{k}"] = f"{xml[k]}/{htm[k]}"
                if xml[k] != htm[k]:
                    v2.fail(f"{profile} {unit} {k}: XML {xml[k]} vs HTML {htm[k]}")

        # V8 (text level): no Gowland bracket text in public pages
        if profile == "public":
            for unit in units:
                root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
                raw = (site / unit / "index.html").read_text(encoding="utf-8")
                for t in root.iter(f"{ED}trans", f"{ED}verse-trans"):
                    s = " ".join("".join(t.itertext()).split())
                    if s and s in " ".join(raw.split()):
                        tot["leaks"] += 1
                        v8.fail(f"public/{unit}: Gowland text present: {s[:50]!r}")

        # V9: every visible code point is in a served font
        fonts_dir = site / "assets" / "fonts"
        covered = set()
        for f in fonts_dir.glob("*.woff2"):
            covered |= set(TTFont(str(f)).getBestCmap())
        report = json.loads((paths.STATE / "build" / f"{profile}.json").read_text(encoding="utf-8"))
        from ..site.build import visible_codepoints

        used = set()
        for page in pages(profile):
            used |= visible_codepoints(page.read_text(encoding="utf-8"))
        missing = sorted(used - covered)
        tot["uncovered"] += len(missing)
        v9.counts[f"{profile}:glyphs"] = f"{len(used) - len(missing)}/{len(used)}"
        if missing:
            v9.fail(f"{profile}: no glyph for {' '.join(f'U+{c:04X}({chr(c)})' for c in missing)}")
        del report

    v2.counts = v2.counts
    v3.counts = {"markers": tot["markers"], "resolved": tot["resolved"]}
    v4.counts = {"script_chars": tot["script_chars"], "untagged": tot["untagged"]}
    v6.counts = {"links": tot["links"], "broken": tot["broken"]}
    v8.counts = {"leaks": tot["leaks"]}
    v10.counts = {"pages": sum(len(pages(p)) for p in ("private", "public")),
                  "parse_errors": tot["parse_errors"], "a11y_issues": tot["a11y_issues"]}
    return [v2, v3, v4, v6, v8, v9, v10]
