# Human-Centered UX Optimization — Parked State & Offline Handover (2026-11-25)

## 1. Safety & Repository State ("Nothing Killed")
* **Tracked files modified or deleted:** `0` (`git status` on `m0-m1/vertical-slice` has zero modified tracked files).
* **Automated health verified:** `159/159` unit tests pass (`uv run pytest -q`), and your latest whole-book report (`verify/reports/latest.json`) stands at **22/22 PASS, 0 DEFER, 0 FAIL**.
* **Cloud workflow status:** Stopped cleanly before going offline. Layer 1's browser/corpus measurements are saved on disk, and the full 5-layer workflow script is parked ready to re-run whenever you are back online.
* **T3 Code folder note:** When this project was created in T3 Code, T3 pointed its default folder to an empty stub (`C:\Users\Grood\.t3\projects\the-anatomy-of-melancholy`). Your real edition lives intact at `C:\Users\Grood\Melancholy`.

---

## 2. What Layer 1 Already Found (Real Browser Measurements on `site/private`)

Full raw measurements are saved in `state/review/human-ux-audit-2026-11-25.json` and screenshots in `state/review/ux-shots-2026-11-25/`.

### Tier 1 — Silent Viewport & Interaction Blind Spots (No Aesthetic Changes Needed)
1. **F1 · Front page breaks its "one screen, no scrollbars" rule on 16:10 laptops (`1440×900`, `1280×800`)**
   * **What happens:** On `1920×1080`, `1536×864`, `1366×768`, and `1280×720` (16:9 screens), the front page fits on one screen as intended. On `1440×900` (MacBook / 14" laptop) and `1280×800`, the taller screen makes the full-height frontispiece engraving wider (`526 px`), squeezing `.front-side` just below `@container front-side (width < 39em)` in `edition.css:947`. That collapses the right side into 1 column, pushing **Synopses** and **Contents** `220 px` off the bottom of the screen while leaving `202 px` of blank paper on the right.
   * **Clean fix:** Adjust `.front-side` container threshold / `--fcol` proportion on `60rem+` viewports so 16:10 laptops keep the two-column layout and fit one screen with zero scrollbars.

2. **F2 · Clicking a citation on an Author page lands in the wrong place on wide screens (`>= 1100 px`)**
   * **What happens:** Every author page links to sidenotes like `/3.2.3.1/#3.2.3.1-n5`. On load, the browser scrolls to `#3.2.3.1-n5` *before* `edition.js` runs `layoutNotes()`. One frame later, `layoutNotes()` switches notes to `position: absolute`, moving the note **out of the viewport** (`inViewport: false`) and leaving neither the note nor Burton's words highlighted (`isHotOrPinned: false`).
   * **Clean fix:** After `layoutNotes()` settles on load/hashchange, check `location.hash`: if it targets a sidenote, margin card, or foreign passage, scroll its anchor smoothly into view and call `pin(note)` (or open its popover on narrow screens) so both the note and Burton's words light up immediately.

3. **F3 · Touch, tablet & half-screen (`< 1100 px`) annotation gaps**
   * **Inline citations (`§`) do nothing on tap or keyboard (`3.2.3.1` has 18 of them):** `.ic-m` is an unfocusable `<span>` (`tabIndex: -1`) and tapping it opens no popover (`inlineCiteTapOpensPopover: false`).
   * **Gowland's 3,907 notes vanish below `1100 px`:** On `3.2.3.1`, 252 of 253 Gowland notes have no visible underline or marker below `1100 px`, so phone, iPad, and half-screen readers never know an explanation exists.
   * **Author links (`a.nm`) rip mobile readers out of their chapter:** Below `1100 px`, hover windows are disabled (`if (!t || !wide.matches) return`), so tapping *Avicenna* navigates straight to `/authors/avicenna/` instead of showing the quick identification card first.
   * **Frontispiece panels on touch:** Tapping a panel on an iPad/phone navigates immediately to `argument/` instead of showing its stanza + glosses on the front page first (first tap = preview stanza, tap link = open Argument).

4. **F4 · Small polish blemishes caught in CSS/templates**
   * **Print stylesheet at `>= 1380 px`:** `.two-side .unit` adds a wide `margin-left` that `@media print` (`edition.css:649`) forgets to reset (`margin-left: 0 !important`).
   * **Shortened note highlight corner (`edition.css:1126`):** `.mn-fold.hot > .fold-more` fades to `var(--paper)` instead of blending with the warm gold `--hot` highlight.
   * **Front-page `Aa` Reading Options panel:** Has no "Restore defaults" button (unlike `/settings/`) and shows almost no visual change when clicked on the front page because `.opt-sample` is hidden there.

---

## 3. Tier 2 — Intuitive Reading & Scholarly Ergonomics (For Human Habits)

1. **E1 · Quiet Reading-Place Memory ("Where I Left Off")**
   * *Democritus Junior to the Reader* (`djr`) is **64,162 words (~141 screens, ~5 hours of reading)**, and **44 subsections exceed 5,000 words**. Right now, closing the tab or following a link loses your place completely.
   * *Proposal:* Save `{unit, paragraphId}` quietly in `localStorage` as you read. Show a single, unobtrusive rubric line or ribbon ("Continue at *Democritus Junior*, ¶84 →") when returning—invisible in "As printed" mode, zero clutter.

2. **E2 · Scholarly Locus & Permanent Deep-Link Copier**
   * All **2,476 paragraphs**, **5,703 sidenotes**, and **7,865 foreign passages** already have permanent IDs (`#3.2.3.1-p35`), and Penguin page breaks (`#pg-714`) sit right in the text—yet a human reader has no way to copy a paragraph link or a standard scholarly citation (`Burton, Anatomy of Melancholy, Part. 3, Sect. 2, Memb. 3, Subsect. 1 [p. 714]`).
   * *Proposal:* On hovering/focusing a paragraph or pinned note, reveal a whisper-faint pilcrow/locus action that copies either the deep link or the formatted scholarly citation.

3. **E3 · Instant Finder & Sort on *Authors Cited* (253) and *The Table* (574)**
   * *Authors cited* is alphabetical only—a reader cannot sort by **most-cited authorities** (Galen, Seneca, Hippocrates, Augustine…), filter by field (physicians, poets, theologians), or type an abbreviation (*Tully*, *Austin*) to see who Burton means.
   * *The Table* has 574 entries across 24 letters with no sticky `A · B · C … Z` rubric jump strip or instant word filter.

---

## 4. Tier 3 — Unconsidered Burtonian Visions & Use-Functions

1. **V1 · A Personal Commonplace Book (`localStorage`, 100% Offline & Private)**
   * Burton built *The Anatomy* out of his own commonplace notebooks. Readers naturally want to save remedies, Latin aphorisms, and favorite passages as they wander.
   * *Vision:* A quiet period mark (`☞` or ribbon) on any pinned passage/note saves it locally to **My Commonplace Book** (accessible from the tools/footer, exportable as clean Markdown or plain text with full Burton citations and translations, zero server needed).

2. **V2 · Ways into the Labyrinth: Famous Digressions, Cures & *Sortes Burtonianae***
   * Historically, people rarely read Burton strictly from page 1 to page 1,000—Samuel Johnson, Keats, Lamb, and Borges dipped into the great set-pieces (*Digression of Air* `2.2.3.1`, *Misery of Scholars* `1.2.3.15`, *Nature of Spirits* `1.2.1.2`, *Love-Melancholy* `3.2.3.1`, *Remedies for Discontents* `2.3.1.1`) or opened the book at random (*Sortes Burtonianae*).
   * *Vision:* A compact, folded rubric drawer or index of **Landmarks & Digressions** plus **"Open at a notable leaf"**—giving newcomers and browsers curated doors into Burton's best writing without touching the one-screen front-page balance.

3. **V3 · Long-Unit Discourse Compass (For Monster Chapters like `djr`)**
   * For units over ~5,000 words (`djr`, `3.2.3.1`, `2.2.3.1`), hovering/clicking the top-left location badge can show Burton's internal topic movements or marginal-note clusters so a reader isn't flying blind down a 141-screen scroll.

---

## 5. How to Browse & Decide Offline Right Now

1. **View your edition offline as usual:** Double-click `View the edition.cmd` in `C:\Users\Grood\Melancholy`.
2. **Open the Interactive UX Review Workbench offline:**
   * Double-click `C:\Users\Grood\Melancholy\state\review\human-ux-2026-11-25.html` directly in your browser (or serve the repo on port `8790` with `uv run python -m http.server 8790 --bind 127.0.0.1` and open `http://127.0.0.1:8790/state/review/human-ux-2026-11-25.html` so it loads the exact subsetted EB Garamond WOFF2 fonts from `site/private`).
   * Click through the live mini-prototypes, pick **Accept / Variant / Skip** on any item, add notes, and click **"Copy my choices"**—your picks save automatically in your browser's `localStorage` even offline!
3. **When you reconnect to the internet:**
   * Paste your copied choices into chat to build only what you want, **or** ask me to re-run the full 5-layer multi-agent workflow (`tools/human_ux_workflow/workflow.py`) over any specific area you want explored deeper.
