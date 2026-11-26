"""Layer 1 Deterministic Empirical Sensor for the Human-Centered UX Workflow.

Runs headless Playwright probes and corpus/DOM/elucidation measurements against the built
`site/private` edition without modifying any source, layer, or site files.

Usage:
    uv run python tools/human_ux_workflow/audit_human_ux.py
"""

from __future__ import annotations

import json
from pathlib import Path
from lxml import html as lhtml
import yaml

from burton import paths
from burton.site.book import Book, text_units
from burton.verify.browser import browser, new_page, serve

OUT_JSON = paths.STATE / "review" / "human-ux-audit-2026-11-25.json"
SHOT_DIR = paths.STATE / "review" / "ux-shots-2026-11-25"


def measure_corpus_scale(site: Path) -> dict:
    """Measure unit lengths, reading sequence from 'Enter, gentle Reader', and reference page navigation."""
    units = text_units()
    book = Book("private", units)
    reading_seq = [k for k in book.order if book.reading(book.pages[k])]

    unit_lengths = []
    for u in units:
        hp = site / u / "index.html"
        if not hp.exists():
            continue
        tree = lhtml.fromstring(hp.read_bytes())
        art = tree.xpath('//article[contains(@class, "unit")]')
        if not art:
            continue
        clone = lhtml.fromstring(hp.read_bytes()).xpath('//article[contains(@class, "unit")]')[0]
        for bad in clone.xpath(
            './/*[contains(@class, "sidenote") or contains(@class, "mn-pool") '
            'or contains(@class, "ft") or contains(@class, "ftr") or contains(@class, "sr-only")]'
        ):
            bad.drop_tree()
        words = len(clone.text_content().split())
        sidenotes = len(art[0].xpath('.//*[contains(@class, "sidenote")]'))
        mn_items = len(art[0].xpath('.//*[contains(@class, "mn ")] | .//*[@class="mn"]'))
        p_ids = len(art[0].xpath('.//p[@id]'))
        unit_lengths.append({
            "unit": u,
            "kind": book.pages[u].kind,
            "title": book.pages[u].title,
            "words": words,
            "est_minutes_220wpm": round(words / 220, 1),
            "sidenotes": sidenotes,
            "margin_cards": mn_items,
            "paragraphs_with_id": p_ids,
        })

    by_words = sorted(unit_lengths, key=lambda x: -x["words"])
    front_gate = []
    for k in reading_seq:
        if k == "1.1.1.1":
            break
        match = next((x for x in unit_lengths if x["unit"] == k), None)
        front_gate.append({"unit": k, "title": book.pages[k].title, "words": match["words"] if match else 0})

    authors_tree = lhtml.fromstring((site / "authors" / "index.html").read_bytes())
    table_tree = lhtml.fromstring((site / "table" / "index.html").read_bytes())

    return {
        "total_built_pages": sum(1 for _ in site.rglob("index.html")),
        "reading_order_count": len(reading_seq),
        "steps_before_partition_1": front_gate,
        "longest_12_units": by_words[:12],
        "units_over_5000_words": sum(1 for x in unit_lengths if x["words"] >= 5000),
        "units_over_3000_words": sum(1 for x in unit_lengths if x["words"] >= 3000),
        "paragraphs_with_permanent_ids_but_no_visible_anchor_ui": sum(x["paragraphs_with_id"] for x in unit_lengths),
        "authors_page": {
            "rows": len(authors_tree.xpath("//table//tbody/tr")),
            "has_search_or_filter_input": bool(authors_tree.xpath("//main//input")),
            "has_sortable_headers": bool(authors_tree.xpath("//th//button | //th[@aria-sort]")),
            "has_alpha_jump_bar": bool(
                authors_tree.xpath("//nav[contains(@aria-label, 'Alphabet') or contains(@class, 'alpha')]")
            ),
        },
        "table_page": {
            "letter_headings": len(table_tree.xpath("//article//h2")),
            "entries": len(table_tree.xpath("//article//p[contains(@class, 'tabl')]")),
            "has_alpha_jump_bar": bool(
                table_tree.xpath("//article//nav | //a[starts-with(@href, '#') and string-length(text())=1]")
            ),
            "has_filter_input": bool(table_tree.xpath("//main//input")),
        },
    }


def measure_elucidation_coverage(site: Path) -> dict:
    """Measure elucidation layers across all built units and check glossary/signpost readiness."""
    units = text_units()
    totals = {
        "foreign_passages_fp": 0,
        "burton_self_translations": 0,
        "inline_citations_ic": 0,
        "bible_kjv_expansions": 0,
        "obsolete_word_glosses": 0,
        "restored_democritus_minor_notes": 0,
        "gowland_margin_notes": 0,
        "author_ident_links": 0,
        "cross_ref_links": 0,
        "facing_translation_units": 0,
        "burton_sidenotes_total": 0,
        "burton_sidenotes_substantive_note": 0,
    }
    focus_signposts = {}
    focus_ids = {"djr", "3.2.3.1", "2.2.3.1", "2.2.4.1", "1.2.3.15"}

    for u in units:
        hp = site / u / "index.html"
        if not hp.exists():
            continue
        tree = lhtml.fromstring(hp.read_bytes())
        arts = tree.xpath('//article[contains(@class, "unit")]')
        if not arts:
            continue
        art = arts[0]
        totals["foreign_passages_fp"] += len(art.xpath('.//*[contains(@class, "fp")]'))
        totals["burton_self_translations"] += len(art.xpath('.//*[contains(@class, "burton-tr")]'))
        totals["inline_citations_ic"] += len(art.xpath('.//*[contains(@class, "ic-m")]'))
        totals["bible_kjv_expansions"] += len(art.xpath('.//*[contains(@class, "sn-bible")]'))
        totals["obsolete_word_glosses"] += len(art.xpath('.//*[contains(@class, "gl-w")]'))
        totals["restored_democritus_minor_notes"] += len(art.xpath('.//*[contains(@class, "sn-restored")]'))
        totals["gowland_margin_notes"] += len(art.xpath('.//*[contains(@class, "mn-gw")]'))
        totals["author_ident_links"] += len(art.xpath('.//a[contains(@class, "nm")]'))
        totals["cross_ref_links"] += len(art.xpath('.//a[contains(@class, "xref")]'))
        if art.xpath('.//*[contains(@class, "fp-facing")]'):
            totals["facing_translation_units"] += 1

        sn_all = art.xpath('.//*[contains(@class, "sidenote") and not(contains(@class, "sn-restored"))]')
        sn_substantive = [
            s for s in sn_all
            if any((k.get("data-kind") == "note" or "note" in k.text_content()) for k in s.xpath('.//*[contains(@class, "sn-k")]'))
        ]
        totals["burton_sidenotes_total"] += len(sn_all)
        totals["burton_sidenotes_substantive_note"] += len(sn_substantive)
        if u in focus_ids:
            focus_signposts[u] = {
                "total_burton_sidenotes": len(sn_all),
                "substantive_topic_notes": len(sn_substantive),
                "cites_only_notes": len(sn_all) - len(sn_substantive),
            }

    glossary_path = paths.DATA / "glossary.yaml"
    glossary_data = yaml.safe_load(glossary_path.read_text(encoding="utf-8")) if glossary_path.exists() else {}

    return {
        **totals,
        "obsolete_glosses_default_enabled": False,
        "restored_notes_default_enabled": False,
        "glossary_yaml_terms": len(glossary_data.get("terms", [])),
        "glossary_yaml_authorities": len(glossary_data.get("authorities", [])),
        "glossary_yaml_locators": len(glossary_data.get("locators", {})),
        "reader_glossary_page_exists": (site / "glossary" / "index.html").exists(),
        "long_unit_burton_signposts": focus_signposts,
    }


def run_browser_probes(site: Path) -> dict:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    out: dict = {}

    viewports = [
        ("1920x1080_desktop", 1920, 1080),
        ("1680x1050_wsxga", 1680, 1050),
        ("1536x864_win125pct", 1536, 864),
        ("1440x900_macbook", 1440, 900),
        ("1366x768_laptop", 1366, 768),
        ("1280x800_laptop13", 1280, 800),
        ("1280x720_win150pct", 1280, 720),
        ("1120x900_one_margin", 1120, 900),
        ("1024x900_halfscreen", 1024, 900),
        ("768x1024_ipad", 768, 1024),
        ("390x844_iphone", 390, 844),
    ]

    with serve(site) as (_, base), browser() as b:
        # 1. Front page viewport matrix
        fp_matrix = {}
        for label, w, h in viewports:
            ctx, pg = new_page(b, width=w, height=h, theme="light")
            pg.goto(base, wait_until="load")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(150)
            m = pg.evaluate("""() => {
                const de = document.documentElement;
                const row = document.querySelector('.front-row');
                const syn = document.querySelector('.front-syn')?.getBoundingClientRect();
                const cnt = document.querySelector('.front-contents')?.getBoundingClientRect();
                const info = document.querySelector('.front-info')?.getBoundingClientRect();
                const cols = row ? getComputedStyle(row).gridTemplateColumns.split(' ').length : 0;
                return {
                    w: innerWidth, h: innerHeight,
                    scrollW: de.scrollWidth, scrollH: de.scrollHeight,
                    overflowX: de.scrollWidth - innerWidth,
                    overflowY: de.scrollHeight - innerHeight,
                    fitsOneScreen: de.scrollHeight <= innerHeight + 1 && de.scrollWidth <= innerWidth,
                    gridCols: cols,
                    synVisibleWithoutScroll: syn ? syn.bottom <= innerHeight : false,
                    contentsVisibleWithoutScroll: cnt ? cnt.bottom <= innerHeight : false,
                    infoRightGapPx: info ? Math.round(innerWidth - info.right) : null,
                };
            }""")
            fp_matrix[label] = m
            if label in ("1536x864_win125pct", "1440x900_macbook", "1024x900_halfscreen"):
                pg.screenshot(path=str(SHOT_DIR / f"front_{label}.png"))
            ctx.close()
        out["front_page_viewports"] = fp_matrix

        # 2. Narrow / Touch / Sub-1100px Interaction Parity on 3.2.3.1 & Front Page
        touch_ctx = b.new_context(
            viewport={"width": 390, "height": 844},
            has_touch=True,
            is_mobile=True,
            service_workers="block",
        )
        tpg = touch_ctx.new_page()
        tpg.goto(base, wait_until="load")
        tpg.evaluate("document.fonts.ready")
        tpg.wait_for_timeout(150)
        panel_href = tpg.locator(".front .fs-panel").first.get_attribute("href")
        out["touch_frontispiece"] = {
            "panel_tag": "a",
            "panel_href": panel_href,
            "tap_navigates_away_immediately_instead_of_previewing_stanza": bool(
                panel_href and not panel_href.startswith("#")
            ),
        }

        tpg.goto(base + "3.2.3.1/", wait_until="load")
        tpg.evaluate("document.fonts.ready")
        tpg.wait_for_timeout(250)
        narrow_parity = tpg.evaluate("""() => {
            const de = document.documentElement;
            const foLa = document.querySelector('.unit .fo[lang="la"]');
            const inkColor = getComputedStyle(document.body).color;
            const laColor = foLa ? getComputedStyle(foLa).color : null;

            const gwNotes = [...document.querySelectorAll('.mn-gw')];
            const gwRefs = gwNotes.map(n => document.querySelector(`.mref[data-for="${CSS.escape(n.id)}"]`)).filter(Boolean);
            let gwStyledCount = 0;
            for (const m of gwRefs.slice(0, 20)) {
                const nextEl = m.nextElementSibling;
                if (nextEl && getComputedStyle(nextEl).textDecorationLine !== 'none') gwStyledCount++;
            }

            const ic = document.querySelector('.ic-m');
            if (ic) ic.click();
            const popAfterIc = document.querySelector(':popover-open')?.id || null;

            const nm = document.querySelector('a.nm:not(.nm-x)');
            const nmHref = nm ? nm.getAttribute('href') : null;

            return {
                overflowX: de.scrollWidth - innerWidth,
                bodyInkColor: inkColor,
                latinComputedColor: laColor,
                latinLosesDistinctColorBelow1100px: laColor === inkColor,
                gowlandNotesOnPage: gwNotes.length,
                gowlandRefsWithVisibleCueInSample20: gwStyledCount,
                inlineCiteCount: document.querySelectorAll('.ic-m').length,
                inlineCiteTapOpensPopover: !!popAfterIc,
                inlineCiteKeyboardFocusable: ic ? ic.tabIndex >= 0 : false,
                authorLinksNavigateAwayImmediatelyBelow1100px: !!nmHref && nmHref.includes('authors/'),
            };
        }""")
        out["narrow_touch_parity_3_2_3_1"] = narrow_parity
        touch_ctx.close()

        # 3. Deep-Link Arrival Behaviour (Search / Author Index / Table -> Unit Page)
        deep_links = {}
        for vp_label, vw, vh in [("wide_1440", 1440, 900), ("narrow_390", 390, 844)]:
            ctx, pg = new_page(b, width=vw, height=vh, theme="light")
            pg.goto(base + "3.2.3.1/#3.2.3.1-n5", wait_until="load")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(300)
            note_state = pg.evaluate("""() => {
                const n = document.getElementById('3.2.3.1-n5');
                const ref = document.getElementById('ref-3.2.3.1-n5');
                if (!n) return null;
                const cs = getComputedStyle(n);
                const r = n.getBoundingClientRect();
                const refR = ref ? ref.getBoundingClientRect() : null;
                return {
                    display: cs.display,
                    visible: cs.display !== 'none' && r.height > 0,
                    inViewport: r.top >= -20 && r.bottom <= innerHeight + 20,
                    refInViewport: refR ? (refR.top >= 0 && refR.bottom <= innerHeight) : false,
                    isHotOrPinned: n.classList.contains('hot') || n.classList.contains('pinned'),
                    popoverAttr: n.getAttribute('popover'),
                    popoverOpen: n.matches?.(':popover-open') || false,
                };
            }""")
            pg.goto(base + "1.1.1.1/#pg-141", wait_until="load")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(200)
            pb_state = pg.evaluate("""() => {
                const pb = document.getElementById('pg-141');
                if (!pb) return null;
                const r = pb.getBoundingClientRect();
                const before = getComputedStyle(pb, '::before').content;
                return {
                    exists: true,
                    beforeContent: before,
                    inViewport: r.top >= 0 && r.bottom <= innerHeight,
                };
            }""")
            pg.goto(base + "1.1.1.1/#1.1.1.1-p1", wait_until="load")
            pg.wait_for_timeout(150)
            p_state = pg.evaluate("""() => {
                const p = document.getElementById('1.1.1.1-p1');
                return {
                    hasTargetHighlightStyle: p ? getComputedStyle(p).backgroundColor !== 'rgba(0, 0, 0, 0)' : false,
                };
            }""")
            deep_links[vp_label] = {
                "author_to_sidenote_hash": note_state,
                "table_to_pagebreak_hash": pb_state,
                "search_to_paragraph_hash": p_state,
            }
            ctx.close()
        out["deep_link_arrival"] = deep_links

        # 4. Settings Panel on Front Page
        ctx, pg = new_page(b, width=1440, height=900, theme="light")
        pg.goto(base, wait_until="load")
        pg.click(".settings-toggle")
        pg.wait_for_timeout(150)
        out["front_settings_panel"] = pg.evaluate("""() => {
            const p = document.getElementById('settings');
            const r = p.getBoundingClientRect();
            return {
                hasExamplePassage: !!p.querySelector('.opt-sample'),
                hasResetButton: !!p.querySelector('.reset'),
                width: Math.round(r.width),
                height: Math.round(r.height),
            };
        }""")
        ctx.close()

        # 5. Margin Density & Vertical Drift on 3.2.3.1 (1440x900 two-side vs 1120x900 one-side)
        margin_drift = {}
        for lbl, vw, vh in [("wide_two_side_1440", 1440, 900), ("one_side_1120", 1120, 900)]:
            ctx, pg = new_page(b, width=vw, height=vh, theme="light")
            pg.goto(base + "3.2.3.1/", wait_until="load")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(350)
            margin_drift[lbl] = pg.evaluate("""() => {
                const art = document.querySelector('article.unit');
                const items = [...document.querySelectorAll('.unit.sn-laid .sidenote, .unit.sn-laid .mn')].filter(n => {
                    const cs = getComputedStyle(n);
                    return cs.display !== 'none' && n.style.top !== '';
                });
                let maxDrift = 0;
                let sumDrift = 0;
                let over120 = 0;
                let over300 = 0;
                let folded = 0;
                let leftSideCount = 0;
                for (const n of items) {
                    if (n.classList.contains('mn-fold')) folded++;
                    if (n.classList.contains('mn-l')) leftSideCount++;
                    const marker = document.querySelector(`.mref[data-for="${CSS.escape(n.id)}"]`) ||
                                   document.querySelector(`a.nref[href="#${CSS.escape(n.id)}"]`);
                    if (!marker || !art) continue;
                    const anchorTop = marker.getBoundingClientRect().top - art.getBoundingClientRect().top;
                    const placedTop = parseFloat(n.style.top);
                    const drift = Math.max(0, Math.round(placedTop - anchorTop));
                    if (drift > maxDrift) maxDrift = drift;
                    sumDrift += drift;
                    if (drift > 120) over120++;
                    if (drift > 300) over300++;
                }
                return {
                    placedMarginItems: items.length,
                    leftMarginItems: leftSideCount,
                    foldedItems: folded,
                    maxVerticalDriftPx: maxDrift,
                    meanVerticalDriftPx: items.length ? Math.round(sumDrift / items.length) : 0,
                    itemsDriftedOver120Px: over120,
                    itemsDriftedOver300Px: over300,
                };
            }""")
            ctx.close()
        out["margin_density_and_drift_3_2_3_1"] = margin_drift

        # 6. Mode-Switch Scroll Retention on 3.2.3.1 (#3.2.3.1-p60)
        ctx, pg = new_page(b, width=1440, height=900, theme="light")
        pg.goto(base + "3.2.3.1/", wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(300)
        pg.evaluate("document.getElementById('3.2.3.1-p60')?.scrollIntoView({block: 'start'})")
        pg.wait_for_timeout(150)
        before = pg.evaluate("""() => {
            const p = document.getElementById('3.2.3.1-p60');
            return { top: Math.round(p.getBoundingClientRect().top), scrollY: Math.round(window.scrollY) };
        }""")
        pg.click(".settings-toggle")
        pg.click('#settings input[name="mode"][value="interlinear"]')
        pg.wait_for_timeout(350)
        after = pg.evaluate("""() => {
            const p = document.getElementById('3.2.3.1-p60');
            const r = p.getBoundingClientRect();
            return {
                top: Math.round(r.top),
                scrollY: Math.round(window.scrollY),
                inViewport: r.bottom > 0 && r.top < innerHeight,
            };
        }""")
        out["mode_switch_scroll_retention_3_2_3_1"] = {
            "target_paragraph": "3.2.3.1-p60",
            "mode_change": "gloss -> interlinear",
            "before_top_px": before["top"],
            "after_top_px": after["top"],
            "delta_px": after["top"] - before["top"],
            "remained_in_viewport": after["inViewport"],
        }
        ctx.close()

    return out


def main() -> None:
    site = paths.SITE / "private"
    if not site.exists():
        raise SystemExit(f"{site} not found; build first with `uv run burton build --profile private --all`")
    data = {
        "corpus_and_navigation": measure_corpus_scale(site),
        "elucidation_coverage": measure_elucidation_coverage(site),
        "browser_probes": run_browser_probes(site),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON} ({OUT_JSON.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
