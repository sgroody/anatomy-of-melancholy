You are checking quotation sources for a scholarly digital edition of Robert Burton's *The Anatomy of Melancholy* (1651). For each item, an earlier record claims an author for a Latin passage Burton quotes, and a text-matching rule found the same words in a different author's text in a Latin corpus. Decide what the evidence shows.

Each item gives:
- `passage`: the Latin exactly as Burton prints it, and `context`: Burton's words around it (his sidenote attribution, if any, appears there);
- `claim`: the author (and work) the record claims, and its status (`burton-cites` = Burton's own attribution, `probable` = a stated guess);
- `match`: the corpus author, work and locus, and `corpus_text`: the matched corpus words (normalised: lower case, u/v and i/j merged, ae/oe written e).

Answer:
- `verdict`: one of
  - "claim-quoted-in-match": the claimed author wrote these words, and the matched author is quoting them;
  - "match-is-source": the matched author is the source and the claim is mistaken (Burton's own attribution can be wrong);
  - "both-share": a proverb, formula or line used by both, with no clear original;
  - "unclear": the evidence does not settle it.
- `source_author` and `source_work`: who and what, if the verdict names a source; else null. Use well-established knowledge only.
- `reason`: one or two sentences.
- `confidence`: "high", "medium" or "low".

Rules: Do not invent works or loci. When unsure, say "unclear". Return exactly one answer per item, with the same `id`.
