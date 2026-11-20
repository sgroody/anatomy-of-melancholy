# V5 census: the pilot (2026-11-20)

The method is in `data/eval/CENSUS.md` (D13). The pilot covered four units chosen for dense and varied Latin: 1.2.3.15,
2.3.7.1, 3.2.5.3 and 2.5.1.6. Together they are 748 blocks and 28,693 counted words, 6.0% of the book's 475,239
(Chaucer left out). They are not a random sample: dense Latin is where the edition errs most, so these are not
book-wide figures. Reproduce with `burton census --unit … --report`.

## Counts (words)

| | words |
|---|---|
| tagged by both detectors | 4,111 |
| tagged only by the edition (detector 1) | 158; the judge found 10 of them foreign |
| tagged only by detector 2 | 470; the judge found 455 of them foreign |
| judge unsure (counted against the edition) | 8 tagged, 10 untagged |
| agreed sample (60 stretches, 354 words) | 354 judged foreign: no shared false positive found |

## Estimate (words)

| | precision | recall |
|---|---|---|
| the edition as it is now | 0.965 | 0.898 |
| after applying the judge's rulings | 0.998 (90% lower bound 0.996) | 0.998 (90% lower bound 0.996) |

Capture-recapture puts the foreign words both detectors miss at 1. This is a lower bound: all three readers are Claude
models, and they may share blind spots.

## What the disagreements are

- **Only detector 2 (missed by the edition):** long stretches of Latin in roman type that the edition leaves untagged
  (1.2.3.15: "fungi forsan & bardi, nihil a saxo differentes…", "Idiotae, literarum crepusculo positi…"), and short
  phrases ("quod ait ille", "qui tanquam mures alienum panem comedunt"). The 300-item rounds rarely draw these: a round
  samples items, and a long untagged stretch is one item however many words it holds.
- **Only the edition (wrongly tagged):** references tagged as Latin ("Seneca act. 2 Herc. Oeteus", "Plautus mil. glor.
  act. 3 sc", "Tully pro Archia Poeta"), names in attributions, and titles. In the first pass Chaucer's lines were also
  here, because the judge read Gowland's modernised spelling as English. Chaucer is now left out of the count (set in
  CENSUS.md before the whole-book run).
- The judge's rulings were read in session for both kinds; they follow the conventions.

## Cost and projection

| | pilot (list) | whole book, projected |
|---|---|---|
| detector 2 (sonnet) | $1.30 (20 calls) | about $21 (about 330 calls, about 2 hours) |
| judge (opus) | $0.86 (212 stretches) | about $10–12 (up to 2,500 disagreements and 300 agreed) |
| translating what the fixes add | — | about $25–40 (up to about 1,000 new passages, at about $0.04 each) |

Weekly meter: 14% before the pilot, 16% after; that reading also includes $0.99 of translations and the session's own
use. At that rate the whole book would use roughly 35–45% of a week.

## Not built yet

Applying the judge's rulings to the edition. These would be model rulings, applied by text quote at ingest and
labelled like the rest. The "after" figures above assume they are applied.
