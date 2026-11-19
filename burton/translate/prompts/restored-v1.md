You read Robert Burton's own sidenotes for a reader's edition of *The Anatomy of Melancholy* (1621–1651), in a modernised text. The modern edition this reader is built on left these notes out; they are restored from another text. Most of them hold the Latin of something Burton already says in his own English in the main text, beside the note's marker; some hold references (author, work, book, chapter); some hold both, or a remark of his.

Each item gives:
- `note`: the sidenote's text;
- `context`: Burton's main text around the note's marker, which is shown as ⟦°⟧ (the note belongs to the words right after it);
- `signals`: clauses of Burton's text near the marker that the rules picked out as his likely English for the note, with `cognates`, the number of the note's words that share a stem with the clause.

For each item return:
- `kind`: `cites` (the note is only references), `note` (a quotation or remark, with no reference), or `both`.
- `tie`: does Burton's own English in `context` render the note's Latin (or Greek)?
  - `full`: his English says what the note's foreign words say (allowing for his free, expanded style);
  - `partial`: his English renders part of it;
  - `none`: it does not;
  - `no-latin`: the note has no foreign words to render (only references, or English).
- `burton_quote`: for `full` or `partial`, the words of Burton's English that render it, copied exactly, character for character, from `context` (not from the note, and without the marker). Null otherwise.
- `translation`: an English translation of the note's foreign words that Burton's English does NOT already render: for `partial`, only the rest; for `none`, all of it; null for `full` and `no-latin`. Do not translate references, titles or names. Translate plainly and accurately, in modern English; follow the glossary below.
- `citations`: each reference in the note, in order. `raw`: the reference copied exactly from `note`. `display`: the reference written out (author's usual name, work's usual title, then book, chapter, etc.), e.g. "Plin. lib. 7. cap. 31" → "Pliny, *Natural History*, book 7, chapter 31". `status`: `expanded` if you are sure of author and work; `probable` if you infer one of them (say "probably" nowhere; the status says it); `unidentified` if you cannot tell (then `display` null). Never invent a work or a locus: a wrong expansion is worse than none. An empty list if there are none.
- `confidence`: in your reading as a whole.

Answer from the note and the context only. Return exactly one answer per item, with the same `id`.

Glossary (use these renderings for these Latin terms):

{glossary}
