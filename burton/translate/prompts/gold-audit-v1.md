You label language for a scholarly digital edition of Robert Burton's *The Anatomy of Melancholy* (1651), in a modernised text. Burton writes English full of Latin quotations, terms, names and references. Each item is a stretch of the text (`text`), usually with the passage it stands in (`context`), the unit it is from, and whether it stands in one of Burton's sidenotes (`in_sidenote`). Decide what the item is.

Labels:
- `la`, `grc`, `it`, `fr`, `es`, `de`, `nl`, `he`: the item is (essentially) in that language. `enm`: Middle English (Chaucer). Give `kind`: `phrase` (words or a sentence), `term` (a technical term: a disease, drug, part of the body, a philosophical term), or `verse` (a line or lines of poetry).
- `en`: English, including English words Burton sets in italics for emphasis, and words borrowed into English (an English dictionary would list them).
- `name`: proper names of people, places, peoples, gods, stars, even when Latin in form.
- `citation`: a reference rather than a quotation: locators and numbers, "lib.", "cap.", abbreviated authors or titles, "idem", "vide" with an author or title, apothecary numerals, a book's title cited as a source.
- `mixed`: part English, part foreign. Put the foreign words in `foreign_part`, copied exactly from `text`.

Rules:
- Latin terms (diseases, drugs, anatomy, terms of art) are `la` with `kind: term`, not names.
- Greek written in Latin letters is `grc`.
- "&c" alone is `en`.
- A bare author's name standing as a reference in a sidenote is `name`; an abbreviated one is `citation`.
- A verse line followed by an attribution is the verse's language; put the verse without the attribution in `foreign_part`.
- `foreign_part` is null unless the label is `mixed` or that verse case. `kind` is null for `en`, `name`, `citation` and `mixed`.

Judge from the item and its context only. Give a short `reason`. Return exactly one answer per item, with the same `id`.
