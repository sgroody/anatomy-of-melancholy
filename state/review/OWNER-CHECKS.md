# M6: what the owner still needs to look at

Everything else in M6 has been decided (by you, or by Claude on your delegation, recorded as such) or checked
by rule. Two items remain, both sign-offs on machine drafts that have already been tested.

## 1. The abbreviation and title tables (machine draft)

* Files: [data/abbreviations.yaml](../../data/abbreviations.yaml), [data/works.yaml](../../data/works.yaml)
* What they do: turn Burton's "Hor. lib. 3 Od. 6" into Horace, *Odes*, book 3, ode 6.
* Already tested: three held-out rounds of 65 random resolutions each, checked by hand
  ([data/eval/m6-citations-holdout.yaml](../../data/eval/m6-citations-holdout.yaml)): c1 61/65 (failed; rule
  replaced), c2 64/65, c3 65/65.
* What to do: skim the `authors:` and `ambiguous:` sections for any reading you know to be wrong. If none,
  reply "tables accepted" and their status becomes `checked`.

## 2. The top 100 author entries (machine draft)

* List: [state/review/authors-top100.md](authors-top100.md): each author, Burton's forms, counts, the Wikidata
  match and the drafted description.
* Already tested: an independent checker read all 100
  ([state/review/m6-audit.md](m6-audit.md)): 99 identities right after one fix (Chytraeus), 0 factual errors,
  3 minor slips you accepted.
* What to do: reply "authors accepted", or name any entry to correct.

## For reference: decisions made on your delegation

* Cross-references: 32 confirmed, 7 rejected, each with a reason:
  [state/review/xrefs-relative.md](xrefs-relative.md)
* Source disagreements, with Burton's attribution kept beside each finding:
  [data/manual/source-findings.yaml](../../data/manual/source-findings.yaml)
* "Mart." citations: 17 Martial, 1 Martianus Capella, 1 Justin Martyr, 1 Peter Martyr Vermigli (his
  commentary on Samuel), and 1 "P. Mart." recorded as Vermigli from its theological context only (medium
  confidence): [data/manual/citation-decisions.yaml](../../data/manual/citation-decisions.yaml)
