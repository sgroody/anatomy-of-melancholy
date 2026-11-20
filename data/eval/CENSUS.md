# V5 by census: the gate, fixed before measuring

Decided 2026-11-20. The owner, after the options were set out in plain language, said: "Do as you recommend". This
replaces the 300-item gate rounds as V5's pass condition. It was written before any census measurement was made. Why:
`state/review/v5-rethink-2026-11-20.md`. A 300-item round fails a detector that meets the targets nine times in ten,
and its gold leans on the same model as the detector.

## What is measured

The unit is the **word**: a run of letters in Burton's text, in the running text and the sidenotes. Gowland's matter is
left out (his translations, interpolations, unbracketed blocks and supplied text), and so are our own transcriptions of
the heading images. A word is **foreign** when it belongs to a passage in another language. The conventions are
LABELLING.md's: a cited title, a locator or a name is a reference, not foreign; Latin terms are foreign; "&c" is not a
word. Chaucer's verse is left out of the count: the source's own markup (`span.lucida`) marks it, so it is known rather
than detected, and in Gowland's modernised spelling a reader cannot tell it from English. That is what the pilot's
judge did; this was changed after the pilot, before the whole-book run. Counting words takes in the old boundary measure: a passage that is too short or too long shows up as words
missed or wrongly tagged.

## How

1. **Detector 1** is the edition's own detector (the rules and their model rulings), as it stands when the census is
   drawn.
2. **Detector 2** is independent of it. It uses a different model (`claude-sonnet-5-5`) and a different method: it
   marks the foreign stretches in each whole block. It never sees our tags, our rulings or anything of Gowland's.
   Prompt `census-v1`, ledgered.
3. **The judge.** Every stretch the two detectors disagree on goes to a judge (`claude-opus-5-5`, prompt `judge-v1`).
   The judge sees the block and the stretch, but not which detector marked it. Its ruling decides those words. A
   ruling of low confidence is reported apart and counted against the edition: a doubtful word counts as missed if
   untagged and wrong if tagged.
4. **Where they agree.** Words both detectors tag are checked by the judge on a random sample of 300 agreed stretches
   (seed 20261123). This estimates the false positives they share.
5. **Where both miss.** Foreign words that neither detector tags are estimated by capture-recapture (the Chapman
   estimator) on the judged true-foreign words: n1 found by detector 1, n2 by detector 2, and m by both. The estimate
   assumes the two detectors miss independently. Both are Claude models, so the estimate is a lower bound on what both
   miss, and it is reported as one.
6. **Fixes.** Judged disagreements are applied to the edition as model rulings, labelled. The scores below are the
   edition's after the fixes.
7. **A human check alongside.** Gowland's brackets are a human scholar's mark of foreign text. The share of his
   brackets that follow a passage is reported with the census. It is not part of the gate.

## Pass condition

V5 passes when, for the edition after the census fixes, the 90% lower bounds clear the targets:

- **word precision ≥ 0.98**: the share of tagged words that are foreign, with the agreed region estimated from step 4;
- **word recall ≥ 0.97**: the share of foreign words that are tagged, out of the found words plus the step-5 estimate.

The bounds are taken by bootstrap over blocks, with 2,000 resamples. The held-out rounds h1–h7 keep running as a
regression report and do not gate.

## Order

A pilot on a few units runs first, to measure the cost and the number of disagreements. The whole book runs only after
the pilot is reported. The census code may change after the pilot. This file may not change once the whole-book run
has started.
