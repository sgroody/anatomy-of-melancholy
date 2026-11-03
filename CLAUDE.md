# CLAUDE.md — Burton's *Anatomy of Melancholy*: digital edition

A static, offline reading edition of Burton's *Anatomy* built by a pipeline:
**EPUB (Gowland 2021) → TEI-flavoured XML + JSON layers (source of truth) → generated site.**
Read `SPEC.md` for the design, `PLAN.md` for the current milestone, and `SURVEY.md` for facts about the source.

## Fidelity rules (non-negotiable)

1. **Never silently alter, modernize or drop source text.**
   * Base text (`data/text/`) stores the EPUB's code points exactly.
   * A correction is made only as `choice/sic/corr` *and* recorded in `data/manual/source-fixes.yaml`, with location and reason.
   * Normalization (NFC, Greek elision marks, small-caps case) happens only in comparison and search code, never in stored text.
2. **The base text is generated, not hand-edited.** Change the ingest code or a file in `data/manual/`, then re-ingest. Never edit `data/text/*.xml` by hand.
3. **Layers never overwrite the base text.** Translations, citations, cross-references, glosses, authors and synopses live in their own files, keyed by stable ids. Any layer can be deleted and regenerated without touching another.
4. **Ids are permanent.**
   * Assign them only through `data/ids/registry.tsv`.
   * Never renumber; retired ids stay reserved.
   * XML ids carry a `u` prefix; HTML ids and layer keys do not (one conversion function).
5. **Gowland's editorial matter is kept but marked**: `ed:trans`, `ed:verse-trans`, `ed:enref`, `supplied[@resp=#gowland]`, `pb`.
   * It must never appear in a `public` build, and the leak check enforces this.
   * **It must never be sent to a model** as input or as an example.
   * It must never be copied into a layer file.

## Honesty rules (non-negotiable)

* **Never invent a source attribution.**
  * If a quotation's source cannot be identified with real confidence, record `"status": "unidentified"`.
  * A wrong attribution to a plausible authority is worse than none.
  * `identified` requires `verified: true`, which only the source verifier sets.
  * `probable` requires a stated `basis`, and the UI must say "probably".
  * Burton's own attribution in a sidenote is recorded as `burton-cites`. It is not proof, because Burton misquotes and mis-cites.
* **Every machine-produced item is labelled** in the data (`by: machine`, `model`, `prompt` version, `date`) and in the UI (visible label naming the model). This covers translations, source guesses, citation expansions, author entries, glosses and cross-reference proposals. Templates read the label from the data and never hard-code it.
* **Prefer public-domain human translation.**
  * Dell & Jordan-Smith (1927) is public domain in the USA. Record it alongside the machine version.
  * Show it by default per the preference order in SPEC §6.3, unless [D1] restricts it.
  * **Never copy from copyrighted editions:** Clarendon (1989–2000), Gowland's translations and notes (except as marked source text in the private build), or any modern translation.
* **Glossary consistency.**
  * Recurring Latin terms (melancholia, hypochondriacus, humores, spiritus animales, atra bilis, …) and recurring authorities have one entry in `data/glossary.yaml`.
  * Translations use those renderings, and the post-check counts deviations.
  * Add a term to the glossary before translating more passages that use it.
* **Don't guess cross-reference targets.** Unresolvable cross-references stay `unresolved` and are rendered unlinked.
* **Report counts, not impressions.** "Done" means `burton check` passes. Say "1,654/1,654 sidenotes resolved", not "notes look fine". If a check is skipped or fails, say so with the numbers.

## Verification rules

A unit is not done until `burton check` passes for it. The build **fails loudly** (non-zero exit, printed counts) on:
* any orphaned note;
* a broken link or cross-reference;
* an untagged foreign-script run;
* an unexplained text difference against the EPUB;
* a profile leak;
* a layer key that is missing from the base text.

Required checks (SPEC §9):
* **V1**: normalized plain text of output == normalized plain text of the EPUB, with every difference listed in `verify/allowed-diffs.yaml` (with a reason) or in `source-fixes.yaml`.
* **V2/V3**: per-unit note and sidenote counts match, and every note resolves to an anchor.
* **V4**: every Greek, Hebrew or Arabic character has an ancestor with a matching `lang`.
* **V5**: language identification is evaluated on the hand-checked gold sample (`data/eval/langid-gold.jsonl`). It uses italics, script and context, never a language-detector library alone.
* **V6–V11**: links, layers, leak, font coverage, HTML and accessibility, synopsis completeness.

**Verifiers are independent of the code they verify.** EPUB-side counts come from `burton/verify/epub_counts.py`, which must not import from `burton/ingest/`.

When a check fails, fix the cause. Do not add an `allowed-diffs` entry to make a failure go away unless the difference is genuinely intended, and give the reason.

## Conventions

* **Python ≥ 3.12 via `uv`** (`uv run burton …`). Lint with `ruff` and test with `pytest`.
  * Installed: Python 3.13.15 (through the `py` launcher), uv 0.13.1, git, Node 24, Claude Code 2.1.304.
  * Bare `python`/`python3` on PATH is the Microsoft Store stub and does nothing useful, so always go through `uv run`.
  * Calibre's `calibre-debug -e script.py` exists for quick looks at the EPUB.
* **Shell.** This is Windows: the Bash tool is Git Bash and PowerShell is also available. Use forward slashes in Python paths (`pathlib`).
* **CLI** (single entry point `burton`): `unpack`, `ingest`, `verify`, `align-djs`, `translate`, `expand-citations`, `verify-sources`, `build --profile private|public`, `serve`, `check`.
  * Built so far: `unpack`, `counts`, `ingest`, `verify`, `translate` (`--dry-run`, `--packet-size`, `--max-packets`), `fonts`, `build`, `serve`, `check`. Most take `--unit` (repeatable).
  * `uv run burton check --unit 1.1.1.2` is the "done" gate. It re-ingests, verifies, builds both profiles and checks the site; the report goes to `verify/reports/latest.json`.
  * `uv run python tests/manual/kill_resume.py <unit>` kills the translation runner mid-run and resumes it. It uses real `claude -p` calls, so it is not part of pytest.
  * M2 added: `lexicon` (rebuilds the book's Latin/English word lists from a rules-only ingest; changes language decisions, so run it deliberately), `adjudicate` (model rulings on undecided language runs → `data/layers/langid-adjudication.json`), `xrefs`, `selftrans` (rules-only self-translation signals → `data/layers/selftrans/`; re-run after any ingest that changes passages, or V7 reports stale records), and `ingest --all` (which also writes `data/text/gowland-endnotes.xml`).
  * M5 added: `translate --all --budget-usd N` (stops before the next packet at that list-equivalent spend) and `--wait-on-limit` (retries every 20 min at a usage limit instead of exiting 3). Full runs also queue the Chaucer (`enm`) verse groups as gloss-only items and move records keyed by retired ids to `data/layers/retired/`. Read the plan's meter with the app's usage tool before and after a run and append it to `state/translate/meter.jsonl`. `align-djs --all` (or `--unit`) aligns Dell & Jordan-Smith for whole units (rules only); re-run it after any ingest that changes passages, or V7 reports stale records. Changing its rules means bumping `rules/djs-align-vN` and a fresh held-out round (`data/eval/djs-holdout.yaml`). `translate --select F --redo` re-translates named items even when current. `djs-audit` and `tr-audit` run a blind second rater (model, ledgered) over a held-out round or the spot-check. A source claim withdrawn by a check goes in `data/manual/source-downgrades.yaml`, never by editing the layer.
  * M4 added: `translate --select data/eval/m4-pilot.yaml` (only the listed items; gloss-only Chaucer items go to `data/layers/glosses/`), `align-djs --select …` (Dell & Jordan-Smith → `data/layers/djs/`), and `pilot-report` (→ `verify/reports/m4-pilot.json` and the review page `m4-review.html`).
  * M7 added: `synopses` (`data/manual/synopses/pN.yaml`, the shape read from the images as hidden-table ids, + the hidden text verbatim → `data/synopses/pN.json`; `burton check` re-runs it and V11 checks it against the EPUB) and `syn-audit` (blind model reading of the sampled strings' parents from the images, `--report` compares; round s1 in `data/eval/m7-structure-sample.yaml`). Reader: `/pN/synopsis/`, and every unit page links to its node.
  * M8 added: back-matter unit `table` (Burton's Table; its Penguin page numbers are `ed:locs`/`ed:pageref`, linked to page markers in the private build only), full-text search (`assets/search-index.json`, built with the site; V6/V8/V9 check it), frontispiece panels (`data/manual/frontispiece.yaml`, machine-read rectangles), `obsolete` (obsolete-word glosses: Webster 1913, pinned in `data/source/WEBSTER.lock`, candidates by rule, a ledgered model ruling per occurrence → `data/layers/obsolete/`; held-out round o1 in `data/eval/m8-obsolete-sample.yaml`) and `axe --all` (axe-core on every page, both themes → `verify/reports/axe-<profile>-all.json`). Gloss ids (`g`) are a layer's: ingest retires only `p`, `lg`, `n`, `f`.
* **Hand-made decisions live in `data/manual/`**, never in code:
  * `blocks.yaml`: block-level language and Gowland-block decisions;
  * `source-fixes.yaml`: `sic`/`corr` corrections;
  * `link-fixes.yaml`: mis-targeted note links (original kept as `@sic`);
  * `source-downgrades.yaml`: source claims withdrawn by a check (shown as unidentified; V7 checks);
  * `heading-images.yaml`, `alt-text.yaml`, `known-source-defects.yaml`;
  * `deferred-checks.yaml`: checks the owner allows to fail for now (reported `DEFER`, never `PASS`; currently V5, D10).
* **`resp="#editor"` on markup means an editorial decision, not added text.** Text we add is only: transcribed heading images (`head[@facs]`), `corr`, and `supplied[@resp=#editor]`. V1 excludes exactly those.
* **Passage ids are anchored on their text** (container + text fingerprint), so better detection elsewhere in a paragraph never renumbers them. Never change the locator scheme without the re-identification fallback in `burton/ids.py`.
* **Language decisions record provenance.** `resp="#rules"` for rules and the book lexicon (never `cert="high"` from the lexicon); `resp="#model"` for adjudicated runs (high becomes `medium`, and low rulings are not applied); `resp="#editor"` for `blocks.yaml`.
* **Editing code on Windows:** don't patch Python through shell heredocs; `\b`, `\d` and line continuations get mangled. Use the Edit tool or a script file. Write data files with `burton.fsutil.atomic_write_text`, which retries Windows' transient file locks.
* **Translation runner facts** (learned in M1):
  * `claude -p` must run from a temp dir outside the repo, or it loads this CLAUDE.md.
  * `--bare` cannot authenticate with the subscription.
  * The parsed result arrives in `structured_output`.
  * On Windows, killing `uv run` leaves the child alive, so the runner holds `state/translate/runner.lock` and a second runner refuses to start.
* **Browser testing**: the site's service worker is cache-first, so after a rebuild reload twice (or clear site data). The app's browser pane can register it (seen 2026-11-03): after a rebuild, unregister it and clear `caches` from the page, or you are looking at the previous build. Offline behaviour is tested with Playwright (M3).
* **Layout:**
  * `burton/` package (`ingest/`, `layers/`, `translate/`, `site/`, `verify/`)
  * `data/source/` (gitignored originals + `SOURCE.lock` hashes)
  * `data/text/`, `data/layers/<layer>/<unit>.json`, `data/authors/`, `data/manual/`, `data/eval/`
  * `schema/`, `verify/`, `state/` (runner ledgers, review queues), `site/` (generated, gitignored)
* **Unit ids**: `1.2.3.4`, `djr`, `argument`, `dedication`, `ad-librum`, `abstract`, `lectori`, `heraclite`, `p1`, `p1-synopsis`.
  **Element ids**: `<unit>-p3`, `-lg2`, `-n12`, `-f7`, `-x1`, `-n12-c2`.
* **Pointing into running text** from a layer uses a text-quote selector `{in, exact, prefix, suffix}` that must match exactly once. Character offsets are not used.
* **JSON layers** have sorted keys, 2-space indent, UTF-8, a trailing newline, and are written atomically (temporary file, then rename).
* **Model calls** happen only in resumable scripts that write ledgers (`state/…/ledger.jsonl`), never as conversational translation inside a session.
  * **There is no API key.** Scripts call `claude -p` headless as a subprocess, with tools disabled and `--json-schema` for the output. They stop cleanly on usage limits and resume from the ledger. Do not add the `anthropic` SDK or ask for a key.
  * Each call records model id, prompt version and input hash.
  * Prompts live in `burton/translate/prompts/` and are versioned (`tr-v3`). Changing a prompt means bumping its version.
  * The default model is `claude-opus-5-5` unless the project owner chooses otherwise (PLAN [D8]).
* **Commits**: one logical change each. Run `burton check` (or the relevant subset) before committing and put the counts in the message body. Never commit `data/source/` or `site/`.
* **Copyright hygiene**: the repository contains EPUB-derived text. Do not push it to any public remote unless the project owner decides otherwise ([D1]).

## Known source facts to remember (details in SURVEY.md)

* Gowland's text is already **modernized**. There is no original spelling in the source.
* Burton's **sidenotes were pruned** by Gowland. Sidenote counts match the EPUB, not Burton's 1651.
* `[…]` = Gowland translation, `{…}` = Gowland interpolation. Class `TS*` verse marks the start of *any* verse translation. It is Gowland's only if bracketed; otherwise it is Burton's own rendering.
* 3 sidenote refs, 3 endnote refs and 3 page markers sit on Gowland's translation pages (`preface004`, `preface008`).
* `ß` in recipes is the apothecary *semis* (½), not German. Keep it and gloss it.
* `span.lucida` = Chaucer (Middle English, `enm`). `span.arial_bold` = astrological keys and symbols.
* Synopses and four headings are **images**. The hidden table text of the synopses is flat and partly reordered.
* The EPUB defect list in SURVEY §3–§5 is the starting content of `data/manual/known-source-defects.yaml`.
