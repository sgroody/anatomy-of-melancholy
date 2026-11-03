# M7 brief: the synopses (start a fresh session with this)

**Status 2026-11-03: done in one session** (PLAN.md, "M7 built"). All three trees, V11, the spot check and the reader are in place. The owner reviewed P2 against the sheets and accepted it, flagged readings included ("All accepted"). M7 is closed.

Owner, 2026-11-02: "Yes, start M7". M6 is done (PLAN.md, M6 status). Read CLAUDE.md, the PLAN.md M7 section,
SPEC §4.2 "Synopses", §7.3 (links both ways) and §9 V11, SURVEY §6. Skip everything else.

## Settled facts (reproduce with `uv run burton synopses --checklist`)

* 3 synopses, 20 images: P1 8 (`pg131_01`–`pg134_02`), P2 8 (`pg427_01`–`pg430_02`), P3 4 (`pg667_01`–`pg668_02`),
  in `work/epub/EPUB/images/`, about 1,400 × 900 px each.
* Hidden tables (`chapter001/2/3.xhtml`): 330 / 413 / 250 `<p>`, every one with a unique id (`nat…`). Brace-only
  glyph paragraphs (⎧ ⎨ ⎩): 111 / 189 / 132. **Non-glyph strings: 219 / 224 / 118 = 561** (V11's number).
* Checklists: `state/m7/p1-checklist.tsv` etc. (id, text). The order is partly shuffled (P1 inverts 11 times).
* "Or" is its own paragraph: Burton's connector between alternatives. Use it as the relation marker on its node
  so it, too, is used exactly once.
* Known duplicate: "In diseases consider Sect. 1 Memb. 1." is both `nat0000034a` and `nat0000108`. Explain it in
  the structure file; V11 allows exactly this one.
* Cross-keys: astrological glyphs in `span.arial_bold` ("Melancholy. See ♈") join parts of the tree across
  images. Record them as `see` links.

## Method (decided in the M6 session; keep it)

1. **Words come only from the hidden table, verbatim** (`burton/ingest/synopses.py: hidden()`); never retype text
   from an image. The base-text fidelity rules apply.
2. **Only the shape comes from the images**: read each image (Read tool, one at a time) and write the nesting as
   ids in `data/manual/synopses/pN.yaml`: each node `{p: nat…, children: [...], relation: or?, see: ♈?}`. This is a
   machine-made structure: put a provenance header (`by: claude-opus-5-5, in session, date`), status
   `machine-draft`, like the M6 tables. Work one partition at a time and commit after each.
3. `burton synopses` (to write): build `data/synopses/pN.json` from the structure + verbatim text (SPEC §4.2
   shape: id, text, ref, relation, see, src_p), and resolve each node's "Sect./Memb./Subsect." label to a unit,
   inheriting missing upper levels from ancestor nodes (as `burton/layers/xrefs.py` does). An unresolvable label
   stays unresolved, never guessed.
4. V11 in `burton/verify/` (independent of the builder: read the EPUB and the JSON, not the builder's code): the
   multiset of non-glyph hidden strings equals the multiset of node texts (duplicate explained); every label
   resolves to a unit; every `see` key has a target.
5. Reader: `/p1/synopsis/` etc. as nested disclosure buttons with brace styling in CSS; each node links to its
   unit; each unit page links back to its node ("where am I in the synopsis"); the images stay as the facsimile
   with alt text. Then `burton check --all` (V6 covers the new links; V10a/V10k the new widget).
6. Check: a held-out style spot check of the structure against the images (sample written before labelling), and
   offer the owner a visual review of one partition.

## Budget

Weekly meter at M6 end: 22 %. Owner's cap: 92 % per week. Reading 20 images in session is the main cost; read
the meter before and after each partition and append it to `state/translate/meter.jsonl`. No model runs are
planned beyond session work.
