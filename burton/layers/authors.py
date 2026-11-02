"""`burton authors`: the author registry (SPEC §4.2) and the owner's top-100 review list.

* Counts come from data/layers/citations/ every time; they are never stored in the author files, so they
  cannot go stale.
* data/authors/<id>.yaml holds what is not derivable: Wikidata id and dates (`by: wikidata`), the model-drafted
  identification and "why Burton cites them" (`by: machine`, status `machine-draft`), and the owner's check
  (`status: checked`). Burton's forms live only in data/abbreviations.yaml. This command creates a skeleton for
  a cited author without a file and never overwrites a field that is already set.
* state/review/authors-top100.md lists the 100 most-cited authors with what the owner should check. It is a
  review list: nothing in it is approved here.
"""

import json
from collections import Counter, defaultdict
from datetime import date

import yaml

from .. import paths
from ..fsutil import atomic_write_text
from . import citations

DIR = paths.DATA / "authors"
REVIEW = paths.STATE / "review" / "authors-top100.md"
NOT_AUTHORS = {"bible", "burton"}  # Scripture and Burton's own cross-references have no author page


def cited() -> dict[str, dict]:
    """Per author: citations, sidenotes, units and up to 8 example citations (raw), from the layer."""
    out: dict[str, dict] = defaultdict(lambda: {"citations": 0, "notes": set(), "units": set(), "examples": [],
                                                "statuses": Counter(), "works": Counter()})
    for f in sorted((paths.LAYERS / "citations").glob("*.json")):
        for nid, rec in json.loads(f.read_text(encoding="utf-8")).items():
            for c in rec["citations"]:
                a = c.get("author")
                if not a or a in NOT_AUTHORS:
                    continue
                d = out[a]
                d["citations"] += 1
                d["notes"].add(nid)
                d["units"].add(f.stem)
                d["statuses"][c["status"]] += 1
                if c.get("work"):
                    d["works"][c["work"]] += 1
                if len(d["examples"]) < 8 and c["raw"] not in [e["raw"] for e in d["examples"]]:
                    d["examples"].append({"note": nid, "raw": c["raw"]})
    return dict(out)


def ranked() -> list[tuple[str, dict]]:
    return sorted(cited().items(), key=lambda kv: (-kv[1]["citations"], kv[0]))


def load(aid: str) -> dict:
    f = DIR / f"{aid}.yaml"
    return yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else {}


def save(aid: str, rec: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    head = ("# Author registry entry (SPEC §4.2). Burton's forms: data/abbreviations.yaml. Counts: computed from\n"
            "# data/layers/citations/ by `burton authors`. Set `status: checked` only after the owner's review.\n")
    atomic_write_text(DIR / f"{aid}.yaml",
                      head + yaml.safe_dump(rec, allow_unicode=True, sort_keys=False, width=110))


SKELETON = {"id": None, "name": None, "status": "machine-draft", "wikidata": None, "identification": None,
            "why_cited": None, "review": {"state": "unreviewed", "by": None, "date": None, "note": None}}


def build() -> Counter:
    """Create a skeleton for every cited author without a file; fill only missing keys."""
    t = citations.tables()
    stats: Counter = Counter()
    for aid, _ in ranked():
        rec = load(aid)
        new = not rec
        for k, v in SKELETON.items():
            rec.setdefault(k, v if not isinstance(v, dict) else dict(v))
        rec["id"], rec["name"] = aid, t["authors"][aid]["name"]
        save(aid, rec)
        stats["created" if new else "kept"] += 1
    for f in DIR.glob("*.yaml"):
        if f.stem not in t["authors"]:
            stats["orphan_files"] += 1
    stats["authors_cited"] = len(ranked())
    stats["authors_in_table"] = len(t["authors"]) - len(NOT_AUTHORS & set(t["authors"]))
    return stats


def review_list(n: int = 100) -> Counter:
    """state/review/authors-top100.md: the owner's checklist for the n most-cited authors."""
    t = citations.tables()
    rows = ranked()[:n]
    lines = [
        f"# Top {n} authors by citation count: owner review (M6)",
        "",
        f"Generated {date.today().isoformat()} by `uv run burton authors --review`. Counts are from the rules-only",
        "citation layer (`data/layers/citations/`, method `rules/abbrev-v1`). Everything below is a draft until you",
        "check it: the identification of Burton's form, the Wikidata match, and the model-drafted identification",
        "and \"why Burton cites them\" (labelled `machine-draft`).",
        "",
        "To record your check, edit `data/authors/<id>.yaml`: set `review.state` to `agreed` or `corrected`",
        "(with `review.note`), and `status: checked`. Corrections to a form go in `data/abbreviations.yaml`.",
        "",
        "| # | Author | id | Burton's forms | Citations | Sidenotes | Units | Wikidata | Draft |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    stats: Counter = Counter()
    for k, (aid, d) in enumerate(rows, 1):
        rec = load(aid)
        amb = [" ".join(f) + " (ambiguous)" for f, spec in t["forms"].items()
               if len(spec["candidates"]) > 1 and aid in spec["candidates"]]
        forms = ", ".join([*t["authors"][aid]["forms"], *amb]) or "(by work only)"
        wd = (rec.get("wikidata") or {}).get("qid") or "—"
        draft = "yes" if rec.get("identification") else "—"
        stats["with_wikidata"] += wd != "—"
        stats["with_draft"] += draft == "yes"
        lines.append(f"| {k} | {t['authors'][aid]['name']} | `{aid}` | {forms} | {d['citations']} | "
                     f"{len(d['notes'])} | {len(d['units'])} | {wd} | {draft} |")
    lines += ["", "## Examples of each author's citations", ""]
    for k, (aid, d) in enumerate(rows, 1):
        lines.append(f"**{k}. {t['authors'][aid]['name']}** (`{aid}`): "
                     + "; ".join(f"{e['raw']} ({e['note']})" for e in d["examples"][:4]))
        lines.append("")
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(REVIEW, "\n".join(lines) + "\n")
    stats["listed"] = len(rows)
    return stats
