# M6: corpora for the source verifier, awaiting your approval

`burton verify-sources` (burton/layers/sources.py) upgrades a quotation's source to **identified** only on a
verified text match against a local corpus. Nothing has been downloaded. Downloading is your decision; reply
with which of these (if any) to fetch. Each would go, gitignored, under `data/source/corpora/`, pinned by hash
in `data/source/CORPORA.lock`, and be converted to one `locus<TAB>text` file per work.

| # | Corpus | Source | Size (GitHub repository, with history; a snapshot is smaller) | Licence |
|---|---|---|---|---|
| 1 | Perseus Digital Library, Latin literature (TEI) | github.com/PerseusDL/canonical-latinLit | about 384 MB | CC BY-SA 4.0 |
| 2 | Perseus Digital Library, Greek literature (TEI) | github.com/PerseusDL/canonical-greekLit | about 848 MB | CC BY-SA 4.0 |
| 3 | First Thousand Years of Greek (TEI) | github.com/OpenGreekAndLatin/First1KGreek | about 934 MB | CC BY-SA 4.0 |

Notes:

* The plan says "public-domain corpora". These are **not** public domain: the underlying editions are old, but
  the encoded texts are CC BY-SA 4.0. The edition would store only a reference (corpus, work, locus) and match
  scores, never corpus text, so no share-alike text would enter the layers; please confirm that is acceptable.
* Burton's Latin authorities (Horace, Ovid, Virgil, Seneca, Juvenal, Terence, Plautus, Lucretius, Cicero …)
  are mostly in #1. #2/#3 matter only for the 66 Greek passages. The neo-Latin physicians and the Church
  Fathers (Cardano, Lemnius, Augustine, Chrysostom …) are not in these corpora, so most of Burton's
  quotations from them will stay `burton-cites` / `probable`.
* A shallow snapshot (latest commit only) of #1 would be enough to start; sizes above are upper bounds.
* Not proposed: The Latin Library (rights statements unclear), PHI Latin texts (licensed), any modern edition.
