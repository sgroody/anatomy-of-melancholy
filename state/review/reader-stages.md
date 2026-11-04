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
| 5 | Windows on cited authors' names (`burton/site/names.py`; hairline, R5 C) and on cross-references; CK3-style lock | (this stage) |
| 6 | In-line citations and Bible verses | to do |
| 7 | Language colours in the line, the in-line switch, Burton's own English, long passages | to do |

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
