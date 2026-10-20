# EPUB Survey — *The Anatomy of Melancholy*, ed. Angus Gowland (Penguin Classics)

Source file: `C:\Users\Grood\Calibre Library\Robert Burton\The Anatomy of Melancholy (1423)\The Anatomy of Melancholy - Robert Burton.epub`
(10,941,768 bytes; Calibre id 1423). Surveyed 2026-10-20 with the scripts in `survey/scripts/`.
Every number below comes from those scripts. Paths are relative to `EPUB/xhtml/` inside the EPUB.

> **Edition date.** The OPF says EPUB 3, published 2021-03-29, ISBN source `9780241533758`,
> `dc:rights` "All rights reserved". The brief says 2023, so this may be a later printing of the same
> e-book. The edition is cited as **Gowland 2021** below.

---

## 1. What the EPUB actually is (read this first)

Gowland's *Note on the Text* (`note_on_text.xhtml`) says this is an edited, modernized reading text.
It is not a diplomatic transcription. His own description of the changes:

| Gowland's editorial change | Consequence for this project |
|---|---|
| A *Mischtext* of the six editions 1621–51, based on the 6th (1651) | Fine as a base text, but it is Gowland's text, not any single early edition |
| English spelling and word division **modernized** to OED headwords | **The EPUB has no original spelling.** "Modernized spelling as an optional layer over the original" is not possible from this source (see Decision 3) |
| Unusual Latin spellings "modified or corrected"; accents removed except on proper nouns | Latin is normalized too |
| `l.` and `c.` in references expanded to `lib.` and `cap.` | Some citation expansion has already been done |
| **Translations of Latin and Greek are Gowland's own, in square brackets** | About 5,000 bracketed translations are inline in Burton's text. They are copyrighted editorial matter and must be separable (§4) |
| Interpolations in **braces** `{…}` | Editorial additions inside Burton's text |
| Burton's sidenotes **"pruned aggressively"**: Latin that Burton translates in the main text was removed, and notes made only of such Latin were deleted with their markers | **Sidenote counts cannot match Burton's originals.** The deleted material is not in the file |
| Burton's descriptive marginal tags **omitted** | Not recoverable from the EPUB |
| Note markers placed *before* the words they gloss (17th-century convention) | Keep this. Anchor positions are meaningful |
| 3,907 Explanatory Notes (endnotes) by Gowland | Copyrighted editorial apparatus, separate from Burton's notes |

## 2. File map

| Files | Content | Size |
|---|---|---|
| `cover`, `brand_page`, `title`, `copyright`, `about_the_author`, `chronology`, `introduction`, `further_reading`, `note_on_text`, `follow_penguin` | Penguin/Gowland matter (exclude) | — |
| `preface.xhtml` | Half-title (exclude) | — |
| `preface001` | The Argument of the Frontispiece (verse) + frontispiece image `pg003.png` (1151×1900) | 9 KB |
| `preface002` | Dedication (Latin + Gowland's "[Translation]") | 3 KB |
| `preface003` / `preface004` | *Democritus Junior ad Librum suum* (Latin verse) / **Gowland's** "[Translation]". Printed on facing pages: pp. 6, 8, 10 vs 7, 9, 11 | 10 + 10 KB |
| `preface005` | The Author's Abstract of Melancholy, Διαλογικῶς | 9 KB |
| `preface006` | Democritus Junior to the Reader ("DJR"), one file, no internal divisions | 460 KB |
| `preface007` / `preface008` | *Lectori male feriato* / **Gowland's** "[Translation]" | 2 + 2 KB |
| `preface010` | *Heraclite fleas, misero sic convenit aevo* | 3 KB |
| `chapter001`, `chapter002`, `chapter003` | Synopses of Partitions 1–3 (images + hidden text) | 23 / 26 / 17 KB |
| `chapter001-01…03`, `chapter002-01…02`, `chapter003-01…04` | Partition text | 2.3 MB / 1.0 MB / 1.8 MB |
| `footnotes`, `footnotesa`, `footnotesb`, `footnotesc` | **Burton's sidenotes** for DJR, P1, P2, P3 | 1.5 MB |
| `notes001…003` | **Gowland's** Explanatory Notes | 1.5 MB |
| `index.xhtml` | Burton's "Table" (alphabetical index, from 1624) | 89 KB |

## 3. Structure encoding

* **Partitions** are `h2.chapter_title`. Below that, heading **tag levels do not follow the hierarchy**.
  `MEMB.` is an `h3.mem_head_s2`, `SECT.` is an `h4.section_head1`, `SUBSECT.` is an `h4.subsect_head3`,
  and the subsection's descriptive title is an `h3.HeadA0`.
  Example from `chapter001-01`: `h4 SECT. 1.` → `h3 MEMB. 2.` → `h4 SUBSECT. 1.` → `h3 Digression of Anatomy`.
* **Combined headings.** One element sometimes carries several levels, e.g. `h3.mem_head_s2` "MEMB. 1. SUBSECT. 1." (`chapter001-01#nat0001377`).
  So the hierarchy must come from the **numbering text**, not from tags.
* **Opening headings exist only as images, with `alt=""` and no text alternative.**
  `pg135.png` is the brace heading "The First {Section. Member. Subsection.}" for P1, after `#nat0001098`.
  `pg431.png` and `pg669.png` are the same for P2 and P3.
  **`pg142.png` (`#apg142`) is the only copy of the title of 1.1.1.2**, "The {Definition / Number / Division} of diseases".
* **Navigation document.** It has 149 entries of the form `1.1.1.1 Title`, which give a usable P.S.M.S key per unit.
  Walking the headings finds 150 text titles plus the `pg142` image title, so there are 151 candidate units versus 149 in the nav. Two must be reconciled in M1.
  In Partition 3, three titles have no Sect./Memb./Subsect. heading immediately before them:
  `chapter003-02#nat0014996` (3.3.1.1), `chapter003-03#nat0015644` (3.4.1.1) and `#nat0015982` (3.4.2.2).
  One nav label is attached to the wrong file: "The Synopsis of the First Partition" links to `chapter001-01.xhtml` (the text), while the synopsis is in `chapter001.xhtml`, which the nav labels "THE FIRST PARTITION".
  `preface004` and `preface008` (Gowland's translations) are not in the nav.
* **End matter of P3:** `h4.part_end_head_s4` "SPERATE MISERI, CAVETE FOELICES." and "FINIS." in `chapter003-04`.
* **10 headings contain note markers**, e.g. 1.1.1.5 `chapter001-01#nat0001198` and 3.3.1.1 `chapter003-02#nat0014996`.
* **Fake small caps.** 220 of 221 `span.small_caps` contain uppercase letters (`S<span class="small_caps">UBSECT</span>`).
  So the stored text is uppercase, and a real small-caps rendering needs the case handled in CSS, not in the text.
* **Page markers.** There are 959 `span[epub:type=pagebreak]` (`pg2` … `pg1081`): 956 in Burton's text and 3 on Gowland's translation pages (`preface004`).
  Within files, **81 page numbers are skipped**, e.g. `chapter001-01` 148→150 and `chapter003-02` 916→922.
  There are 4 more gaps from the facing-page Latin/translation layout (pp. 6–11). No page marker splits a word.

## 4. Notes

| | Count | Encoding |
|---|---|---|
| Burton's sidenotes (refs = bodies) | **5,703** (3 of the refs sit on Gowland's translation pages `preface004`/`preface008`; found in M0) | `a.noteref[epub:type=noteref]` with text `fn123` → `footnotes*.xhtml#TFootnote_N`, which is `aside.footnote[epub:type=footnote]` with `a.backlink` |
| Gowland's endnotes (refs / bodies) | **3,907 / 3,907** | `a.noteref` with text `123` → `notes00N.xhtml#ch…_en_N`, which is `aside[epub:type=rearnote]` |
| Broken note hrefs | 0 | |
| Duplicate ids | 0 | |
| Sidenote bodies containing another note ref | 0 | |

* **Sidenote numbering** runs continuously through each partition and restarts at 1 for each.
  DJR is 1–747, P1 1–1654, P2 1–1269, P3 1–2026, with no gaps or reordering.
  Id prefixes are `sFootnote_` (DJR), `TFootnote_` (P1), `VFootnote_` (P2) and `VWFootnote_` (P3).
* **One mis-linked endnote.** In `chapter003-02`, the ref `id="chi3_en30"`, after the Chaucer line "And eke the Owl that of death bode bringeth", points to `notes003#chh3_en_30` (a note on Xenophon) instead of `#chi3_en_30` ("eke: Also. bode: Omen"). As a result, `chh3_en_30` has two refs and `chi3_en_30` has none.
* **Sidenote content** (5,703 notes):
  * 2,888 are shorter than 25 characters.
  * 2,268 contain `lib./cap./c./l./epist./tom./consil.`-style locators.
  * 1,489 contain a Gowland bracketed translation.
  * 713 are a bare author name, most often `Hor.` (65), `Ovid.` (43), `Seneca.` (39), `Virg.` (19), `Plautus.` (19), `Catullus.` (17) and `Idem.` (11).
  * Locator tokens: `lib.` 1,586, `cap.` 1,007, `c.` 688, `l.` 481, `epist.` 211, `sat.` 83, `ep.` 79, `dial.` 74, `fol.` 72, `tom.` 69, `consil.` 47.
  * The longest note is `footnotesa#TFootnote_30529` (1,315 characters): Latin, a Gowland translation, then a run of citations.
* **Citations are italicized token by token.** There are 49,039 `<em>` elements, and 16,952 places where italics close and reopen across punctuation, e.g. `<em>Scalig</em>. <em>exercit</em>. <em>365 sect</em>.` (`footnotesa#TFootnote_29344`). The citation parser must merge these runs.

## 5. Languages and scripts

* **No `lang` attribute anywhere except `lang="en"`** on the 25 `<html>` elements. Every foreign span is untagged.
* **Greek:** about 1,100 characters, in about 200 word-runs. 158 runs are in the text (most in `chapter001-01` (44) and `chapter002-02` (34)) and 41 in sidenotes. Examples:
  * Hesiod in verse at `chapter001-01#nat0001171`–`75`.
  * "εὕρηκα I have found" (`chapter001-02`) is a **self-translation**.
  * "Οὐδὲν πενίας βαρύτερόν ἐστι φορτίον, no burden (saith *Menander*) so intolerable as poverty" (`chapter002-02`) is a self-translation.
* **Damaged Greek:**
  * **Mixed script.** "Mανία γὰρ οὐ πᾶσιν ὁμοία" (`preface006`, near fn190) begins with Latin **M** (U+004D) instead of Greek Μ (U+039C).
  * **Breathings typed as spacing modifiers.** "ʼˋΗ πῖθι ἢ ἄπιθι" (`footnotesb`, n. 611) uses U+02BC + U+02CB + Η where Ἢ is meant. The same problem appears in "ʼΑγαθὴ" (`chapter002-01#nat0007978`) and "ʼΑφροδίτης" (`footnotesc`, n. 1296).
  * **Inconsistent elision marks in one line.** "δʼ … ἐφ̓ … ἠδ̓" (`chapter001-01#nat0001172`) mixes U+02BC with combining U+0313. The same line is repeated in `chapter002-02` (fn1070) with different marks.
* **Hebrew, Arabic, Syriac script: 0 characters.** Burton mentions these languages in the English text only. Whether early editions printed any Hebrew that this edition dropped or transliterated must be checked against an early-edition scan. That check is unverified.
* **Latin and vernaculars** are mostly italic. Italics are also used for proper nouns, book titles, English Bible quotations ("*Man in honour that understandeth not, is like unto beasts that perish*", `chapter001-01#nat0001108`) and emphasis. **So italics alone do not identify a foreign language.**
* **Gowland's brackets are a strong signal that a passage is foreign.**
  * Burton's text has 3,511 `[`. 2,473 of them come directly after `</em>`.
  * The sidenotes have 1,563 `[`.
  * 1,008 verse lines carry class `TS`/`TS1`/`TS2`. **Correction (M1):** `TS` marks the *first line of any verse translation*, Gowland's or Burton's. Only brackets identify Gowland. Example: `chapter001-01#nat0001167` "[… wasting disease …" is Gowland's (bracketed, and its second line has no `TS`). But `#nat0001176` "Th’ earth’s full of maladies, and full the Sea," is **Burton's own** rendering of Hesiod: it has `TS` and no brackets.
  * Gowland *omits* the bracket when Burton's own rendering keeps most of the sense, and *completes* partial ones in brackets. So **a Latin run with no following bracket is a candidate self-translation.** Example: "*Quantum mutatus ab illo?* How much altered from that he was" (`chapter001-01#nat0001112`).
* **Braces** `{…}`: 68 in the text and 85 in sidenotes, e.g. "{of Canterbury}" (`chapter001-01`) and "[we know, and {claim} that licence, etc.]" (`preface006`). Braces occur inside brackets too.
* **Middle English:** Chaucer quotations are set in `span.lucida` (83 spans, e.g. `chapter003-02#nat0015033`). That font switch is the only marker of the language. Tag these `enm`.
* **Symbols:**
  * Astrological glyphs ♈♉♊♋♌♍♎☾☿♂♀♄☌ appear in `span.arial_bold` (34 spans). In the synopses they are **cross-reference keys** ("Melancholy. See ♈").
  * Apothecary signs: ℞ (12), ℥ (10), ʒ (10), ℈ (3).
  * **`ß` (6) stands for the apothecary *semis* "ss" (half)**, e.g. "℥ ß [½ oz. each]" (`chapter002-02`). It is not German ß. Preserve it and gloss it.
  * There is one U+2006 six-per-em space (`chapter002-01`, fn481).

## 6. Synopses

* All three are **raster images** with a hidden HTML table of text (`table.hidden_content[hidden]` linked by `aria-describedby`).
  * P1: 8 images (`pg131_01`–`pg134_02`).
  * P2: 8 images (`pg427_01`–`pg430_02`).
  * P3: 4 images (`pg667_01`–`pg668_02`), with the heading "ANALYSIS OF THE THIRD PARTITION".
* **The hidden text has lost the tree.** It is a flat list of `<p>`:
  * P1 has 330 `<p>`, P2 413 and P3 250. Of these, 111 / 189 / 132 contain only a brace glyph (⎧, ⎨ or ⎩).
  * In P1 the paragraph-id order inverts 11 times relative to document order, so the reading order was shuffled.
  * One duplicate: "In diseases consider Sect. 1 Memb. 1." appears as both `#nat0000034a` and `#nat0000108`.
* **The images are clean** and the brace structure is fully legible (checked `pg131_01.png`).
  So the trees can be rebuilt from the images, and the hidden text gives an exact word-level checklist that the rebuilt tree must use exactly once.

## 7. Frontispiece and front matter

* The frontispiece is the image `pg003.png` (1151×1900, `alt=""`). The *Argument* has numbered verse stanzas 1–10 (stanzas 8 and 9 share one: "Borage and Hellebore"), which map to the engraving's panels.
* The *Argument* has 5 Gowland endnote refs (obsolete-word glosses: "Hern", "hie", "indite", "from's", "amain").

## 8. Accessibility of the source

The publisher's own summary says: "The publication is missing alternative text for images." All 25 images in Burton's text have `alt=""`: the frontispiece, 20 synopsis images and 4 heading images.

## 9. Other sources checked (for the translation and restoration layers)

| Source | What it is | Status |
|---|---|---|
| Dell & Jordan-Smith, *The Anatomy of Melancholy … with the Latin completely given in translation and embodied in an all-English text* (New York: Farrar & Rinehart, ©1927) | Human translations of Burton's Latin, built into the English text | Scans with OCR are on the Internet Archive, not lending-restricted (e.g. [`anatomyofmelanch1927burt`](https://archive.org/details/anatomyofmelanch1927burt), 1,066 images, Tudor reprint with "COPYRIGHT, 1927, BY FARRAR & RINEHART"; also [`anatomyofmelanch0000unse_n2h4`](https://archive.org/details/anatomyofmelanch0000unse_n2h4)). **Public domain in the USA** (published 1927, so US term ended 1 Jan 2023). **Probably *not* public domain in life+70 countries (UK/EU)**: Dell died 1969 and Jordan-Smith 1971, so the term runs to the end of 2041. OCR quality is mediocre (the sample "URTOX'S" is "BURTON'S"). This is not legal advice |
| Project Gutenberg [#10800](https://www.gutenberg.org/ebooks/10800) | A 19th-century modernized edition with translations of the classical extracts and full notes | Public domain in the USA; the source edition still needs to be identified. Could restore the sidenotes that Gowland pruned (Decision 4) |
| EEBO-TCP [A17310](https://ota.bodleian.ox.ac.uk/repository/xmlui/handle/20.500.12024/A17310?show=full) | Old-spelling transcription of the **1621 first edition**, CC0 | Only the first edition, which is much shorter than 1651. No TCP transcription of 1632/1638/1651 was found |
| 1628 and 1638 scans on the Internet Archive (`b30330105`, `McGillLibrary-RBSC_FOLIO-674-18479`) | Page images | Usable for spot-checks (Hebrew, marginal tags, synopsis layout), not as text |
| Clarendon edition (1989–2000) | Critical edition | **Do not use** (copyright) |
