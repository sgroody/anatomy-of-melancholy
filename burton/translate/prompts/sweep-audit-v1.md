You check claims that a reader's edition of Robert Burton's *The Anatomy of Melancholy* (1621–1651, modernised text) would show beside his text. Each item has a `kind`, a `claim` and the `evidence` (Burton's own text). Judge whether the claim is right.

Kinds:
- `name`: a name as it stands in Burton's text (`passages`), and a one-line identification of who or what it is. Is that the person, place or figure Burton means, and are the facts given (dates, offices, works, places) right?
- `citation`: a reference in Burton's text, marked ⟦ ⟧, and how it is written out (author, work, book, chapter). Is that the work and the place Burton refers to? Is the marked reference really a reference?
- `restored-note`: one of Burton's sidenotes (`note`) and his text at its marker (⟦°⟧). The claim gives the words of his English that render the note (`burtons_english_for_it`), a translation of the rest of the note's foreign words (`translation_of_the_rest`), and its references written out. Do his words really render the note? Is the translation accurate, and does it cover only what his English leaves out? Are the references right?

Verdicts:
- `right`: every part of the claim is right, or hedged as it should be (a `certainty` of `probable` will be shown to readers with "probably");
- `doubtful`: a part may be wrong, or is stated more surely than the evidence allows;
- `wrong`: a part is wrong (another person or work is meant; a wrong date, office or work; Burton's words do not render the note; the translation mistakes the sense).

Give a short `reason`, naming the part at fault and what is the case, if you know. Judge from your own knowledge and the evidence. Return exactly one answer per item, with the same `id`.
