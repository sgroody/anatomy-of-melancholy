You help gloss obsolete English words for a scholarly digital edition of Robert Burton's *The Anatomy of Melancholy* (1651), in a modernised text. A reader turns the glosses on to see what an old word meant where Burton uses it.

Each item is one occurrence of a word, marked ⟦like this⟧ in its sentence, with every sense Webster's dictionary of 1913 gives for that spelling (`webster`: ids `w1`, `w2`, …). All of those senses are labelled obsolete or archaic in Webster. But the same spelling is often also an ordinary word that Webster lists under another headword or another form (for example "led" as the past of "lead", "wonders" as the plural of "wonder"), so Webster's obsolete senses may have nothing to do with Burton's use.

For each item decide `verdict`:
- `webster`: Burton uses the word in one of the listed senses. Give that sense's id in `webster_sense`. Choose it only if it fits this sentence; a sense that is merely possible is not enough.
- `ordinary`: Burton uses an ordinary word a present-day reader understands (a modern sense, or an inflection of a common word), so no gloss is needed. `webster_sense` and `sense` are null.
- `other-obsolete`: Burton uses an obsolete or archaic sense that none of the listed senses gives. Write that sense in `sense`: a short gloss of a few words, in the style of a dictionary definition ("Witty, facetious"), giving the meaning in this sentence only. Do not explain, do not cite anyone.
- `not-english`: the marked word is not English here (part of a Latin phrase, an abbreviation, a name). `webster_sense` and `sense` are null.

`confidence`: "high", "medium" or "low". Use "low" when the sentence does not let you tell.

Judge each occurrence on its own sentence, even when the same word appears in several items. Return exactly one answer per item, with the same `n`.
