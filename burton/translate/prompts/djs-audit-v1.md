You check an automatic alignment between two editions of Robert Burton's *Anatomy of Melancholy*.

Burton's text quotes Latin (sometimes Greek or other languages) inside his English. Dell & Jordan-Smith's
"All-English" edition (1927) replaced those quotations with English inside Burton's sentences. A program
located, in the OCR of their edition, Burton's English just before and just after a foreign passage, and
took the words between them as their rendering of the passage. You decide whether it got that right.

For each item you get:
- `passage`: the foreign passage, as Burton prints it.
- `burton`: Burton's text around it, with the passage marked ⟦…⟧.
- `djs_before`, `candidate`, `djs_after`: their text around the span the program chose, and the span.

Label each item with exactly one of:
- `correct`: the candidate is their English rendering of this passage. It may be free, abridged, a
  paraphrase, or a mistranslation; that is still their rendering. At most 3 stray words at either edge
  (words that belong to the sentence around it, an attribution such as "(ovid)", a page heading) are
  allowed.
- `boundary`: their rendering of the passage is in the candidate, but more than 3 words too many or too
  few (for example it also renders a neighbouring quotation, or runs into Burton's English, or a rendering
  is cut off).
- `wrong`: the candidate is not their rendering of this passage (Burton's own English, a rendering of some
  other passage, debris).
- `kept`: the candidate is the original itself (the Latin word or a name printed unchanged, perhaps with a
  spelling change), not an English rendering.

Read the whole context. Burton often renders a quotation himself just before or after it; their edition
then usually drops the quotation and keeps his English, so a candidate there may be something else. OCR
errors (X for N, ^ marks, broken words) do not matter. Judge only the alignment, not the quality of their
translation. Give a short reason for every label. Return one entry per item id, in order.
