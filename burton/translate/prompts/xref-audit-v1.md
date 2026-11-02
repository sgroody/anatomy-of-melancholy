You are checking cross-references in Robert Burton's *The Anatomy of Melancholy* (1651) for a scholarly digital edition. The book is divided into Partitions, Sections, Members and Subsections; each unit has an id like `1.2.3.4`; front matter has ids like `djr` ("Democritus Junior to the Reader").

Each item is a phrase marked ⟦like this⟧ in Burton's text that may point elsewhere in the book ("as I have said", "in his place", "before mentioned"). You get its context, the unit it stands in, and the outline of the whole book (unit ids and titles).

Work it out yourself and answer:
- `kind`: "reference" if Burton points to a particular other place in the *Anatomy*; "same-place" if he points back within the same passage or unit; "not-a-reference" if the phrase only orders his argument or refers to another author's book; "too-vague" if it points elsewhere in the book but no single place can be named.
- `target`: the unit id, only for "reference" and only if the outline and the context make it clear; otherwise null. Do not choose between two plausible units.
- `reason`: one sentence.
- `confidence`: "high", "medium" or "low".

Return exactly one answer per item, with the same `id`.
