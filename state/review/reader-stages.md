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
* **Owner, 2026-11-19:** the remedy for translator notes is accepted: rate all; blind audit of every note rated 3 and not
  doubtful; show only those judged sound; a fresh spot check of what would show before any is shown (after the login).

# Round 7: owner's choices (2026-11-19)

Round 6 (front-page compartments): none satisfies; set aside for now. Round 7: **P1 B** (Next and Previous as the whole
left and right edges of the window) "but it should be some stylized symbol, not a simple arrow" (built with the
printer's manicule, ☜ ☞, in EB Garamond) · **P2 C** (Burton's note letters in a small filled red box, the letter in the
page colour) · **P3 B** (the rubric rule on the side facing the text), to be revisited: listed in
state/review/to-revisit.md.

# The synopses re-set by the printer's rules (side project, 2026-11-19)

Owner: look at the layout of the printed synopsis sheets and find a way to show them that flows on the web, on the
front page and at the opening of each Partition. Prototype: `state/review/synopsis-sheets-2026-11-19.html` (served
by `review-pages`, port 8790; it borrows fonts and images from site/private), built by
`tools/synopsis_sheets/proto.py` from `data/synopses/pN.json` (words verbatim; nothing in the edition changed).

* **The sheets' rules (R1-R7).** Heads that divide are set narrow, leaves run to the edge; a head stands at its
  brace's middle; a brace is pieces (curls, beak, rule), never stretched; "Or" in the members' column; leaves hang
  their turnovers; the italic locators and signs are the finding aids; short of width the printer gives way branch by
  branch (narrower heads, then a tall head turned, as "Not necessary, as Memb. 4 Sect. 2." on sheet A).
* **One component, three places.** The same sheet at full width, at a Partition's head (first sheet open, the others
  one line each with the sign column ♈ A ♊ ♉ B ♋ C) and on the front page (the three Partitions on one lighter,
  editorial brace, each folded to its sheets' opening lines). A brace is the fold button; a folded branch is a stub
  with its count ("21 heads"); pointing at a head inks the braces above it.
* **Responsive by the same rule (R7).** A short script measures each branch: a head stays beside its members while the
  width holds its words; a tall head with room along its brace is turned; otherwise the head is set over its members
  with a bracket. Deepest branches give way first. Without script, container queries give a rougher version.
  Measured on P1 ♈ + A (53 nodes, 17 ms): full width 0 set over, 2 turned (as printed); 900 px 5 set over; 640 px 9;
  390 px 19; no sideways scroll at any width (page 375 px wide on the phone preset).
* **Locators are the links.** Burton's own words (*Subsect.* 4, "6, 7, 8" number by number, "2nd.", a label or column
  heading where the locator is printed) link to the unit: 169/169 nodes with units. Sign links: 0 broken.
* Not checked: axe on this page, print, keyboard-only use beyond the brace buttons' names. Known blemish: where several
  nested branches are set over their members, their bracket ends gather at the bottom.
* **For the owner (Q1-Q4 on the page):** adopt this as the form everywhere (replacing "As a sheet / As an outline"
  and the front page's three boxes)? Turn tall heads as the printer did? Front page all folded, or the First
  Partition's first sheet open? Locators as links, or the section-number chips as now?

## Owner's answers (2026-11-19) and round 8

Owner, on the first version: "This looks pretty great." Settled: **the form** is used wherever the synopses appear,
with differences noted for the front page; **tall heads are turned**; **no ◇ on the synopses** ("the words are all
Burton's"; the branching's machine provenance stays in data/synopses/pN.json and is not shown). The front page keeps
its present layout, everything in one screen with the synopses folded; resting on a Partition's name opens it, not at
once. Asked for: folded braces that open slowly on hover, "more organic" (A/B allowed); a better or more Burtonian
word than "heads"; the synopsis labels on the front page redesigned.

Round 8, on the same page (`state/review/synopsis-sheets-2026-11-19.html`, sticky switches at the top):
* **H, opening on rest** (0.42 s rest, the brace inks red while waiting; leaving a branch opened this way folds it
  after 0.9 s; a click keeps it; touch and keyboard open by tap/Enter only): **H1 Unfurl**, the whole branch in one
  movement (height grows from the stub over ~1.15 s, members fade in from the beak outward); **H2 Grow**, one level at
  a time (~0.95 s apiece) while the pointer rests. Measured in the pane: H1 0 -> 446 px over ~1.1 s, folding ~0.75 s
  after the linger; H2 inner branches open 0 -> 2 -> 5 -> 8 at ~1 s steps.
* **C, the count on a folded brace:** C1 "25 parts" (Burton's anatomy word), C2 "branches", C3 "&c.", C4 numeral;
  a folded Partition counts "8 sheets".
* **L, the front page's labels:** L1 "The Synopses" braced to the three Partitions (a small sheet; editorial braces
  lighter); L2 a heading, with rubric numerals I II III in the key column.
* Front mock at 1400 x 900: 899 px of content in a 900 px frame, so it fits one screen folded.
* Fixed on the way: a branch set over its members collapsed to its stub's height once `.kw` had a min-height
  (flex-basis 0 in a column); after the fix, 0 spills and no sideways scroll in all three frames at 390, 640 and full.
* Not checked: axe, print, Safari/Firefox (the height animation needs `interpolate-size`, Chrome 129+; elsewhere it
  opens without the growth). At phone width the counts take a fair share of each folded line.

# The owner's notes of 2026-11-19 (second set)

* Search matched parts of words ("test" found "Potest"): words now match whole; a trailing * matches beginnings.
* "Why is this in-line: And this belike gloss:…": the obsolete-word option put the sense, and the model's name, in
  the line. Those glosses now stand in the margin as cards (Webster by name, a model by its ◇), shown with the option.
* "When toggling notes away the languages should not still be different colors": "Hide all notes" now gives the text
  as printed: no language colours or tints, no underlines or links in the line, Burton's abbreviations, the original
  in place of any translation mode, no glosses, brackets or page numbers.
* Option labels shortened ("Hide all notes (the text as printed)" for "Nothing but the text", and the rest).
* The search, options and light/dark signs float at the top right once the running head has scrolled away; the
  options open under them.
* Design questions, round 8 (state/review/ab-2026-11-19-r8.html): F1 the front matter's contents (tablet; numerals;
  before and after; thumb index), D1 showing what the options do (live sample; before/after; "show me").

# The owner's notes of 2026-11-19 (third set) and round 8's answers

* Round 8: **F1 A** (the ruled tablet, a hedera before the page you are on), "but I want to see how A, B and D look on
  the actual page"; **D1 A** (a live sample at the head of the options).
  * F1: one markup for all three, chosen by CSS. A is the default; `?fm=B` or `?fm=D` on any front-matter page shows
    B or D and is remembered from page to page, `?fm=A` goes back. D stands at the window's edge from 1100 px (below
    that it falls back to A); in D a front-matter page sets all its notes in the right margin, so that the index has
    the left (measured on "To the Reader" at 1100-1920 px: no left-margin note, index clear of the text).
  * D1: "As you choose", a few lines of 3.2.3.1 (Hercules de Saxonia, Ovid's line, Hesiod, *belike*) with a small
    margin, at the head of the options and kept in view while they change. Its words are checked against the base
    text at build time; its translation, citation and gloss come from their layers with their ◇. It answers the
    options for what to show, the translation mode, citations, obsolete words and the Latin colour; not "translation
    first" (it shows the machine translation, to keep Gowland's wording out of it).
* "Glosses should not exist when one toggles away everything but the core text": "Hide all notes" now hides every
  translation as well (on hover, beneath, facing, the Dedication's, Gowland's brackets): counted 0 visible on Ad
  Librum and 1.1.1.1, against 2 and 19 with the notes shown.
* The key: no line for the hederas; the last group reads "Who made it"; every source has a sign, its name on hover:
  g Gowland, dj Dell & Jordan-Smith, **w** Webster 1913, **kjv** the King James Bible, **pg** Project Gutenberg (the
  restored notes, which carried a ◇ for their source, wrongly: the ◇ is for a model's work).
* Also fixed: the hederas at the window's edges sat at different heights when the page titles differed in length
  (the hidden title took up room); the title is now out of the flow and the hedera stays in the middle.
* "Where are we at with V5. Can't you do it yourself?": a third cycle, done here (see deferred-checks.yaml): h4 seen,
  rules changed, a fresh round h5 drawn and labelled blind. h5 P 0.959, R 0.940, B 0.979: still below 0.98 / 0.97.
* Translator notes (the remedy, carried out): every note rated (2,895 asked, $15.29); the 1,492 rated 3 and not
  doubtful audited blind (note-audit-v1, $18.37 in two windows): 1,432 judged sound. A fresh spot check
  (data/eval/notes-spotcheck2.yaml, seed 20261121, 60 of the 1,432, rules fixed before labelling: S1 none wrong,
  S2 at most 3 doubtful) labelled by Claude in session, then blind by a different model (claude-sonnet-5-5, $0.45):
  54/60 agree; of the 6 disagreements, 5 were the second rater unable to confirm a locus and 1 called Lucan's text
  wrong. All 6 were settled from the Perseus texts in data/source/corpora (Lucan 10.407 "Nulla fides pietasque",
  Cicero Fam. 5.12.1, Gellius 5.11.14, HA Hadrian 18) or by reading the note: 0 wrong, 0 doubtful, passed. A
  cleared note now stands open in its translation card with its ◇; the rest stay folded under the chevron. Limit:
  60 with none wrong bounds the wrong share below about 5 % (95 %), not to zero.

## Round 8: the owner's choices (2026-11-19) and the reworked opening

Choices: **H2 Grow** (listed in to-revisit.md: "feels a little too chaotic"), **C3 "&c."** on a folded brace, **L2
rubric numerals** I II III for the front page's Partitions. Owner asked for the windows' hold indicator on the braces
(something visible that says resting here will open or fix), and for one brace at a time unless the pointer stays on
the broader brace. The locator question was unclear; it is now shown on the page as two renderings side by side.

Reworked (prototype only; the switches for H, C and L are gone, the choices are fixed on the page):
* Resting on a folded brace fills it with rubric from the beak outward (0.65 s, the windows' time), then it opens one
  brace deep, its inner braces folded. Resting on: it fills again (0.9 s) and the branch is **fixed** (faint rubric
  brace; stays when the pointer leaves). Resting on still: inner braces open one at a time in reading order, level by
  level, each filling first (0.45 s fill, 0.3 s pause). Moving off the brace stops the growing; resting on an inner
  brace opens just that one. Not fixed: folds 0.9 s after the pointer leaves the branch. Click: open and fix, or fold
  a fixed branch. A Partition opens onto its sheets and stops there.
* Only real pointer movement ends a rest: an opening sheet narrows its head and slides its brace from under a still
  pointer, and the browser's leave/enter reports for that are ignored (the first build stopped there).
* Checked in the pane (1400 x 900): sheet A grew to 9/9 inner braces while rested on; on ♈, moving off after one inner
  brace left 1 open 4 s later, the branch fixed; the front page's First Partition opened, fixed, 0 sheets opened, page
  still fits its 900 px frame. No console errors.
* **Locators (owner, 2026-11-19): "A is fine."** Burton's words stay as printed and the small box with the division's
  number follows them as the link, as the edition does now (361 boxes on the review page). Burton's own "Subsect. 4" is
  no longer made the link; `link_locators` stays in proto.py, unused.

## The synopses as Burton's sheets, in the reader (2026-11-19)

Owner: "Looks solid, add it to the reader." Ported from the prototype (tools/synopsis_sheets) with the settled choices:
* `burton/site/synopsis.py`: `tree_html(tree, root, titles, fold)` sets the sheet (classes `syn-*`); `front_html` the
  front page's three keyed Partitions. A folded branch is only marked (`data-fold`); edition.js folds it, so without
  script every brace is open. Links into the book are the number boxes (`syn-ref`), as before; signs are `syn-see`.
* `edition.css`: the sheet, the brace pieces, the hold fill, the fixed tint, "&c." stubs, the no-script width rules;
  the old outline, the 2026-11-18 sheet view and its "As a sheet / As an outline" switch are gone.
* `edition.js`: fit (R7, measured), turned heads only where a branch lacks room upright (the first port turned three
  heads at 1.1.1.1's 760 px that the printer kept upright), folding on load, rest -> fill -> open -> fill -> fixed ->
  inner braces one at a time, click, signs and "where this stands" links open the way to their node.
* Places: the synopsis pages (every brace open; page up to 90rem wide; "Open all" / "Fold to the first brace");
  the head of each Partition's first page (first sheet open, the rest folded; reaches into the margin from 1,100 px);
  the front page (three Partitions folded, rubric numerals; resting on a name opens its sheets under it, across the
  column; links to the three synopsis pages below).
* Checked in the pane at 1400 x 900: front page fits above Contents; 1.1.1.1 760 px wide, 7/8 sheets folded, one head
  turned ("Habits, as Subsect. 4."); p1 synopsis 1,321 px wide, sheet A wholly in Burton's form; resting on "The
  Second Partition" opens and fixes it with 0/9 sheets opened. V10k's synopsis steps now use the brace buttons.
* `burton check --all` (2026-11-20): 21 PASS, V5 DEFER (D10), 0 FAIL. V6 846 pages, 192,631 links, 0 broken; V10a 0
  serious (the sign links are underlined again: colour alone failed it, 10 findings, in the first run); V10k 22/22;
  V11 561/561; L1 3.2.4.1 79 notes, 37 shortened, 0 held back. L1 now waits for the page to lay its notes out (up to
  10 s) instead of a fixed 150 ms: on a busy machine it had measured 3.2.4.1 and 1.1.3.2 before layout, and the
  committed edition.css/js failed the same way.

# The owner's notes of 2026-11-20

1. Glosses must not exist when everything but the core text is toggled away (re-stated; see 2026-11-19, third set).
2. The key: no hedera line; the section reads "Who made it"; Webster, like every source, a sign (re-stated).
3. "Hide in-line citations" should switch between Burton's own abbreviated citations in the line and the § with its
   note in the margin (as now), not between the § and nothing.
4. The foot: Authors Cited, About, Table. "About this edition" and "How to read this book" rewritten as one shorter
   page, and a very short version made to sit in the front page's blank space. The colophon sentence (Gowland's
   edition; every translation labelled …) goes: the informational pages say it.
5. In *Despair* (3.4.2.2) "Joseph. lib. 1 de bello Jud. cap. 14, L. Danaeus in Aphoris. polit. pag. 226" stands in the
   line with nothing: "clearly some things have been missed" (it is in the held-back citation sweep).
6. The front page "in one page", without the running head or the foot.
7. Remove "Each on its own page, with the printed sheets: I · II · III".
8. Clearer signs that resting the pointer will open something: perhaps the "&c." brace moving, and something on the
   main brace.
9. The front page's Contents folded by default.
10. The front-matter box halfway between before and now: not out over the sides, not so tall.
11. At the head of each Partition the synopsis folded wholly, as on the front page, with no "Burton's synopsis" and no
    "The synopsis on its own page …": just "I The First Partition {&c."
12. With the front page on one screen, the options widget fixed (not floating), perhaps in the about box.
13. The live sample at the foot of the options, called "Example passage" (not "As you choose").
14. Choices to include the marginal notes of each source, each one on or off.
15. "The Synopses" as —— Synopses —— (rubric rules either side), better aligned.
16. Not every sign on the front page's synopses is red.
17. "Point at a panel …" no wider than the rules above and below "Enter, gentle Reader".
18. The restored notes cite Project Gutenberg; if its text is an edition of the *Anatomy*, cite that edition.
19. The subtitle a little smaller, so "of it." does not wrap.
20. V5: "Just do the remainder of V5 yourself; I can't hand check it."

## The notes of 2026-11-20, carried out (reader)

* 1, 2 were already so in the build (counted with "None: the text as printed" on 3.2.3.1, 1.2.2.1, 3.2.2.1 and Ad
  Librum: 0 margin notes, glosses, translations or § visible; the key has no hedera line and ends "Who made it", w for
  Webster). The owner was most likely shown an older build by the service worker, which answered from its cache first.
  It now asks the network first and falls back to the precache offline, so a rebuilt edition shows on the first load.
* 3, 14: "What to show" became **Notes in the margin**, one switch per source: Burton's notes, his notes restored from
  Democritus Minor's edition (°), Gowland's notes (private), translations, citations in his text written out (§; off:
  as he printed them, in the line), Bible verses, obsolete-word glosses, and "None: the text as printed". A source
  switched off takes its markers with it and no room in the margin (the layout skips it). Settings saved under the old
  names carry over ("Hide in-line citations" -> citations off; "Only Gowland's notes" -> every other source off).
  Counted on 3.2.3.1, each switch alone: Burton's 281 -> 0, restored 50 -> 0, Gowland's 253 -> 0, translations 180 +
  87 "Author trans." -> 0, § 9 -> 0 with Burton's own words back in the line (48 spans, none inside his notes),
  Bible verses 2 + 1 -> 0; the other sources unchanged each time.
* 13: the live sample is at the foot of the options as "Example passage" (no longer sticky).
* 4: the foot reads Authors cited · About · The Table; the colophon sentence is gone. "About this edition" and "How to
  read this book" are one page, About (1,243 words against 1,829); guide/ is no more. The front page carries a short
  version in its about box.
* 18: the restored notes cite **Democritus Minor's edition**: Project Gutenberg #10800 is the nineteenth-century "new
  edition, corrected, and enriched by translations of the numerous classical extracts, by Democritus Minor" (its title
  page; PG gives no date and a web search did not settle one, so none is given), re-edited by Karl Hagen against the
  1638 edition. Sign **dm**; the hover names PG #10800 and the note's number there.
* 6, 7, 9, 12, 15, 16, 17, 19 (the front page): no running head or foot; the engraving the window's height; the
  subtitle on one line (scaled with the window); the hint as wide as the rules of "Enter, gentle Reader"; an about box
  with the short text, the search / options / light-dark signs (the options open over the page from there) and About ·
  Authors cited · The Table; a panel's stanza takes the box's place while the pointer is on the engraving;
  —— Synopses —— between rubric rules, the three Partitions on one line each; Contents folded the same way (a link
  into them opens them). "Each on its own page …" is gone (About says where the synopsis pages are). Measured: one
  screen at 1920 x 1080, 1400 x 900, 1366 x 768 and 1280 x 720 (page height = window height; short windows set
  tighter), no sideways scroll, every stanza within its box. Every sign in the synopses is red now: the planets and
  signs in Burton's words were ink (♄ ♃ ♂ and four `sym` runs), and the supplied [☾] was grey (its brackets mark it).
* 10: the front-matter tablet runs on in three centred lines inside the page (was one a line, seven lines; before
  that one row as wide as 64rem).
* 11: at the head of each Partition's first page, "I The First Partition {&c." alone, folded as on the front page.
* 8: resting on a folded brace now shows what will happen as it fills: the stub draws itself taller, the "&c." spreads
  in rubric with a rule running under it; a Partition's name is underlined as it fills; an open brace filling to stay
  fixed thickens and glows. Frames at 0.35 s / 0.9 s / 1.7 s on the First Partition: filling, opened, fixed.
* Not done here, for the meter (weekly 86 % at 2026-11-20 06:00 UTC, against the 90 % stop): 5, the held-back
  citation sweep (918 records; a full blind audit is about $8), and 20, the V5 cycle. See the closing note.
* Counted after the last build: the front page's synopses (all opened) have 43 signs, 43 in rubric.
* Fixed on the way: the first build of the sign rule wrote a control character for its back-reference, which replaced
  every sign in the synopses (V10's parser stopped on it); the rule now inserts the sign itself. V9 failed once on ▸ ▾
  (no glyph in the fonts) in the Contents' fold mark; it is drawn now.
* `burton check --all` (2026-11-20): 21 PASS, V5 DEFER, 0 FAIL. V6 844 pages, 190,569 links, 0 broken; V9 266/266;
  V10 0 parse errors; V10a 0 serious; V10k 22/22; L1 3.2.4.1 79 notes, 37 shortened, 0 held back; OFF 499/499
  precached, 6/6 pages offline.

## The missed in-line citations (note 5): the sweep's remedy (2026-11-20)

Owner, on *Despair* (3.4.2.2): "Joseph. lib. 1 de bello Jud. cap. 14, L. Danaeus in Aphoris. polit. pag. 226 … clearly
some things have been missed." They were in the citation sweep (data/layers/citations-inline-model/, 918 records),
held back since its blind sample failed (2 wrong of 50: two Aquinas write-outs with the wrong part of the Summa).
Owner: "Start now anyway" (past the 90 % weekly stop). The remedy, as for the translator notes:
* Every record judged blind (`sweep-audit --all cites`, prompt sweep-audit-v1, **claude-sonnet-5-5** to save the
  meter, $3.05 list): 848 right, 64 doubtful, 6 wrong. Both Aquinas errors were caught (as doubtful). The Despair
  example: right (Josephus, Jewish War 1.14; Daneau, Politici aphorismi).
* Withheld: everything judged wrong or doubtful there, in the first sample, or in the recheck: 82. Shown: 836.
* The gate (`sweep-audit --recheck cites`): a fresh sample of 50 of the survivors (seed 20261120, not in the first
  sample), drawn after the full pass and before any judgement, judged blind by claude-opus-5-5 under the first rule
  (at most 3 % wrong): **0 wrong, 5 doubtful: passed**. The 5 doubtful (a sure author where the text allows only
  "probably", one book title) are withheld too. Limit: 5 doubtful in 50 suggests about one shown record in ten
  states its author or work more surely than the passage alone allows; none in the sample was wrong.
* The reader shows the layer (§ with its ◇ card) less the withheld records (build.py, `sweep_audit.withheld`).

# The owner's notes of 2026-11-20 (second set)

1. A fitting "expand all" sign (seventeenth-century if possible) for the synopses' Partition sections.
2. A way to close the reading options (at least on the front page).
3. The underline on resting (front page synopses) runs twice, the second time seemingly doing nothing. "Multiple
   underlines are good! Each time they finish they should open up another full bracket layer." It should also work on
   the heads of the first bracket layer, not only the brace (which moves as it opens, making a steady rest awkward).
4. Names and authors in the margins underlined, with their windows (especially noting their associated text).
5. "Now that the model's notes are rated by significance, give me samples of them to judge what the cutoff for
   inclusion should be."

## The second set of 2026-11-20, carried out

* 3 (the rest, reworked): every completed fill now opens one more full layer of the branch: first the branch, then
  every brace at its next depth together, and so on while the pointer stays (T 0.65 s for the first, 0.9 s for each
  layer after, 0.25 s between). What resting opens stays open; a click folds it. No more second fill that only
  "fixes". The heads of the Partitions and of each sheet's first layer are places to rest as well (they do not move as
  the branch opens; the brace does), underlined as they fill, once per layer. The fills are animations now, so each
  layer's underline runs from the start. Measured on the front page, resting on "The First Partition": 1 open at
  1.0 s, then 9, 29, 56, 65 braces at 2.0, 3.2, 4.4, 5.6 s (66 in all).
* 1: the expand-all sign is the printer's **asterism ⁂** (three stars, which seventeenth-century printers set to mark
  the whole of a thing or a passage passed over), after each Partition's name on the front page and at the head of
  each Partition's first page: a click opens every brace (65 of 65), again folds the Partition. Shown only with
  script.
* 2: the reading options close by a × at the panel's corner, by Escape, or by a click anywhere outside (front page
  and the floating panel elsewhere).
* 4: names in the margin: Burton's written-out citations in his notes and in the § cards link to the author, with
  the same window as a name in the text, which adds "Cited here: …" where the citation names a work; names in the
  restored notes are linked as in his own. On 3.2.3.1: 243 citation links and 9 restored-note names; 75 authors'
  window data on the page.
* 5: samples to judge the translator notes' cutoff: state/review/note-cutoff-2026-11-20.html (tools/
  note_cutoff_samples.py, seed 20261120): 14 rated 3, 14 rated 2, 12 rated 1, 8 flagged doubtful, each with its
  passage, the machine translation and the note, its kind and audit verdict, and the table of ratings by kind (3:
  1,456; 2: 1,866; 1: 1,755, not doubtful). Shown now: 1,396 (rated 3, sound; 36 of the 1,432 sat on passages the
  V5 re-ingest changed).

## V5, the fourth cycle (2026-11-20; owner: "just do the remainder of V5 yourself")

Done without the owner's hand check: the gate h6 was labelled blind by two models (opus, sonnet) and their 13
disagreements settled by Claude from the text (data/eval/langid-holdout6-settled.yaml). The lever: short runs decided on
one or two lexicon hits, and capitalised runs the names sweep ruled not a name, take a model ruling (2,361 rulings).
**h6: P 0.990, R 0.941, B 0.947** (targets 0.98 / 0.97 / 0.95): precision passes, recall and boundaries do not; V5
stays DEFER. The re-ingest changed 129 units; 182 passages re-translated ($5.06), selftrans and Dell & Jordan-Smith
re-run. Details and the misses: data/manual/deferred-checks.yaml.

## V5, fifth cycle (2026-11-20; owner: "Run a fifth")

h6's errors, read closely, were on the line between a reference and Latin (three of them raters putting a cited title's
words or a locator into the foreign part). Lever: reference runs with two or more Latin words, pieces the trim cut off a
Latin run, and roman prepositions before a Latin passage ("in secundis") take a model ruling (310 rulings); a ruling of
kind title keeps a cited title a reference (which returned 10 older title passages to references). The raters' prompt
became gold-audit-v2 (LABELLING.md's reference conventions spelled out), set before h7 was drawn; h6's gold is unchanged.
**h7: P 0.958, R 0.968, B 0.967** (targets 0.98 / 0.97 / 0.95): boundaries pass, recall one item short, precision
fails; V5 stays DEFER. None of h7's four false positives was made by this cycle. 11 rater disagreements settled
(data/eval/langid-holdout7-settled.yaml); one settlement doubtful ("Phoebades"), recorded, not changed.


# Human-UX review and reader upgrades (2026-11-25 / 2026-11-26)

* **5-layer audit & decision workbench:** `tools/human_ux_workflow/` and `state/review/human-ux-2026-11-25.html` (parked ideas recorded in `state/review/human-ux-parked-2026-11-25.md`).
* **Owner's choices carried out:**
  * **Fixes (`F1`–`F5`):** `F1` keeps the front page in two columns with zero scrollbars across `1440×900`, `1280×800`, `1366×768`, and `1920×1080` and fixes horizontal overflow at `1024×900` and phone (`390×844`) widths; `F2` centers and highlights deep-link arrivals (`#3.2.3.1-n5`, paragraph anchors) after margin layout settles; `F3` makes `.ic-m` (`§`) citation markers keyboard-focusable (`tabindex="0"`, `role="button"`) and interactive on tap/Enter/Space plus subtle narrow-screen Gowland underlines; `F4` adds two-tap preview parity on touch and `< 1100 px` windows (`fs-panel`, `fs-title`, `a.nm`, `a.xref`); `F5` clears `.two-side .unit` left margin in `@media print`, matches `.mn-fold.hot > .fold-more` fade color, and adds **Reset** buttons to the front page and reading-options drawer.
  * **Ergonomics (`E1`–`E5`):** `E1` anchors the top visible paragraph across reading-option toggles; `E2` stores reading place in `localStorage` (`burton-ribbon`), showing side-by-side **Enter** | **Continue ☞** buttons on the front page without adding height, **Silk ribbon** in Contents, and a dismissible *"Last read here"* unit-top link (hidden in *"As printed"*); `E3` adds a margin `¶` button copying formatted citations (`Burton, The Anatomy of Melancholy, ... ¶N [p. P] — URL#id`) with `¶` added to `options.html` for font subsetting; `E4` adds live filtering, `Author`/`Citations` sorting, and an A–Z jump bar to `authors/` and `table/` (`tableHeadA` anchors); `E5` adds `/`, `[`/`]`, `p`/`Shift+Enter` preview lock (guarded against scroll-induced hover clobbering), and `Escape` focus return.
  * **Elucidation & navigation (`V2`–`V6`; `V1` skipped):** `V2` adds `burton/site/labyrinth.py` with 12 curated entrances (*Ways into the Labyrinth* with `~N min` reading times) and *Sortes Burtonianae* (**Open at a venture**, `assets/sortes.json`) tucked inside folded Contents; `V3` adds `burton/site/glossary_page.py` and `/glossary/` from `data/glossary.yaml`; `V4` adds collapsed `+ literal` comparison toggles inside Burton's self-translations (`.mn-lit`, phrasing `.ft-lit` in prose); `V5` harvests substantive `note`-kind sidenotes into the top-left `{` drawer on units `>= 2,500` words including a compass badge on `djr`; `V6` coalesces unanchored sibling Gowland segments sharing one endnote anchor, tightens `1100–1379 px` margin typography, and priority-folds editorial `.mn` notes before Burton's sidenotes.
  * **Revisits (`P3`, `H2`):** Updated `state/review/to-revisit.md`: left-margin Burton sidenotes align flush-right against their rubric rule (`?p3=left` compares); synopsis brace cadence tuned to settle-first timing (`--syn-t-open: .82s`, `T_PAUSE: 620 ms`).
* **Verification (`ruff`, `pytest`, full private + public builds & verifiers):** `V2h` sidenotes 5703/5687, foreign 7865; `V3h` markers 13752/13752; `V4h` script_chars 12218, untagged 0; `V6` pages 846, links 204444, broken 0; `V8` leaks 0; `V9` glyphs 276/276 private, 255/255 public; `V10` 846 pages, 0 parse/a11y issues; `V10a` 44 axe runs, 0 issues; `V10k` 22/22; `L1` 10700 notes, 0 overlaps, max_drift 22.8 rem; `HY` 48879 soft hyphens, 0 stray; `OFF` 501/501 precached; `pytest` 163 passed.
