# M4 translation pilot: report (2026-10-20)

Counts come from `uv run burton pilot-report` (`verify/reports/m4-pilot.json`) unless a line says it was
checked by hand. The owner's review page is `verify/reports/m4-review.html` (open it in a browser; the
ratings save to a JSON file).

## 1. The 50 passages

`data/eval/m4-pilot.yaml` gives each item's stratum, the reason it is hard, and the self-translation
verdict a correct answer should give (drafted by Claude, for the owner to confirm).

| stratum | items | | stratum | items |
|---|---|---|---|---|
| self-translation (full, partial, paraphrase) | 10 | | technical medical Latin | 5 |
| Greek | 5 | | long prose | 4 |
| suspected misquotation | 5 | | verse | 4 |
| apothecary recipes | 4 | | citation-only Latin in sidenotes | 4 |
| puns | 3 | | Italian and French | 3 |
| Chaucer (gloss only) | 3 | | **total** | **50** |

The base text has fewer vernacular quotations than PLAN assumed:
* One passage is tagged `it` (*citadella*) and none `fr`. The Italian proverb 3.3.2.1-f5 and the phrase 3.2.5.3-f163 are tagged `la`, and "à la mort" (1.3.1.4) is French but untagged. So the stratum has 3 Italian items and no French.
* Chaucer's 83 `lucida` spans are not tagged `enm` and are not passages. The 3 Chaucer items are keyed by their verse-group ids, and their glosses go to a new layer, `data/layers/glosses/`.

## 2. Prompt tr-v2, glossary v2, runner

* **Explanation inside translations** ("Curable (salutary)"): the prompt now says `translation` holds only the rendering and all explanation goes in `note`. A new validator check retries any translation that adds parentheses or brackets the source lacks. It fired 3 times (all Sonnet: 1.2.3.10-f1, djr-f387, 2.5.1.6-f22), and each retry fixed it. **0 of 94 final records add a parenthesis.**
* **`burton-cites` must be checkable**: the basis has to quote Burton's own words in quotation marks, and those words must stand in the packet (his sidenote or his text, e.g. `text "saith Tertullian"`). Otherwise the item is retried, then downgraded. It fired once (Opus, 1.3.2.1-f5; fixed on retry). 0 records were downgraded.
* **Other prompt changes:**
  * Packets carry the rules-only self-translation hints from `data/layers/selftrans/`, labelled as hints, not verdicts.
  * New flags `language-mismatch` and `boundary-suspect`.
  * Rules for recipes (ß = *semis*), citations (no added locus), wordplay (the play goes in the note), and nonsense words.
  * Gloss-only items (empty translation, glosses copied exactly from the text, each checked by selector).
* **Glossary v2** (`data/glossary.yaml`, 25 terms, up from 9):
  * humoral adjectives (*pituitosi*, *biliosi*, *lienosi*);
  * bloodletting and cupping; *ventriculus* = stomach; *per consensum*, *per essentiam*; *atra cura* (not black bile);
  * apothecary signs ℞ ℥ ʒ ℈ ß, *ana*, *gr.*; locator abbreviations;
  * 16 more authorities.
  * The glossary check now matches symbols as well as words.
* **Two models per passage**: each machine translation keeps its own self-translation verdict and source claim. The record's top-level view and the reader follow the primary model (`claude-opus-5-5` until D8).
* **Bugs found and fixed on the way:**
  * Packets crashed on the 14 passages outside any paragraph (verse at division level, list items).
  * `public_text` printed both `sic` and `corr` of the book's one correction, so djr-f972 reached the model as "MανίαΜανία". It now reads as the correction. The djr self-translation layer was regenerated (3 lines changed).
* **Leak check on the packets**: 0 of the 4,526 Gowland translations of 20+ characters occur in any of the 30 packets.

## 3. Runs (`burton translate --select data/eval/m4-pilot.yaml --model …`, prompt tr-v2)

| | Opus (claude-opus-5-5) | Sonnet (claude-sonnet-5-5) |
|---|---|---|
| packets / calls | 30 / 31 (1 retry) | 30 / 34 (4 retries) |
| invalid, failed, deferred | 0 | 0 |
| model time | 455.8 s (median 13.2 s per packet) | 871.7 s (median 6.2 s per packet; one packet took 618.5 s before succeeding) |
| output tokens per passage | 636 | 445 |
| list-price equivalent reported by the CLI | $1.40 ($0.028 per passage) | $0.67 ($0.013 per passage) |
| Pro plan meter, 5-hour window | 64 % → 75 % (includes this session working at the same time) | 75 % → 78 % (this session nearly idle) |
| Pro plan meter, weekly | 61 % → 63 % (same caveat) | 63 % → 63 % |

## 4. Results

**Self-translation verdicts** (12 exit-gate items; all 47 foreign items in brackets):

| | as drafted before the runs | after 3 labels were revised |
|---|---|---|
| Opus | 11 / 12 (43 / 47) | **12 / 12** (46 / 47) |
| Sonnet | 9 / 12 (41 / 47) | **10 / 12** (44 / 47) |

* The three revised labels (2.4.1.3-f2, which is a gate item, plus djr-f972 and 1.3.2.1-f5) moved toward the models' answer after I saw it. The draft is kept in the file with the reason. For example, 2.4.1.3-f2 was drafted from the rules candidate, which stops after "some herbs provoke lust", but Burton's sentence goes on to render the second half. **The owner should confirm these three.**
* Sonnet's gate misses: 2.3.3.1-f166 and 3.2.3.1-f417 are called `full`, but Burton drops part of the Latin in both.
* Both models miss 3.2.5.1-f47. It is a known boundary defect: Burton's English couplet is inside the passage, so no quote can pass the "outside the passage" check. Both flag it `boundary-suspect`.

**Honest attribution** (checked by hand, every claim that is not `unidentified`):

| | burton-cites | probable | unidentified | invented | downgraded by the validator |
|---|---|---|---|---|---|
| Opus | 26 | 5 | 16 | **0** | 0 |
| Sonnet | 23 | 4 | 20 | **0** | 0 |

* Every `burton-cites` quotes a sidenote or Burton's own words.
* Every `probable` names a line I can confirm: Aeneid 4.529ff, Horace Epistles 1.10.24 and 2.2.200, Terence's *Andria*, Palladas in the Greek Anthology (10.84), Aristophanes' *Frogs*.
* The proverb trap 2.3.1.1-f11 is `unidentified` in both.
* For the owner, not counted as invented:
  1. Both models attribute all of lectori-f2 (Burton's own Latin) to Martial, because a "Martial." sidenote belongs to one line inside it.
  2. Sonnet gives a Georgics line range (1.416-419) that I could not confirm; Opus says 1.417-420.

**Misquotations**: Opus flagged 9, including all 4 expected (djr-f324, 1.2.3.15-f58, 2.3.7.1-f52, 3.2.2.4-f92). Its notes give the standard readings (e.g. *fors obiecerit*, *quod palles*, *uvidus Austris*), and they agree with the texts as I know them. Sonnet flagged 1 (3.2.3.1-f68) and caught none of the 4.

**Other checks:**
* Both models flagged both Italian items `language-mismatch` and both boundary defects (3.2.5.1-f31, 3.2.5.1-f47).
* The only glossary warning is 1.2.2.5-f17 (*humor* = moisture of the sky). Both models explain it in the note, as the glossary asks.
* Chaucer glosses: Opus 4, 4 and 8 per item; Sonnet 2, 2 and 8. Sonnet glosses *I wis* as "I know", the old false etymology.

## 5. Dell & Jordan-Smith (1927)

* **Download**: the owner agreed on 2026-10-20. Files: `anatomyofmelanch1927burt_djvu.txt` (3,333,664 bytes) and `_page_numbers.json` (181,800 bytes), from archive.org. Both SHA-1s match the Internet Archive's, and the SHA-256s are in `data/source/DJS.lock`.
* **What their edition is**: an "All-English" text. They replaced the Latin with English inside Burton's sentences. Where Burton renders a passage himself, they usually drop the Latin and keep his English.
* **Method**: `burton align-djs` (`burton/layers/djs.py`, threshold 0.85) locates Burton's English on both sides of each passage in their text, using word-trigram votes and then rapidfuzz. The text between the two anchors is the candidate. A length gate discards spans that cannot be a rendering of the passage. Results are in `data/layers/djs/`; they are not yet merged into the translations layer or shown in the reader.

**Coverage**, 47 foreign items:

| result | items | kept? |
|---|---|---|
| aligned (a candidate is kept) | 10 | yes |
| omitted (they print nothing for it) | 12 | yes |
| discarded: below threshold 2, implausible length 3, anchors not found 3 | 8 | no, never shown |
| no anchor: 13 sidenotes, plus 4 passages with no English of Burton's beside them | 17 | — |

Coverage is 22/47 overall and 22/34 for passages in running text.

**Accuracy** (checked by hand against their text):
* aligned: **9 / 10 correct**. The error is 3.2.5.1-f47, the boundary defect: the span is Burton's own couplet, which they kept.
* omitted: **11 / 12 correct**. The error is 3.2.5.1-f27: for the *amantes/amentes* pun they kept the Latin words and glossed them in parentheses.
* The rules were adjusted after looking at these 47 (a length gate and a rule for one-word passages). These are tuning figures, so the M5 run needs a held-out check.

**Sidenotes**:
* Their preface (pp. v–vi) says they left off Burton's marginal references. A name is sometimes written into the text in square brackets ("As one [Tully] saith"). They cut chapter-and-book references short, kept "the most interesting" notes, worked a few into the text in parentheses, and added a few footnotes of their own (marked * and †). Their index doubles as a dictionary of the authorities.
* A seeded sample of 60 sidenotes agrees:
  * 32 leave nothing at their anchor.
  * The 4 English sidenotes in the sample ("Near St. Albans", "The possession of William Purefoy, Esq.", "Michael a musician", "Founder of our public library in Oxon.") occur nowhere in their text.
  * One ("R. T. notis in blazon jealousy") became a bracketed insertion, "[R. Tofte in his Blason of Jealousy]".
  * Author notes on verse often reappear as a lower-case attribution after the quotation, "(horace)", "(martial)"; the sample found 2 by rule.
  * For 24 the anchor could not be placed exactly, mostly because the anchor words were Latin verse that they replaced.
* So their edition gives no translation of the Latin sidenotes. For those 13 pilot items, only the machine versions exist.

## 6. Throughput projection for the full pass (7,785 passages)

* **Packets**: 475 of up to 20 passages within a unit (54 already have a machine record: 7 from M1, 47 from the pilot).
* **Pilot packets were tiny** (1.7 passages on average), so the fixed cost per packet is overstated. The Opus fit is $0.0166 per packet + $0.0175 per passage, so the full pass is about **$144** list-equivalent, against $218 at pilot packet size. For Sonnet the fit is unreliable (26 packets, almost all of 1 passage); at pilot size the full pass is $104, and with full packets it is probably about two-thirds of that.
* **Calibration on your Pro plan**: Sonnet's run used 3 points of the 5-hour window for $0.67 (±1 point from integer rounding), about 4.5 points per list-dollar (3.0–6.0). Opus's reading, 11 points for $1.40, also includes this session's own work, so it is an upper bound.
* **Weekly**: the two runs moved the weekly meter about 1 point for every 5–7 points of the 5-hour window. So a full week's allowance is roughly 5–7 five-hour windows.

| full pass | list-equivalent | 5-hour windows | share of the weekly allowance |
|---|---|---|---|
| Opus | about $144 | about 6.5 (range 4.3–8.6; up to 11 on the Opus reading) | about 1–2 full weeks, if nothing else uses the plan |
| Sonnet | about $70 | about 3 (2–5) | about half a week to one week |

* **Model time is not the limit.** Opus produces about 504 output tokens per passage at roughly 70 tokens a second, about 15 hours of generation in all.
* **Usage limits are the limit.** The runner stops cleanly at a limit and resumes from the ledger, so the pass runs over consecutive windows.
* **Recommendation for M5**: calibrate in the first session. Run one whole unit in 20-passage packets with nothing else using the plan, and read the meter before and after. A 20-passage packet returns 10–13k output tokens, well inside the CLI's limit.

## 7. Exit criteria (PLAN M4)

| criterion | status |
|---|---|
| Zero invented attributions in the 50 | **met**: 0 for both models (hand check of 31 Opus and 27 Sonnet claims) |
| Self-translation verdict correct on the self-translation items | **Opus 12/12** with the 3 revised labels (11/12 as drafted); Sonnet 10/12. Owner to confirm the revisions |
| Throughput projection written | **met** (§6) |
| Rubric pass rate agreed with the owner | **met** (2026-10-23): the owner accepted the pilot results, confirmed the 3 revised labels and chose Opus (PLAN D8) |

## 8. Found on the way (follow-ups, not fixed here)

* Chaucer is not tagged `enm` (83 `lucida` spans), so it is not in the translation queue. SURVEY says to tag it.
* Italian is tagged `la` (3.3.2.1-f5, 3.2.5.3-f163). French "à la mort" (1.3.1.4) is untagged.
* Boundary defects:
  * 3.2.5.1-f47 includes Burton's English couplet;
  * 3.2.5.1-f31 cuts a wholly Latin paragraph into passage and non-passage;
  * djr-f1489 runs two citations and a quotation together.
* One Sonnet packet took 618.5 s before succeeding. The runner has no per-call timeout below 30 minutes.
