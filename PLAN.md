# PLAN — milestones

Every milestone ends with `burton check` passing for its scope, and with a short report of **counts** committed to `verify/reports/`.
Each milestone's exit criteria are the definition of done.
Decisions **[D#]** are listed at the end. D2–D6 and D9 are decided; D1, D7 and D8 are still open but do not block M0 or M1.

---

## Status (2026-10-20)

**M0 done.**
* EPUB pinned in `data/source/SOURCE.lock` (sha256 `a0e3641f…`).
* The independent counter reproduces SURVEY: 5,703 sidenote refs and bodies, 3,907 endnotes, 959 page markers, 149 nav units. 3 of the sidenote refs, 3 of the endnote refs and 3 of the page markers sit on Gowland's translation pages.

**M1 done for 1.1.1.2** (`uv run burton check --unit 1.1.1.2`: all 14 checks PASS):
* V1: 614 words, 0 unexplained differences; 11/11 notes identical.
* V2: sidenotes 11/11, endnote anchors 6/6, page markers 2/2, paragraphs 4/4, verse lines 9/9, Greek characters 85/85.
* V3: 11/11 notes resolved, 25 unique ids.
* V4: 85/85 Greek characters tagged.
* V5 (rules only, gold sample of 77 items): precision 1.000, recall 0.700. The 3 misses are the Latin disease names *Scorbutum*, *Plica* and *Morbus Gallicus*; M2's model adjudication must catch them.
* V7: 7/7 passages translated and labelled, 4/4 self-translation selectors match, 0 stale.
* V2h/V3h: XML = HTML in both profiles; 22/22 note markers resolve.
* V4h: 198 Greek characters tagged.
* V6: 50 links, 0 broken. V8: 0 Gowland leaks. V9: glyph coverage 118/118 and 115/115. V10: 0 parse errors, 0 accessibility issues.
* Kill/resume test PASS (`verify/reports/m1-kill-resume.log`).

**Carried forward** (not done, with the milestone that takes each):
* **Offline/PWA install not verified.** The service worker is served correctly, but the app's browser pane refuses registration and quick headless attempts were inconclusive. → M3, with a Playwright test.
* EB Garamond lacks ℥, ℈ and the astrological signs. A fallback font is needed before units with recipes or synopses. → M3
* Gowland's endnote bodies are not ingested yet; only their anchors are. → M2 (private build)
* A note marker can end a line apart from the word it precedes. In interlinear mode a space can appear before a comma. → M3
* The model sometimes puts explanation inside a translation ("Curable (salutary)"). → prompt `tr-v2` in M4
* The gold sample is labelled by Claude and awaits your review (D7).

## M0 — Setup (short)
* Python 3.13 and uv are installed (D9). `git init`. Create the package skeleton and the `burton` CLI stub, plus ruff and pytest.
* `burton unpack`: copy the EPUB into `data/source/`, write `SOURCE.lock` (SHA-256), unzip to a gitignored work directory.
* Port the survey counts into `burton/verify/epub_counts.py`, the **independent** counter, with tests asserting SURVEY's numbers: 5,703 sidenotes, 3,907 endnotes, 959 page markers, 149 nav units.

**Exit:** `uv run pytest` is green, and the counter reproduces every SURVEY count.

## M1 — Vertical slice: one subsection end-to-end
**Unit: 1.1.1.2 "The Definition, Number, Division of diseases".**

It is small, and it exercises most of the known problems:
* an image-only title (`pg142.png`);
* Greek verse (Hesiod) with mixed elision marks;
* Latin with and without Gowland brackets;
* sidenotes, endnote anchors and page markers.

Steps:
1. Ingest: structure, inline conversion, Gowland separation, script tagging, Latin candidates (rules only), id registry → `data/text/1.1.1.2.xml`, validated by `schema/edition.rng`.
2. One machine translation per foreign passage, using the `claude -p` runner (D2) at small scale, to prove the ledger and resume logic. Kill the runner mid-run and resume it, as a test.
3. Minimal reader page:
   * EB Garamond;
   * sidenotes in the margin and as popovers;
   * the three language modes;
   * `lang` attributes;
   * light and dark themes;
   * served by `burton serve` and installable as an offline PWA (D5).
4. Checks V1–V4, V6–V8 for this unit, plus V9 for its code points.

**Exit:** all checks pass with printed counts; the page works offline after first load; killing and resuming the runner loses nothing.

## M2 — Full ingestion with verification
* All units and front matter. Reconcile 151 candidate units against the 149 nav entries in `structure-overrides.yaml`.
* Transcribe the 4 heading images. Record every SURVEY defect in `source-fixes.yaml` or `known-source-defects.yaml`.
* Language identification at full strength (lexicons, context, model adjudication of low-confidence segments via the runner). Build the **600-segment gold sample** [D7] and run V5.
* Explicit numeric cross-references (Part./Sect./Memb./Subsect.) resolved deterministically. Relative ones queued.
* Self-translation candidates flagged (signals only; verdicts come in M5).

**Exit:**
* V1 has zero unexplained differences across the whole book.
* V2/V3 pass for all units: 5,703/5,703 sidenotes; 3,907/3,907 endnote anchors (private).
* V4 has zero untagged Greek.
* V5 meets its targets: Latin P ≥ 0.98, R ≥ 0.97; Greek 1.00/1.00; boundaries ≥ 0.95.
* The report also gives the number of `foreign` passages by language. That number sizes M5.

## M3 — The reader
* All page types: home and frontispiece, front matter, DJR, partition landings, units, about, settings.
* Sidenote collision layout, prototyped on the densest unit (chosen by the M2 count of notes per 1,000 words).
* Font subsetting and the fallback-symbol font. Hyphenation test for `la` and `grc`, with the Pyphen fallback if needed.
* Navigation: breadcrumbs, previous/next, contents tree.
* Settings persistence and both themes.
* Accessibility: axe-core on 20 pages and a keyboard walk-through script.

**Exit:** V6, V9 and V10 pass on all pages. You review three representative pages and sign off on the typography.

## M4 — Translation pilot: 50 hard passages
* Choose 50 passages stratified across:
  * long prose quotations;
  * verse;
  * Greek;
  * suspected misquotations;
  * puns;
  * technical medical Latin;
  * apothecary recipes (`℞ … ℥ ß`);
  * partial self-translations;
  * Italian and French;
  * Chaucer (gloss only);
  * citation-only Latin in sidenotes.
* Run the real runner with both `claude-opus-5-5` and `claude-sonnet-5-5` (`--model`) [D8].
* Run Dell & Jordan-Smith alignment on the same passages: measure coverage and alignment accuracy, and find out what that edition did with the sidenotes.
* Tune the glossary and prompt (`tr-v1` → `tr-vN`). Measure time and reported usage per packet, and project how many sessions the full pass needs under your usage limits.
* You review all 50 using a rubric (accuracy, register, glossary use, honest attribution).

**Exit:**
* Rubric pass rate is agreed with you.
* Zero invented attributions in the 50.
* The self-translation verdict is correct on the pilot's self-translation items.
* A throughput projection is written down.

## M5 — Full translation pass
* Run the runner over every `foreign` passage, in sequential packets across as many sessions as the usage limits require.
* Self-translation verdicts for every flagged candidate.
* Dell & Jordan-Smith alignment across the whole book.
* Clear the review queue. Spot-check a random 2 % of results.

**Exit:** V7 has zero passages without a translation or verdict. Every machine record is labelled. The review queue is empty, or the remaining items are explicitly deferred with counts.

## M6 — Citation expansion and the author index
* `abbreviations.yaml`, the citation parser (with merging of fragmented italics), `Idem`/`ibid.` resolution.
* Author registry: Wikidata matching for dates and ids. Identifications and "why Burton cites them" are drafted by the model, labelled `machine-draft`, and checked by you for the top 100 authors by citation count.
* Author pages and index.
* Source verifier against local public-domain classical corpora. Upgrade `probable` to `identified` only on a verified match.
* Relative cross-references: model proposals with evidence quotes, plus your review.

**Exit:**
* Every sidenote is `parsed`, `partial` or `unidentified`, with counts per status.
* Every author link resolves.
* Zero `identified` sources without a verifier basis.

## M7 — Synopses
* Rebuild the three trees from the 20 images, using the hidden text as the word-level checklist.
* Link the "See ♈" cross-keys. Link every node to its unit and back.
* Collapsible accessible tree UI (nested disclosure buttons; brace styling in CSS).

**Exit:** V11 passes: every one of the 561 non-glyph hidden-text strings is used exactly once (duplicates explained), and every node label resolves to a unit.

## M8 — Polish
* Obsolete-word glosses layer (off by default): Gowland where he glosses (private build), then Webster 1913, then labelled model drafts (D6).
* Burton's *Table* (the alphabetical index of 1624). Its locators point to Penguin pages, so whether it can be linked depends on the page markers [D1].
* Frontispiece with clickable panels tied to the *Argument* stanzas.
* Full-text search (index loaded on demand, precached for offline use).
* Print stylesheet and performance pass.
* Full-site axe run and an "About this edition" page.
* (Deferred by D4: restoring pruned sidenotes.)

**Exit:** V1–V11 pass on the whole site in the chosen profile(s).

---

## Decisions

### Decided (2026-10-20)

| # | Decision | Effect |
|---|---|---|
| D2 | **No API key.** | The translation runner drives `claude -p` headless as a subprocess under your subscription: tools disabled, `--json-schema` output, sequential packets. It stops cleanly on usage limits and resumes from the ledger (SPEC §6.4) |
| D3 | **Gowland's modernized text is the base.** | No old-spelling layer |
| D4 | **Pruned sidenotes are not restored for now.** | Sidenote counts are checked against the EPUB only |
| D5 | **A local server or installed app is enough.** | `burton serve` plus a PWA with a service worker for offline use. No `file://` constraints (SPEC §7.5) |
| D6 | **Obsolete-word glosses at my discretion.** | Gowland's endnote glosses where he gives one (private build only), then Webster 1913 (public domain), then labelled model drafts. Wiktionary may be consulted, never copied (SPEC §4.2) |
| D9 | **Tools installed.** | Python 3.13.15 (via `py`), uv 0.13.1, git 2.56, Node 24, Claude Code 2.1.304. Bare `python` is the Store stub, so always use `uv run` |

### Still open (none blocks M0 or M1)

**D1 — Private or public?** This decides the rights model (SPEC §2). The EPUB is © Penguin.
* Its bracketed translations, braces, endnotes and introduction are Gowland's copyrighted editorial work.
* Even the base text is his edited, modernized text.
* Using Gowland's glosses (D6) already ties the gloss layer to the private build.
* **Working assumption until you say otherwise:** build the **private profile** only, keep the public filter and its leak check in place, and push to no remote.
* Answer when publishing becomes a question. If you then want a private GitHub remote, say so.

**D7 — Gold-sample labelling (needed by M2).** I draft labels for 600 segments. Will you review all of them, or a random 25 % audit (passing only if zero disagreements, otherwise a full review)?

**D8 — Model for the full pass (needed after M4).** The default is `claude-opus-5-5`. The pilot also runs `claude-sonnet-5-5` on the same 50 passages, so you can choose on measured quality and usage-limit consumption.
