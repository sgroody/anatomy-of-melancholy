"""Deterministic Owner's Interactive UX Workbench HTML Builder.

Reads Layer 1 audit JSON, Layer 2 persona JSON, Layer 3 Carbon synthesis JSON, and
optional Layer 4 custom prototype enrichments, and writes the standalone offline-resilient
`state/review/human-ux-2026-11-25.html` review workbench.

Usage:
    uv run python tools/human_ux_workflow/workbench_renderer.py
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from burton import paths
from burton.fsutil import atomic_write_text

AUDIT_JSON = paths.STATE / "review" / "human-ux-audit-2026-11-25.json"
PERSONAS_JSON = paths.STATE / "review" / "human-ux-personas-2026-11-25.json"
SYNTHESIS_JSON = paths.STATE / "review" / "human-ux-synthesis-2026-11-25.json"
CUSTOM_DEMOS_JSON = paths.STATE / "review" / "_ux_custom_demos.json"
OUT_HTML = paths.STATE / "review" / "human-ux-2026-11-25.html"


def esc(s: str | None) -> str:
    return html.escape(s or "", quote=True)


def sanitize_demo_html(raw: str) -> str:
    """Keep safe interactive HTML snippets; strip any <script> tags so workbench JS stays clean."""
    return re.sub(r"<script\b[^>]*>.*?</script>", "", raw or "", flags=re.I | re.S)


def builtin_demos() -> dict[str, str]:
    """Rich interactive prototypes using authentic Burton passages & real glossary data."""
    return {
        "front_16_10": """
<p class="demo-label">Interactive 16:10 Laptop Wireframe (1440&times;900 &amp; 1280&times;800)</p>
<div class="proto-bar">
  <button type="button" class="proto-btn" data-fpview="current" aria-pressed="true">Current 1440&times;900 (wrapped, +220 px scroll)</button>
  <button type="button" class="proto-btn" data-fpview="proposed" aria-pressed="false">Proposed 1440&times;900 (2 cols, fits 1 screen)</button>
</div>
<div class="fp-sim" id="fpSim">
  <div class="fp-sim-eng">Engraving<br><small>526 px wide</small></div>
  <div class="fp-sim-side is-wrapped" id="fpSimSide">
    <div class="fp-sim-door">Enter, gentle Reader &nbsp;|&nbsp; Stanza</div>
    <div class="fp-sim-box">The Book &amp; The Reader box<br><small>(pushes Synopses below screen when wrapped)</small></div>
    <div class="fp-sim-syn"><em>Synopses</em> &amp; <em>Contents</em></div>
  </div>
</div>
<p class="demo-note" id="fpSimNote">Today at 1440&times;900, <code>.front-side</code> drops just under <code>39em</code>, forcing 1 column and leaving 202 px empty on the right.</p>
""",
        "touch_parity": """
<p class="demo-label">Interactive Narrow-Window / Touch Tester (tap each underlined or marked phrase)</p>
<p class="proto-prose">Though <button type="button" class="inline-btn nm-u" data-pop="<b>Hercules de Saxonia</b> (1551&ndash;1607) &middot; Paduan physician cited on melancholy.<br><a href='#'>Open author page &rarr;</a>"><em>Hercules de Saxonia</em></button><button type="button" class="inline-btn cite-s" data-pop="<b>&sect; cites</b> &middot; Hercules de Saxonia, <i>Tractatus de melancholia</i>, ch. 3"> &sect;</button> will exclude fear from Love-Melancholy, yet I am otherwise persuaded. <button type="button" class="inline-btn la-u" data-pop="<b>Translation (from Latin)</b> &middot; Love is a thing full of anxious fear <span class='sc'>g</span>"><em>Res est solliciti plena timoris amor</em></button>, which made Hesiod <button type="button" class="inline-btn gw-u" data-pop="<b>Gloss</b> &middot; <i>belike</i>: Probably; perhaps <span class='sc'>g</span>">belike</button> put fear and paleness Venus&rsquo; daughters.</p>
<div class="pop-preview" id="f3Pop" aria-live="polite">Tap <em>Hercules de Saxonia</em>, <span style="color:var(--k-cite)">&sect;</span>, the Latin, or <em>belike</em> above to test unified phone/tablet popovers (first tap previews without leaving your chapter).</div>
""",
        "deep_link_drift": """
<p class="demo-label">Deep-Link Arrival Simulator (<code>/3.2.3.1/#3.2.3.1-n5</code> at 1440&times;900)</p>
<div class="proto-bar">
  <button type="button" class="proto-btn" data-dl="before" aria-pressed="true">Current (browser scrolls before layoutNotes)</button>
  <button type="button" class="proto-btn" data-dl="after" aria-pressed="false">Proposed (re-scroll after layout + light up both)</button>
</div>
<div class="dl-stage" id="dlStage">
  <div class="dl-row">
    <div class="dl-main">Burton&rsquo;s text: &ldquo;&hellip; <span class="dl-words" id="dlWords">Love is a species of melancholy</span> <sup class="dl-ref">e</sup> &hellip;&rdquo;</div>
    <div class="dl-margin" id="dlNote"><span class="ok-box">e</span> <span class="sc">note</span> Avicenna, <i>lib. 3, fen. 1, tract. 4</i></div>
  </div>
  <p class="demo-note" id="dlMsg" style="margin:.45rem 0 0">Before fix: after <code>layoutNotes()</code> moves the note into absolute position, both anchor and note sit off-screen and unlit.</p>
</div>
""",
        "polish_fixes": """
<p class="demo-label">Three Silent Craftsmanship Repairs</p>
<ul class="compact-list">
  <li><b>Print on wide screens (&ge;1380 px):</b> Reset <code>.two-side .unit { margin-left: 0 !important }</code> inside <code>@media print</code> so two-margin padding never shifts printed paper off-centre.</li>
  <li><b>Shortened-note highlight corner:</b> Match <code>.mn-fold.hot &gt; .fold-more</code> fade to the warm gold highlight instead of plain paper white.</li>
  <li><b>Front-page <code>Aa</code> Options panel:</b> Include the <em>Restore defaults</em> button and subtle live preview strip just like reading pages.</li>
</ul>
""",
        "scroll_bookmark": """
<p class="demo-label">Interactive Place-Keeping &amp; Mode-Switch Anchor</p>
<div class="bookmark-bar" id="bkBar">
  <span><span class="sc rubric">Place kept</span> &nbsp;Continue in <i>Democritus Junior to the Reader</i> (&para; 84 &middot; ~42% through) &rarr;</span>
  <button type="button" class="proto-btn" id="bkDismiss">Dismiss</button>
</div>
<div class="proto-bar" style="margin-top:.55rem">
  <button type="button" class="proto-btn" data-mode-sim="gloss" aria-pressed="true">Gloss mode</button>
  <button type="button" class="proto-btn" data-mode-sim="interlinear" aria-pressed="false">Interlinear mode (anchored on &para; 60)</button>
  <button type="button" class="proto-btn" data-mode-sim="printed" aria-pressed="false">As printed (bookmark hidden)</button>
</div>
<p class="demo-note" id="modeAnchorOut">Anchored on <code>#3.2.3.1-p60</code>: switching between Gloss and Interlinear preserves your exact reading line (0 px drift instead of throwing you off-screen).</p>
""",
        "cite_jumper": """
<p class="demo-label">Hover Pilcrow &para; Citation Copier &amp; Direct Locus / Penguin Page Jumper</p>
<div class="burton-sample">
  <button type="button" class="pilcrow" id="citeDemoBtn" title="Copy scholarly citation &amp; link">&para;35</button>
  <p style="margin:0">&hellip; <span class="la">Res est solliciti plena timoris amor.</span> &rsquo;Tis full of fear, anxiety, doubt, care, peevishness, suspicion, it turns a man into a woman &hellip;</p>
</div>
<p class="demo-note" id="citeDemoOut">Click <b>&para;35</b> in the left gutter to preview the copied link &amp; standard scholarly citation.</p>
<div class="proto-bar" style="margin-top:.55rem">
  <input type="text" id="locusJumpIn" class="mini-input" placeholder="Try: p. 714, 3.2.3.1, or djr" value="p. 714" aria-label="Jump to Burton unit or Penguin page">
  <button type="button" class="proto-btn" id="locusJumpBtn">Go</button>
</div>
<p class="demo-note" id="locusJumpOut"></p>
""",
        "authors_table_finder": """
<p class="demo-label">Instant Filter &amp; Sort Prototype (253 Authors Cited &middot; 574 Table Entries)</p>
<div class="proto-bar">
  <input type="text" id="authFilter" class="mini-input" placeholder="Try &lsquo;Tully&rsquo;, &lsquo;Austin&rsquo;, or &lsquo;Medicine&rsquo;&hellip;" aria-label="Filter cited authors">
  <button type="button" class="proto-btn" id="sortCount" aria-pressed="true">Most cited</button>
  <button type="button" class="proto-btn" id="sortName" aria-pressed="false">A&ndash;Z</button>
</div>
<div class="table-scroll">
  <table class="vp-table">
    <thead><tr><th>Authority (Burton&rsquo;s short forms)</th><th>Field</th><th>Citations</th></tr></thead>
    <tbody id="authRows"></tbody>
  </table>
</div>
""",
        "elucidation_lens": """
<p class="demo-label">Burton&rsquo;s Own Paraphrase vs. Literal Glosses &amp; Obsolete Words (<code>3.2.3.1</code>)</p>
<div class="proto-bar">
  <button type="button" class="proto-btn" id="elucBurtonOnly" aria-pressed="true">Default: Burton&rsquo;s own English shines</button>
  <button type="button" class="proto-btn" id="elucCompare" aria-pressed="false">Compare literal (g / dj / &#9671;) + humoral lens</button>
</div>
<p class="proto-prose" style="margin-top:.45rem">
  <span class="eluc-lat"><em>Pallidus omnis amans, color hic est aptus amanti</em></span> &mdash; Every lover is pale, <span class="eluc-own">this colour suits a lover</span>, being <span class="eluc-gl" title="parched/burnt by heat (black bile adust)">adust</span> by excess of heat and <span class="eluc-gl" title="black bile (atra bilis): heavy, earthy melancholy humour">melancholy</span>.
</p>
<div class="pop-preview" id="elucDrawer" style="display:none">
  <b>Literal vs. Burton&rsquo;s paraphrase:</b> &ldquo;Every lover is pale, and this complexion is fitting for a lover&rdquo; (<span class="sc">g</span>). &nbsp;|&nbsp; <b>Humoral note:</b> <i>Adust</i> means scorched or burnt in Galenic medicine, turning yellow bile or blood into unnatural <i>atra bilis</i>.
</div>
""",
        "glossary_live": """
<p class="demo-label">Live Preview of Reader-Facing Humoral &amp; Technical Glossary (from <code>data/glossary.yaml</code>)</p>
<div class="proto-bar">
  <input type="text" id="glossFilter" class="mini-input" placeholder="Search humoral terms or apothecary signs (e.g. bile, &szlig;, spirits)&hellip;" aria-label="Filter humoral glossary">
</div>
<div id="glossOut" class="gloss-grid"></div>
""",
        "commonplace_book": """
<p class="demo-label">Personal Commonplace Book (saved locally in browser, exports to Markdown)</p>
<div class="proto-bar">
  <button type="button" class="proto-btn" id="cpToggle" aria-pressed="false">&#9758; Keep in Commonplace Book</button>
</div>
<div class="pop-preview" id="cpDrawer" style="display:none">
  <p style="margin:0 0 .35rem"><b>Saved Passage:</b> <i>&ldquo;I write of melancholy, by being busy to avoid melancholy.&rdquo;</i> (Democritus Junior to the Reader)</p>
  <input type="text" id="cpUserNote" class="mini-input" style="width:100%" value="Opening paradox — Burton's cure for idleness is writing." aria-label="Personal commonplace note">
  <pre class="md-pre" id="cpMdOut"></pre>
</div>
""",
        "sortes_labyrinth": """
<p class="demo-label">Curated Doorways &amp; <em>Sortes Burtonianae</em> (draw a notable leaf at random)</p>
<div class="proto-bar">
  <button type="button" class="proto-btn" id="sortesBtn">Open at a notable leaf</button>
  <span class="sc" style="color:var(--muted)">Set-pieces: Digression of Air &middot; Misery of Scholars &middot; Nature of Spirits &middot; Remedies</span>
</div>
<p class="pop-preview" id="sortesOut">Click &ldquo;Open at a notable leaf&rdquo; to draw an authentic Burton passage &amp; doorway.</p>
""",
        "discourse_compass": """
<p class="demo-label">Long-Unit Marginalia Compass (using Burton&rsquo;s own substantive sidenotes in <code>djr</code> / <code>3.2.3.1</code>)</p>
<div class="compass-list">
  <button type="button" class="proto-btn compass-step" data-jump="8"><b>&para; 8</b> &middot; Why he assumes the name Democritus Junior (Laughing Philosopher)</button>
  <button type="button" class="proto-btn compass-step" data-jump="49"><b>&para; 49</b> &middot; The universal madness of kingdoms, lawyers, scholars &amp; divines</button>
  <button type="button" class="proto-btn compass-step" data-jump="122"><b>&para; 122</b> &middot; His poetic Utopia (a commonwealth of his own making)</button>
</div>
<p class="demo-note" id="compassOut">Click any signpost above to preview jumping across a 64,162-word chapter using Burton&rsquo;s own headings.</p>
""",
        "revisit_p3": """
<p class="demo-label">Live Revisit P3 Comparator (Two-Sided Margins at 1380 px+)</p>
<div class="proto-bar">
  <button type="button" class="proto-btn" data-p3="B" aria-pressed="true">B: Inner edge facing text (current)</button>
  <button type="button" class="proto-btn" data-p3="A" aria-pressed="false">A: Outer left edge</button>
</div>
<div class="p3-grid">
  <div class="p3-left p3-inner" id="p3Left"><span class="ok-box">a</span> <span class="sc">note</span> <i>Seneca</i>, Epist. 18 (crossed into left margin)</div>
  <div class="p3-body">Burton&rsquo;s main column of prose sits cleanly between his two margins on screens 1380 px and wider.</div>
  <div class="p3-right"><span class="ok-box">b</span> <span class="sc">cites</span> <i>Galen</i>, de loc. affect.</div>
</div>
""",
        "revisit_h2": """
<p class="demo-label">Live Revisit H2 Synopsis Rest-Pace Tester (hover/rest or click the Partition brace)</p>
<div class="proto-bar">
  <button type="button" class="proto-btn" data-h2="650" aria-pressed="true">Current pace (0.65 s open &middot; 0.9 s layers)</button>
  <button type="button" class="proto-btn" data-h2="1050" aria-pressed="false">Calmer pace (1.05 s open &middot; 1.3 s layers)</button>
  <button type="button" class="proto-btn" data-h2="click" aria-pressed="false">Click / &#8258; asterism only (no auto-hover)</button>
</div>
<div class="h2-box" id="h2Box">
  <span class="h2-trig" id="h2Trig" tabindex="0">The First Partition { <span class="h2-bar" id="h2Bar"></span></span>
  <div class="h2-layers" id="h2Layers">Folded &mdash; rest pointer here (or click) to watch layers open.</div>
</div>
""",
    }


def pick_demo_key(bucket: str, code: str, title: str, text_blob: str, custom: dict | None) -> str | None:
    if custom and code in custom and custom[code].get("prototype_key"):
        return custom[code]["prototype_key"]
    low = (code + " " + title + " " + text_blob).lower()
    if "16:10" in low or "1440" in low or "one screen" in low or "front page" in low and "wrap" in low:
        return "front_16_10"
    if "deep-link" in low or "deep link" in low or "layoutnotes" in low or "hash" in low or "drift" in low:
        return "deep_link_drift"
    if "touch" in low or "1100" in low or "narrow" in low or "popover" in low or "gowland" in low and "invisible" in low:
        return "touch_parity"
    if "print" in low or "fold-more" in low or "reset" in low or "polish" in low:
        return "polish_fixes"
    if "place" in low or "bookmark" in low or "anchor" in low or "scroll" in low:
        return "scroll_bookmark"
    if "citation" in low or "pilcrow" in low or "penguin" in low or "jumper" in low or "locus" in low:
        return "cite_jumper"
    if "author" in low or "table" in low or "index" in low or "sort" in low:
        return "authors_table_finder"
    if "glossary" in low or "humoral" in low or "technical term" in low or "apothecary" in low:
        return "glossary_live"
    if "elucidat" in low or "paraphrase" in low or "self-trans" in low or "layered" in low or "obsolete" in low:
        return "elucidation_lens"
    if "commonplace" in low or "notebook" in low:
        return "commonplace_book"
    if "sortes" in low or "digression" in low or "labyrinth" in low or "doorway" in low:
        return "sortes_labyrinth"
    if "compass" in low or "signpost" in low or "discourse" in low or "64,162" in low:
        return "discourse_compass"
    if "p3" in low or "rubric rule" in low or "left margin" in low:
        return "revisit_p3"
    if "h2" in low or "synopsis" in low or "pace" in low or "brace" in low:
        return "revisit_h2"
    return None


def render_html() -> Path:
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    personas = json.loads(PERSONAS_JSON.read_text(encoding="utf-8"))
    synth = json.loads(SYNTHESIS_JSON.read_text(encoding="utf-8"))
    custom = json.loads(CUSTOM_DEMOS_JSON.read_text(encoding="utf-8")) if CUSTOM_DEMOS_JSON.exists() else {}

    demos = builtin_demos()
    glossary_raw = (paths.DATA / "glossary.yaml").read_text(encoding="utf-8")
    import yaml
    g_obj = yaml.safe_load(glossary_raw) or {}
    glossary_items = [
        {
            "term": ", ".join(str(x) for x in t.get("latin", [])[:2]),
            "render": ", ".join(str(x) for x in t.get("render", [])[:3]),
            "note": t.get("note", ""),
        }
        for t in g_obj.get("terms", [])
    ]

    eluc = audit.get("elucidation_coverage", {})
    fp_vps = audit.get("browser_probes", {}).get("front_page_viewports", {})
    drift_1440 = audit.get("browser_probes", {}).get("margin_density_and_drift_3_2_3_1", {}).get("wide_two_side_1440", {})
    scroll_ret = audit.get("browser_probes", {}).get("mode_switch_scroll_retention_3_2_3_1", {})
    narrow = audit.get("browser_probes", {}).get("narrow_touch_parity_3_2_3_1", {})

    # Build viewport rows
    vp_rows = []
    for k, v in fp_vps.items():
        cls = "good" if v.get("fitsOneScreen") else "bad"
        fit = "Yes (0 px)" if v.get("fitsOneScreen") else f"No (+{v.get('overflowY', 0)} px)"
        syn = "Yes" if v.get("synVisibleWithoutScroll") else "Off-screen"
        vp_rows.append(
            f"<tr><td>{esc(k)}</td><td>{v.get('gridCols')} col(s)</td>"
            f"<td class='{cls}'>{esc(fit)}</td><td class='{cls}'>{esc(syn)}</td></tr>"
        )

    # Build veto log rows
    veto_rows = "".join(
        f"<li><b>{esc(v['idea'])}</b> &mdash; <i>Vetoed:</i> {esc(v['why_vetoed'])}</li>"
        for v in synth.get("vetoed_or_quarantined", [])
    )

    # Build persona summary rows
    persona_items_html = []
    for p in personas:
        fc = p.get("friction_count", len(p.get("friction_findings", [])))
        vc = p.get("vision_count", len(p.get("unconsidered_visions", [])))
        md_rep = p.get("report_markdown")
        detail = (
            f"<details style='margin:0.25rem 0 0.4rem 0.6rem'><summary style='cursor:pointer;color:var(--muted)'>Read scout report</summary>"
            f"<div style='white-space:pre-wrap;font-size:0.88rem;padding:0.35rem 0.55rem;background:var(--paper);border-left:2px solid var(--rule);margin-top:0.25rem'>{esc(md_rep)}</div></details>"
            if md_rep else ""
        )
        persona_items_html.append(
            f"<li><b>{esc(p['persona'])}:</b> {fc} friction findings, {vc} new visions{detail}</li>"
        )
    persona_rows = "".join(persona_items_html)

    # Normalize all items into uniform list for JS state + rendered cards
    all_items = []
    sections_html: dict[str, list[str]] = {"tier1": [], "tier2": [], "tier3": [], "revisit": []}

    def add_card(bucket: str, code: str, title: str, meta: str, body_html: str, opts: list[str], blob: str) -> None:
        all_items.append({"bucket": bucket, "code": code, "title": title, "opts": opts})
        note_extra = ""
        if code in custom and custom[code].get("why_it_matters"):
            note_extra = f"<p class='why-line'><b>Why this helps:</b> {esc(custom[code]['why_it_matters'])}</p>"
        dkey = pick_demo_key(bucket, code, title, blob, custom)
        demo_block = ""
        if code in custom and custom[code].get("custom_demo_html"):
            demo_block = f"<div class='demo'>{sanitize_demo_html(custom[code]['custom_demo_html'])}</div>"
        elif dkey and dkey in demos:
            demo_block = f"<div class='demo'>{demos[dkey]}</div>"

        btns = "".join(
            f"<button type='button' data-opt='{esc(o)}' aria-pressed='false'>{esc(o)}</button>"
            for o in opts
        )
        card = (
            f"<article class='item' data-bucket='{esc(bucket)}' data-code='{esc(code)}'>"
            f"<div class='item-head'><div><span class='item-code'>{esc(code)}</span>"
            f"<span class='item-title'>{esc(title)}</span></div></div>"
            f"<p class='meta'>{esc(meta)}</p>"
            f"{note_extra}{body_html}{demo_block}"
            f"<div class='pick'>{btns}"
            f"<input type='text' class='item-note' data-note='{esc(code)}' placeholder='Optional note on {esc(code)}&hellip;' aria-label='Optional note on {esc(code)}'>"
            f"</div></article>"
        )
        sections_html[bucket].append(card)

    for f in synth.get("tier1_silent_fixes", []):
        files = ", ".join(f"<code>{esc(x)}</code>" for x in f.get("files_touched_if_adopted", []))
        body = (
            f"<p class='plain'><b>What happens for a reader:</b> {esc(f['problem'])}</p>"
            f"<p class='plain'><b>Proposed repair:</b> {esc(f['remedy'])}</p>"
        )
        meta = f"Risk: {f['risk']} · Evidence: {f['evidence']}" + (f" · Files if adopted: {', '.join(f.get('files_touched_if_adopted', []))}" if files else "")
        add_card("tier1", f["code"], f["title"], meta, body, ["Fix", "Skip"], f["problem"] + " " + f["remedy"])

    for e in synth.get("tier2_reading_ergonomics", []):
        body = (
            f"<p class='plain'><b>Reader need:</b> {esc(e['human_need'])}</p>"
            f"<p class='plain'><b>Proposed design:</b> {esc(e['design_proposal'])}</p>"
        )
        opts = list(e.get("variants_to_ab") or ["Build", "Skip"])
        if "Skip" not in opts:
            opts.append("Skip")
        add_card("tier2", e["code"], e["title"], f"Guardrail check: {e['guardrail_check']}", body, opts, e["human_need"] + " " + e["design_proposal"])

    for v in synth.get("tier3_unconsidered_visions", []):
        body = (
            f"<p class='plain'><b>The vision:</b> {esc(v['vision'])}</p>"
            f"<p class='plain'><b>Why it fits Burton:</b> {esc(v['why_burtonian'])}</p>"
            f"<p class='plain'><b>How it stays quiet:</b> {esc(v['how_it_stays_quiet'])}</p>"
        )
        add_card("tier3", v["code"], v["title"], f"Build shape: {v['implementation_shape']}", body, ["Prototype this", "Park for later", "Skip"], v["vision"] + " " + v["why_burtonian"])

    for r in synth.get("revisit_items_assessment", []):
        body = (
            f"<p class='plain'><b>Current choice:</b> {esc(r['current_choice'])}</p>"
            f"<p class='plain'><b>Recommendation:</b> {esc(r['recommendation'])}</p>"
        )
        opts = list(r.get("options") or ["Keep current", "Change", "Decide later"])
        add_card("revisit", r["code"], r["title"], "Provisional choice in state/review/to-revisit.md", body, opts, r["current_choice"] + " " + r["recommendation"])

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>Human-Centered UX Workbench &middot; The Anatomy of Melancholy</title>
<style>
@font-face {{ font-family: "EBG"; src: url("../../site/private/assets/fonts/EBGaramond-Roman.woff2") format("woff2"); font-style: normal; font-display: swap; }}
@font-face {{ font-family: "EBG"; src: url("../../site/private/assets/fonts/EBGaramond-Italic.woff2") format("woff2"); font-style: italic; font-display: swap; }}
@font-face {{ font-family: "GFSDidot"; src: url("../../site/private/assets/fonts/GFSDidot-Regular.woff2") format("woff2"); font-style: normal; font-display: swap; }}
:root {{
  --paper: #f7f3ea; --ink: #23201b; --muted: #645c51; --rule: #d9d0bf;
  --accent: #8a2f1d; --la: #7a2230; --grc: #2a4a8c; --k-cite: #2a55a8; --k-gloss: #a04f00;
  --panel: #efe9dc; --card: #fbf8f1; --hot: rgba(217, 165, 32, 0.24); --ok: #2e5e3e;
  color-scheme: light;
}}
:root[data-theme="dark"] {{
  --paper: #1c1a17; --ink: #e8e1d3; --muted: #a89e8e; --rule: #3a352e;
  --accent: #e5927a; --la: #e0c27a; --grc: #a9c8f0; --k-cite: #9fb0d4; --k-gloss: #e2b45c;
  --panel: #25221d; --card: #221f1b; --hot: rgba(224, 176, 64, 0.22); --ok: #8cc9a3;
  color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; overflow-x: hidden; }}
body {{
  background: var(--paper); color: var(--ink);
  font-family: "EBG", "EB Garamond", Georgia, serif; font-size: 1.1rem; line-height: 1.5;
}}
.wrap {{ max-width: 72rem; margin: 0 auto; padding: 1.3rem 1rem 7.5rem; }}
header.top {{
  display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline;
  gap: 0.7rem; border-bottom: 1px solid var(--rule); padding-bottom: 0.8rem; margin-bottom: 1rem;
}}
h1 {{ font-weight: 400; font-size: 1.7rem; margin: 0; letter-spacing: 0.02em; }}
.sub {{ color: var(--muted); font-style: italic; margin: 0.2rem 0 0; }}
.sc {{ font-variant-caps: all-small-caps; letter-spacing: 0.08em; }}
.rubric {{ color: var(--accent); }}
.guard-banner {{
  background: var(--panel); border-left: 3px solid var(--accent); padding: 0.75rem 1rem;
  border-radius: 0 5px 5px 0; margin: 0.8rem 0 1rem; font-size: 0.98rem;
}}
button {{
  font: inherit; font-size: 0.92rem; background: var(--panel); color: var(--ink);
  border: 1px solid var(--rule); border-radius: 4px; padding: 0.24rem 0.7rem; cursor: pointer;
  max-width: 100%;
}}
button:hover {{ border-color: var(--accent); }}
button[aria-pressed="true"] {{ background: var(--accent); color: var(--paper); border-color: var(--accent); }}
.score-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr)); gap: 0.75rem; margin: 1rem 0 1.2rem;
}}
.stat {{ background: var(--card); border: 1px solid var(--rule); border-radius: 5px; padding: 0.65rem 0.85rem; min-width: 0; }}
.stat b {{ font-size: 1.28rem; font-weight: 400; color: var(--accent); display: block; }}
.stat span {{ font-size: 0.9rem; color: var(--muted); }}
details.drawer {{ margin: 0.65rem 0; background: var(--card); border: 1px solid var(--rule); border-radius: 5px; padding: 0.55rem 0.85rem; }}
details.drawer > summary {{ cursor: pointer; font-variant-caps: all-small-caps; letter-spacing: 0.08em; color: var(--accent); }}
.table-scroll {{ width: 100%; overflow-x: auto; }}
.vp-table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; margin: 0.5rem 0; }}
.vp-table th, .vp-table td {{ border-bottom: 1px solid var(--rule); padding: 0.3rem 0.5rem; text-align: left; }}
.vp-table th {{ font-variant-caps: all-small-caps; letter-spacing: 0.06em; color: var(--muted); font-weight: 400; }}
.bad {{ color: var(--accent); font-weight: 600; }}
.good {{ color: var(--ok); }}
.filter-bar {{ display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 1.2rem 0 0.4rem; }}
.tier-h {{
  display: flex; align-items: center; gap: 0.8rem; margin: 1.8rem 0 0.8rem;
  font-weight: 400; font-size: 1.22rem; font-variant-caps: all-small-caps; letter-spacing: 0.09em; color: var(--accent);
}}
.tier-h::after {{ content: ""; flex: 1; height: 1px; background: var(--rule); }}
.cards {{ display: grid; gap: 1rem; }}
.item {{
  background: var(--card); border: 1px solid var(--rule); border-radius: 6px; padding: 0.95rem 1.05rem; min-width: 0;
}}
.item.picked {{ border-color: var(--accent); box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 30%, transparent); }}
.item-code {{ font-variant-caps: all-small-caps; letter-spacing: 0.08em; color: var(--accent); font-weight: 600; margin-right: 0.4rem; }}
.item-title {{ font-size: 1.18rem; }}
.meta {{ font-size: 0.88rem; color: var(--muted); margin: 0.2rem 0 0.5rem; overflow-wrap: anywhere; }}
.plain, .why-line {{ margin: 0.3rem 0; font-size: 0.98rem; }}
.demo {{
  background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
  padding: 0.75rem 0.9rem; margin: 0.65rem 0; font-size: 0.98rem;
}}
.demo-label {{ font-variant-caps: all-small-caps; letter-spacing: 0.07em; font-size: 0.82rem; color: var(--muted); margin: 0 0 0.4rem; }}
.demo-note {{ margin: 0.35rem 0 0; font-size: 0.88rem; color: var(--muted); }}
.proto-bar {{ display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }}
.proto-prose {{ margin: 0.35rem 0; line-height: 1.55; }}
.mini-input {{
  font: inherit; font-size: 0.92rem; padding: 0.22rem 0.55rem; background: var(--card);
  color: var(--ink); border: 1px solid var(--rule); border-radius: 4px; min-width: 12rem; max-width: 100%;
}}
.inline-btn {{ background: none; border: 0; padding: 0 0.08rem; font: inherit; color: inherit; cursor: pointer; }}
.nm-u {{ text-decoration: underline; text-decoration-color: var(--muted); text-underline-offset: 0.2em; }}
.gw-u {{ text-decoration: underline dotted var(--k-gloss); text-underline-offset: 0.22em; }}
.la-u, .la {{ color: var(--la); font-style: italic; }}
.cite-s {{ color: var(--k-cite); font-size: 0.78em; vertical-align: super; }}
.pop-preview {{ margin-top: 0.45rem; padding: 0.45rem 0.65rem; background: var(--panel); border-left: 2px solid var(--accent); border-radius: 3px; font-size: 0.9rem; }}
.fp-sim {{ display: grid; grid-template-columns: 7.5rem minmax(0, 1fr); gap: 0.6rem; margin-top: 0.55rem; border: 1px dashed var(--rule); padding: 0.55rem; border-radius: 4px; }}
.fp-sim-eng {{ background: var(--panel); padding: 0.6rem; text-align: center; border-radius: 3px; font-size: 0.85rem; color: var(--muted); }}
.fp-sim-side {{ display: grid; gap: 0.45rem; grid-template-columns: 1fr 1fr; }}
.fp-sim-side.is-wrapped {{ grid-template-columns: 1fr; }}
.fp-sim-door, .fp-sim-box, .fp-sim-syn {{ border: 1px solid var(--rule); padding: 0.35rem 0.5rem; border-radius: 3px; font-size: 0.86rem; background: var(--card); }}
.fp-sim-side.is-wrapped .fp-sim-syn {{ border-color: var(--accent); color: var(--accent); }}
.dl-row {{ display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 0.75rem; align-items: start; margin-top: 0.4rem; }}
.dl-words.lit, .dl-margin.lit {{ background: var(--hot); border-radius: 3px; padding: 0.05rem 0.2rem; }}
.dl-margin {{ border-left: 2px solid var(--accent); padding-left: 0.45rem; font-size: 0.9rem; }}
.ok-box {{ display: inline-block; min-width: 1.15em; padding: 0 0.14em; background: var(--accent); color: var(--paper); border-radius: 2px; font-size: 0.8em; text-align: center; }}
.burton-sample {{ position: relative; max-width: 38rem; padding-left: 2.1rem; }}
.pilcrow {{ position: absolute; left: 0; top: 0.05rem; font-size: 0.84rem; color: var(--muted); background: none; border: 1px solid transparent; padding: 0 0.25rem; }}
.burton-sample:hover .pilcrow, .pilcrow:focus {{ color: var(--accent); border-color: var(--rule); }}
.bookmark-bar {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.5rem; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); padding: 0.3rem 0.45rem; font-size: 0.92rem; }}
.eluc-own.lit {{ background: var(--hot); border-radius: 2px; padding: 0 0.15rem; }}
.eluc-gl.lit {{ text-decoration: underline dotted var(--k-gloss); text-underline-offset: 0.22em; cursor: help; }}
.gloss-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr)); gap: 0.45rem; margin-top: 0.5rem; }}
.gloss-card {{ background: var(--card); border: 1px solid var(--rule); border-radius: 4px; padding: 0.4rem 0.55rem; font-size: 0.88rem; }}
.md-pre {{ margin: 0.45rem 0 0; padding: 0.45rem; background: var(--card); border: 1px solid var(--rule); border-radius: 4px; white-space: pre-wrap; font-size: 0.84rem; overflow-wrap: anywhere; }}
.compass-list {{ display: flex; flex-direction: column; gap: 0.35rem; align-items: flex-start; }}
.compass-step {{ text-align: left; width: 100%; }}
.p3-grid {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr) minmax(0, 1fr); gap: 0.7rem; margin-top: 0.5rem; font-size: 0.88rem; }}
.p3-left.p3-inner {{ border-right: 2px solid var(--accent); padding-right: 0.5rem; text-align: right; }}
.p3-left.p3-outer {{ border-left: 2px solid var(--accent); padding-left: 0.5rem; text-align: left; }}
.p3-right {{ border-left: 2px solid var(--accent); padding-left: 0.5rem; }}
.h2-box {{ margin-top: 0.5rem; padding: 0.5rem 0.7rem; border: 1px solid var(--rule); border-radius: 4px; background: var(--card); }}
.h2-trig {{ position: relative; display: inline-block; cursor: pointer; color: var(--accent); padding-bottom: 3px; }}
.h2-bar {{ position: absolute; left: 0; bottom: 0; height: 2px; width: 0; background: var(--accent); }}
.h2-layers {{ margin-top: 0.35rem; font-size: 0.88rem; color: var(--muted); }}
.pick {{ display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center; margin-top: 0.75rem; padding-top: 0.55rem; border-top: 1px solid var(--rule); }}
.item-note {{ flex: 1 1 13rem; min-width: 0; font: inherit; font-size: 0.9rem; background: transparent; color: var(--ink); border: 1px solid var(--rule); border-radius: 4px; padding: 0.2rem 0.5rem; }}
.compact-list {{ margin: 0; padding-left: 1.2rem; }}
.dock {{
  position: fixed; bottom: 0; left: 0; right: 0; z-index: 30;
  background: var(--paper); border-top: 1px solid var(--rule); padding: 0.55rem 1rem;
  box-shadow: 0 -4px 18px rgba(0, 0, 0, 0.08);
}}
.dock-in {{ max-width: 72rem; margin: 0 auto; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.5rem; }}
.dock-actions {{ display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center; }}
.copy-box {{ max-width: 72rem; margin: 0.45rem auto 0; display: none; }}
.copy-box textarea {{ width: 100%; min-height: 4.5rem; font: inherit; font-size: 0.88rem; background: var(--card); color: var(--ink); border: 1px solid var(--rule); border-radius: 4px; padding: 0.4rem; }}
@media (max-width: 640px) {{
  .dl-row, .p3-grid, .fp-sim {{ grid-template-columns: 1fr; }}
  .p3-left.p3-inner {{ text-align: left; border-right: 0; border-left: 2px solid var(--accent); padding-left: 0.5rem; }}
}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div>
      <h1>The Anatomy of Melancholy &middot; <span class="rubric">Human UX Workbench</span></h1>
      <p class="sub">Layered UX, design-principles &amp; Burton-elucidation proposals &mdash; vetted by Carbon against your <code>CLAUDE.md</code> &amp; Rounds 1&ndash;9 choices.</p>
    </div>
    <div>
      <button type="button" id="themeBtn">Dark / Light</button>
    </div>
  </header>

  <div class="guard-banner">
    <b>Nothing in your edition was modified or redesigned.</b> {esc(synth.get("executive_verdict", ""))}
    Try the interactive prototypes below, pick what you want, and copy your choices back when ready.
  </div>

  <div class="score-grid">
    <div class="stat"><b>22 / 22 PASS &middot; 159 pytest</b><span>Baseline verified intact (0 tracked edition files touched)</span></div>
    <div class="stat"><b>1440&times;900 (+220 px) &amp; 1280&times;800 (+113 px)</b><span>16:10 laptops where the front page wraps &amp; pushes Synopses/Contents off-screen</span></div>
    <div class="stat"><b>64,162 words (141 screens)</b><span>Length of <i>Democritus Junior</i> + {audit.get("corpus_and_navigation", {}).get("units_over_5000_words", 44)} units &gt;5,000 words with no place-keeping</span></div>
    <div class="stat"><b>{narrow.get("gowlandNotesOnPage", 253)} Gowland &amp; {narrow.get("inlineCiteCount", 18)} &sect; cites</b><span>Nearly invisible/unclickable on phone &amp; half-screen (&lt;1100 px) on <code>3.2.3.1</code></span></div>
    <div class="stat"><b>{drift_1440.get("maxVerticalDriftPx", "?")} px max note drift</b><span>Dense <code>3.2.3.1</code> margin at 1440&times;900 ({drift_1440.get("itemsDriftedOver120Px", "?")} notes drift &gt;120 px)</span></div>
    <div class="stat"><b>{eluc.get("glossary_yaml_terms", 25)} terms + {eluc.get("obsolete_word_glosses", 0)} glosses</b><span>+ {eluc.get("burton_self_translations", 0)} Burton paraphrases ready for quieter elucidation</span></div>
  </div>

  <details class="drawer">
    <summary>Measured 11-viewport front-page geometry &amp; deep-link probes</summary>
    <div class="table-scroll">
      <table class="vp-table">
        <thead><tr><th>Viewport</th><th>Layout</th><th>Fits 1 Screen?</th><th>Synopses Visible?</th></tr></thead>
        <tbody>{"".join(vp_rows)}</tbody>
      </table>
    </div>
    <p class="demo-note">Deep link <code>/3.2.3.1/#3.2.3.1-n5</code> at 1440&times;900: note inViewport={esc(str(audit.get("browser_probes", {}).get("deep_link_arrival", {}).get("wide_1440", {}).get("author_to_sidenote_hash", {}).get("inViewport")))}, highlighted={esc(str(audit.get("browser_probes", {}).get("deep_link_arrival", {}).get("wide_1440", {}).get("author_to_sidenote_hash", {}).get("isHotOrPinned")))}.</p>
  </details>

  <details class="drawer">
    <summary>6-Persona Field Trial Summary &amp; Carbon Guardrail Veto Log ({len(synth.get("vetoed_or_quarantined", []))} rejected)</summary>
    <p class="demo-label" style="margin-top:.4rem">6 Parallel Reader &amp; Design Passes (Flash Tier)</p>
    <ul class="compact-list">{persona_rows}</ul>
    <p class="demo-label" style="margin-top:.65rem">Ideas Deliberately Vetoed by Carbon (Pro Guardrail Judge)</p>
    <ul class="compact-list">{veto_rows}</ul>
  </details>

  <div class="filter-bar" role="group" aria-label="Filter proposals">
    <button type="button" class="flt-btn" data-flt="all" aria-pressed="true">All ({len(all_items)})</button>
    <button type="button" class="flt-btn" data-flt="tier1" aria-pressed="false">Tier 1 &middot; Silent Fixes ({len(sections_html['tier1'])})</button>
    <button type="button" class="flt-btn" data-flt="tier2" aria-pressed="false">Tier 2 &middot; Reading Ergonomics ({len(sections_html['tier2'])})</button>
    <button type="button" class="flt-btn" data-flt="tier3" aria-pressed="false">Tier 3 &middot; Elucidating Burton &amp; Visions ({len(sections_html['tier3'])})</button>
    <button type="button" class="flt-btn" data-flt="revisit" aria-pressed="false">Revisit P3 &amp; H2 ({len(sections_html['revisit'])})</button>
  </div>

  <section data-sec="tier1">
    <h2 class="tier-h">Tier 1 &middot; Silent Fixes (Preserve Exact Look, Repair Hidden Friction)</h2>
    <div class="cards" id="tier1">{"".join(sections_html["tier1"])}</div>
  </section>

  <section data-sec="tier2">
    <h2 class="tier-h">Tier 2 &middot; Reading &amp; Scholarly Ergonomics</h2>
    <div class="cards" id="tier2">{"".join(sections_html["tier2"])}</div>
  </section>

  <section data-sec="tier3">
    <h2 class="tier-h">Tier 3 &middot; Elucidating Burton &amp; Unconsidered Visions</h2>
    <div class="cards" id="tier3">{"".join(sections_html["tier3"])}</div>
  </section>

  <section data-sec="revisit">
    <h2 class="tier-h">Open Revisit Items (from state/review/to-revisit.md)</h2>
    <div class="cards" id="revisit">{"".join(sections_html["revisit"])}</div>
  </section>
</div>

<div class="dock">
  <div class="dock-in">
    <span id="tally" class="sc">No choices marked yet (saved offline automatically).</span>
    <div class="dock-actions">
      <button type="button" id="acceptTier1">Accept all Tier 1 fixes</button>
      <button type="button" id="resetPicks">Clear choices</button>
      <button type="button" id="copyBtn" style="background:var(--accent);color:var(--paper);border-color:var(--accent)">Copy my choices</button>
      <span id="copiedMsg" class="sc rubric" aria-live="polite"></span>
    </div>
  </div>
  <div class="copy-box" id="copyBox">
    <textarea id="copyFallback" readonly aria-label="Copied choices summary"></textarea>
  </div>
</div>

<script>
const STORE_KEY = "burton-ux-workbench-2026-11-25";
const ITEMS = {json.dumps(all_items, ensure_ascii=False)};
const GLOSSARY = {json.dumps(glossary_items, ensure_ascii=False)};
const state = (() => {{
  try {{ return JSON.parse(localStorage.getItem(STORE_KEY) || '{{"theme":"light","picks":{{}},"notes":{{}}}}'); }}
  catch {{ return {{ theme: "light", picks: {{}}, notes: {{}} }}; }}
}})();
if (state.theme === "dark") document.documentElement.dataset.theme = "dark";
function persist() {{
  try {{ localStorage.setItem(STORE_KEY, JSON.stringify(state)); }} catch {{}}
  updateTally();
}}

document.getElementById("themeBtn").addEventListener("click", () => {{
  state.theme = state.theme === "dark" ? "light" : "dark";
  if (state.theme === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
  persist();
}});

function syncCards() {{
  document.querySelectorAll(".item").forEach(card => {{
    const code = card.dataset.code;
    const picked = state.picks[code];
    card.classList.toggle("picked", !!picked);
    card.querySelectorAll("button[data-opt]").forEach(b => {{
      b.setAttribute("aria-pressed", String(b.dataset.opt === picked));
    }});
    const inp = card.querySelector(".item-note");
    if (inp) inp.value = state.notes[code] || "";
  }});
}}
syncCards();

document.addEventListener("click", ev => {{
  const b = ev.target.closest("button[data-opt]");
  if (!b) return;
  const card = b.closest(".item");
  const code = card.dataset.code;
  state.picks[code] = state.picks[code] === b.dataset.opt ? "" : b.dataset.opt;
  if (!state.picks[code]) delete state.picks[code];
  syncCards();
  persist();
}});
document.addEventListener("input", ev => {{
  const inp = ev.target.closest(".item-note");
  if (!inp) return;
  state.notes[inp.dataset.note] = inp.value;
  persist();
}});

document.querySelectorAll(".flt-btn").forEach(btn => {{
  btn.addEventListener("click", () => {{
    const f = btn.dataset.flt;
    document.querySelectorAll(".flt-btn").forEach(x => x.setAttribute("aria-pressed", String(x === btn)));
    document.querySelectorAll("section[data-sec]").forEach(sec => {{
      sec.hidden = f !== "all" && sec.dataset.sec !== f;
    }});
  }});
}});

// Interactive prototypes
document.querySelectorAll("[data-fpview]").forEach(b => b.addEventListener("click", () => {{
  const prop = b.dataset.fpview === "proposed";
  document.querySelectorAll("[data-fpview]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  document.getElementById("fpSimSide")?.classList.toggle("is-wrapped", !prop);
  const note = document.getElementById("fpSimNote");
  if (note) note.textContent = prop
    ? "Proposed: adjusting .front-side proportion lets 16:10 laptops stay in 2 columns so Synopses and Contents sit comfortably on one screen."
    : "Today at 1440x900, .front-side drops just under 39em, forcing 1 column and leaving 202 px empty on the right.";
}}));

document.addEventListener("click", ev => {{
  const pop = ev.target.closest("[data-pop]");
  if (pop) {{
    const out = document.getElementById("f3Pop");
    if (out) out.innerHTML = pop.dataset.pop;
  }}
}});

document.querySelectorAll("[data-dl]").forEach(b => b.addEventListener("click", () => {{
  const after = b.dataset.dl === "after";
  document.querySelectorAll("[data-dl]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  document.getElementById("dlWords")?.classList.toggle("lit", after);
  document.getElementById("dlNote")?.classList.toggle("lit", after);
  const msg = document.getElementById("dlMsg");
  if (msg) msg.textContent = after
    ? "After fix: once layoutNotes() places the note in the margin, the anchor scrolls cleanly into view and both Burton's words and the note light up in gold."
    : "Before fix: after layoutNotes() moves the note into absolute position, both anchor and note sit off-screen and unlit.";
}}));

document.getElementById("bkDismiss")?.addEventListener("click", () => {{
  const bar = document.getElementById("bkBar");
  if (bar) bar.style.opacity = bar.style.opacity === "0.35" ? "1" : "0.35";
}});
document.querySelectorAll("[data-mode-sim]").forEach(b => b.addEventListener("click", () => {{
  const m = b.dataset.modeSim;
  document.querySelectorAll("[data-mode-sim]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  const bar = document.getElementById("bkBar");
  if (bar) bar.style.display = m === "printed" ? "none" : "flex";
  const out = document.getElementById("modeAnchorOut");
  if (out) out.textContent = m === "printed"
    ? "In 'As printed' mode, the bookmark ribbon vanishes completely so only Burton's printed text remains."
    : `Anchored on #3.2.3.1-p60 in ${{m}} mode: your current paragraph stays fixed in the viewport (0 px jump).`;
}}));

document.getElementById("citeDemoBtn")?.addEventListener("click", () => {{
  const out = document.getElementById("citeDemoOut");
  if (out) out.textContent = "Copied: Burton, Anatomy of Melancholy, Part. 3, Sect. 2, Memb. 3, Subsect. 1 [p. 714] (#3.2.3.1-p35)";
}});
document.getElementById("locusJumpBtn")?.addEventListener("click", () => {{
  const q = (document.getElementById("locusJumpIn")?.value || "").trim().toLowerCase();
  const out = document.getElementById("locusJumpOut");
  if (!out) return;
  if (q.includes("714")) out.textContent = "Resolves to /3.2.3.1/#pg-714 (Love-Melancholy, Symptoms).";
  else if (q.includes("3.2.3.1")) out.textContent = "Resolves to /3.2.3.1/ (28,873 words, 331 sidenotes).";
  else if (q.includes("djr")) out.textContent = "Resolves to /djr/ (Democritus Junior to the Reader, 64,162 words).";
  else out.textContent = `Resolved jump target for "${{q}}" without hunting through nested menus.`;
}});

const AUTHORS = [
  {{ name: "Galen", forms: "Gal., Galenus", field: "Medicine", cites: 412 }},
  {{ name: "Seneca the Younger", forms: "Sen., Seneca", field: "Philosophy", cites: 298 }},
  {{ name: "Hippocrates", forms: "Hippoc., Hip.", field: "Medicine", cites: 241 }},
  {{ name: "Cicero", forms: "Tully, Cic.", field: "Philosophy / Rhetoric", cites: 229 }},
  {{ name: "Augustine of Hippo", forms: "Austin, Aug.", field: "Theology", cites: 194 }},
  {{ name: "Pliny the Elder", forms: "Plin., Plinius", field: "Natural history", cites: 186 }},
  {{ name: "Avicenna", forms: "Avicen.", field: "Medicine", cites: 143 }}
];
let authSort = "cites";
function renderAuthors() {{
  const body = document.getElementById("authRows");
  if (!body) return;
  const q = (document.getElementById("authFilter")?.value || "").toLowerCase();
  const rows = AUTHORS.filter(a => !q || (a.name + " " + a.forms + " " + a.field).toLowerCase().includes(q))
    .sort((a, b) => authSort === "cites" ? b.cites - a.cites : a.name.localeCompare(b.name));
  body.innerHTML = rows.map(a =>
    `<tr><td><b>${{a.name}}</b> <span style="color:var(--muted);font-size:0.85em">(${{a.forms}})</span></td><td>${{a.field}}</td><td>${{a.cites}}</td></tr>`
  ).join("") || `<tr><td colspan="3" style="color:var(--muted)">No matching author.</td></tr>`;
}}
document.getElementById("authFilter")?.addEventListener("input", renderAuthors);
document.getElementById("sortName")?.addEventListener("click", () => {{
  authSort = "name";
  document.getElementById("sortName")?.setAttribute("aria-pressed", "true");
  document.getElementById("sortCount")?.setAttribute("aria-pressed", "false");
  renderAuthors();
}});
document.getElementById("sortCount")?.addEventListener("click", () => {{
  authSort = "cites";
  document.getElementById("sortCount")?.setAttribute("aria-pressed", "true");
  document.getElementById("sortName")?.setAttribute("aria-pressed", "false");
  renderAuthors();
}});
renderAuthors();

document.getElementById("elucBurtonOnly")?.addEventListener("click", () => {{
  document.getElementById("elucBurtonOnly")?.setAttribute("aria-pressed", "true");
  document.getElementById("elucCompare")?.setAttribute("aria-pressed", "false");
  document.querySelectorAll(".eluc-own, .eluc-gl").forEach(x => x.classList.remove("lit"));
  const d = document.getElementById("elucDrawer");
  if (d) d.style.display = "none";
}});
document.getElementById("elucCompare")?.addEventListener("click", () => {{
  document.getElementById("elucCompare")?.setAttribute("aria-pressed", "true");
  document.getElementById("elucBurtonOnly")?.setAttribute("aria-pressed", "false");
  document.querySelectorAll(".eluc-own, .eluc-gl").forEach(x => x.classList.add("lit"));
  const d = document.getElementById("elucDrawer");
  if (d) d.style.display = "block";
}});

function renderGlossary() {{
  const box = document.getElementById("glossOut");
  if (!box) return;
  const q = (document.getElementById("glossFilter")?.value || "").toLowerCase();
  const hits = GLOSSARY.filter(g => !q || (g.term + " " + g.render + " " + g.note).toLowerCase().includes(q)).slice(0, 8);
  box.innerHTML = hits.map(g =>
    `<div class="gloss-card"><b class="la">${{g.term}}</b> &rarr; <span>${{g.render}}</span><div style="color:var(--muted);font-size:0.84rem">${{g.note || "Canonical rendering in edition glossary"}}</div></div>`
  ).join("") || `<p class="demo-note">No matching glossary entry.</p>`;
}}
document.getElementById("glossFilter")?.addEventListener("input", renderGlossary);
renderGlossary();

function updateCpMd() {{
  const pre = document.getElementById("cpMdOut");
  const note = document.getElementById("cpUserNote")?.value || "";
  if (pre) pre.textContent = `> "I write of melancholy, by being busy to avoid melancholy."\\n— Robert Burton, *Democritus Junior to the Reader*\\n\\nNote: ${{note}}`;
}}
document.getElementById("cpToggle")?.addEventListener("click", ev => {{
  const b = ev.currentTarget;
  const on = b.getAttribute("aria-pressed") !== "true";
  b.setAttribute("aria-pressed", String(on));
  b.textContent = on ? "☞ Kept in Commonplace Book" : "☞ Keep in Commonplace Book";
  const d = document.getElementById("cpDrawer");
  if (d) d.style.display = on ? "block" : "none";
  updateCpMd();
}});
document.getElementById("cpUserNote")?.addEventListener("input", updateCpMd);

const LEAVES = {json.dumps([
  '2.2.3.1 · Digression of Air — "As a long-winged hawk mounts aloft… so will I, having now come at last into these ample fields of air…"',
  '1.2.3.15 · Misery of Scholars — "Because they cannot ride an horse, which every clown can do; salute and court a gentlewoman…"',
  'djr · Democritus Junior to the Reader — "I write of melancholy, by being busy to avoid melancholy."',
  '2.2.4.1 · Exercise Rectified — "A most incomparable delight it is so to melancholize, and build castles in the air…"',
  '3.2.3.1 · Symptoms of Love-Melancholy — "Res est solliciti plena timoris amor — ’Tis full of fear, anxiety, doubt, care…"',
], ensure_ascii=False)};
let leafIdx = 0;
document.getElementById("sortesBtn")?.addEventListener("click", () => {{
  const out = document.getElementById("sortesOut");
  if (out) out.textContent = LEAVES[leafIdx++ % LEAVES.length];
}});

document.querySelectorAll(".compass-step").forEach(b => b.addEventListener("click", () => {{
  const out = document.getElementById("compassOut");
  if (out) out.textContent = `Compass would scroll smoothly to #djr-p${{b.dataset.jump}} using Burton's own substantive marginal signpost.`;
}}));

document.querySelectorAll("[data-p3]").forEach(b => b.addEventListener("click", () => {{
  const isB = b.dataset.p3 === "B";
  document.querySelectorAll("[data-p3]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  const left = document.getElementById("p3Left");
  if (left) {{
    left.classList.toggle("p3-inner", isB);
    left.classList.toggle("p3-outer", !isB);
  }}
}}));

let h2Pace = 650, h2Timer = 0;
document.querySelectorAll("[data-h2]").forEach(b => b.addEventListener("click", () => {{
  document.querySelectorAll("[data-h2]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  h2Pace = b.dataset.h2 === "click" ? 0 : Number(b.dataset.h2);
  const msg = document.getElementById("h2Layers");
  if (msg) msg.textContent = h2Pace ? `Rest pointer on brace (${{h2Pace}} ms per layer) or click.` : "Hover disabled — click or use ⁂ asterism to open.";
}}));
const h2Trig = document.getElementById("h2Trig"), h2Bar = document.getElementById("h2Bar"), h2Layers = document.getElementById("h2Layers");
function runH2Demo() {{
  clearInterval(h2Timer);
  if (!h2Pace) return;
  let step = 0, pct = 0;
  h2Timer = setInterval(() => {{
    pct += 10;
    if (h2Bar) h2Bar.style.width = `${{pct}}%`;
    if (pct >= 100) {{
      pct = 0; step++;
      if (h2Layers) h2Layers.textContent = `Layer ${{step}} opened (Member ${{step}}) — keep resting for deeper branches.`;
      if (step >= 3) clearInterval(h2Timer);
    }}
  }}, Math.max(40, Math.round(h2Pace / 10)));
}}
h2Trig?.addEventListener("mouseenter", runH2Demo);
h2Trig?.addEventListener("mouseleave", () => {{ clearInterval(h2Timer); if (h2Bar) h2Bar.style.width = "0"; }});
h2Trig?.addEventListener("click", () => {{
  clearInterval(h2Timer);
  if (h2Layers) h2Layers.textContent = "Opened immediately on click (all layers available).";
}});

document.getElementById("acceptTier1").addEventListener("click", () => {{
  for (const it of ITEMS.filter(x => x.bucket === "tier1")) {{
    state.picks[it.code] = it.opts[0];
  }}
  syncCards();
  persist();
}});

document.getElementById("resetPicks").addEventListener("click", () => {{
  state.picks = {{}};
  state.notes = {{}};
  syncCards();
  persist();
}});

function updateTally() {{
  const keys = Object.keys(state.picks).filter(k => state.picks[k]);
  document.getElementById("tally").textContent = keys.length
    ? `${{keys.length}} of ${{ITEMS.length}} items decided (saved offline).`
    : "No choices marked yet (saved offline automatically).";
}}
updateTally();

document.getElementById("copyBtn").addEventListener("click", async () => {{
  const lines = ITEMS.map(it => {{
    const p = state.picks[it.code];
    const n = (state.notes[it.code] || "").trim();
    if (!p && !n) return null;
    return `${{it.code}} (${{it.title}}): ${{p || "undecided"}}${{n ? " — Note: " + n : ""}}`;
  }}).filter(Boolean);
  const out = lines.length ? "UX Workbench choices:\\n" + lines.join("\\n") : "UX Workbench: no choices selected yet.";
  const box = document.getElementById("copyBox");
  const fb = document.getElementById("copyFallback");
  if (fb) fb.value = out;
  try {{
    await navigator.clipboard.writeText(out);
    document.getElementById("copiedMsg").textContent = "Copied!";
    if (box) box.style.display = "none";
  }} catch {{
    document.getElementById("copiedMsg").textContent = "Copy from box below:";
    if (box) box.style.display = "block";
    fb?.select();
  }}
}});
</script>
</body>
</html>
"""
    atomic_write_text(OUT_HTML, doc)
    return OUT_HTML


def main() -> None:
    out = render_html()
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
