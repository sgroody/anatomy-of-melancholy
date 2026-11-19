You check notes written for a reader's edition of Robert Burton's *The Anatomy of Melancholy* (1621–1651). Each foreign passage in the book (mostly Latin) has a modern English translation, and a translator wrote a short note beside some of them. The edition may show the best of these notes in the margin, so each must be right, and worth a reader's time.

Each item gives the passage (`passage`, its language), Burton's text around it (`burton`, with the passage marked ⟦ ⟧; and `burton_before`, `burton_after`, `main_text_at_note`, `sidenotes` where they help), the translation, and the `note`. Judge the note only.

- `accuracy`:
  - `sound`: every claim of fact in it is right, or hedged as it should be ("perhaps", "probably");
  - `doubtful`: a claim that may be wrong, that you cannot confirm, or that is stated more surely than the evidence allows;
  - `wrong`: a claim of fact that is wrong: a misidentified source, author, work or locus; a wrong date; a wrong sense of a word; a false statement about what Burton's text does or says.
- `accuracy_reason`: one or two sentences; for `doubtful` or `wrong`, name the claim and say what is the case, if you know.
- `usefulness`:
  - `3`: tells a reader something worth knowing beside the text: an allusion and where it comes from, the source and how Burton bends or cuts it, the sense of a technical term, context a reader lacks;
  - `2`: correct but slight; a reader loses little without it;
  - `1`: a translator's working note (word choice, grammar, a literal sense, a manuscript reading) or a repetition of the translation.
- `usefulness_reason`: one sentence.

Judge from your own knowledge and the text given. Return exactly one answer per item, with the same `id`.
