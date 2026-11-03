# M8 handover (2026-11-03, session 1; stopped at the 5-hour usage limit)

## Done and committed
* `69fb79a`, `16d5b0d`: full-text search, Burton's *Table* (back-matter unit `table`), frontispiece panels.
  `burton check --all` passed for exactly that state: 21 PASS, V5 DEFER, 0 FAIL (counts in the commit body).

## Done, NOT yet committed (needs `burton check --all` first)
* **Obsolete-word glosses** (owner, 2026-11-03: Webster download "Yes"; model drafts "Up to $5 list-equiv."):
  * Webster 1913 = Gutenberg #29765, pinned `data/source/WEBSTER.lock` (sha256 86fb9c28…, 28,956,350 bytes);
    `.gitignore` now tracks the lock. Parser `burton/layers/webster.py` (94,578 headwords; a sense is obsolete
    only if "[Obs.]"/"[Archaic]" is in its first three lines).
  * `burton obsolete` (`burton/layers/obsolete.py`, prompt `obs-v1`, ledger `state/obsolete/ledger.jsonl`):
    candidates by rule `rules/obs-v1` = 748 occurrences of 161 words (stoplist `data/manual/gloss-stoplist.yaml`:
    hath, saith, lib); a model ruling per occurrence → `data/layers/obsolete/<unit>.json`, ids `<unit>-gN` from
    the registry. **560 of 748 ruled ($1.65 list-equivalent so far); 188 left = 5 packets**:
    `uv run burton obsolete --budget-usd 3` (resumes; the cap left is $5 − $1.65).
  * `ids.py`/`ingest/run.py`: ingest now retires only its own id kinds (p, lg, n, f), so gloss ids survive a re-ingest.
  * Reader: `burton/site/glosses.py` (Gowland's glosses by rule `gowland-gloss-v1`, private only, read at build
    time, never in a layer; then Webster/machine from the layer; then the M5 Chaucer glosses), `mark_glosses` in
    render.py, option "Obsolete words" (off by default). Private build: 1,036 placed (Gowland 699, Webster 204,
    machine 133), 63 unplaced (counted). V7 `_obsolete` checks the layer, including that every Webster sense is
    Webster's own words (it caught one: labels are now ignored on both sides). V8 also greps `gl-gowland`.
  * **Held-out rounds:**
    * `data/eval/m8-obsolete-sample.yaml` (round o1): 50 occurrences, labels written BEFORE the run. Score it
      once all 748 are ruled (39 of the 50 were ruled at the stop). Rule: gloss-or-not ≥ 45/50, ≤ 2 wrong senses shown.
    * `data/eval/m8-gowland-gloss-check.yaml` (round g1): **PASS**, 30/30 accepted are word glosses.
* Print stylesheet (edition.css `@media print`): margin sidenotes as floats, light colours, controls hidden.
* Performance: sidenote layout in three passes; desktop djr longest task 1,389 ms → 234–511 ms, 3.2.3.1 298 → ~90 ms.
* `burton axe --all` (full-site V10, both themes, glosses and citations on): was running at the stop;
  log `state/m8-axe-all.log`, report `verify/reports/axe-private-all.json`.
* About page: search, Table, frontispiece, glosses explained (the gloss model name is read from the layer).

## Next session, in order
1. Read the meter. Finish `burton obsolete` (5 packets). Score round o1 against the layer (do not relabel).
2. `uv run burton check --all` (and read `axe-private-all.json`); fix what fails; commit the gloss work with counts.
3. PLAN.md: M8 status block; SPEC §4.2 (layer is `data/layers/obsolete/`, not `glosses/`, which keeps the
   Chaucer records); CLAUDE.md CLI list (`obsolete`, `axe`).
4. M8 exit: V1–V11 on the whole private site, plus the full axe run.

## Do not redo
* Webster download and lock; the candidate rule; the o1 labels (they are blind; keep them).
* The Table ingest (943/943 page references verified).
