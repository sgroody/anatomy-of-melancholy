# Spot check of five h2 gold labels (PLAN D7)

Drawn 2026-10-20 from `langid-holdout2-gold.jsonl` (300 items) with `random.Random(20261020).sample(gold, 5)`.
For each item, write **agree** or the label you would give. Any disagreement means a wider review.

| # | item (sid, unit) | text in context (item in ⟦ ⟧) | label | owner |
|---|---|---|---|---|
| 1 | h2-sidenote-036, 2.2.3.1 | ⟦Multa sane hinc consequuntur absurda, & si nihil aliud, tot Cometae in aethere animadversi, qui nullius orbis ductum comitantur, idipsum sufficienter refellunt⟧ [Of course many absurdities follow…] (a sidenote) | `la` phrase | agree |
| 2 | h2-roman-before-bracket-011, 1.2.1.2 | …Rob. Gaguinus … telleth such another wonderful story at the death of Johannes de Monteforti a French Lord, Anno 1345, ⟦tanta Corvorum multitudo aedibus morientis insedit, quantam esse in Gallia nemo judicasset⟧. Such prodigies… | `mixed`: the Latin part is the span in ⟦ ⟧ | agree |
| 3 | h2-italic-109, 3.2.3.1 | Salmacis would not be seen of ⟦*Hermaphroditus*⟧, till she had spruced up herself first. | `name` | agree |
| 4 | h2-sidenote-047, 1.2.1.2 | ⟦*Hierom*⟧. in 3 Ephes. Idem Michaelis cap. 4 de spiritibus. … (a sidenote) | `citation` (abbreviated author in a reference) | agree |
| 5 | h2-italic-032, 2.3.2.1 | …you shall scarce find of a multitude (as ⟦*Aeneas Silvius*⟧ observes) qui sceleratum non habent ortum, that have not a wicked beginning… | `name` | agree |

Label meanings: data/eval/LABELLING.md.

**Result (2026-10-20): the owner agreed with all 5 labels (0 disagreements).**
