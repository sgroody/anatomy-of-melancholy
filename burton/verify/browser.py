"""Browser checks on the built site (SPEC §9 V10, §7): axe-core on a 20-page sample in both themes,
a keyboard walk-through, the sidenote layout, Latin/Greek hyphenation, and offline use.

Drives the installed Chrome (or Edge) through Playwright against a throwaway local server, so no
browser download is needed. axe-core comes pinned from tests/browser (npm ci --prefix tests/browser).
Reads only site/; imports nothing from burton.site.
"""

import contextlib
import functools
import http.server
import threading
from pathlib import Path

from .. import paths
from .checks import Result

AXE = paths.ROOT / "tests" / "browser" / "node_modules" / "axe-core" / "axe.min.js"

# 20 pages: every page type, the densest and longest units, Greek, verse, lists, a Gowland page.
SAMPLE = ["", "about/", "settings/", "p1/", "p2/", "p3/", "argument/", "dedication/", "abstract/", "djr/",
          "lectori/", "heraclite/", "1.1.1.1/", "1.1.1.2/", "1.1.3.2/", "3.2.4.1/", "1.2.4.6/", "2.3.3.1/",
          "3.2.5.5/", "2.4.1.3/"]
LIMIT_REM = 14  # must match edition.js: the furthest a laid-out note may drift below its marker


def built(site: Path, rels: list[str]) -> list[str]:
    """The pages of `rels` that this build has (a `--unit` build has only some)."""
    return [r for r in rels if (site / r / "index.html").exists()]


def unit_page(site: Path) -> str:
    """A unit page with notes and foreign passages for the walk-through: 1.1.1.2 when built."""
    if (site / "1.1.1.2" / "index.html").exists():
        return "1.1.1.2/"
    for d in sorted(site.iterdir()):
        if d.name[:1].isdigit() and (d / "index.html").exists():
            return f"{d.name}/"
    raise SystemExit(f"{site}: no unit page built")


class _Quiet(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".webmanifest": "application/manifest+json", ".woff2": "font/woff2",
                      ".js": "text/javascript", ".svg": "image/svg+xml"}

    def log_message(self, *args):
        pass


@contextlib.contextmanager
def serve(site: Path):
    handler = functools.partial(_Quiet, directory=str(site))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield httpd, f"http://127.0.0.1:{httpd.server_address[1]}/"
    finally:
        httpd.shutdown()
        httpd.server_close()


@contextlib.contextmanager
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        last = None
        for channel in ("chrome", "msedge", None):
            try:
                b = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
                break
            except Exception as e:  # noqa: BLE001 - try the next installed browser
                last = e
        else:
            raise SystemExit(f"no Chromium-family browser for Playwright: {last}")
        try:
            yield b
        finally:
            b.close()


def new_page(b, *, width=1280, height=900, theme=None, settings=None):
    ctx = b.new_context(viewport={"width": width, "height": height}, color_scheme=theme or "light",
                        service_workers="block")
    if settings:
        import json

        ctx.add_init_script(f"try{{localStorage.setItem('burton-settings', {json.dumps(json.dumps(settings))})}}catch(e){{}}")
    return ctx, ctx.new_page()


# ---------------------------------------------------------------- V10a: axe-core
def axe_check(profile: str = "private") -> Result:
    r = Result("V10a", "axe-core on 20 pages, light and dark (serious/critical = 0)")
    if not AXE.exists():
        r.fail(f"{AXE} missing: run `npm ci --prefix tests/browser`")
        return r
    axe_src = AXE.read_text(encoding="utf-8")
    site = paths.SITE / profile
    runs = serious = minor = 0
    rules: dict[str, int] = {}
    with serve(site) as (_, base), browser() as b:
        for theme in ("light", "dark"):
            settings = {"theme": theme}
            ctx, pg = new_page(b, theme=theme, settings=settings)
            for rel in built(site, SAMPLE):
                pg.goto(base + rel, wait_until="load")
                pg.add_script_tag(content=axe_src)
                res = pg.evaluate("""async () => {
                    const out = await axe.run(document, {resultTypes: ['violations'],
                        runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']}});
                    return out.violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length,
                        target: v.nodes[0] && v.nodes[0].target.join(' '), summary: v.nodes[0] && v.nodes[0].failureSummary}));
                }""")
                runs += 1
                for v in res:
                    rules[v["id"]] = rules.get(v["id"], 0) + v["n"]
                    if v["impact"] in ("serious", "critical"):
                        serious += v["n"]
                        r.fail(f"{theme} {rel or 'home'}: {v['id']} ({v['impact']}) x{v['n']} at {v['target']}: "
                               f"{(v['summary'] or '').splitlines()[-1][:160]}")
                    else:
                        minor += v["n"]
            ctx.close()
    r.counts = {"runs": runs, "pages": f"{len(built(site, SAMPLE))}/{len(SAMPLE)}", "serious_or_critical": serious, "moderate_or_minor": minor,
                "rules": ", ".join(f"{k}:{v}" for k, v in sorted(rules.items())) or "none"}
    return r


# ---------------------------------------------------------------- V10k: keyboard walk-through
def keyboard_check(profile: str = "private") -> Result:
    r = Result("V10k", "keyboard walk-through")
    site = paths.SITE / profile
    steps = 0

    def step(ok: bool, msg: str):
        nonlocal steps
        steps += 1
        if not ok:
            r.fail(msg)

    def focused(pg) -> str:
        return pg.evaluate("""() => { const a = document.activeElement; if (!a) return '';
            return a.tagName.toLowerCase() + (a.id ? '#' + a.id : '') + (a.className ? '.' + String(a.className).split(' ').join('.') : ''); }""")

    with serve(site) as (_, base), browser() as b:
        # 1. skip link, header controls, settings panel and Esc, contents panel and Esc (wide)
        unit = unit_page(site)
        ctx, pg = new_page(b)
        pg.goto(base + unit)
        pg.keyboard.press("Tab")
        step(focused(pg).startswith("a.skip"), f"first Tab should reach the skip link, got {focused(pg)}")
        pg.keyboard.press("Enter")
        step(focused(pg).startswith("main#main"), f"skip link should move focus to main, got {focused(pg)}")
        pg.focus(".settings-toggle")
        pg.keyboard.press("Enter")
        step(pg.is_visible("#settings"), "Enter on Reading options should open the panel")
        step("input" in focused(pg), f"opening the panel should focus an option, got {focused(pg)}")
        pg.keyboard.press("ArrowDown")  # radio group: moves the choice
        step(pg.evaluate("document.body.classList.contains('mode-interlinear')"),
             "ArrowDown in the language radios should switch to interlinear")
        pg.keyboard.press("ArrowUp")
        pg.keyboard.press("Escape")
        step(not pg.is_visible("#settings") and focused(pg).startswith("button"),
             f"Esc should close the panel and return focus to its button, got {focused(pg)}")
        pg.focus(".toc-panel > summary")
        pg.keyboard.press("Enter")
        step(pg.evaluate("document.querySelector('.toc-panel').open"), "Enter on Contents should open it")
        step(pg.is_visible('.toc-panel [aria-current="page"]'), "the current unit should be visible in Contents")
        pg.keyboard.press("Escape")
        step(not pg.evaluate("document.querySelector('.toc-panel').open") and focused(pg).startswith("summary"),
             f"Esc should close Contents and return focus, got {focused(pg)}")
        # Tab reaches a note marker and a foreign passage; focusing the passage shows its gloss
        seen_marker = seen_fo = False
        for _ in range(60):
            pg.keyboard.press("Tab")
            f = focused(pg)
            if f.startswith("a#ref-"):
                seen_marker = True
            if ".fo" in f and pg.evaluate("getComputedStyle(document.activeElement.nextElementSibling).display") != "none":
                seen_fo = True
            if seen_marker and seen_fo:
                break
        step(seen_marker, "Tab should reach a note marker")
        step(seen_fo, "focusing a foreign passage should show its translation")
        ctx.close()

        # 2. narrow: marker opens a popover, Esc closes it and returns focus
        ctx, pg = new_page(b, width=390, height=800)
        pg.goto(base + unit)
        first = pg.locator("a.nref").first
        first.focus()
        pg.keyboard.press("Enter")
        note_id = first.get_attribute("href")[1:]
        is_open = pg.evaluate(f"document.getElementById({note_id!r}).matches(':popover-open, .open')")
        step(is_open and first.get_attribute("aria-expanded") == "true", "Enter on a marker should open its note")
        inside = pg.evaluate(f"""() => {{ const n = document.getElementById({note_id!r}).getBoundingClientRect();
            return n.left >= 0 && n.right <= innerWidth && n.top >= 0 && n.bottom <= innerHeight; }}""")
        step(inside, "the note popover should sit inside the viewport")
        pg.keyboard.press("Escape")
        closed = not pg.evaluate(f"document.getElementById({note_id!r}).matches(':popover-open, .open')")
        step(closed and focused(pg).startswith("a#ref-"), f"Esc should close the note and refocus its marker, got {focused(pg)}")
        ctx.close()

        # 3. settings page: choices persist across pages and reloads; reset restores defaults
        ctx, pg = new_page(b)
        pg.goto(base + "settings/")
        pg.focus('input[name="theme"][value="dark"]')
        pg.keyboard.press("Space")
        pg.focus('input[name="size"][value="l"]')
        pg.keyboard.press("Space")
        pg.goto(base + unit)
        step(pg.evaluate("document.documentElement.dataset.theme") == "dark", "dark theme should persist")
        step(pg.evaluate("document.documentElement.dataset.size") == "l", "type size should persist")
        pg.goto(base + "settings/")
        pg.focus(".reset")
        pg.keyboard.press("Enter")
        pg.reload()
        step(pg.evaluate("document.documentElement.dataset.theme") is None, "reset should restore the system theme")
        ctx.close()
    r.counts = {"steps": steps, "failed": len(r.problems)}
    return r


# ---------------------------------------------------------------- sidenote layout
LAYOUT_JS = """() => {
  const art = document.querySelector('article.unit');
  const rem = parseFloat(getComputedStyle(art).fontSize);
  const notes = [...document.querySelectorAll('a.nref')].map(m => [m, document.getElementById(m.getAttribute('href').slice(1))]);
  const laid = notes.filter(([m, n]) => !n.classList.contains('sn-stacked'));
  const rects = laid.map(([m, n]) => n.getBoundingClientRect());
  let overlaps = 0, maxDrift = 0, outside = 0;
  const textRight = art.getBoundingClientRect().right;
  for (let i = 0; i < laid.length; i++) {
    const [m] = laid[i]; const r = rects[i];
    if (r.left < textRight) outside++;
    maxDrift = Math.max(maxDrift, (r.top - m.getBoundingClientRect().top) / rem);
    for (let j = i + 1; j < laid.length; j++) {
      const q = rects[j];
      if (r.top < q.bottom - 0.5 && q.top < r.bottom - 0.5) overlaps++;
    }
  }
  const more = [...document.querySelectorAll('.sn-more')];
  return {notes: notes.length, laid: laid.length, stacked: notes.length - laid.length, stacks: more.length,
          overlaps, maxDrift: Math.round(maxDrift * 10) / 10, inText: outside};
}"""

MARKER_LINE_JS = """() => {
  // the first visible character after each marker (skipping its note; hidden text has no rect,
  // so in English mode the translation that replaces a passage counts) must be on the marker's line
  const bad = [];
  for (const a of document.querySelectorAll('a.nref')) {
    const w = document.createTreeWalker(document.querySelector('main'), NodeFilter.SHOW_TEXT);
    w.currentNode = a.lastChild || a;
    let t, rr = null;
    while ((t = w.nextNode())) {
      if (t.parentElement.closest('.sidenote, .sr-only')) continue;
      const i = t.data.search(/\\S/); if (i < 0) continue;
      const g = document.createRange(); g.setStart(t, i); g.setEnd(t, i + 1);
      rr = g.getBoundingClientRect(); if (rr.height) break;
    }
    if (!rr) continue;
    const ar = a.getBoundingClientRect();
    if (rr.top > ar.bottom + 2) bad.push(a.id);
  }
  return bad;
}"""


def layout_check(profile: str = "private") -> Result:
    r = Result("L1", "sidenote layout: no overlaps, drift within the limit, markers on their word's line")
    site = paths.SITE / profile
    units = [u.rstrip("/") for u in built(site, ["3.2.4.1/", "1.1.3.2/", "1.2.4.6/", "1.1.1.2/", "djr/"])]
    tot = {"pages": 0, "notes": 0, "stacked": 0, "overlaps": 0, "max_drift_rem": 0.0, "marker_breaks": 0}
    with serve(site) as (_, base), browser() as b:
        for width, mode in ((1280, "gloss"), (1600, "interlinear"), (1100, "english")):
            ctx, pg = new_page(b, width=width, settings={"mode": mode})
            for u in units:
                pg.goto(base + f"{u}/", wait_until="load")
                pg.evaluate("document.fonts.ready")
                pg.wait_for_timeout(150)
                m = pg.evaluate(LAYOUT_JS)
                tot["pages"] += 1
                tot["notes"] += m["notes"]
                tot["stacked"] += m["stacked"]
                tot["overlaps"] += m["overlaps"]
                tot["max_drift_rem"] = max(tot["max_drift_rem"], m["maxDrift"])
                if m["overlaps"]:
                    r.fail(f"{u} at {width}px ({mode}): {m['overlaps']} overlapping notes")
                if m["maxDrift"] > LIMIT_REM + 0.5:
                    r.fail(f"{u} at {width}px ({mode}): a note drifts {m['maxDrift']} rem below its marker")
                if m["inText"]:
                    r.fail(f"{u} at {width}px: {m['inText']} notes overlap the text column")
                if u == "3.2.4.1" and width == 1280:
                    r.counts["densest_3.2.4.1"] = f"{m['notes']} notes, {m['stacked']} stacked in {m['stacks']} stacks"
            ctx.close()
        # interlinear glosses are atomic inline boxes, which allow a break before them: without the
        # word joiner after each marker, 62 markers in these pages part from their word
        for mode in ("gloss", "interlinear", "english"):
            for width in (360, 480, 760, 1280):
                ctx, pg = new_page(b, width=width, settings={"mode": mode})
                for u in units:
                    pg.goto(base + f"{u}/", wait_until="load")
                    pg.evaluate("document.fonts.ready")
                    bad = pg.evaluate(MARKER_LINE_JS)
                    tot["marker_checks"] = tot.get("marker_checks", 0) + pg.locator("a.nref").count()
                    tot["marker_breaks"] += len(bad)
                    if bad:
                        r.fail(f"{u} at {width}px ({mode}): marker on a different line from its word: {bad[:4]}")
                ctx.close()
    r.counts.update(tot)
    return r


# ---------------------------------------------------------------- hyphenation
HYPH_JS = """(words) => {
  const out = {};
  for (const [lang, w, shy] of words) {
    const d = document.createElement('div');
    d.lang = lang; d.style.cssText = 'width:3em;hyphens:auto;-webkit-hyphens:auto;font-size:20px;position:absolute;left:0;top:0';
    d.textContent = shy ? w : w.replaceAll('\\u00ad', '');
    document.body.appendChild(d);
    const g = document.createRange(); g.selectNodeContents(d);
    out[lang + (shy ? '+shy' : '')] = g.getClientRects().length;
    d.remove();
  }
  return out;
}"""


def hyphenation_check(profile: str = "private") -> Result:
    """Does the browser hyphenate la/grc by itself? If not, the build's soft hyphens must be in
    those spans (and only there) and must actually break lines."""
    r = Result("HY", "hyphenation: native la/grc support, else build-time soft hyphens")
    site = paths.SITE / profile
    from lxml import html as lhtml

    shy = chr(0xAD)
    # soft hyphens only inside la/grc; keep the longest hyphenated word of each language as a sample
    stray = placed = 0
    sample = {"la": "", "grc": ""}
    for page in site.rglob("*.html"):
        tree = lhtml.fromstring(page.read_bytes())
        for e in tree.iter():
            if not isinstance(e.tag, str):
                continue
            for text, owner in ((e.text, e), (e.tail, e.getparent())):
                if not text or owner is None or shy not in text:
                    continue
                lang = owner.get("lang") or next((x.get("lang") for x in owner.iterancestors() if x.get("lang")), None)
                if lang in sample:
                    placed += text.count(shy)
                    sample[lang] = max([sample[lang], *(w for w in text.split() if shy in w)], key=len)
                else:
                    stray += text.count(shy)
    sample_la, sample_grc = sample["la"], sample["grc"]
    if not sample_la or not sample_grc:
        r.fail("no soft-hyphenated la/grc word found")
    with browser() as b:
        ctx, pg = new_page(b)
        pg.set_content("<!doctype html><html lang='en'><body></body></html>")
        native = pg.evaluate(HYPH_JS, [["en", "incomprehensibilities", False], ["la", sample_la, False],
                                       ["grc", sample_grc, False], ["la", sample_la, True], ["grc", sample_grc, True]])
        ctx.close()
    r.counts = {"browser_en": "yes" if native["en"] > 1 else "no", "browser_la": "yes" if native["la"] > 1 else "no",
                "browser_grc": "yes" if native["grc"] > 1 else "no",
                "soft_hyphens_break_la": native["la+shy"] > 1, "soft_hyphens_break_grc": native["grc+shy"] > 1,
                "soft_hyphens": placed, "stray_soft_hyphens": stray}
    if native["la"] <= 1 and native["la+shy"] <= 1:
        r.fail(f"Latin does not hyphenate natively and the soft hyphens in {sample_la!r} do not break")
    if native["grc"] <= 1 and native["grc+shy"] <= 1:
        r.fail(f"Greek does not hyphenate natively and the soft hyphens in {sample_grc!r} do not break")
    if stray:
        r.fail(f"{stray} soft hyphens outside la/grc spans")
    return r


# ---------------------------------------------------------------- offline
def offline_check(profile: str = "private") -> Result:
    """First visit installs the service worker and precaches the site; then, with the server shut
    down, other pages, fonts and images still load."""
    r = Result("OFF", "works offline after first load (service worker)")
    site = paths.SITE / profile
    with browser() as b:
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page()
        with serve(site) as (_, base):
            pg.goto(base + unit_page(site))
            pg.evaluate("navigator.serviceWorker.ready.then(() => true)")
            n = pg.evaluate("""async () => {
                for (let i = 0; i < 600; i++) {
                    const keys = await caches.keys();
                    if (keys.length) {
                        const c = await caches.open(keys[0]); const n = (await c.keys()).length;
                        const reg = await navigator.serviceWorker.getRegistration();
                        if (reg && reg.active && reg.active.state === 'activated') return n;
                    }
                    await new Promise(res => setTimeout(res, 100));
                }
                return -1; }""")
            files = sum(1 for p in site.rglob("*") if p.is_file())
            r.counts["precached"] = f"{n}/{files}"  # every file but sw.js, plus "./"
            if n != files:
                r.fail(f"service worker precached {n} entries, expected {files}")
        # server is now down
        loaded = 0
        targets = built(site, ["", "3.2.4.1/", "p2/", "about/", "djr/", unit_page(site)])
        for rel in targets:
            try:
                resp = pg.goto(base + rel, wait_until="load", timeout=15000)
                ok = resp is not None and resp.ok and pg.locator("main").count() == 1
                fonts_ok = pg.evaluate("document.fonts.ready.then(() => [...document.fonts].some(f => f.status === 'loaded'))")
                img_ok = pg.evaluate("""() => Promise.all([...document.images].map(i => {
                    i.loading = 'eager'; return i.decode().then(() => i.naturalWidth > 0, () => false);
                })).then(all => all.every(Boolean))""")
                if ok and fonts_ok and img_ok:
                    loaded += 1
                else:
                    r.fail(f"offline {rel or 'home'}: page {ok}, fonts {fonts_ok}, images {img_ok}")
            except Exception as e:  # noqa: BLE001
                r.fail(f"offline {rel or 'home'}: {str(e).splitlines()[0][:120]}")
        r.counts["offline_pages_loaded"] = f"{loaded}/{len(targets)}"
        ctx.close()
    return r


def browser_results(profile: str = "private") -> list[Result]:
    return [axe_check(profile), keyboard_check(profile), layout_check(profile), hyphenation_check(profile),
            offline_check(profile)]
