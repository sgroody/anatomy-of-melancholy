"""Samples of the translation passes' notes by their rating, for the owner to judge the cutoff (2026-11-20: "give me
samples of them to judge what the cutoff for inclusion should be").

Draws, with a fixed seed, notes from each usefulness rating (note-rate-v1, 1 to 3) and from those flagged doubtful,
and writes a review page: state/review/note-cutoff-2026-11-20.html. Reads the layers only; no model call.

    uv run python tools/note_cutoff_samples.py
"""

import html
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from burton import paths  # noqa: E402
from burton.translate import audit, notes_rate  # noqa: E402

SEED = 20261120
PER = {3: 14, 2: 14, 1: 12}
OUT = paths.ROOT / "state" / "review" / "note-cutoff-2026-11-20.html"
LANG = {"la": "Latin", "grc": "Greek", "it": "Italian", "fr": "French", "es": "Spanish", "de": "German", "enm":
        "Middle English", "he": "Hebrew", "nl": "Dutch"}


def main() -> None:
    rated = notes_rate._layer()
    auds = notes_rate._audits()
    from burton.translate import packets

    live = set()
    for unit in sorted({p.rsplit("-", 1)[0] for p in rated}):
        live |= {x["packet_item"]["id"] for x in packets.passages(unit)}
    rated = {p: r for p, r in rated.items() if p in live}  # passages a re-ingest retired are left out
    rng = random.Random(SEED)
    groups = []
    for u in (3, 2, 1):
        pool = sorted(p for p, r in rated.items() if r["usefulness"] == u and not r["doubtful"])
        groups.append((u, False, len(pool), sorted(rng.sample(pool, min(PER[u], len(pool))))))
    dpool = sorted(p for p, r in rated.items() if r["doubtful"])
    groups.append(("doubtful", True, len(dpool), sorted(rng.sample(dpool, min(8, len(dpool))))))
    want = [p for g in groups for p in g[3]]
    items = {i["id"]: i for i in audit.items(want)}
    table = Counter((r["usefulness"], r["kind"]) for r in rated.values() if not r["doubtful"])
    kinds = notes_rate.KINDS
    shown_n = sum(notes_rate.shown(r, auds.get(p)) for p, r in rated.items())

    def card(p: str) -> str:
        it, r, a = items[p], rated[p], auds.get(p)
        verdict = ""
        if a and a.get("note_hash") == r["note_hash"]:
            verdict = f'<span class="tag t-{a["accuracy"]}">audit: {a["accuracy"]}</span>'
        shows = notes_rate.shown(r, a)
        return (f'<article class="card{" on" if shows else ""}"><header><span class="pid">{html.escape(p)}</span>'
                f'<span class="tag">{html.escape(LANG.get(it["language"], it["language"]))}</span>'
                f'<span class="tag k">{html.escape(r["kind"])}</span><span class="tag r">rated {r["usefulness"]}</span>'
                f'{"<span class=tag>doubtful</span>" if r["doubtful"] else ""}{verdict}'
                f'{"<span class=tag t-sound>shown now</span>" if shows else ""}</header>'
                f'<p class="orig">{html.escape(it["passage"])}</p>'
                f'<p class="tr">{html.escape(it["translation"])}</p>'
                f'<p class="note">{html.escape(it["note"] or "")}</p></article>')

    head_row = "".join(f"<th>{k}</th>" for k in kinds)
    rows = "".join(f"<tr><th>{u}</th>{''.join(f'<td>{table[(u, k)]}</td>' for k in kinds)}"
                   f"<td>{sum(table[(u, k)] for k in kinds)}</td></tr>" for u in (3, 2, 1))
    sections = []
    for u, doubt, n, ids in groups:
        title = f"Flagged doubtful by the rater ({n:,} in all)" if doubt else f"Rated {u} ({n:,} notes, not doubtful)"
        sections.append(f'<section><h2>{title}</h2><p class="drawn">{len(ids)} drawn at random (seed {SEED}).</p>'
                        f'{"".join(card(p) for p in ids if p in items)}</section>')
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Note cutoff samples</title>
<style>
:root {{ --paper:#f7f3ea; --ink:#23201b; --muted:#6b6358; --rule:#d8cfbf; --accent:#8a2f1d; --card:#fffdf8;
  --ok:#2f6b3a; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --paper:#1c1a17; --ink:#e8e1d4;
  --muted:#a59c8e; --rule:#3a352e; --accent:#e0a27a; --card:#24211d; --ok:#8fc79a; }} }}
body {{ background:var(--paper); color:var(--ink); font:17px/1.5 Georgia, "EB Garamond", serif; margin:0 auto;
  max-width:60rem; padding:1.5rem 16px 4rem; }}
h1 {{ font-weight:400; margin:0 0 .3rem; }}
h2 {{ font-weight:400; font-variant-caps:all-small-caps; letter-spacing:.06em; color:var(--accent);
  border-bottom:1px solid var(--rule); margin:2.2rem 0 .4rem; }}
.lead {{ color:var(--muted); }} .drawn {{ color:var(--muted); font-size:.85em; margin:0 0 .8rem; }}
table {{ border-collapse:collapse; font-size:.85em; margin:.6rem 0; }}
th, td {{ border:1px solid var(--rule); padding:.15rem .5rem; text-align:right; }}
thead th {{ font-weight:400; color:var(--muted); }}
.card {{ background:var(--card); border:1px solid var(--rule); border-radius:4px; padding:.6rem .8rem;
  margin:0 0 .7rem; }}
.card.on {{ border-left:3px solid var(--ok); }}
.card header {{ display:flex; flex-wrap:wrap; gap:.35rem; align-items:baseline; font-size:.78em; color:var(--muted); }}
.pid {{ font-family:ui-monospace, monospace; margin-right:.3rem; }}
.tag {{ border:1px solid var(--rule); border-radius:3px; padding:0 .35em; }} .tag.r {{ color:var(--accent); }}
.t-sound {{ color:var(--ok); }} .t-doubtful, .t-wrong {{ color:var(--accent); }}
.orig {{ font-style:italic; margin:.4rem 0 .2rem; }} .tr {{ margin:0 0 .3rem; }}
.note {{ margin:0; padding-left:.6rem; border-left:2px solid var(--rule); font-size:.92em; }}
</style></head><body>
<h1>The translators’ notes: where to cut</h1>
<p class="lead">Each translation pass could add a note to its translation. Every note was rated by a model for its
use to a reader (note-rate-v1): <b>3</b> worth a place in the margin, <b>2</b> of some use, <b>1</b> of little use;
and its kind.
The reader now shows a note only if it is rated 3, not flagged doubtful, and judged sound by the blind auditor:
<b>{shown_n:,}</b> notes (a green rule marks them below). Below: notes drawn at random from each rating, to judge
whether 2 should be shown too, or 3 is already too generous. Each card: the passage, the machine translation, then
the note.</p>
<table><thead><tr><th>rating</th>{head_row}<th>all</th></tr></thead><tbody>{rows}</tbody></table>
{"".join(sections)}
</body></html>
"""
    OUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"{OUT.relative_to(paths.ROOT)}: {sum(len(g[3]) for g in groups)} notes; shown now {shown_n:,}")


if __name__ == "__main__":
    main()
