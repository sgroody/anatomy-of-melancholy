"""Build the Round 11 visual A/B workbench (Sortes placement & gloss palette): state/review/ab-2026-11-26-r11.html."""
# ruff: noqa: E501

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "state" / "review" / "ab-2026-11-26-r11.html"

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>Round 11 Visual A/B: Sortes Placement &amp; Gloss Colors · The Anatomy of Melancholy</title>
<style>
@font-face { font-family: "EBG"; src: url("../../site/private/assets/fonts/EBGaramond-Roman.woff2") format("woff2"); font-style: normal; font-weight: 400 800; font-display: swap; }
@font-face { font-family: "EBG"; src: url("../../site/private/assets/fonts/EBGaramond-Italic.woff2") format("woff2"); font-style: italic; font-weight: 400 800; font-display: swap; }

:root {
  --paper: #f7f3ea; --ink: #23201b; --muted: #645c51; --rule: #d9d0bf;
  --accent: #8a2f1d; --la: #7a2230; --k-cite: #2a55a8; --k-expl: #8a2f9a;
  --panel: #efe9dc; --card: #fbf8f1; --ok: #2e5e3e;
  color-scheme: light;
}
:root[data-theme="dark"] {
  --paper: #1c1a17; --ink: #e8e1d3; --muted: #a89e8e; --rule: #3a352e;
  --accent: #e5927a; --la: #e0c27a; --k-cite: #9fb0d4; --k-expl: #c3a3d6;
  --panel: #25221d; --card: #221f1b; --ok: #8cc9a3;
  color-scheme: dark;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--paper); color: var(--ink);
  font-family: "EBG", "EB Garamond", Georgia, serif; font-size: 1.06rem; line-height: 1.48;
  font-variant-numeric: oldstyle-nums proportional-nums;
}
.wrap { max-width: 78rem; margin: 0 auto; padding: 1.3rem 1.2rem 7rem; }
header.top {
  display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 0.8rem;
  border-bottom: 1px solid var(--rule); padding-bottom: 0.75rem; margin-bottom: 1rem;
}
h1 { font-weight: 400; font-size: 1.65rem; margin: 0; letter-spacing: 0.02em; }
.sub { color: var(--muted); font-style: italic; margin: 0.15rem 0 0; }
button {
  font: inherit; font-size: 0.92rem; background: var(--panel); color: var(--ink);
  border: 1px solid var(--rule); border-radius: 4px; padding: 0.22rem 0.7rem; cursor: pointer;
}
button:hover { border-color: var(--accent); }
button[aria-pressed="true"] { background: var(--accent); color: var(--paper); border-color: var(--accent); }

.sec-h {
  display: flex; align-items: center; gap: 0.75rem; margin: 2rem 0 0.4rem;
  font-weight: 400; font-size: 1.22rem; font-variant-caps: all-small-caps; letter-spacing: 0.09em; color: var(--accent);
}
.sec-h::after { content: ""; flex: 1; height: 1px; background: var(--rule); }
.sec-desc { margin: 0 0 0.85rem; color: var(--muted); font-size: 0.96rem; max-width: 64rem; }

.ab-grid { display: grid; gap: 0.95rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 24rem), 1fr)); }
.ab-grid.two { grid-template-columns: repeat(auto-fit, minmax(min(100%, 31rem), 1fr)); }
.card {
  background: var(--card); border: 1px solid var(--rule); border-radius: 6px; padding: 0.85rem 1rem;
  display: flex; flex-direction: column; min-width: 0;
}
.card.picked { border-color: var(--accent); box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent); }
.card-h { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; margin-bottom: 0.35rem; }
.tag { font-variant-caps: all-small-caps; letter-spacing: 0.08em; color: var(--accent); font-weight: 600; }
.rec-badge {
  font-size: 0.76rem; font-variant-caps: all-small-caps; letter-spacing: 0.06em;
  color: var(--ok); border: 1px solid color-mix(in srgb, var(--ok) 45%, transparent);
  padding: 0.02rem 0.4rem; border-radius: 3px;
}
.why { font-size: 0.92rem; color: var(--muted); margin: 0 0 0.6rem; }
.stage {
  background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
  padding: 0.75rem 0.85rem; margin: 0 0 0.7rem; flex: 1 1 auto;
}
.pick-row { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; margin-top: auto; padding-top: 0.35rem; }
.note-inp {
  flex: 1 1 12rem; min-width: 0; font: inherit; font-size: 0.88rem; padding: 0.2rem 0.5rem;
  background: transparent; color: var(--ink); border: 1px solid var(--rule); border-radius: 4px;
}

/* Sortes mockups */
.mock-col { max-width: 22rem; margin: 0 auto; font-size: 0.84rem; line-height: 1.36; }
.mock-box {
  border: 1px solid var(--rule); border-radius: 4px; padding: 0.55rem 0.78rem 0.45rem;
  background: color-mix(in srgb, var(--paper) 94%, var(--ink));
}
.mock-q { text-align: center; font-style: italic; font-size: 0.92em; padding-bottom: 0.35rem; border-bottom: 1px solid var(--rule); margin-bottom: 0.4rem; }
.mock-q cite { display: block; font-style: normal; font-variant-caps: all-small-caps; letter-spacing: 0.06em; color: var(--muted); font-size: 0.9em; }
.mock-p { margin: 0 0 0.35rem; }
.mock-h { font-variant-caps: all-small-caps; letter-spacing: 0.09em; color: var(--accent); margin-right: 0.28em; }
.mock-foot { border-top: 1px solid var(--rule); padding-top: 0.35rem; margin-top: 0.35rem; color: var(--muted); font-size: 0.92em; }
.sortes-door {
  margin-top: 0.42rem; padding: 0.42rem 0.7rem; border: 1px solid var(--rule); border-radius: 4px;
  background: color-mix(in srgb, var(--accent) 4%, var(--paper)); text-align: center;
}
.sortes-ruled {
  margin-top: 0.5rem; padding: 0.36rem 0; border-top: 1px solid var(--accent); border-bottom: 1px solid var(--accent);
  text-align: center;
}
.sortes-inline {
  margin-top: 0.48rem; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.4rem 0.65rem;
  padding: 0.35rem 0.55rem; border: 1px dotted var(--rule); border-radius: 4px;
}
.sbtn {
  display: inline-block; border: 1.5px solid var(--accent); border-radius: 4px; padding: 0.32rem 1.25rem;
  font-variant-caps: all-small-caps; letter-spacing: 0.09em; color: var(--accent); font-size: 1.12em;
  background: color-mix(in srgb, var(--accent) 6%, transparent); cursor: pointer;
}
.sbtn-fill { background: var(--accent); color: var(--paper); border-color: var(--accent); padding: 0.25rem 0.95rem; font-size: 1.05em; }
.ssub { margin: 0.2rem 0 0; font-style: italic; font-size: 0.88em; color: var(--muted); white-space: nowrap; }

/* Gloss color dual Light + Dark specimens */
.dual-spec { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; }
@media (max-width: 34rem) { .dual-spec { grid-template-columns: 1fr; } }
.spec-half {
  border-radius: 4px; padding: 0.6rem 0.7rem; font-size: 0.84rem; line-height: 1.38;
  border: 1px solid;
}
.spec-light { background: #f7f3ea; color: #23201b; border-color: #d9d0bf; --s-la: #7a2230; --s-exp: #8a2f9a; --s-cit: #2a55a8; --s-acc: #8a2f1d; --s-mut: #645c51; --s-rule: #d9d0bf; }
.spec-dark { background: #1c1a17; color: #e8e1d3; border-color: #3a352e; --s-la: #e0c27a; --s-exp: #c3a3d6; --s-cit: #9fb0d4; --s-acc: #e5927a; --s-mut: #a89e8e; --s-rule: #3a352e; }
.spec-cap { display: flex; justify-content: space-between; font-variant-caps: all-small-caps; letter-spacing: 0.06em; font-size: 0.84em; color: var(--s-mut); border-bottom: 1px solid var(--s-rule); padding-bottom: 0.2rem; margin-bottom: 0.45rem; }
.spec-la { color: var(--s-la); font-style: italic; }
.spec-m-tr { border-left: 1.5px dotted var(--s-la); padding-left: 0.4rem; color: var(--s-la); margin: 0.35rem 0; font-size: 0.92em; }
.spec-m-exp { margin: 0.35rem 0; font-size: 0.92em; }
.spec-m-exp i { color: var(--s-exp); }
.spec-m-gl { margin: 0.35rem 0; font-size: 0.92em; }
.spec-m-gl i { color: var(--s-gl); }
.spec-term { text-decoration: underline dotted var(--s-gl); text-decoration-thickness: 1.5px; text-underline-offset: 0.2em; }
.swatch-bar { display: flex; gap: 0.6rem; align-items: center; margin-top: 0.4rem; font-size: 0.8em; color: var(--s-mut); font-family: ui-monospace, monospace; }
.sw { display: inline-block; width: 0.72rem; height: 0.72rem; border-radius: 50%; vertical-align: -1px; margin-right: 0.22rem; border: 1px solid var(--s-rule); }

.tray {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 40;
  background: var(--panel); border-top: 1px solid var(--rule); padding: 0.55rem 1.2rem;
  display: flex; flex-wrap: wrap; gap: 0.6rem 1rem; align-items: center; justify-content: space-between;
}
.copy-box { margin-top: 0.8rem; display: none; }
.copy-box textarea { width: 100%; height: 6.5rem; font: inherit; font-size: 0.86rem; background: var(--card); color: var(--ink); border: 1px solid var(--rule); border-radius: 4px; padding: 0.5rem; }
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div>
      <h1>Round 11 Visual A/B Workbench</h1>
      <p class="sub">Sortes Burtonianae placement &amp; gloss color alternatives against Latin in light and dark mode</p>
    </div>
    <div><button type="button" id="themeBtn">Light / Dark workbench</button></div>
  </header>

  <h2 class="sec-h">R11-A · Sortes Burtonianae Placement &amp; Look</h2>
  <p class="sec-desc">Comparing keeping <em>Sortes</em> inside the infobox vs. setting it right beneath the infobox so the infobox remains pure orientation and <em>Sortes</em> reads as a distinct literary doorway.</p>

  <div class="ab-grid two" data-group="Sortes Placement">
    <div class="card" data-opt="Current: Inside Infobox">
      <div class="card-h"><span class="tag">Current · Inside Infobox</span></div>
      <p class="why">Keeps everything inside one bordered rectangle; convenient, though competes slightly with the utility row at the foot.</p>
      <div class="stage">
        <div class="mock-col">
          <div class="mock-box">
            <div class="mock-q">“The best book ever written.” <cite>— Nicholas Lezard</cite></div>
            <p class="mock-p"><span class="mock-h">The Book</span> In 1621, an Oxford scholar…</p>
            <p class="mock-p"><span class="mock-h">The Reader</span> This edition keeps his prose unbroken…</p>
            <p class="mock-p" style="color:var(--accent);font-style:italic">Burton read everything. Now you can read him.</p>
            <p class="mock-p" style="font-size:0.86em;color:var(--muted)">KEY · Latin Greek · § citation · a Burton’s note · + How a page looks</p>
            <div style="border-top:1px dotted var(--rule);padding-top:0.42rem;margin-top:0.35rem;text-align:center">
              <span class="sbtn">Sortes Burtonianae ☞</span>
              <p class="ssub">A page at random; take it as counsel</p>
            </div>
            <div class="mock-foot">⌕ · Aa · ☾ · About · Sources · Glossary · Index</div>
          </div>
        </div>
      </div>
      <div class="pick-row"><button type="button" class="pick-btn" aria-pressed="false">Pick Current</button><input class="note-inp" type="text" placeholder="Optional note…"></div>
    </div>

    <div class="card" data-opt="Option A: Standalone Companion Card Under Infobox">
      <div class="card-h"><span class="tag">Option A · Companion Card Under Infobox</span><span class="rec-badge">Recommended</span></div>
      <p class="why">Infobox ends cleanly on the search/links footer; Sortes sits immediately underneath in its own lightly rubric-tinted invitation card, balancing the bottom of Florilegium/Contents on the left.</p>
      <div class="stage">
        <div class="mock-col">
          <div class="mock-box">
            <div class="mock-q">“The best book ever written.” <cite>— Nicholas Lezard</cite></div>
            <p class="mock-p"><span class="mock-h">The Book</span> In 1621, an Oxford scholar…</p>
            <p class="mock-p"><span class="mock-h">The Reader</span> This edition keeps his prose unbroken…</p>
            <p class="mock-p" style="color:var(--accent);font-style:italic">Burton read everything. Now you can read him.</p>
            <p class="mock-p" style="font-size:0.86em;color:var(--muted)">KEY · Latin Greek · § citation · a Burton’s note · + How a page looks</p>
            <div class="mock-foot">⌕ · Aa · ☾ · About · Sources · Glossary · Index</div>
          </div>
          <div class="sortes-door">
            <span class="sbtn">Sortes Burtonianae ☞</span>
            <p class="ssub">A page at random; take it as counsel</p>
          </div>
        </div>
      </div>
      <div class="pick-row"><button type="button" class="pick-btn" aria-pressed="false">Pick Option A</button><input class="note-inp" type="text" placeholder="Optional note…"></div>
    </div>

    <div class="card" data-opt="Option B: Ruled Printer Doorway Under Infobox">
      <div class="card-h"><span class="tag">Option B · Ruled Doorway Under Infobox</span></div>
      <p class="why">Echoes <i>Enter, gentle Reader ☞</i> across the right column with top-and-bottom rubric rules and no extra outer box border.</p>
      <div class="stage">
        <div class="mock-col">
          <div class="mock-box">
            <div class="mock-q">“The best book ever written.” <cite>— Nicholas Lezard</cite></div>
            <p class="mock-p"><span class="mock-h">The Book</span> In 1621, an Oxford scholar…</p>
            <p class="mock-p"><span class="mock-h">The Reader</span> This edition keeps his prose unbroken…</p>
            <p class="mock-p" style="color:var(--accent);font-style:italic">Burton read everything. Now you can read him.</p>
            <div class="mock-foot">⌕ · Aa · ☾ · About · Sources · Glossary · Index</div>
          </div>
          <div class="sortes-ruled">
            <span style="color:var(--accent);font-size:1.15em;letter-spacing:0.06em;cursor:pointer">Sortes Burtonianae ☞</span>
            <p class="ssub">A page at random; take it as counsel</p>
          </div>
        </div>
      </div>
      <div class="pick-row"><button type="button" class="pick-btn" aria-pressed="false">Pick Option B</button><input class="note-inp" type="text" placeholder="Optional note…"></div>
    </div>

    <div class="card" data-opt="Option C: Filled Accent Button + Side Caption Under Infobox">
      <div class="card-h"><span class="tag">Option C · Filled Button + Side Caption</span></div>
      <p class="why">Solid oxblood CTA for unmistakable visual weight under the infobox, paired beside the single-line counsel note.</p>
      <div class="stage">
        <div class="mock-col" style="max-width:25rem">
          <div class="mock-box">
            <div class="mock-q">“The best book ever written.” <cite>— Nicholas Lezard</cite></div>
            <p class="mock-p"><span class="mock-h">The Book</span> In 1621, an Oxford scholar…</p>
            <p class="mock-p"><span class="mock-h">The Reader</span> This edition keeps his prose unbroken…</p>
            <div class="mock-foot">⌕ · Aa · ☾ · About · Sources · Glossary · Index</div>
          </div>
          <div class="sortes-inline">
            <span class="sbtn sbtn-fill">Sortes Burtonianae ☞</span>
            <span class="ssub" style="margin:0">A page at random; take it as counsel</span>
          </div>
        </div>
      </div>
      <div class="pick-row"><button type="button" class="pick-btn" aria-pressed="false">Pick Option C</button><input class="note-inp" type="text" placeholder="Optional note…"></div>
    </div>
  </div>

  <h2 class="sec-h">R11-B · Gloss Colour vs. Latin Colour (Light &amp; Dark on 2.2.3.1)</h2>
  <p class="sec-desc">In dark mode right now, Latin is warm gold (<code>#e0c27a</code>) and Gloss is amber-gold (<code>#e2b45c</code>) — nearly identical to the eye. Each candidate below shows <b>Paper</b> and <b>Candlelit</b> together on <i>2.2.3.1</i> alongside Explanatory purple and Citation blue.</p>

  <div class="ab-grid two" data-group="Gloss Color Palette">
    <div class="card" data-opt="Current: Amber #a04f00 / Gold #e2b45c">
      <div class="card-h"><span class="tag">Current · Burnt Amber / Warm Gold</span></div>
      <p class="why">Dark-mode gloss (<code>#e2b45c</code>) barely separates from Latin (<code>#e0c27a</code>): compare <i>amain</i>/<i>stoops</i> against <i style="color:#e0c27a">obiter</i> and <i style="color:#e0c27a">in passing</i>.</p>
      <div class="stage">
        <div class="dual-spec">
          <div class="spec-half spec-light" style="--s-gl:#a04f00">
            <div class="spec-cap"><span>Paper (Light)</span><span>Latin #7a2230 vs Gloss #a04f00</span></div>
            <p style="margin:0 0 0.35rem">… meet <span class="spec-la">obiter</span> with Elias Artifex … <span class="spec-la">Vel situs in vena terrae</span>, as Agricola … comes down <span style="border-bottom:1px dotted #645c51">amain</span>, and <span style="border-bottom:1px dotted #645c51">stoops</span> …</p>
            <p class="spec-m-exp"><i>wandering Jew</i> — Three mythical itinerants…</p>
            <p class="spec-m-tr">in passing <span style="font-size:0.8em;color:var(--s-mut)">g</span></p>
            <p class="spec-m-gl"><i>amain</i> — At full speed, or full force. (<span class="spec-term">terra</span>)</p>
            <p class="spec-m-gl"><i>stoops</i> — Swoops.</p>
          </div>
          <div class="spec-half spec-dark" style="--s-gl:#e2b45c">
            <div class="spec-cap"><span>Candlelit (Dark)</span><span>Latin #e0c27a vs Gloss #e2b45c</span></div>
            <p style="margin:0 0 0.35rem">… meet <span class="spec-la">obiter</span> with Elias Artifex … <span class="spec-la">Vel situs in vena terrae</span>, as Agricola … comes down <span style="border-bottom:1px dotted #a89e8e">amain</span>, and <span style="border-bottom:1px dotted #a89e8e">stoops</span> …</p>
            <p class="spec-m-exp"><i>wandering Jew</i> — Three mythical itinerants…</p>
            <p class="spec-m-tr">in passing <span style="font-size:0.8em;color:var(--s-mut)">g</span></p>
            <p class="spec-m-gl"><i>amain</i> — At full speed, or full force. (<span class="spec-term">terra</span>)</p>
            <p class="spec-m-gl"><i>stoops</i> — Swoops.</p>
          </div>
        </div>
      </div>
      <div class="pick-row"><button type="button" class="pick-btn" aria-pressed="false">Keep Current</button><input class="note-inp" type="text" placeholder="Optional note…"></div>
    </div>

    <div class="card" data-opt="Option A: Apothecary Verdigris #1f6657 / Seafoam Teal #7ecab8">
      <div class="card-h"><span class="tag">Option A · Apothecary Verdigris / Seafoam Teal</span><span class="rec-badge">Recommended</span></div>
      <p class="why">Crisp botanical teal in light (<code>#1f6657</code>, 6.1:1) and cool seafoam in dark (<code>#7ecab8</code>, 9.3:1). Unmistakably different from oxblood/gold Latin, citation blue, and explanatory purple.</p>
      <div class="stage">
        <div class="dual-spec">
          <div class="spec-half spec-light" style="--s-gl:#1f6657">
            <div class="spec-cap"><span>Paper (Light)</span><span>#1f6657 (6.1:1)</span></div>
            <p style="margin:0 0 0.35rem">… meet <span class="spec-la">obiter</span> with Elias Artifex … <span class="spec-la">Vel situs in vena terrae</span>, as Agricola … comes down <span style="border-bottom:1px dotted #1f6657">amain</span>, and <span style="border-bottom:1px dotted #1f6657">stoops</span> …</p>
            <p class="spec-m-exp"><i>wandering Jew</i> — Three mythical itinerants…</p>
            <p class="spec-m-tr">in passing <span style="font-size:0.8em;color:var(--s-mut)">g</span></p>
            <p class="spec-m-gl"><i>amain</i> — At full speed, or full force. (<span class="spec-term">terra</span>)</p>
            <p class="spec-m-gl"><i>stoops</i> — Swoops.</p>
          </div>
          <div class="spec-half spec-dark" style="--s-gl:#7ecab8">
            <div class="spec-cap"><span>Candlelit (Dark)</span><span>#7ecab8 (9.3:1)</span></div>
            <p style="margin:0 0 0.35rem">… meet <span class="spec-la">obiter</span> with Elias Artifex … <span class="spec-la">Vel situs in vena terrae</span>, as Agricola … comes down <span style="border-bottom:1px dotted #7ecab8">amain</span>, and <span style="border-bottom:1px dotted #7ecab8">stoops</span> …</p>
            <p class="spec-m-exp"><i>wandering Jew</i> — Three mythical itinerants…</p>
            <p class="spec-m-tr">in passing <span style="font-size:0.8em;color:var(--s-mut)">g</span></p>
            <p class="spec-m-gl"><i>amain</i> — At full speed, or full force. (<span class="spec-term">terra</span>)</p>
            <p class="spec-m-gl"><i>stoops</i> — Swoops.</p>
          </div>
        </div>
      </div>
      <div class="pick-row"><button type="button" class="pick-btn" aria-pressed="false">Pick Option A</button><input class="note-inp" type="text" placeholder="Optional note…"></div>
    </div>

    <div class="card" data-opt="Option B: Herbal Forest #2d6838 / Botanical Sage #93ce95">
      <div class="card-h"><span class="tag">Option B · Herbal Forest / Botanical Sage</span></div>
      <p class="why">True leafy green (<code>#2d6838</code>, 6.1:1 light / <code>#93ce95</code>, 9.7:1 dark). Warm-page friendly and furthest on the colour wheel from Oxblood and Crimson; note it also resembles the optional Sage Latin setting if chosen.</p>
      <div class="stage">
        <div class="dual-spec">
          <div class="spec-half spec-light" style="--s-gl:#2d6838">
            <div class="spec-cap"><span>Paper (Light)</span><span>#2d6838 (6.1:1)</span></div>
            <p style="margin:0 0 0.35rem">… meet <span class="spec-la">obiter</span> with Elias Artifex … <span class="spec-la">Vel situs in vena terrae</span>, as Agricola … comes down <span style="border-bottom:1px dotted #2d6838">amain</span>, and <span style="border-bottom:1px dotted #2d6838">stoops</span> …</p>
            <p class="spec-m-exp"><i>wandering Jew</i> — Three mythical itinerants…</p>
            <p class="spec-m-tr">in passing <span style="font-size:0.8em;color:var(--s-mut)">g</span></p>
            <p class="spec-m-gl"><i>amain</i> — At full speed, or full force. (<span class="spec-term">terra</span>)</p>
            <p class="spec-m-gl"><i>stoops</i> — Swoops.</p>
          </div>
          <div class="spec-half spec-dark" style="--s-gl:#93ce95">
            <div class="spec-cap"><span>Candlelit (Dark)</span><span>#93ce95 (9.7:1)</span></div>
            <p style="margin:0 0 0.35rem">… meet <span class="spec-la">obiter</span> with Elias Artifex … <span class="spec-la">Vel situs in vena terrae</span>, as Agricola … comes down <span style="border-bottom:1px dotted #93ce95">amain</span>, and <span style="border-bottom:1px dotted #93ce95">stoops</span> …</p>
            <p class="spec-m-exp"><i>wandering Jew</i> — Three mythical itinerants…</p>
            <p class="spec-m-tr">in passing <span style="font-size:0.8em;color:var(--s-mut)">g</span></p>
            <p class="spec-m-gl"><i>amain</i> — At full speed, or full force. (<span class="spec-term">terra</span>)</p>
            <p class="spec-m-gl"><i>stoops</i> — Swoops.</p>
          </div>
        </div>
      </div>
      <div class="pick-row"><button type="button" class="pick-btn" aria-pressed="false">Pick Option B</button><input class="note-inp" type="text" placeholder="Optional note…"></div>
    </div>

    <div class="card" data-opt="Option C: Peacock Teal-Blue #195e73 / Mineral Cyan #78c5d9">
      <div class="card-h"><span class="tag">Option C · Prussian Peacock / Mineral Cyan</span></div>
      <p class="why">Deep slate-cyan (<code>#195e73</code>, 6.5:1 / <code>#78c5d9</code>, 8.9:1). Totally immune to warm-gold collision in dark mode, though closer in hue to Citations (<code>#2a55a8</code> / <code>#9fb0d4</code>).</p>
      <div class="stage">
        <div class="dual-spec">
          <div class="spec-half spec-light" style="--s-gl:#195e73">
            <div class="spec-cap"><span>Paper (Light)</span><span>#195e73 (6.5:1)</span></div>
            <p style="margin:0 0 0.35rem">… meet <span class="spec-la">obiter</span> with Elias Artifex … <span class="spec-la">Vel situs in vena terrae</span>, as Agricola … comes down <span style="border-bottom:1px dotted #195e73">amain</span>, and <span style="border-bottom:1px dotted #195e73">stoops</span> …</p>
            <p class="spec-m-exp"><i>wandering Jew</i> — Three mythical itinerants…</p>
            <p class="spec-m-tr">in passing <span style="font-size:0.8em;color:var(--s-mut)">g</span></p>
            <p class="spec-m-gl"><i>amain</i> — At full speed, or full force. (<span class="spec-term">terra</span>)</p>
            <p class="spec-m-gl"><i>stoops</i> — Swoops.</p>
          </div>
          <div class="spec-half spec-dark" style="--s-gl:#78c5d9">
            <div class="spec-cap"><span>Candlelit (Dark)</span><span>#78c5d9 (8.9:1)</span></div>
            <p style="margin:0 0 0.35rem">… meet <span class="spec-la">obiter</span> with Elias Artifex … <span class="spec-la">Vel situs in vena terrae</span>, as Agricola … comes down <span style="border-bottom:1px dotted #78c5d9">amain</span>, and <span style="border-bottom:1px dotted #78c5d9">stoops</span> …</p>
            <p class="spec-m-exp"><i>wandering Jew</i> — Three mythical itinerants…</p>
            <p class="spec-m-tr">in passing <span style="font-size:0.8em;color:var(--s-mut)">g</span></p>
            <p class="spec-m-gl"><i>amain</i> — At full speed, or full force. (<span class="spec-term">terra</span>)</p>
            <p class="spec-m-gl"><i>stoops</i> — Swoops.</p>
          </div>
        </div>
      </div>
      <div class="pick-row"><button type="button" class="pick-btn" aria-pressed="false">Pick Option C</button><input class="note-inp" type="text" placeholder="Optional note…"></div>
    </div>

    <div class="card" data-opt="Option D: Antique Olive #576322 / Pale Celadon #b5c99a">
      <div class="card-h"><span class="tag">Option D · Antique Olive / Pale Celadon</span></div>
      <p class="why">Quiet manuscript moss-olive (<code>#576322</code>, 6.0:1 light / <code>#b5c99a</code>, 9.6:1 dark). Softer and cooler than warm gold, keeping the antique parchment mood while parting clearly from <code>#e0c27a</code>.</p>
      <div class="stage">
        <div class="dual-spec">
          <div class="spec-half spec-light" style="--s-gl:#576322">
            <div class="spec-cap"><span>Paper (Light)</span><span>#576322 (6.0:1)</span></div>
            <p style="margin:0 0 0.35rem">… meet <span class="spec-la">obiter</span> with Elias Artifex … <span class="spec-la">Vel situs in vena terrae</span>, as Agricola … comes down <span style="border-bottom:1px dotted #576322">amain</span>, and <span style="border-bottom:1px dotted #576322">stoops</span> …</p>
            <p class="spec-m-exp"><i>wandering Jew</i> — Three mythical itinerants…</p>
            <p class="spec-m-tr">in passing <span style="font-size:0.8em;color:var(--s-mut)">g</span></p>
            <p class="spec-m-gl"><i>amain</i> — At full speed, or full force. (<span class="spec-term">terra</span>)</p>
            <p class="spec-m-gl"><i>stoops</i> — Swoops.</p>
          </div>
          <div class="spec-half spec-dark" style="--s-gl:#b5c99a">
            <div class="spec-cap"><span>Candlelit (Dark)</span><span>#b5c99a (9.6:1)</span></div>
            <p style="margin:0 0 0.35rem">… meet <span class="spec-la">obiter</span> with Elias Artifex … <span class="spec-la">Vel situs in vena terrae</span>, as Agricola … comes down <span style="border-bottom:1px dotted #b5c99a">amain</span>, and <span style="border-bottom:1px dotted #b5c99a">stoops</span> …</p>
            <p class="spec-m-exp"><i>wandering Jew</i> — Three mythical itinerants…</p>
            <p class="spec-m-tr">in passing <span style="font-size:0.8em;color:var(--s-mut)">g</span></p>
            <p class="spec-m-gl"><i>amain</i> — At full speed, or full force. (<span class="spec-term">terra</span>)</p>
            <p class="spec-m-gl"><i>stoops</i> — Swoops.</p>
          </div>
        </div>
      </div>
      <div class="pick-row"><button type="button" class="pick-btn" aria-pressed="false">Pick Option D</button><input class="note-inp" type="text" placeholder="Optional note…"></div>
    </div>
  </div>
</div>

<div class="tray">
  <span id="summaryTxt">No choices picked yet — click any Pick button above.</span>
  <div>
    <button type="button" id="clearBtn">Clear</button>
    <button type="button" id="copyBtn">Copy Picks</button>
  </div>
</div>
<div class="wrap"><div class="copy-box" id="copyBox"><textarea id="copyArea" readonly></textarea></div></div>

<script>
const KEY = "burton-r11-choices";
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch {}
const saveState = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch {} };

document.getElementById("themeBtn").addEventListener("click", () => {
  const d = document.documentElement;
  d.dataset.theme = d.dataset.theme === "dark" ? "light" : "dark";
});

function renderSummary() {
  const keys = Object.keys(state).filter(
    (k) => state[k]?.opt || Object.values(state[k]?.notes || {}).some((v) => v.trim())
  );
  document.getElementById("summaryTxt").textContent = keys.length
    ? `${keys.length} group(s) picked`
    : "No choices picked yet — click any Pick button above.";
  document.querySelectorAll("[data-group]").forEach((grp) => {
    const g = grp.dataset.group, picked = state[g]?.opt;
    grp.querySelectorAll(".card").forEach((c) => {
      const hit = c.dataset.opt === picked;
      c.classList.toggle("picked", hit);
      c.querySelector(".pick-btn")?.setAttribute("aria-pressed", String(hit));
      const inp = c.querySelector(".note-inp");
      if (inp && state[g]?.notes?.[c.dataset.opt] != null && document.activeElement !== inp) {
        inp.value = state[g].notes[c.dataset.opt];
      }
    });
  });
}

document.querySelectorAll("[data-group]").forEach((grp) => {
  const g = grp.dataset.group;
  grp.querySelectorAll(".card").forEach((c) => {
    const opt = c.dataset.opt;
    c.querySelector(".pick-btn")?.addEventListener("click", () => {
      state[g] = state[g] || {};
      state[g].opt = state[g].opt === opt ? null : opt;
      saveState(); renderSummary();
    });
    c.querySelector(".note-inp")?.addEventListener("input", (e) => {
      state[g] = state[g] || {};
      state[g].notes = state[g].notes || {};
      state[g].notes[opt] = e.target.value;
      saveState(); renderSummary();
    });
  });
});

document.getElementById("clearBtn").addEventListener("click", () => { state = {}; saveState(); renderSummary(); });
document.getElementById("copyBtn").addEventListener("click", async () => {
  const lines = [];
  document.querySelectorAll("[data-group]").forEach((grp) => {
    const g = grp.dataset.group, st = state[g];
    if (!st) return;
    const notes = Object.entries(st.notes || {}).filter(([, v]) => v.trim()).map(([k, v]) => `${k}: ${v.trim()}`).join("; ");
    if (st.opt || notes) lines.push(`- ${g}: ${st.opt || "(no pick)"}${notes ? " — Notes: " + notes : ""}`);
  });
  const txt = lines.join("\n") || "No choices picked yet.";
  const box = document.getElementById("copyBox"), area = document.getElementById("copyArea");
  area.value = txt; box.style.display = "block";
  try { await navigator.clipboard.writeText(txt); document.getElementById("copyBtn").textContent = "Copied!"; } catch {}
});
renderSummary();
</script>
</body>
</html>
"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HTML, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT} ({len(HTML.encode('utf-8')):,} bytes)")


if __name__ == "__main__":
    main()
