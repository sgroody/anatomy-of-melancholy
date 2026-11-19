# The reader rebuild (2026-11-03): where it stands

The owner's A/B decisions are in `state/review/ab-2026-11-03-decisions.md`, and the mockups are the three
`ab-2026-11-03*.html` pages (served by the launch config `review-pages`, port 8790). The reader is being rebuilt
in stages, each committed after `burton check`.

| Stage | What | Commit |
|---|---|---|
| 1 | The margin: lettered notes; translation cards in the language's colour; Gowland's endnote entries by kind (`burton/site/gowland_notes.py`); citations expanded in place; ◇ provenance; hover and pin with the CSS Highlight API | f38fe14 |
| 2 | Two margins from 1,380 px: commentary left, translations and Burton's notes right, with crossing over | 0af78e4 |
| 3 | Penguin headings (brace), red decorated initials (`data/source/INITIALS.lock`) | 6037d60 |
| 4 | Front page (engraving held large, stanzas on hover, synopses collapsed, "Enter, gentle Reader"), facing Gowland translations for Ad Librum and Lectori, synopsis signs as links | 00db8a4 |
| 5 | Windows on cited authors' names (`burton/site/names.py`; hairline, R5 C) and on cross-references; CK3-style lock | a487cfa |
| 6 | In-line citations (name kept, § in the line, card in the margin), Bible verses from the KJV (`burton/site/kjv.py`), numbered books in the rules (abbrev-v2, inline-v2), guard on model expansions | 4d198db |
| 7 | Translations in the line (R6 B), Burton's own English in the language's colour, long verse passages set facing (4+ lines, 104), Greek in GFS Didot, Chaucer in small capitals, How to read this book | (this stage) |

## Stage 6: in-line citations and Bible verses

* **In-line citations (C1 C).** Use `data/layers/citations-inline/<unit>.json` (924 records, selectors on the
  block's public text). In the line: keep the author's name, hide the reference words (wrap them in a
  `span.cx-b`-like element shown under the "Burton's abbreviations" option), and put a raised § in the
  citation colour (`--k-cite`) after the name. A Bible reference has no name to keep, so only the § stays.
  The margin card is kind "cites", with the expansion (the record's `display`) and, for Bible, the KJV verse.
  Place with `_locate` as `mark_xrefs` does. Count placed and unplaced.
* **KJV.** `data/source/kjv/pg10.txt` (Gutenberg #10) and `pg124.txt` (#124, the Apocrypha); hashes in
  `data/source/KJV.lock`. Layout: the contents list at the top gives the exact book titles. In the body each
  book starts with its title line, and a subtitle may follow within a few lines ("The First Book of the
  Kings" right after "The First Book of Samuel"). Verses are `C:V text`, sometimes several on one line.
  Split the book's text on `(\d+):(\d+) `. Map the titles to `data/abbreviations.yaml` bible ids. Numbered
  books (1-2 Samuel, Kings, Chronicles, Corinthians, Thessalonians, Timothy, Peter, 1-3 John, Maccabees,
  Esdras) need the number, which the rules do not record yet (see the next point). Show a verse range
  folded after three lines ("more"), with the label KJV.
* **Bible rule gap found.** `burton/layers/citations.py` misses numbered books ("1 Cor. 6. 5, 6." comes out
  as no-citation) and a reference after "?" or "!" ("…sapietis? Psal. 94. 8."). Fix it in the parser, with
  tests, bump `METHOD` (abbrev-v2), and re-run `burton citations`. Citation ids are `<note>-c<k>` by order,
  so a newly found earlier citation renumbers the later ones. **Before re-running**, make the renderer use a
  model expansion (`data/layers/citation-expansions`) only when its `raw` equals the rules citation's `raw`,
  and count any mismatch.

## Stage 7: language colours, the in-line switch, Burton's own English, long passages

* Colours for Latin, Greek and Middle English in the line are done for the margin layout. Make "Read in
  English" (R6 B) set the translation in place of the Latin, in the language's colour and italic, with no
  ⟨ ⟩ and no "Lat." tag; the Latin on hover. Rename the reading option "Translations in the line".
* Burton's own English (R2 A + C): colour his rendering (`span.burton-tr`, placed by `mark_burton_spans`) in
  the language's colour, roman; the margin card already says "Burton's own".
* Long passages (T12 B): a verse block whose preferred translation has as many " / " lines as the block
  has lines is set facing, line for line, in place of a margin card. Gowland's Plautus in 1.2.2.6 runs on
  from the passage before, so take its last lines.
* Greek in GFS Didot (T10 B): the font is pinned in `FONTS.lock` (`GFSDidot-Regular.ttf`). Add a face for
  `[lang="grc"]` to `fonts.py` FACES/subsetting and the CSS. Chaucer (`span.lucida`) in small capitals.
* Also owed: a "How to read this book" page (the owner asked in the first notes), and an A/B round on the
  typefaces later (T10 stays open).

## Facts for whoever continues

* Headless checks: the app's browser pane runs hidden pages as background pages, so `requestAnimationFrame`
  (the layout) never fires there. Use Playwright with `channel="chrome"`, as `burton/verify/browser.py` does.
* Build with `uv run burton build --profile private --all`. Without `--all` it builds a single unit. A
  partial `burton check --unit …` always fails V6 (links to unbuilt units), HY (no Greek) and OFF (offline
  search); those pass on `--all`.
* V2h counts `.sidenote` and `.ft-gowland`, and V3h checks every `a.nref`. The new margin items use
  `.mn`/`.mref` so those counts stay exact. V8's text-level leak test skips `.ft`, `.mn` and `.sn-tr`, and
  anything with `data-src="djs1927"`.
* Python written through shell heredocs mangles `\n` and `\d`. Use the Edit tool for code.
* Bible verses (stage 6): Burton sometimes numbers the Psalms as the Vulgate does ("Psalm. 118. 140" is KJV 119:140;
  "Psal. 126. 7." has no KJV verse, so nothing shows). Where a Vulgate number names a verse the KJV also has, the
  margin shows the KJV verse of that number, which may not be the one Burton meant: 74 Psalm citations show verses.
  Owner to decide (suppress Psalms, or check each against Burton's words). "Reg." is Kings, numbered as in the KJV
  (1 Reg. 11. 5 is Ashtoreth, 1 Kings 11:5).
* Citation ids are renumbered by rules changes; `Renderer.expansion` uses a model expansion only when its `raw` matches
  (1 mismatch after abbrev-v2: 1.4.1.1-n38-c1, "cap. 8." became "De provid. cap. 8.").

## Owner's notes for the next session (2026-11-03, late; after stages 6 and 7)

Recorded as given, for A/B rounds and work after stage 7:
* "Where this stands in Burton's synopsis": show it as a visual, not the words. A/B a bunch of options. Perhaps always
  at the top left of the page.
* A settings widget and search bar always at the top right, looking more natural within the rest of the page.
* The synopses' unique layout of the text should be visualized better on the home page.
* Language colours: consider other colours for Latin and the other languages; give a visual of alternatives; perhaps
  they change between light and dark mode.
* Burton's own matter in the margins should perhaps have a distinct identifier.
* A stylized G instead of writing "Gowland" every time: A/B it.
* The top of the reader: "The Anatomy of Melancholy" as now, with "An Englished Reader" under it.
* The owner will be asleep: don't let a permission prompt stop the work.

Round 4 page for those notes: `state/review/ab-2026-11-04.html` (served by `review-pages`, port 8790; it borrows
fonts from site/private, so build first). Tests N1 synopsis position, N2 search and options, N3 synopses on the home
page, N4 language colours (light and dark), N5 a mark for Burton's notes, N6 a sign for Gowland. The subtitle "An
Englished Reader" is done directly (header, every page).

# Round 4 answers and the owner's notes of 2026-11-04

Round 4: N1 D (a mark that opens the branch) · N2 C (title centred, two quiet signs) · N3 Neither ("Reflect on
aesthetic design principles and come up with something that matches both Burton's original and our front page") ·
N4 D (a different colour by night), "but let me see what it would look like if the Latin were some shade of red. Most
of the non-English is Latin so it's important that it looks right" · N5 C (a rubric rule beside his notes) · N6 D
(a raised small-capital g).

Notes (owner's words condensed; grouped into the stages below):
* Fonts: explore fonts that capture Burton's original printing; italics in a slightly different face? marginalia in
  one, yet distinct? Where Burton glosses a statement with Latin, make that more distinct.
* "+ more" expands over the notes below instead of pushing them down; things must never overlay each other.
* The reader asks for manual expansion of notes ("n more notes") when the margin has room: it should never hold back
  new notes, only shorten a long note with a way to read it in full.
* Where several notes cover the same thing it is confusing: explore ways to simplify. A word with several notes (a
  gloss inside a passage with a broader note) lights all of them.
* "Gowland", "Claude" after a translation are not distinct enough from it: an ascription, not text. "trans." perhaps
  not in the translated text's colour: the eye should go straight to the text, while a first-time reader still sees
  what it is.
* Light/dark switch always at the side, with search and options.
* The Dedication (the first page after "Enter, gentle Reader"): styled better, uniquely.
* Facing pages (Ad librum and the like): pointing at a line lights its translation line; no "[TRANSLATION]" heading
  and no divider; a place for the first note (Haec comice dicta cave ne male capias); explanatory notes between the
  columns, lighting both passages; Gowland should not have a separate page when he is already facing. Heraclite
  fleas: Gowland's translation facing too.
* Synopses break the flow when clicking through ("Burton's synopsis, reproduced as the source prints it"): jump into
  the first Partition, with the interactive synopsis at the top of each Partition's first page.
* "How to read this book" begins with a couple of sentences on what this is: the source text and this reader.
* The note on Praxiteles misses the declined form "Praxitelem": is it a broader class?
* Restored (Gutenberg) sidenotes: translate them; find out why Gowland left them out.
* The notes the Claude translation passes wrote: add them (to the margin), after a spot check and an independent
  audit of their quality.
* Psalm verses: check them against Burton's words.
* V5 (deferred): deal with it now.
* "I should not be seeing things differently out of concerns of a separate public build at this point": no
  public-build hedges in what the reader shows.

## Plan (2026-11-04)

| Stage | What |
|---|---|
| 8 (a118170) | Decided design: N1 D, N2 C (+ light/dark switch), N4 D colours, N5 C, N6 D, quiet ascriptions, "trans." neutral; the margin never stacks notes (long notes shortened with "more", which pushes the rest down); a word lights all its notes; no public-build hedges in the private reader; the guide's opening |
| 9 (this commit) | Front matter: facing pages done properly (line lights line, no heading/divider, first note, notes between, Heraclite, Gowland's pages folded in); the Dedication; synopses at the head of each Partition's first page, not in the click-through |
| 10 | A/B round 5: typefaces after Burton's printing (text, italic, margin), Latin in shades of red, the synopsis on the home page (N3 again), Burton's English with its Latin |
| 11 | Data: declined names (Praxitelem), Psalm verses checked, restored notes (why left out; translated), the translation passes' notes (spot check + independent audit, then shown) |
| 12 | V5: language-ID back to target, with a fresh held-out round |

### Finding (2026-11-04): Gowland entries that do not light their words (the Praxiteles note)

Of 4,392 Gowland entries with words to find, 4,112 are placed on their words and 280 (6.4%) stand at his marker.
* Declined or variant forms: ~11 recoverable by a stem rule (Praxiteles/Praxitilem, Dionysus/Dionysio, Paeon/Paeoniis,
  Papinian/Papinianus, tormentum/torment).
* The lemma is in Burton's sidenote, not his running text (Otho Nicholson, Maecenas, liberales disciplinas): Gowland
  annotates the notes too. These should sit on the sidenote's words.
* The lemma is in the paragraph but outside the stretch searched (from the previous endnote marker to this one), e.g.
  Gentiles, Ethnics in 1.2.1.2.
Stage 11: the stem rule, the whole-block fallback (unique occurrence only), and entries on sidenote words.

### Finding (2026-11-04): why Gowland left out sidenotes (his "A Note on the Text", EPUB note_on_text.xhtml)

His stated policy, in short: the notes were pruned "aggressively". Latin in a note that Burton translates directly in
the main text was removed, and notes made up only of such Latin were deleted with their markers; the marginal
descriptive tags were dropped too. So most restored notes are the Latin of something Burton already renders in his
own English beside it. For stage 11: show each restored note's tie to Burton's English (the selftrans signals), and
translate only what his English does not cover; notes Gowland shortened (Latin cut, citation kept) are not restored
yet and would need a separate comparison with Project Gutenberg #10800.

Added to stage 8 (owner, 2026-11-04, later): an icon for the desktop shortcut (tools/desktop/anatomy.ico, the red
initial A); a machine translation's ascription is the ◇ alone, not "Claude"; Burton's own rendering in the margin gets
the rubric rule of his notes; and where Gowland has decided, a passage is not translated over again: 38 passages his one
bracket translates with the next ("covered"), 67 he glosses in a note ("glossed"), and 408 more that Burton renders
himself, fully, partly or by paraphrase ("own"); translation cards 5,976 -> 5,871.

Round 5 page: `state/review/ab-2026-11-04-r5.html` (fonts from Google Fonts for the comparison only). F1 typefaces after
Burton's printing (EB Garamond; IM Fell English; IM Fell DW Pica; Garamond roman with Fell italic; margins varied),
F2 Latin in a shade of red (oxblood, crimson lake, rose madder, beside the rubric), F3 the synopses on the home page
again (the sheet live with true braces; three framed compartments; the outline with true braces), F4 Burton's English
beside his Latin (tinted pair; "=" with an underline; the Latin raised over his English).

### Finding (2026-11-04): Psalm verses against Burton's words (rules pass, scratch)

76 Psalm citations show a verse. Comparing the KJV verse (content words) with Burton's words at the citation and the
English of the Latin quoted there: 58 match the verse of Burton's number; 2 have no such KJV verse (Vulgate numbers);
16 are unclear, and the word-overlap rule is too crude to settle them (it prefers Ps 18:9 for "Psal. 17. 8", where the
KJV 17:8 "Keep me as the apple of the eye" is plainly meant). Stage 11: keep the rule only for clear matches, and send
the 18 others to a ledgered model reading (private-only check; Gowland's translation of the quoted Latin may be used),
with the verse shown only where it is confirmed, or the Vulgate-numbered one with a note where that is confirmed.

### Where things stand (2026-11-04, ~09:20 UTC)

Usage meter read before any model run: weekly 85% (resets 2026-11-08 23:00 UTC), 5-hour 73%. The owner's ceiling is
90% weekly, and this session's own work counts too, so **no model runs until the weekly reset**. Waiting on that:
* Psalm verses: the 18 citations the rules cannot settle (a ledgered reading, private-only check);
* the notes the Claude translation passes wrote: spot check + independent audit before they go into the margin;
* restored notes: tie each to Burton's own English (rules, selftrans), then translate only what his English leaves out;
* V5 (stage 12): the fixes are rules, but a fresh held-out round needs a gold sample (owner's hand, or the D7 blind
  rater: a model run).
Done in stage 11 without a model: Gowland's entries placed on their words (stem rule, whole paragraph, sidenote words):
136 more on words (116 on sidenote words, anchored at the note's marker and lit inside the note; 11 by declined or
variant forms, incl. Praxiteles/Praxitilem; 9 elsewhere in the paragraph); 195 still at his marker.
Owner's choices awaited: round 5 (state/review/ab-2026-11-04-r5.html).

# Round 5: owner's choices (2026-11-04)

F1 A (EB Garamond throughout, as now) · F2 B, adjusted: "Oxblood by day, Candle-gold by night. Perhaps a setting to
adjust color?" · F3 B (three compartments, as in the engraving): "Might have to see more options, and visualized on the
full front page" · F4 Neither: "Keep A for now" (Burton's English in the Latin's colour).
What follows: Latin #7a2230 by day, #e0c27a by night, with a reading option for the colour (presets and a custom
colour); round 6 shows compartment variants on the whole front page.

Round 6 page: `state/review/ab-2026-11-04-r6.html` (it borrows the engraving from site/private, so build first). G1 the
synopses as compartments on the whole front page: A three across under the way in, a click opens the chosen
Partition's branches below; B stacked, shut to a line, one open at a time; C a triptych under the whole page, like the
engraving's lowest row; D one compartment with three numbered panels to choose.

# The owner's notes of 2026-11-18 (after a few weeks away)

Grouped as stages; weekly meter 19% at the start (resets 2026-11-22 23:00 UTC), so model runs are possible again.

| Stage | What |
|---|---|
| 12 | The margin and the page: "Author trans." for Burton's own; no redundant Burton/machine double ("gullet"); no translation of trivial words in notes ("de" -> "on"); no card where Burton renders a whole block himself; the rubric rule only on what Burton wrote, the lines added to his note (expansions, translations, KJV) set as belonging to it without the rule; CITES / NOTE on Burton's notes by what they are; Dell & Jordan-Smith's own sign; kind colours more distinct in light mode; a quieter expand sign than "+ more"; names linked in the sidenotes too; hovering a note that translates Latin lights Burton's English and the reverse; Bible notes lighting their words (bug); the two floating Bible references at the head of DJR (bug); "Haec comice dicta" untranslated (bug); front matter centred, with its own contents list at the top marking where one is; search opening in place; the settings panel sleeker and with a key to colours and signs; options to hide Burton's in-line citations, to show only Gowland's notes, and to show nothing but the text |
| 13 | A/B round 7: Next/Previous as whole side zones; Burton's note letters in a small box; the rubric rule on the inner side of notes in the left margin |
| 14 | Data (model runs, ledgered, meter read before and after): names sweep (obscure names), missed in-line citations, restored notes translated + citations expanded + kind, the most useful notes from the translation passes rated and shown, Psalm verses checked, V5 |
| 15 | The synopses visualized: research first, then options |
Later: IM Fell instead of EB Garamond (general consideration).

Round 7 page: `state/review/ab-2026-11-18-r7.html`. P1 Next and Previous (foot of the page; whole side zones; fixed
side arrows; in the running head), P2 Burton's note letters (alone; ruled box; filled box; raised), P3 the rubric rule
on a note in the left margin (left side; the side facing the text; the outer side).
Synopsis research (stage 15): `reports/Visualizing the Burton synopses.md`, notes in `research_notes/`. Recommends
re-setting the synopses as live type with drawn braces (columns per level, leaves linked to their sections, the signs as
jumps), three ruled compartments on the front page that unfold into each sheet, a brace outline below ~700 px and for
print, and the brace path in rubric for "where this page stands".

Status 2026-11-18 (usage limit reached): stage 12 is built and checked by hand in headless Chrome but NOT committed; its `burton check --all` was still running. Next session: re-run the check, then commit stage 12 (files: burton/site/render.py, build.py, static/edition.css, edition.js, templates/*.html).

Stage 15 begun (2026-11-18): the synopsis pages show the synopsis as a sheet (Burton's braces drawn, read left to right,
one column per level) by default on wide windows, with "As an outline" beside it. The front page (round 6) and the
"where this page stands" path (research report) are next, after the owner's round 6 choice.

### Where things stand (2026-11-18, evening)

Done and committed: stage 12 + Psalm check (d556b7b), synopsis as a sheet (68e5b4b), langid + h3 gate (6846623).
V5 on h3: P 0.962, R 0.952, B 0.960; still DEFER (D10). Next cycle: treat h3 as seen; rules for Latin titles in the
running text ("de atra bile" -> citation), and the missed phrases; then draw and label h4 (`gold-audit --label-round`).
Still to do (model runs, meter before/after): names sweep (obscure names), missed in-line citations, restored notes
(translate, expand citations, kind; tie to Burton's English first), rate the translation passes' notes for the margin.
Awaiting the owner: round 6 (front-page synopsis compartments), round 7 (Next/Previous, note letters, rule side).

### V5, second cycle (2026-11-18, night)

h3 studied and marked seen. Rules (burton/ingest/langid.py): a Latin title after "book", "tract", "consultation"… or
after an author or a title abbreviation, and "De X" in a sidenote, is a citation (64 title passages retired, e.g. *de
atra bile*, *pro hypocondriaco*, *Tr. de morbis amentium*); Latin pronoun and possessive forms; Latin whose only
"English" words are Latin forms (*more*, *his*); superscript endings joined to their run (*12ma*), never cut inside a
word; a Latin clause inside an English italic run wrapped as a passage (*…what shall I do? Vos O dii Averrunci…*, *si
cerebrum sit calidius, if the brain…*). Scorer: "&c" no longer counts as a word of a passage. Re-ingest: 26 passages
new, 71 records retired; translated ($0.95). Seen rounds: tuning, h1, h2 unchanged; h3 P 0.991 R 1.000 B 0.943.
Gate h4 (seed 20261119, 300 items, labelled blind, $1.07, no label corrected): **P 0.948, R 0.968, B 0.912**, so V5
stays DEFER (data/manual/deferred-checks.yaml has the errors). Also seen while labelling the notes sample: *John come
kiss me now* (3.2.3.1) is an English song title tagged Latin. Next cycle: English loan-words in italics (*decorum*,
*verbatim*), locator phrases before a bracket (*& passim alias*), capitalised Latin read as names, and the scorer's
"|"-joined labels (never exact) settled before h5 is drawn.

### Data passes (stage 14), begun 2026-11-18 night

Code written, not yet run (the 5-hour meter reached 89% at 23:53 UTC; no model run until it resets):
* `burton names-sweep` (names-v1): unlinked name forms from the rules' `name` verdicts, a blind identification each;
  the reader is to underline obscure, single-bearer, identified/probable forms with a ◇ window.
* `burton cite-sweep` (cite-sweep-v1): italic runs the rules judged `citation` that no rules record covers ->
  data/layers/citations-inline-model/.
* `burton restored-read` (restored-v1): restored notes tied to Burton's English (rules signals, then exact quote),
  the rest translated, citations expanded, kind.
* `burton note-rate` (note-audit-v1, note-rate-v1): spot check drawn (110 of 5,523 notes, data/eval/notes-spotcheck.yaml);
  first rater (in session) done: 110/110 sound, usefulness 3/2/1 = 38/42/30. Next: `--audit`, `--sample`, `--compare`,
  then `--all`; notes shown only if the rules pass (outcome recorded in the yaml).
Reader wiring for the four layers is still to do.
V5 cycle committed as a97b8f9 (check: 21 PASS, V5 DEFER). Stopped at 00:21 UTC with the 5-hour meter at 94% (weekly
13%); resume after 01:20 UTC: `note-rate --audit`, `--sample`, `--compare`; then the three sweeps, each with a
`--limit` spot check first; then the reader wiring, `check --all`, commits. Uncommitted: the four pass modules, their
prompts, the CLI wiring, tests/test_names_sweep.py, data/eval/notes-spotcheck*.

### Data passes, 2026-11-19 (early morning UTC)

* **Translator notes:** blind audit and rating of the 110-note sample done ($2.03). Raters agree on accuracy 107/110,
  usefulness 86/110 exact and 110/110 within one. Adjudicated: 2.2.4.1-f337 **wrong** ('dies' can be feminine, so
  Burton's 'ullam … diem' can agree), 3.1.1.2-f38 doubtful, 1.2.2.2-f68 sound. R1 passes (1/110 wrong), **R2 fails**:
  the rating pass rated f337 3 and not doubtful, so it would be shown. Per the rule fixed before labelling, **no
  translator note is shown until the owner decides**. Proposal in data/eval/notes-spotcheck.yaml: show only notes rated
  3 that the blind auditor also judges sound, then a fresh spot check of what would show.
* **Citation sweep:** complete ($6.57): 922 citations (751 expanded, 171 probable), 82 not citations, 4 unidentified.
* **Restored notes:** the restore rules duplicated 54 of Gowland's notes (Gutenberg marks one note twice, or far from
  his marker): rules/restore-v2 drops a note that repeats one of his in the same paragraph; 1,235 -> 1,181. Readings
  done for 612 ($6.73), then the headless `claude -p` login expired ("OAuth session expired"): the owner must sign in
  again (`claude` in a terminal, /login) before `burton restored-read` resumes (569 left).
* **Names sweep:** spot check of 40 forms only ($0.25; 22 would show); the full run (~5,300 forms, ~$33) waits for the
  login and spans two or more five-hour windows.
* **Reader:** restored notes with kind, Burton's English, the rest translated and references (each with ◇); found
  citations as § with a card (none of Burton's words hidden); obscure names underlined with a window. Each layer is shown
  only when its blind audit (`burton sweep-audit`, sweep-audit-v1, at most 3 % wrong) has passed; none has run yet, so
  the reader shows none of them. Checked in headless Chrome with the gate forced open in one build: 1.1.1.1, no overlaps.
