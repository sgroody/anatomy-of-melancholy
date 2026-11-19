You find references in the running text of Robert Burton's *The Anatomy of Melancholy* (1621–1651), in a modernised text, for a reader's edition that marks each reference and writes it out in the margin. Burton cites constantly in his text: an author's name with a title and locators ("Mercurialis de affect. lib. 1 cap. 10"), a title alone ("in his book de atra bile"), a locator alone after a name ("Plato, 3 de Rep."), or a Bible reference.

Each item gives `text`, a stretch of Burton's text with one run marked ⟦ ⟧, and `run`, the marked words. The marked run was set in italics and judged a reference by rules that can be wrong. For each item:

- `is_citation`: true if the marked run is (part of) a reference to a written work or a place in one; false if it is a quotation, a name standing alone, a term, or anything else.
- `exact`: for a citation, the whole citation as it stands in `text`, copied exactly, character for character, without the ⟦ ⟧ marks: the author's name if it belongs to the citation, the title and the locators, without the words of Burton's sentence around it. It must contain the marked run. Null if not a citation.
- `display`: the citation written out for a reader: author's usual name, the work's usual title in italics with *asterisks*, then book, chapter, etc. ("Girolamo Mercuriale, *De affectibus*, book 1, chapter 10"). Expand only what you know.
- `status`: `expanded` if you are sure of the author and the work; `probable` if you infer one of them (the reader will say "probably"); `unidentified` if you cannot tell what is cited (then `display` null). Never invent a work, an author or a locus: a wrong expansion is worse than none.

Return exactly one answer per item, with the same `id`.
