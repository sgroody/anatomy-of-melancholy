# Language-ID gold labels: conventions

Files: `langid-gold.jsonl` (tuning sample, 677 items: used to develop the rules) and the held-out
rounds listed in `burton/verify/gold.py` (`HOLDOUTS`):

| round | files | items | seed | status |
|---|---|---|---|---|
| h1 | `langid-holdout-{sample,gold}.jsonl` | 150 | 20261021 | **seen** 2026-10-20: its errors were studied to change the rules |
| h2 | `langid-holdout2-{sample,gold}.jsonl` | 300 | 20261022 | **seen** 2026-11-18: the sidenote-title rule |
| h3 | `langid-holdout3-{sample,gold}.jsonl` | 300 | 20261118 | **seen** 2026-11-18: Latin titles, possessives, mixed italics |
| h4 | `langid-holdout4-{sample,gold}.jsonl` | 300 | 20261119 | seen 2026-11-19 (third cycle) |
| h5 | `langid-holdout5-{sample,gold}.jsonl` | 300 | 20261120 | **gate**: drawn after the 2026-11-19 rules, never used to tune them; 1 Chaucer label corrected from the source's markup |

From h3 on, rounds are labelled blind by the second rater (`burton gold-audit --label-round <name>`, prompt
gold-audit-v1). A label is corrected afterwards only from objective source markup (e.g. `span.lucida` is
Chaucer, `enm`), and each correction is kept in the row's `corrected` field with the reason.

Samples are drawn by `gold.draw_holdout(name)`, which excludes every item already in any sample or gold
file and refuses to redraw a labelled round. `evaluate()` scores in place; V5 gates on the newest round
and still reports the seen rounds and the tuning sample. Once a round's errors have been looked at to
change the rules, it is seen: add a new round (new seed, new files) rather than relabelling or reusing it.

## How to label
- Label **blind**: look at the item text and its context only, never at the detector's output.
- Read the **full** item text before labelling. Eight early labels were wrong because a display cut
  items at 120 characters; those are marked with a `note` in the file.

## Labels
| label | meaning |
|---|---|
| `la`, `grc`, `it`, `fr`, `es`, `de`, `nl`, `enm`, `he` | the item is (essentially) in that language; `kind` = phrase / term / verse |
| `en` | English, including English words Burton italicises for emphasis |
| `name` | proper names of people, places, peoples, gods, stars, even when Latin in form (*Nova Albion*, *Premunda*) |
| `citation` | locators and reference fragments: numbers, `lib`, `cap`, abbreviated authors or titles (*Seneca Hippol*, *de atra bile*, *Donat. vita. ejus*), `idem`, apothecary numerals (*ii*) |
| `mixed` | part English, part foreign; `foreign_part` is the foreign span copied exactly (the Latin nearest the bracket, for the roman-before-bracket stratum) |

## Conventions decided so far
- **English loan-words are `en`**: *monsieur*, *signor*, *don*, *peccadillo*, *inamorato*, *Bona-roba*,
  *Halleluia*, *verbatim*. Gowland's spellings follow OED headwords, so these are English words.
- **Latin terms are `la` / term, not names**: *Morbus Gallicus*, *Scorbutum*, *Plica*, *Vena cava*,
  *Dictamen rationis*. Disease and drug names in Latin form count as Latin.
- **Book titles used as references are `citation`** (*Epist. obscurorum virorum* in a citation is debatable:
  the tuning label says `la`; prefer `citation` for new items when the title is cited as a source).
- `&c` alone is `en` (it is "etc."), never a passage.
- Greek in Latin letters is `grc` (the edition tags it `grc-Latn`).
- *(h2)* **`Vide` + author/title is `citation`** (*Vide Boissardum de Magis*): a cross-reference, not a passage.
- *(h2)* **Bare author names standing as a sidenote reference are `name`** (*Abernethy.*, *Nonius.*);
  abbreviated ones are `citation` (*Ter.*, *Hor.*, *Hierom.*).
- *(h2)* **Latin drug and anatomy terms are `la` / term** (*Intestina*, *de quinque generibus mirabolanorum* in a
  list of pills); Latin-form proper names of documents are names (*Magna Carta* inside English is `en`).
- *(h2)* **Italic items that are part English, part Latin are `mixed`** with `foreign_part` (*…Cooks are
  Gentlemen: Venter Deus*); the evaluator then judges the foreign part, not the whole italic element.
- *(h2)* **A verse line with an attribution** (*…arte rubet, (Ovid)*) is `la` / verse with `foreign_part` = the
  verse without the attribution.
- *(h2)* In the roman-before-bracket stratum, when the Latin nearest the bracket is a list of Latin-form names
  (*Carolus Sapiens, Philippus Bonus*), `foreign_part` is the nearest real Latin and a `note` says so.
- Any item whose detector output the labeller saw before labelling gets a `note` saying so (h2 has one).
- *(h6, written into the rater prompt gold-audit-v2 before h7 was drawn)* **What belongs to a reference**: words of a
  title cited as a source are `citation`, even a single word (*dei* in *Austin de civ. dei*); locators, abbreviated
  authors and authors listed as sources never go into `foreign_part` (*Pet. Haedus, Albertus, & infiniti fere
  medici* → *& infiniti fere medici*); a Latin sentence that names its source inside it is Latin (*Elvarum choreas
  Olaus lib. 3. vocat*). **Separate foreign stretches** of a `mixed` item are given as they stand, joined by " | ",
  without the English between them (*in secundis | in tertiis*). The h6 gold is left as its raters labelled it.

Owner review of all labels is pending (PLAN D7).
