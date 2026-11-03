# PLAN — milestones

Every milestone ends with `burton check` passing for its scope, and with a short report of **counts** committed to `verify/reports/`.
Each milestone's exit criteria are the definition of done.
Decisions **[D#]** are listed at the end. D1–D6 and D8–D11 are decided; D7 is still open.

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

**M2 done (2026-10-20), with the language-ID target deferred (D10).** `uv run burton verify --all` over 158 units (149 subsections and 9 front-matter pages):
* V1: 484,453 words, 0 unexplained differences; 5,703/5,703 sidenotes identical.
* V1f: 18/18 EPUB pages fully covered by their units.
* V2: sidenotes 5,703/5,703, endnote anchors 3,907/3,907, page markers 956/956, paragraphs 1,910/1,910, verse lines 5,006/5,006.
* V4: 1,080/1,080 script characters tagged.
* V3g: Gowland endnotes 3,907/3,907 identical, 0 orphans, 0 double references (1 recorded link fix).
* V7: passes. The 7,779 untranslated passages are a count for M5, not a failure. Self-translation layer: 7,786/7,786 records current, 8,421/8,421 candidate selectors match exactly once, 0 touch Gowland text.
* These counts are unchanged by the language-ID hardening below (re-checked after `ingest --all`).

Also in M2:
* 7,786 foreign passages after the hardening (7,775 before; 73 new passage ids, 88 retired, none renumbered).
* Cross-references: 19 resolved, 2 unresolved (a level missing), 160 citations of other books skipped.
* 1,025 model rulings on undecided language runs (`data/layers/langid-adjudication.json`, labelled).
* Self-translation candidates flagged (`burton selftrans`, rules only, SPEC §6.2; signals, not verdicts). Of the 7,785 foreign passages (after the bracket fix below):
  * Gowland bracket: none 2,850; present 4,902; short (under 0.8 × the passage's words) 33.
  * Candidate spans of Burton's English: next clause or sentence 4,008; preceding clause 2,812; text at a sidenote's anchor 1,332; Burton's English verse after a verse 270 (8,422 selectors). 5,977 passages have at least one candidate, including 2,246 of the 2,850 without a bracket.
  * Supporting signals: cognate overlap 704; gloss cue ("that is", "i.e.") 10.
  * Dropped and counted: 0 candidates touching unseparated Gowland brackets (5 before the bracket fix); 0 non-unique selectors. 2 passages nested in a longer passage get no prose candidates.
  * The 4 self-translations the M1 model found in 1.1.1.2 are all among the candidates, with the same span.
* Gowland brackets running over several blocks (2026-10-20). 6 brackets were left as plain text, each one translation over several paragraphs or stanzas (1.2.3.15, 3.1.1.1, 3.2.1.2, 3.2.2.1 prose with quoted verse between; 2.5.1.6, 3.4.2.3 verse, tagged as Burton's `translation-block`). General rules now separate them: a bracket over blocks is wrapped piece by piece (`ed:trans`/`ed:verse-trans` with `@part` I/M/F), and a bracketed verse run may span stanzas and end before punctuation. The 13 sidenotes anchored inside those runs are Gowland's English renderings of Burton's Latin sidenotes and go in with them (public build drops them; V2h counts accordingly). New check V8t: `public_text` of every unit has no `[ ] { }` (0 left; it reports all 12 on the old text). 1 passage id retired (3.2.2.1-f76, a title inside Gowland's translation).

**M2: the language-identification target is deferred (D10).** V5 still runs on the fresh hold-out and reports DEFER, not PASS:
* Hardening (2026-10-20), general rules only (SPEC §6.1): `&c.` is not the locator `c.`; author-and-title lists ("*Grotius de verit.*") are citations; `de` before a capital is a name particle; English runs split at sentence breaks; citation prefixes shed before a bracket; a bracket after the run's closing stop counts.
* Measured on a **new** held-out round h2 (300 items, seed 20261022, labelled blind before any scoring), against targets of 0.98 / 0.97 / 0.95:

  | h2 stratum | TP | FP | FN | precision | recall | boundary |
  |---|---|---|---|---|---|---|
  | italic (150) | 29 | 0 | 1 | 1.000 | 0.967 | 1.000 |
  | roman-before-bracket (50) | 35 | 1 | 2 | 0.972 | 0.946 | 0.971 |
  | sidenote (50) | 2 | 2 | 0 | 0.500 | 1.000 | 1.000 |
  | verse (25) | 13 | 0 | 0 | 1.000 | 1.000 | 0.923 |
  | English (25) | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 |
  | **total (300)** | **80** | **3** | **3** | **0.964** | **0.964** | **0.975** |

* **Below target** on precision and recall; boundary meets its target. The 6 errors:
  * 2 misses where Burton's italics stop short of the Latin: roman "in" before *secundis*, and roman "more" before *aquilae factum*. The italic part is tagged, but it covers under 75 % of the phrase.
  * 2 false positives from sidenote rules: *Ter.* (the lexicon knows *ter*), and *Vita ejus* (the sidenote-lexicon rule).
  * 1 false positive from a model ruling: *Magna Carta* was adjudicated "la title".
  * 1 miss with no model ruling: *Intestina*, left as a name.
* Seen samples (reported, not gated): tuning 0.995 / 0.984 / 0.967 (677 items); h1 1.000 / 1.000 / 0.979 (150 items, seen 2026-10-20).
* h2 has now been seen. Later (D10): fix those error types (absorb adjacent roman Latin into an italic run; treat a lone capitalised sidenote word before a stop as an abbreviation; re-adjudicate capitalised terms), then draw round h3. Do not tune on h2.
* All gold labels await your review (D7). h2 adds conventions to `data/eval/LABELLING.md`.

**M3 done (2026-10-20).** Checks pass, and you signed off the typography on the three review pages ("Looks decent, lets run with it"). `uv run burton check --all`, private and public builds of 158 units:
* Pages: home with frontispiece and contents, 9 front-matter pages (7 in public: Gowland's two translation pages are withheld), 3 Partition landings with the 20 synopsis sheets, 149 units, About this edition, Reading options. 164 pages private, 162 public.
* Navigation: breadcrumbs, previous/next with titles, a contents panel with the current unit marked. Settings (language mode, theme, type size, Gowland toggles) persist in `localStorage`; light and dark themes.
* V6: 326 pages, 69,070 links, 0 broken. V9: 203/203 glyphs private, 194/194 public; 13 come from the fallback face (Cardo, OFL): ⁂ ℈ ℥ ☉ ☌ ☾ ☿ ♀ ♂ ♃ ♄ ♎ ♏. V10: 326 pages, 0 parse errors, 0 static issues. V8: 0 leaks; V8t: 0 brackets left.
* V10a (axe-core 4.13.0): 20 pages × light and dark = 40 runs, 0 violations of any impact. V10k keyboard walk-through: 17/17 steps.
* L1 sidenote layout, prototyped on the densest unit 3.2.4.1 (25.2 notes per 1,000 words, 38 notes) and checked on 5 pages at 3 widths: 0 overlaps, maximum drift 13.4 rem (limit 14), 12 notes collapsed into "more notes" stacks; 0 of 11,028 markers on a different line from their word in the three modes at 4 widths.
* HY: Chrome 155 and Edge 155 hyphenate none of en, la or grc themselves, so the build adds soft hyphens inside la (Beccari's patterns, MIT) and grc (Pyphen el_GR) only: 47,505, 0 outside those spans.
* OFF: the service worker precaches 196/196 files; with the server stopped, 6/6 pages load with fonts and images.
* Carried-forward fixes: the marker/word break happened in interlinear mode (62 markers without the word joiner, 0 with); the interlinear comma gap is 0 px in all 64 measured cases.
* Found and fixed on the way: in "Read in English", passages with no translation yet (7,778) disappeared; they now keep the original.
* Typography signed off on (`uv run burton serve --profile private`): 3.2.4.1 (densest sidenotes, Latin) http://127.0.0.1:8765/3.2.4.1/ · 3.2.3.1 (744 verse lines) http://127.0.0.1:8765/3.2.3.1/ · djr (front matter) http://127.0.0.1:8765/djr/

**M4 done (2026-10-23): the owner accepted the pilot results, confirmed the 3 revised self-translation labels, and chose Opus for the full pass (D8).** Full report: `verify/reports/m4-pilot.md`; review page: `verify/reports/m4-review.html`.
* 50 passages in 11 strata (`data/eval/m4-pilot.yaml`, with the reason for each). The base text has only 3 Italian items and no French; the 3 Chaucer items are keyed by verse group because Chaucer is not tagged `enm`.
* Prompt `tr-v2`, glossary v2 (25 terms, 24 authorities). The new check that retries added parentheses fired 3 times; **0 of 94 final records** put explanation inside the translation.
* Both models ran through the real runner, 30 packets each, 0 invalid. Opus: 31 calls, 455.8 s, 636 output tokens per passage, $1.40 list-equivalent. Sonnet: 34 calls, 871.7 s (one packet took 618.5 s), 445 tokens per passage, $0.67. Both records are kept per passage, each labelled with its model.
* Self-translation, 12 gate items: Opus **12/12**, Sonnet 10/12. Three labels were revised after the runs, toward the models' answer, so you need to confirm them; as drafted, the scores are 11/12 and 9/12.
* Attributions, checked by hand: **0 invented** by either model (Opus 26 burton-cites, 5 probable; Sonnet 23 and 4). Misquotations: Opus flagged all 4 expected (and 5 more), Sonnet 0 of 4.
* Dell & Jordan-Smith: downloaded with your consent (`data/source/DJS.lock`).
  * Alignment (`burton align-djs`) gives 10 candidates (9 correct by hand) and 12 "omitted by them" (11 correct); 8 candidates are discarded. Coverage is 22/47, or 22/34 for passages in running text. These are tuning figures.
  * Sidenotes: their edition drops Burton's marginal notes, apart from a few folded into the text and some author names given in brackets or parentheses. So the Latin sidenotes have no human translation.
* Projection: the full pass (7,785 passages, 475 packets) is about $144 list-equivalent on Opus. That is roughly 6.5 five-hour windows, or 1–2 full weeks of your Pro allowance. Sonnet is about 3 windows. Calibrate on one unit in the first M5 session.
* Checks (2026-10-21), `uv run burton check --all`: 20 PASS, V5 DEFER (D10), 0 FAIL.
  * V7: 54 passages with records, 101 machine translations labelled, 74/74 Burton-span selectors, 0 stale; 3 gloss records, 28/28 gloss selectors.
  * V1: 0 unexplained differences. V6: 69,070 links, 0 broken. V8: 0 leaks. V10a: 40 axe runs, 0 violations. L1: 0 marker breaks.
  * Tests: pytest 59 passed (10 new in `tests/test_translate.py`); ruff clean.
  * The first run found 1 marker break in "Read in English" (djr-f7, a verse Burton translates himself, with a hoisted note). Fixed by drawing the ⁂ as a real character rather than CSS content.
  * V10a first failed only because `tests/browser/node_modules` was missing; installed with `npm ci`.

**M5 in progress (2026-10-23).** Session 1: the text fixes M4 found, runner hardening, calibration. The full run waits for the owner's usage budget (the weekly meter stood at 79 %).
* Text fixes (`ingest --all`; ids retired, never renumbered):
  * Chaucer: 83/83 `lucida` spans tagged `enm` (`resp="#rules"`, not passages). The 23 verse groups that hold them are queued as gloss-only items. The 1 inline quotation in prose (1.2.4.7) is not.
  * General rules: (1) a verse group whose italic Latin lines are followed by roman English lines is split, and the English becomes Burton's `translation-block`. 2 cases: 3.2.5.1-f47 → f61, and 1.2.3.15, whose three line passages became one verse passage, f281. (2) A verse group's italics decide its language only if they cover ≥ 75 % of its letters. That untags 4 English verses whose italics were Latin names (3.2.3.1-f166, f279, f306; 3.2.5.5-f145).
  * `blocks.yaml` gains `inline:` (phrase, whole block or verse group): Italian 3.3.2.1-f5 and 3.2.5.3-f163 (ids kept), French "à la mort" 1.3.1.4-f49, and the wholly Latin recipe paragraph 3.2.5.1-f62 (it replaces 13 fragments).
  * Foreign passages: 7,785 → 7,769 (20 retired, 4 new). The 2 pilot records whose ids were retired moved to `data/layers/retired/translations/3.2.5.1.json`; the two Italian records were re-translated.
* Runner: Chaucer gloss items in full runs; orphan records retired rather than deleted; a language change makes a record stale (runner and V7); `--budget-usd` (stop at a list-equivalent spend); `--wait-on-limit` (retry every 20 min instead of stopping); a hung call times out at 1,200 s and counts as failed (M4 follow-up).
* Calibration, unit 1.2.3.14 (`state/translate/meter.jsonl`): 95 passages, 5 packets, 0 retries, 0 invalid, $1.58 list-equivalent, 284 s, 331 output tokens per passage (pilot: 636; the pilot chose hard passages). Meter: 5-hour window 0 → 5 %, weekly 79 → 80 %.
* Projection for the rest (7,649 items): about **$127** list-equivalent; about **4 five-hour windows** (3.6–4.5); about 6.4 hours of model time; roughly 60–80 % of one week's allowance (range from the M4 ratio of 5–7 window points per weekly point; this run's weekly reading is too coarse to refine it). That is below the M4 estimate of 1–2 weeks.
* Queue: 7,792 items (7,769 passages + 23 Chaucer groups); 143 current, 7,649 to do, about 380 packets.

**M5 run, session 1 (2026-10-23/24), stopped by the owner's cap ("without going over 95 % of the weekly limit").** Four chunks with `--budget-usd` ($5, $10, $8, $6); the meter was read after each (`state/translate/meter.jsonl`, log `state/translate/m5-run.log`):
* 1,386 passages for $29.04 list-equivalent: 104 calls, 17 retries, 0 failed, 0 invalid, 1 deferred (API 529 Overloaded, which ended chunk 2 early; the packet was redone), 5,119 s of model time. Done: front matter, djr (1,059), 1.1.1.1–1.2.1.2.
* Meter: weekly 80 → 91 % (about 0.38 points per list-dollar), 5-hour window 8 → 92 % (about 2.9 points per dollar). djr cost $0.021 a passage, against $0.017 for the calibration unit (djr has many short sidenote passages).
* V7 after the run: 1,526/7,769 passages with records, 6,243 untranslated, 0 stale, 0 orphans; 1,264/1,264 Burton-span selectors match once.
* Found and fixed by V7: 24 Burton-span selectors (12 records) did not match once in the unit. 8 were short spans that recur ("at once" occurs 11 times in djr), and 4 were renderings in a sidenote. Selectors now get a prefix and suffix grown from the packet context until unique, and `view: with-notes` when the span stands in a sidenote. The main text is tried first, because a span may run across a note's anchor. Existing records were repaired from the base text (`runner.repair_spans`); the model's verdicts are unchanged.
* Verdict tallies (Opus tr-v2, 1,526 records): self-translation none 905, paraphrase 261, full 254, partial 105, undetermined 1; source burton-cites 748, unidentified 615, probable 163; 4 burton-cites claims downgraded to unidentified (no checkable basis).
* Remaining: about 6,270 items (with the 23 Chaucer groups), about $120–130 list-equivalent, about 45–50 weekly points and 3.5–4 five-hour windows. Resume after the weekly reset (2026-10-25 23:00 UTC) with `uv run burton translate --all --wait-on-limit`, plus `--budget-usd` if a cap is wanted.

**M5 translation pass complete (2026-10-26 → 2026-10-28).** `translate --all --wait-on-limit` across several five-hour windows. The PC shut down once while the runner waited (2026-10-27), and a runner died mid-packet once (stale lock removed); both resumed from the ledger with no loss. The last stretch ran under the owner's cap "don't exceed 92 % of the weekly allowance" with `--budget-usd 30`.
* This week: 6,243 passages for $150.98 list-equivalent, 66,854 s of model time; 379 packets done, 102 retries, 31 deferred at usage limits (retried by `--wait-on-limit`), 10 failed and 4 transient (all redone; no packet ended invalid). Weekly meter 0 → 79 %, about 0.52 points per list-dollar.
* Whole pass (sessions 1 and 2): 7,769/7,769 passages with records, about $182 list-equivalent; 23/23 Chaucer verse groups glossed (`data/layers/glosses/`). Against the projection of $127: about 40 % over (djr-style short sidenote passages cost more per passage than the calibration unit), and about one week of Pro allowance in all.
* Records by language: la 7,699, grc 63, grc-Latn 3, it 3, fr 1.
* Self-translation verdicts (Opus tr-v2): none 4,316, full 1,541, paraphrase 1,339, partial 566, undetermined 7.
* Sources: burton-cites 4,240, unidentified 2,767, probable 762, identified 0 (only the M6 verifier can set it).
* Review queue (`state/review/translate.jsonl`): 0 items; no packet was invalid after its retry. The post-checks recorded 68 soft issues on written records (43 burton-cites without a quoted basis, downgraded to unidentified with `downgraded_from`; 7 claimed renderings whose quote is not found in Burton's text, recorded as `undetermined` with the claim kept; 11 length ratios; 3 with 4+ source words left untranslated; 2 explanatory phrases; 2 glossary deviations). They join the 2 % spot-check.
* `burton check --all` (2026-10-28): 20 PASS, 1 DEFER (V5, D10), 0 FAIL. V7: 7,769/7,769 passages with a record, untranslated 0, stale 0, orphan keys 0, 7,821 machine translations labelled, 6,916/6,916 Burton-span selectors and 8,422/8,422 self-translation selectors match once, 23 gloss records with 98/98 selectors. V2h: 7,769 foreign passages in both builds.
* Still to do for the M5 exit: Dell & Jordan-Smith alignment over the whole book with a held-out accuracy check, and the 2 % spot-check (about 155 passages) plus the 68 flagged records.

**Dell & Jordan-Smith across the whole book (2026-10-28).** `burton align-djs --all` (rules, no model calls, 11 s). Method `rules/djs-align-v3`, threshold 0.85 as in M4.
* What changed from the M4 rules, each found on the first whole-book run or on held-out round h1:
  * Their page furniture is skipped before anchoring: page numbers, running heads (also printed inside a line, "Memb. 3] Remedies Against Discontents [525"), the footnotes printed just above a page break, and a library stamp in the scanned copy ("MARIN COUNTY FREE LIBRARY"). Before this, running heads stood inside about 100 candidates. Hyphenated words rejoin across a page break ("beg- … gar's" → "beggar's").
  * Their lower-case attribution after a verse, "(ovid)", is kept apart as `attribution` (196), and a trailing footnote mark as `footnote_mark`.
  * New statuses, never shown as a translation: `kept-original` 194 (they print the original: "os sacrum", a name), `broken-span` 7 (the span starts or ends inside one of their [bracketed insertions]), `ocr-noise` 17 (mostly Greek they printed, which the OCR garbled).
* Whole book, 7,769 passages: aligned 2,149, omitted 1,621 (they print nothing; usually Burton renders it himself), kept-original 194; no candidate: no-anchor 2,375 (mostly sidenotes, which their edition does not translate), not-found 798, below-threshold 407, implausible-length 201, ocr-noise 17, broken-span 7.
* Held-out check (`data/eval/djs-holdout.yaml`, labels in `djs-holdout-gold.jsonl`; sample and pass mark written before labelling; the M4 pilot, the items seen while tuning and earlier rounds excluded):
  * Round h1 (v2, 100 aligned + 60 omitted): aligned **87/100 correct**, below the pass mark of 0.95: 8 kept the original, 4 wrong, 1 boundary (a running head inside the line). Omitted **60/60 correct**. All 4 wrong ones were passages that Burton renders in full himself (of those 8 in the sample, 3 were correct). h1 then became tuning data for v3.
  * Round h2 (v3, 100 drawn from what the reader shows): **95/100 correct**, which meets the pass mark exactly (Wilson 95 % interval 0.89–0.98). 2 kept the original (names below the kept threshold), 1 boundary (the passage opens a longer quotation), 2 wrong (a one-letter passage, and a span of Burton's English).
  * Labels are Claude's, made in session. The owner had no time to review them and asked for a double check instead (2026-10-28). A second rater labelled h2 blind (`burton djs-audit`: Opus, prompt `djs-audit-v1`, 10 calls, $0.64, ledger `state/djs-audit/ledger.jsonl`). The decision rule was fixed before it ran: below 0.95 after adjudication, the versions come out of the reader. Result: agreement 97/100 (98/100 on correct vs not), and the second rater also counts 95 correct. After adjudicating the 3 disagreements (`djs-holdout.yaml`, h2 `second_rater`): **95/100**, so the rule is met. It is 94/100 if both raters must say correct.
  * Found by the second rating: our text splits one couplet into two passages (3.2.2.4-f34 "Delectabatur enim", f35), and their single line is shown for both. → language-ID boundaries (D10 list)
* Reader: a Dell & Jordan-Smith version is shown when the alignment is `aligned`, current with the text, and Burton does not render the passage in full himself (there his English is shown and theirs is usually absent): **1,992 passages**, in both profiles (SPEC §2: public domain in the USA). Label "Dell & Jordan-Smith (1927, p. N), aligned by rule"; their attribution is shown as "They attribute it: …". It comes before the machine version (SPEC §6.3). V2h counts it per unit, XML = HTML. V7 checks the layer (keys, currency, statuses, text only where a span is kept).

**M5 spot-check (2026-10-28).** The owner asked for the same double check as the alignment. A random 2 % of all passages (156, seed 20261030) plus the 66 records the post-checks flagged: 221 items. The sample and three rules were written to `data/eval/m5-spotcheck.yaml` before labelling. Each item was judged on translation (good, minor, error), self-translation verdict (ok, wrong) and source (ok, unsupported).
* First rater: Claude in session (`m5-spotcheck-gold.jsonl`). Second rater: Opus, blind (`burton tr-audit`, prompt `tr-audit-v1`, ledger `state/tr-audit/ledger.jsonl`). The translator is the same model, so an error it makes systematically could escape both.
* Agreement: translation 218/221, verdict 212/221, source 219/221. Every disagreement was adjudicated from the base text, with reasons in the yaml. The second rater found 9 verdicts I had passed, and 1 source claim. One of my own objections was wrong: the Athenaeus sidenote is anchored right at its passage.
* Rules (random sample): **R1** translation errors **0/156** (≤ 5 %). **R2** unsupported source claims **1/94** attributed claims (≤ 2 %). **R3** wrong verdicts **3/156** (≤ 5 %). All met. Flagged records: 0 translation errors, 0 unsupported sources, 6 wrong verdicts (5 `undetermined` where Burton plainly renders the note, 1 `none`).
* Actions:
  * The one unsupported claim is withdrawn in `data/manual/source-downgrades.yaml` (new; applied whenever the runner writes a record, checked by V7). In 1.2.3.1-f12, "Virg." is anchored at the next quotation.
  * The 9 wrong verdicts, plus the book's other 2 `undetermined` records, were re-run through the runner (`translate --select data/eval/m5-redo.yaml --redo`; `--redo` is new). All 11 now have a verdict whose span is Burton's exact text, and the book has 0 `undetermined` left. The 3 new source claims each quote Burton at the anchor.
  * Review queue: 0; nothing deferred.
* Found in passing (language-ID, D10 list): English tagged `la` (3.2.3.1-f288 "John come kiss me now", f32, 1.2.4.7-f54); French tagged `la` (2.3.3.1-f150, so the reader says "from Latin"); verse and titles split into fragments (1.2.4.3-f5, 2.2.4.1-f137, 1.2.3.15-f258, djr-f380). The translations handle each correctly and say so in their notes.
* Cost: $3.39 list-equivalent in model calls (second rater $3.02, redo $0.37). The weekly meter went 83 → 88 %, mostly this session reading the 221 items.

**M5 exit met (2026-10-28).** V7: 7,769/7,769 passages with a translation and a verdict (0 undetermined), every machine record labelled, review queue empty. Dell & Jordan-Smith is aligned across the book and shown where it passed the held-out check. The 2 % spot-check passed all three rules.

**Reader: Gowland as a private translation source (D11, 2026-10-27).**
* Private build: 4,934 passages have a Gowland version (every bracket linked to a passage by `@for`; 2 are brackets over several blocks, joined from their pieces). It is read from the base text when the site is built, without his brackets and braces, sidenotes, endnote anchors or page breaks. It is never written to a layer and never sent to a model. A passage whose only translation is Gowland's is no longer "untranslated" in the private build.
* The passage box lists every version, each labelled, in the default order of SPEC §6.3: editor, Dell & Jordan-Smith, machine, Gowland. The model's attribution and note travel with its own version. Burton's own rendering, where he gives one, comes before the list.
* New setting "Translation shown first": human, then machine, then Gowland (default); Gowland first (private only); machine first. It is kept in `localStorage`. `edition.js` reorders the versions, and interlinear and "Read in English" show the first one. When that is Gowland's, his inline bracket is hidden so it is not shown twice. The "Show Gowland's bracketed translations" toggle is unchanged.
* Owner's condition: a translation standing in for the original is marked with its language. "from Latin" (in interlinear under a word, "Lat.") in muted small capitals, a faint tint behind the text (about 14:1 contrast in light, 13:1 in dark), and ⟨ ⟩ in "Read in English". Screen readers hear "Translation from Latin:". The About page explains both.
* Checks: V2h counts Gowland versions per unit, XML = HTML: private 4,934, public 0. V8 also searches the public pages' own text (outside the translation boxes) for Gowland's text without brackets, line by line for verse, for segments of 30+ characters. The first version of that search reported 40 "leaks": machine translations that match a literal bracket word for word ("I came to Athens, and no one knew me"). Those are independent translations, so translation boxes are excluded; a Gowland version rendered into a box is caught by its `data-resp="gowland"` markup.
* Verified in the browser pane (private build, light and dark): the box, interlinear, "Read in English" with each order. On 1.2.3.14 with Gowland first, 71 passages show his version and 0 inline brackets are duplicated; the 1 bracket left visible belongs to Latin that is not a detected passage.

**M6 done (2026-11-02).** (Started as session 1, below; one item left: the Wikidata run, paused by the service's outage.) Started after the weekly reset under the owner's cap "do not exceed 92 % of weekly credits in M6". Rules-only work first; two small ledgered model runs.
* **Citation parser** (`burton citations`, rules `rules/abbrev-v1`, no model): every sidenote's public text → `data/layers/citations/<unit>.json`. Fragmented italics merge because it reads text. Heads: author forms, Bible books with a number, `Idem`/`ibid.` (resolved to the citation before, `resolved_from`), loci and titles whose author is named at the note's anchor (`author_basis: text-at-anchor`: the first name after the marker must be an author form), stand-alone titles (`alone:` forms in works.yaml), unknown names (unidentified, never guessed), and Burton's own divisions (22, recorded as references to this book).
  * Tables, machine-draft by claude-opus-5-5 in session (owner review through the top-100 list): `data/abbreviations.yaml` (43 locators, 66 Bible books, 252 authors, 10 ambiguous forms with their resolution rule and basis) and `data/works.yaml`.
  * **Sidenotes 5,703/5,703 with a record: parsed 2,210, partial 781, unidentified 1,507, no citation 1,205.** Citations: parsed 2,675, partial 621, unidentified 1,868; author from the anchor 602, from a stand-alone title 106.
  * Held-out check of the author resolutions (`data/eval/m6-citations-holdout.yaml`; sample and rule written before labelling; labeller Claude in session; pass ≥ 95 % and ≤ 2 wrong per stratum): round c1 **61/65, FAIL** (lone titles matched by prefix: "Theog.", "Scot.", "Medea", "Phar."); the prefix rule was replaced by explicit stand-alone forms; fresh round c2 **64/65 = 0.985, PASS** (form 29/30, anchor 20/20, title 15/15; the miss, "Basil." = the Basle edition, was then removed).
  * V7 checks the layer: one current record per sidenote, known statuses, author and work ids in the tables, Idem/ibid pointing back, nothing displayed that was not resolved.
* **Author registry** (`burton authors [--review] [--wikidata]`): 247 cited authors, a file each in `data/authors/` (counts are computed from the layer, never stored). Review list for the owner: `state/review/authors-top100.md`.
  * Wikidata (CC0, rules): v1 (search API, method `wikidata-match-v1`) reached 51 authors: matched 32, ambiguous 9, none 10; then the service throttled it to a few authors an hour. v2 (batched SPARQL, exact English/Latin label, human, died by 1651, unique) is written and fast when not throttled, but was throttled at once this session; stopped. Re-run `uv run burton authors --wikidata` in a later session (cache in `state/wikidata/`, gitignored). One test request in this session carried the account email in its User-Agent; the code sends a generic one.
  * Model drafts (`burton author-drafts`, prompt `authors-v1`, claude-opus-5-5, ledger `state/authors/ledger.jsonl`, no Wikidata or Gowland input): **top 100 drafted** (identification, field, why cited, stated doubt, confidence: high 86, medium 13, low 1; 19 state a doubt about the identification), $0.83 list-equivalent, 7 calls. The other 147 authors: `uv run burton author-drafts --budget-usd 3`.
* **Reader**: "Authors cited" index and 247 author pages (Wikidata dates only for a unique match, the draft with its model/prompt/date label, works cited, every citation linked to its sidenote). A new reading option "Expand Burton's abbreviated citations" (off by default) shows the resolved citations under each sidenote with a label naming the tables' model; Scripture is not linked. About page explains both. 412 pages per build (164 before).
* **Relative cross-references** (`burton xrefs-relative`): 109 phrases found by rule, 26 dropped as non-references by rule, 83 sent to claude-opus-5-5 (prompt `xref-rel-v1`, 6 calls, $0.93) → `data/layers/xrefs-relative/`: **33 proposed** (target exists, evidence found verbatim), 30 unresolved, 20 not references. None is linked until the owner confirms (`state/review/xrefs-relative.md`). V7 checks the layer (83/83 selectors match once).
* **Source verifier** (`burton verify-sources`, rules `text-match-v1`): a passage is matched when it shares ≥ 5 consecutive normalised words covering ≥ 80 % of it (i/j, u/v, ae/oe/e, y/i merged, quum/cum) with a corpus unit; a match by the claimed author is preferred (Seneca's letters quote Horace). Results in `data/layers/source-verification/`; the translation layer is not edited. The reader shows "Source: …, text matched by rule in perseus-latin" only for `verified`.
  * Corpus: owner approved "Latin only" (2026-11-02). Perseus canonical-latinLit, shallow clone at 8b536bd (219 MB, CC BY-SA 4.0), pinned in `data/source/CORPORA.lock`; `burton corpora` converts it (364 files, 106,234 citable units, 17 files read with the recovering parser; 44 of 60 textgroups mapped to edition ids in `data/corpora/perseus-latin.yaml`). Only references and scores enter the layer, never corpus text.
  * **7,762 Latin/Greek passages checked: verified 416**, conflict 10, unchecked 7 (claimed name not in the tables) → `state/review/sources-conflicts.md`. Of the verified: 265 had `burton-cites`, 126 `probable`, 25 `unidentified`. 54 have only a whole-work locus (corpus files without citable parts). (First reported as 414 with 2 unmapped: the converter had left stale copies of three authors under their old unmapped names; fixed, it now clears its output.)
  * Check (`data/eval/m6-sources-check.yaml`, rule written before labelling: ≤ 1 wrong): all 25 matches with no prior claim + 30 random agreeing ones: **56/56 correct, PASS** (labeller: Claude in session). After the converter fix one sampled match (djr-f441, Petronius) changed only its locus, all → 14, still correct.
* Meter (weekly · all models): **1 → 12 %** in session 1; **14 %** after the corpus step (rules only, no model calls). 5-hour window 3 → 99 % (stopped there), mostly this session's own context: it rose 41 → 75 % with no model run. Model calls this session: $1.76 list-equivalent (xrefs $0.93, drafts $0.83).
* `burton check --all` (2026-11-02): 20 PASS, V5 DEFER (D10), 0 FAIL. V6: 822 pages, 168,306 links, 0 broken (every author link resolves). V4h: 0 untagged (Greek in citations and drafts on author pages marked `grc`). L1, V10a, OFF pass with the new pages. pytest 95 passed.
* **Independent checks** (owner, 2026-11-02: "Run independent checkers for these"; `burton m6-audit`, claude-opus-5-5, fresh context and own prompts, same model family as the first pass; answers in `data/eval/m6-audit-*.jsonl`, summary `state/review/m6-audit.md`; $1.97 list-equivalent, weekly 15 → 16 %):
  * Author drafts, 100 (`author-audit-v1`): identity ok 98, wrong 1, doubtful 1; facts ok 97, minor 3, error 0; Wikidata 32/32 matches the same person. The wrong one, Chytraeus, was the edition's table (David for Nathan, whose *Deliciae* every citation names): corrected in abbreviations.yaml, redrafted, rechecked ok. Doubtful: "Mart." also abbreviates Justin and Peter Martyr in two citations (left for the owner).
  * Relative cross-references, 83, blind second rater (`xref-audit-v1`): same target 29 of the 33 proposals; first only 4, second only 6, neither 44 (all listed with reasons).
  * Source conflicts, 17 (`source-audit-v1`): match is the source 12 (Burton's attribution is off: e.g. his "Hor." is Martial 10.47, his "Tibullus" Propertius 2.33), claimed author quoted in the match 5 (Cicero quoting Ennius, Caecilius, Catulus; Seneca quoting Horace; Columella quoting Virgil). The first run's excerpts were centred badly (3 were "unclear" for that reason); fixed and re-run. Nothing is changed in a layer: these remain for the owner.
* Counts after this step (`burton check --all`, 2026-11-02: 20 PASS, V5 DEFER, 0 FAIL; V6 828 pages, 169,370 links, 0 broken): the three authors added for the corpus (Phaedrus, Minucius Felix, Silius Italicus) also resolve sidenotes, so **sidenotes parsed 2,212, partial 782, unidentified 1,505, no citation 1,204** (5,703); citations parsed 2,678, partial 623, unidentified 1,864; 250 cited authors.
* **Owner's decisions (2026-11-02)**: the drafts' minor factual slips are acceptable as they stand; cross-references and source disagreements delegated ("Make your own judgements on the cross references", "record both Burton's attribution and your disagreement").
  * Cross-references, judged in session against the target unit's own text: **32 confirmed** (28 agreed proposals; 1.2.2.1 for "the six non-natural things", from the second rater; 2.4.1.5 for borage wine, where both raters had 2.4.1.3; 2 "precedent partition" references to 2.4.1.1, where Partition 2's physic begins), **7 rejected** (too vague, two plausible places, or the subject not in the proposed unit). Recorded in `data/layers/xrefs-relative/` with `review.by` naming the delegated reviewer; `state/review/xrefs-relative.md` shows each decision.
  * The reader now links cross-references: the 19 explicit ones resolved by rule (M2) and the 32 confirmed relative ones, 51 in all (4 split around a sidenote that stands between the words); the 2 unresolved explicit ones are marked unlinked. Placement uses the page's visible text, so token-by-token italics in sidenotes do not hide a reference; one that cannot be placed would be counted, not guessed (0).
  * Source disagreements: `data/manual/source-findings.yaml` keeps the recorded attribution unchanged beside the finding for all 17: agrees 5 (the words survive as quoted by Cicero, Seneca, Columella), same author but Burton's book differs 2, Burton names the author his source names while the Latin is the source's own 3 (Seneca), cites where he read it 1 (Camerarius → Ovid), disagrees 6 (Hor. → Martial 10.47; Catullus → Tibullus 1.5; Tibullus → Propertius 2.33; Petronius → Ovid, Heroides 16; Musaeus → Ovid, Met. 6; the earlier machine guess Claudian → Petronius). The passage box shows both, labelled with who decided; V7 checks that each attribution still equals the layer's claim and that its text match stands.
* **Owner (2026-11-02): "Just say it's one or the other on the Mart. citation. If you can't tell, say so!"** All 21 "Mart." citations decided: Martial 17, Martianus Capella 1 ("Mart. Capella", a new form), Justin Martyr 1 ("Just. Mart. in Apol."), Peter Martyr Vermigli 1 ("Pet. Mart. in Sam.", resolved by work), and 1 "P. Mart." recorded as Vermigli from its theological context only (medium; `data/manual/citation-decisions.yaml`, a new hand-decision file keyed by note and exact citation text, checked by V7). Also: St Basil only with a locus that is not a year ("Basil. ep. 141" yes; "Basil. 1553.", "Basil. Editionis." are Basle).
* Held-out round c3 after those rule changes (same design and rule): **65/65, PASS** (form 30/30, anchor 20/20, title 15/15).
* All cited authors drafted and independently checked: 253 authors (153 more drafted, $1.16; checked $1.04). Checker: identity ok 245, doubtful 7, facts ok 249, minor 3, error 0. Of the doubtful, three were mix-ups in the tables, fixed: "Gomesius" on Ximénez is Alvar Gómez de Castro (decision); "Nicephorus Greg." is Nicephorus Gregoras (new form); "Phaedrus orat. in laudem amoris" is Plato's Symposium (decision). "Caesalp. hist." fits no Cesalpino work: the form is withdrawn. Freitag: Johann Freitag the physician, since all three citations are in the diet subsection (the checker could not tell). Rechecked: ok.
* Wikidata v2 re-run: stopped at 110 of 315 names. The Wikidata query service was in an outage ("Aggressively rate-limiting to 1 req / min … during active wdqs outage") and one batch failed; the per-batch cache in `state/wikidata/` keeps what was fetched. Author files still carry the v1 results (51 authors: matched 32). Re-run `uv run burton authors --wikidata` when the service has recovered.
* **Owner accepted both sign-offs (2026-11-02, "Accept both")**: the abbreviation and works tables (`provenance.status: checked`) and all 253 author entries (`status: checked`, `review.state: accepted`). The reader's labels read these fields: "tables a machine draft (claude-opus-5-5), checked", and on each author page "accepted by the owner".
* **M6 exit met:** every sidenote has a status (5,703/5,703: parsed 2,212, partial 785, unidentified 1,502, no citation 1,204); every author link resolves (V6, 0 broken); zero `identified` without a verifier basis (only the 416 verified matches and the 17 recorded findings show a source). **Carried forward:** the Wikidata v2 run (`uv run burton authors --wikidata`) once the query service has recovered; the 66 Greek passages stay unverified unless Greek corpora are approved.
* **Do not redo:** the c1/c2 held-out rounds are seen; a new parser rule needs a fresh round c3. Do not re-draft the top 100 unless the prompt changes (bump `authors-v1`).

**M7 started (2026-11-02).** Owner: "Yes, start M7". Groundwork only in the M6 session (its context was 71 % full; the 20 images need a fresh one):
* Survey reproduced: 561 non-glyph hidden strings (P1 219, P2 224, P3 118), every hidden `<p>` with a unique id; 20 images of about 1,400 × 900 px.
* `burton synopses --checklist` (`burton/ingest/synopses.py`) writes the word-level checklists `state/m7/pN-checklist.tsv`.
* Method fixed in `state/m7/BRIEF.md`: words only from the hidden table, verbatim; only the tree's shape from the images, as ids in `data/manual/synopses/pN.yaml` (machine-made, labelled); a builder, an independent V11, then the reader. **Next session starts from that brief.**

**Carried forward** (not done, with the milestone that takes each):
* The synopsis is shown as the source's images with pattern alt text until the text tree exists. → M7
* ~~The "translation source order" setting waits for a second source.~~ Built with Gowland as the second source (D11).
* Language-ID edge cases deferred by D10 (see the M2 status above). → later, with a new hold-out round h3
* ~~The model sometimes puts explanation inside a translation ("Curable (salutary)").~~ Fixed in M4 by `tr-v2` and the parenthesis check.
* The gold sample is labelled by Claude and awaits your review (D7).
* ~~Chaucer untagged; Italian tagged `la`; French untagged; boundaries 3.2.5.1-f47 and f31.~~ Fixed in M5 session 1. Still open: djr-f1489 runs two citations and a quotation together (one passage, left as is). → M6 citation parser
* The reader does not show the gloss layer yet; the M5 Chaucer glosses are stored for it. → M8
* ~~The Dell & Jordan-Smith alignment lives in `data/layers/djs/`, separate from `translations/`. Merging it into the reader needs a held-out accuracy check.~~ Done in M5: whole book, held-out 95/100, shown for 1,992 passages. The layer stays separate; the build reads it.

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

## Workflow: shorter session start-up, same checks

Each session starts cold. These steps save start-up time without lowering any check: every saved fact can be reproduced, and every manual step that is dropped is replaced by an automatic one.

**Orientation**
1. `burton status`: one command for the current milestone, passage and translation counts, stale layers, and the last `burton check` result (`verify/reports/latest.json`). Computed live, so it cannot go out of date.
2. `FACTS.md`: settled facts, each with the command that reproduces it (e.g. "French passages: 0" plus the command that counts them). If in doubt, re-run the command; do not re-survey.
3. Keep PLAN.md to the current milestone and open decisions; move finished milestones' status blocks to `verify/reports/`. Keep CLAUDE.md to rules and conventions.
4. Every milestone session ends with a handover note in the shared notes folder: decisions taken, what not to redo, open items.
5. Briefs for spawned sessions name the sections to read, the settled facts, the files to start from, and what to skip.

**Tools instead of throwaway scripts**
6. `burton passages`: query passages by `--lang`, `--min-words`, `--bracket`, `--signal`, `--unit`, `--location`.
7. `burton show <id>`: one passage with its paragraph, sidenotes, self-translation candidates, all translation records and the Dell & Jordan-Smith alignment.
8. Make the pilot's ad-hoc checks permanent: the packet leak test (no Gowland translation text in any packet) as a `burton check` step, and the "no added parentheses" count in V7.

**Manual review only where a judgement is needed**
9. Attribution review list: the validator already proves every `burton-cites` quotes Burton's own words. Generate a list of only what it cannot prove: every `probable`, any work or locus not in Burton's words, and every disagreement between models. Review that list by hand.
10. Score new prompt versions automatically against the expected verdicts in `data/eval/m4-pilot.yaml`. A label is revised only with its draft kept.
11. Measure accuracy (alignment, verdicts) on held-out sets, as language ID does; do not re-check the items you tuned on.

**Not repeating expensive runs**
12. Incremental `burton check`: store input hashes (text, layers, code) with each report and re-verify only changed units. A full `--all` run is still required before a commit.
13. Store usage-meter readings next to the ledger, so projections build on earlier measurements.
14. Run long jobs in the background with a progress log, and read the log when they finish.

Highest value first: 1, 6, 7, 9.

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
| D1 | **Private edition** (owner, 2026-10-20). | Build the private profile only. The public filter and its leak checks (V8, V8t) stay in place. No remote is set up |
| D10 | **Language-ID target deferred** (2026-10-20; confirmed by the owner the same day). | V5 stays below target on h2 (0.964 / 0.964 / 0.975). It still runs and reports `DEFER` (`data/manual/deferred-checks.yaml`). Remove that entry to make it blocking again |
| D8 | **Opus for the full pass** (owner, 2026-10-23, after the M4 pilot). | M5 runs `claude-opus-5-5` (the runner's default). Pilot: self-translation 12/12 against Sonnet's 10/12, misquotations caught 4/4 against 0/4, 0 invented attributions for either; about $144 list-equivalent, roughly twice Sonnet's usage (`verify/reports/m4-pilot.md` §3–§6) |
| D11 | **Gowland as a private translation source** (owner, 2026-10-26). | In the private build Gowland's translations are a translation source (SPEC §6.3), read from the base text when the site is built; they are never copied into a layer and never sent to a model. His brackets and braces are dropped on display only. The passage box lists every version, each labelled, preferred first. A "Translation shown first" setting chooses the order. The owner's condition: any translation standing in for the original is visibly marked with the language it is from |
| D9 | **Tools installed.** | Python 3.13.15 (via `py`), uv 0.13.1, git 2.56, Node 24, Claude Code 2.1.304. Bare `python` is the Store stub, so always use `uv run` |

### Still open

**D7 — Gold-sample labelling.** There are 1,127 labels, all drafted by Claude: 677 in the tuning sample, 150 in h1, 300 in h2.
* 2026-10-20: the owner asked for a 5-label spot check from h2 (the gate sample), drawn with a fixed seed. See `data/eval/audit-h2-spot5.md`.
* This is a spot check, not the 25% audit. Any disagreement means a wider review.
* **Result: the owner agreed with all 5 (0 disagreements).** The other 1,122 labels remain unreviewed.
