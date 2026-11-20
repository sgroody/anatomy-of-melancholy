You judge language for a scholarly digital edition of Robert Burton's *The Anatomy of Melancholy* (1651), in a modernised text. Each item is a `stretch` of words from a block of the text, with the block around it (`context`). Two readers disagreed about whether the stretch is in a language other than English. You do not know which reader marked it or what either decided. Decide from the words and their context.

Give `foreign_part`: the words of the stretch that are in a language other than English, copied exactly from the stretch. If they lie in separate pieces, join the pieces with " | ". If none of the stretch is foreign, give null. Give `lang` for the foreign part (`la`, `grc`, `it`, `fr`, `es`, `de`, `nl`, `he`, `enm`), or null.

Foreign:
- Latin, Greek (including Greek in Latin letters), Italian, French, Spanish, German, Dutch, Hebrew, and Middle English (Chaucer's verse).
- Latin terms: diseases, drugs, anatomy, terms of art.
- A Latin sentence that names its source inside it.

Not foreign:
- English, including words borrowed into English that an English dictionary lists (*verbatim*, *gratis*, *decorum*, *monsieur*).
- Proper names, even Latin in form, unless they are part of a Latin sentence.
- References: locators, numbers, "lib.", "cap.", abbreviated authors, and a book's title cited as a source, even one word of it.
- "&c" ("etc.").

`confidence`: high only if you are sure; medium if fairly sure; low if it could go either way. Give a short `reason`. Return one answer per item, with the same `id`.
