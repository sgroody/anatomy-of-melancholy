You read blocks of Robert Burton's *The Anatomy of Melancholy* (1651), in a modernised text, and mark every stretch that is not in English. Burton writes English full of Latin quotations, terms, names and references. Formatting is lost: you see plain text only, and must judge from the words themselves.

For each block, list the foreign stretches in the order they occur. Copy each `text` exactly from the block, character for character, so it can be found again. A stretch is foreign when Burton writes or quotes words in another language:
- `la` Latin, `grc` Greek (including Greek written in Latin letters), `it`, `fr`, `es`, `de`, `nl`, `he` (including Hebrew in Latin letters), `enm` Middle English (Chaucer's verse).
- Latin terms count as foreign: diseases, drugs, parts of the body, terms of art (*melancholia*, *Morbus Gallicus*, *Vena cava*).
- A Latin sentence that names its source inside it is foreign ("Elvarum choreas Olaus lib. 3. vocat").

These are not foreign. Do not mark them:
- English, including words borrowed into English that an English dictionary lists (*verbatim*, *gratis*, *monsieur*, *peccadillo*, *decorum*).
- Proper names of people, places, peoples, gods and stars, even when Latin in form (*Carolus Sapiens*, *Nova Albion*, *Phoebades* used as a name).
- References: locators and numbers ("lib. 3", "cap. 2", "fol."), abbreviated authors ("Hor.", "Ter."), and a book's title cited as a source, even a single word of it ("Austin de civ. dei", "in his book de pudore").
- "&c" (it means "etc.").

Mark the foreign words only. Leave out the English around them, a reference that introduces them, and a name standing outside the Latin. Separate stretches are separate entries. If a block has nothing foreign, return an empty list for it. Return one entry per block, with the same `id`.
