"""Site-side checks on the generated HTML (SPEC §9): V2/V3 on HTML, V4 on HTML, V6 links,
V8 profile leak, V9 font coverage, V10 HTML validity and static accessibility.

Reads only site/ and data/text (never the renderer), so a renderer bug cannot hide itself.
The browser half of V10 (axe-core, keyboard walk-through) is in burton.verify.browser.
"""

import html
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

import html5lib
from fontTools.ttLib import TTFont
from lxml import etree

from .. import paths
from ..layers import djs
from .checks import ARABIC, ED, GREEK, HEBREW, TEI, Result

XH = "{http://www.w3.org/1999/xhtml}"
HEADINGS = [f"{XH}h{i}" for i in range(1, 7)]


def _layer(unit: str, name: str) -> dict:
    f = paths.LAYERS / name / f"{unit}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def parse(path: Path):
    """Strict HTML5 parse; returns (tree, parse errors)."""
    parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"), strict=False)
    tree = parser.parse(path.read_bytes())
    return tree, parser.errors


def pages(profile: str) -> list[Path]:
    return sorted((paths.SITE / profile).rglob("*.html"))


def by_class(tree, cls: str) -> list:
    return tree.xpath(f"//*[contains(concat(' ', normalize-space(@class), ' '), ' {cls} ')]")


def drop_keeping_tail(e) -> None:
    """Remove e from its tree; the text after it stays where it was."""
    parent, prev = e.getparent(), e.getprevious()
    if parent is None:
        return
    if e.tail:
        if prev is not None:
            prev.tail = (prev.tail or "") + e.tail
        else:
            parent.text = (parent.text or "") + e.tail
    parent.remove(e)


def lang_of(e) -> str | None:
    while e is not None:
        if e.get("lang"):
            return e.get("lang")
        e = e.getparent()
    return None


def shown_codepoints(raw: str) -> set[int]:
    """What a page can draw: text, visible attribute text, minus format characters (soft hyphens)."""
    attrs = " ".join(m.group(2) for m in re.finditer(r'\s(alt|title|aria-label|placeholder)="([^"]*)"', raw))
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text) + " " + attrs
    return {ord(c) for c in html.unescape(text) if not c.isspace() and unicodedata.category(c) != "Cf"}


def css_codepoints(css: str) -> set[int]:
    out = set()
    for m in re.finditer(r'content:\s*((?:"[^"]*"\s*|attr\([^)]*\)\s*)+)', css):
        for s in re.findall(r'"([^"]*)"', m.group(1)):
            s = re.sub(r"\\([0-9a-fA-F]{1,6}) ?", lambda x: chr(int(x.group(1), 16)), s)
            out |= {ord(c) for c in s if not c.isspace() and unicodedata.category(c) != "Cf"}
    return out


def gowland_units(units: list[str]) -> set[str]:
    """Whole units that are Gowland's (his translation pages), from the base text itself."""
    out = set()
    for u in units:
        div = etree.parse(str(paths.TEXT / f"{u}.xml")).getroot().find(f".//{TEI}div")
        if div is not None and div.get("resp") == "#gowland":
            out.add(u)
    return out


def site_results(units: list[str]) -> list[Result]:
    v2 = Result("V2h", "per-unit counts XML = HTML")
    v3 = Result("V3h", "every note marker resolves")
    v4 = Result("V4h", "HTML foreign scripts carry lang")
    v6 = Result("V6", "links resolve")
    v8 = Result("V8", "public build has no Gowland matter")
    v9 = Result("V9", "font coverage")
    v10 = Result("V10", "HTML validity and static accessibility")
    tot = {k: 0 for k in ("pages", "markers", "resolved", "script_chars", "untagged", "links", "broken",
                          "parse_errors", "a11y_issues", "leaks", "uncovered", "unresolved_xrefs",
                          "title_script_chars", "search_docs", "search_broken")}
    gow = gowland_units(units)

    def a11y(profile, rel, msg):
        tot["a11y_issues"] += 1
        v10.fail(f"{profile}/{rel}: {msg}")

    for profile in ("private", "public"):
        site = paths.SITE / profile
        trees: dict[Path, tuple] = {}

        def ids_of(target: Path, trees=trees) -> set[str]:
            if target not in trees:
                t, _ = parse(target)
                trees[target] = (t, {x.get("id") for x in t.iter() if isinstance(x.tag, str) and x.get("id")})
            return trees[target][1]

        for page in pages(profile):
            tot["pages"] += 1
            tree, errors = parse(page)
            rel = page.relative_to(site).as_posix()
            ids_list = [e.get("id") for e in tree.iter() if isinstance(e.tag, str) and e.get("id")]
            ids = set(ids_list)
            trees[page.resolve()] = (tree, ids)
            tot["parse_errors"] += len(errors)
            for pos, code, _data in errors[:5]:
                v10.fail(f"{profile}/{rel}: HTML parse error {code} at {pos}")

            # V3h: markers -> notes
            for a in by_class(tree, "nref"):
                tot["markers"] += 1
                target = a.get("href", "")[1:]
                note = tree.xpath("//*[@id=$t]", t=target)
                if note and "sidenote" in (note[0].get("class") or ""):
                    tot["resolved"] += 1
                else:
                    v3.fail(f"{profile}/{rel}: marker {a.get('id')} -> {target} unresolved")

            # V4h: script characters must sit under a matching lang
            for e in tree.iter():
                if not isinstance(e.tag, str) or e.tag in (f"{XH}script", f"{XH}style"):
                    continue
                if e.tag == f"{XH}title":  # the document title cannot carry inner lang; counted apart
                    tot["title_script_chars"] += len(GREEK.findall(e.text or ""))
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
                if "xref-unresolved" in (e.get("class") or ""):
                    tot["unresolved_xrefs"] += 1
                if "pageref-unlinked" in (e.get("class") or ""):  # every Table locator must find its page
                    tot["broken"] += 1
                    v6.fail(f"{profile}/{rel}: Table page {''.join(e.itertext())} has no page marker in the build")
                for att in ("href", "src"):
                    url = e.get(att)
                    if url is None or re.match(r"^[a-z]+:", url):
                        continue
                    tot["links"] += 1
                    parts = urlsplit(url)
                    target = (page.parent / unquote(parts.path)).resolve() if parts.path else page.resolve()
                    if target.is_dir():
                        target = target / "index.html"
                    ok = target.exists() and bool(url)
                    if ok and parts.fragment:
                        ok = parts.fragment in (ids if target == page.resolve() else ids_of(target))
                    if not ok:
                        tot["broken"] += 1
                        v6.fail(f"{profile}/{rel}: {att}={url!r} does not resolve")

            # V10 (static): language, outline, landmarks, names
            root = tree.getroot()
            if root.get("lang") != "en":
                a11y(profile, rel, "<html> lacks lang=en")
            heads = [int(h.tag[-1]) for h in tree.iter(*HEADINGS)]
            if heads.count(1) != 1 or (heads and heads[0] != 1):
                a11y(profile, rel, f"expected one h1 first, got outline {heads[:6]}")
            for a, b in zip(heads, heads[1:], strict=False):
                if b > a + 1:
                    a11y(profile, rel, f"heading level skips h{a} -> h{b}")
                    break
            if len(tree.findall(f".//{XH}main")) != 1:
                a11y(profile, rel, "expected exactly one <main>")
            if len(set(ids_list)) != len(ids_list):
                dup = sorted({i for i in ids_list if ids_list.count(i) > 1})[:3]
                a11y(profile, rel, f"duplicate ids {dup}")
            skip = tree.xpath("//*[@class='skip']")
            if not skip or skip[0].get("href", "")[1:] not in ids:
                a11y(profile, rel, "skip link missing or broken")
            for nav in tree.iter(f"{XH}nav"):
                if not (nav.get("aria-label") or nav.get("aria-labelledby")):
                    a11y(profile, rel, "nav without an accessible name")
            for img in tree.iter(f"{XH}img"):
                if not (img.get("alt") or "").strip():
                    a11y(profile, rel, f"img {img.get('src')} without alt text")
            for b in tree.iter(f"{XH}button"):
                if not "".join(b.itertext()).strip() and not b.get("aria-label"):
                    a11y(profile, rel, "button without a label")
            for inp in tree.iter(f"{XH}input"):
                if inp.getparent().tag != f"{XH}label" and not inp.get("aria-label"):
                    a11y(profile, rel, f"input {inp.get('name')} without a label")
            for fo in by_class(tree, "fo"):
                if not fo.get("lang"):
                    a11y(profile, rel, "foreign passage without lang")

            # V8: public leak check (markup level)
            if profile == "public":
                raw = page.read_text(encoding="utf-8")
                for needle in ('data-resp="gowland"', "gowland-tr", 'class="pb"', 'class="enref"', 'class="supplied"',
                               "toc-tag", 'class="locs"', 'class="pageref'):
                    if needle in raw:
                        tot["leaks"] += 1
                        v8.fail(f"public/{rel}: contains {needle}")

        # V2h: per-unit counts, XML vs HTML (Gowland's own pages exist only in the private build)
        for unit in units:
            page = site / unit / "index.html"
            if profile == "public" and unit in gow:
                if page.exists():
                    tot["leaks"] += 1
                    v8.fail(f"public/{unit}: Gowland's translation page is present")
                continue
            root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
            if not page.exists():
                v2.fail(f"{profile} {unit}: no page")
                continue
            tree = trees.get(page.resolve(), parse(page))[0]
            notes = root.findall(f".//{TEI}note")
            if profile == "public":  # a sidenote inside Gowland's bracket is his (rendered privately only)
                notes = [n for n in notes if not any(a.tag.startswith(ED) for a in n.iterancestors())]
            # Gowland's translations offered as a version of their passage: one per bracket linked to a
            # foreign passage (@for), private build only
            linked = {t.get("for") for t in root.iter(f"{ED}trans", f"{ED}verse-trans") if t.get("for")}
            # Dell & Jordan-Smith versions: the alignments the reader may show (both profiles)
            tr_layer, djs_layer = _layer(unit, "translations"), _layer(unit, "djs")
            xml = {"sidenotes": len(notes),
                   "foreign": len(root.xpath("//*[@ana='foreign']")),
                   "enrefs": len(root.findall(f".//{ED}enref")) if profile == "private" else 0,
                   "pbs": len(root.findall(f".//{TEI}pb")) if profile == "private" else 0,
                   "gowland_versions": len(linked) if profile == "private" else 0,
                   "djs_versions": sum(1 for k, r in djs_layer.items() if djs.shown(r, tr_layer.get(k))),
                   # the Table's Penguin page numbers (private build only)
                   "pagerefs": len(root.findall(f".//{ED}pageref")) if profile == "private" else 0}
            htm = {"sidenotes": len(by_class(tree, "sidenote")), "foreign": len(by_class(tree, "fp")),
                   "enrefs": len(by_class(tree, "enref")), "pbs": len(by_class(tree, "pb")),
                   "gowland_versions": len(by_class(tree, "ft-gowland")),
                   "djs_versions": len(by_class(tree, "ft-djs1927")),
                   "pagerefs": len(by_class(tree, "pageref"))}
            for k in xml:
                v2.counts[f"{profile}:{k}"] = v2.counts.get(f"{profile}:{k}", 0) + htm[k]
                if xml[k] != htm[k]:
                    v2.fail(f"{profile} {unit} {k}: XML {xml[k]} vs HTML {htm[k]}")

        # V8 (text level): no Gowland text in public pages (soft hyphens and tags ignored)
        if profile == "public":
            for unit in units:
                page = site / unit / "index.html"
                if unit in gow or not page.exists():
                    continue
                root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
                # Dell & Jordan-Smith's versions are left out of the bracket search: their text comes only
                # from the 1927 OCR (data/source/djs/), and their own bracketed glosses can coincide with
                # Gowland's ("[saviours] servatores", 2.1.1.1)
                tree = parse(page)[0]
                for v in by_class(tree, "ft-djs1927"):
                    drop_keeping_tail(v)
                shown = " ".join(html.escape("".join(tree.getroot().itertext()), quote=False)
                                 .replace(chr(0xAD), "").split())
                # the page's own text, without the translation boxes: a machine translation may match a
                # literal bracket word for word ("I came to Athens, and no one knew me"); a Gowland version
                # rendered in a box is caught by its data-resp="gowland" markup above
                for ft in by_class(tree, "ft"):
                    drop_keeping_tail(ft)
                own = " ".join(html.escape("".join(tree.getroot().itertext()), quote=False)
                               .replace(chr(0xAD), "").split())
                for t in root.iter(f"{ED}trans", f"{ED}verse-trans", f"{ED}block"):
                    s = " ".join(html.escape("".join(t.itertext()), quote=False).split())
                    # also without his brackets and braces (the form the private reader shows), line by
                    # line for verse; only long segments, since short bare words also occur in Burton
                    segs = [ln for ln in t.iter(f"{TEI}l")] or [t]
                    bare = [" ".join(re.sub(r"[\[\]{}]", "", html.escape("".join(x.itertext()), quote=False)).split())
                            for x in segs]
                    if (len(s) > 3 and s in shown) or any(len(b) >= 30 and b in own for b in bare):
                        tot["leaks"] += 1
                        v8.fail(f"public/{unit}: Gowland text present: {s[:50]!r}")

        # The search index (M8): V6, every result links to an id on its page; V8, the public index has
        # no Gowland label and none of his bracketed text, by the same rule as the pages
        idx_file = site / "assets" / "search-index.json"
        idx = json.loads(idx_file.read_text(encoding="utf-8")) if idx_file.exists() else None
        if idx is None:
            v6.fail(f"{profile}: assets/search-index.json missing")
        else:
            by_unit: dict[str, list] = {}
            for d in idx["docs"]:
                unit = idx["units"][d[0]][0]
                by_unit.setdefault(unit, []).append(d)
                tot["search_docs"] += 1
                target = (site / unit / "index.html").resolve()
                if not target.exists() or d[2] not in ids_of(target):
                    tot["search_broken"] += 1
                    v6.fail(f"{profile}: search result {unit}#{d[2]} does not resolve")
            if profile == "public":
                for lab in idx["labels"]:
                    if "gowland" in lab.lower():
                        tot["leaks"] += 1
                        v8.fail(f"public search index: translation label {lab!r}")
                for unit, docs in by_unit.items():
                    root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
                    trs = [d for d in docs if d[1] == 2]
                    own = " ".join([d[3] for d in docs if d[1] != 2] + [idx["origs"][d[4]][1] for d in trs])
                    shown = " ".join([own] + [d[3] for d in trs if not idx["labels"][d[5]].startswith("Dell")])
                    for t in root.iter(f"{ED}trans", f"{ED}verse-trans", f"{ED}block"):
                        seg = " ".join("".join(t.itertext()).split())
                        segs = [ln for ln in t.iter(f"{TEI}l")] or [t]
                        bare = [" ".join(re.sub(r"[\[\]{}]", "", "".join(x.itertext())).split()) for x in segs]
                        if (len(seg) > 3 and seg in shown) or any(len(b) >= 30 and b in own for b in bare):
                            tot["leaks"] += 1
                            v8.fail(f"public search index, {unit}: Gowland text present: {seg[:50]!r}")

        # V9: every visible code point (pages, CSS generated content, search results) is in a served font
        covered, fallback = set(), set()
        for f in (site / "assets" / "fonts").glob("*.woff2"):
            cm = set(TTFont(str(f)).getBestCmap())
            covered |= cm
            if "Cardo" in f.name:
                fallback |= cm
        used = set()
        for page in pages(profile):
            used |= shown_codepoints(page.read_text(encoding="utf-8"))
        for css in (site / "assets").glob("*.css"):
            used |= css_codepoints(css.read_text(encoding="utf-8"))
        if idx is not None:
            for text in [*(d[3] for d in idx["docs"]), *(o[1] for o in idx["origs"]), *idx["labels"],
                         *(u[1] for u in idx["units"])]:
                used |= {ord(c) for c in text if not c.isspace() and unicodedata.category(c) != "Cf"}
        missing = sorted(used - covered)
        tot["uncovered"] += len(missing)
        v9.counts[f"{profile}:glyphs"] = f"{len(used) - len(missing)}/{len(used)}"
        v9.counts[f"{profile}:fallback"] = len(used & fallback)
        if missing:
            v9.fail(f"{profile}: no glyph for {' '.join(f'U+{c:04X}' for c in missing)}")
        if profile == "private":
            v9.counts["fallback_codepoints"] = " ".join(f"U+{c:04X}" for c in sorted(used & fallback))

    v2.counts["units"] = len(units)
    v3.counts = {"markers": tot["markers"], "resolved": tot["resolved"]}
    v4.counts = {"script_chars": tot["script_chars"], "untagged": tot["untagged"],
                 "in_document_titles": tot["title_script_chars"]}
    v6.counts = {"pages": tot["pages"], "links": tot["links"], "broken": tot["broken"],
                 "unresolved_xrefs_unlinked": tot["unresolved_xrefs"], "search_results": tot["search_docs"],
                 "search_broken": tot["search_broken"]}
    v8.counts = {"leaks": tot["leaks"], "gowland_pages_withheld": len(gow)}
    v10.counts = {"pages": tot["pages"], "parse_errors": tot["parse_errors"], "a11y_issues": tot["a11y_issues"]}
    return [v2, v3, v4, v6, v8, v9, v10]

