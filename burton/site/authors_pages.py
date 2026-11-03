"""The author index and author pages (M6), built from the citation layer and data/authors/.

Everything shown is read from the data: counts from data/layers/citations/, dates from the Wikidata match,
descriptions from the model draft with its own label. Nothing is hard-coded about who made what.
"""

import json
import re
from collections import Counter

from markupsafe import Markup, escape

from .. import paths
from ..layers import authors as registry
from ..layers import citations

BASIS = {"text-at-anchor": "author named in the text at the note",
         "work-title": "author known from the title",
         "own-divisions": "a reference to this book"}


GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]+(?:[\s.,]+[Ͱ-Ͽἀ-῿]+)*")


def tagged(s: str) -> Markup:
    """Burton's citation text as HTML, with Greek runs marked lang="grc" (V4h)."""
    out, at = [], 0
    for m in GREEK.finditer(s):
        out += [escape(s[at:m.start()]), Markup('<span lang="grc">'), escape(m.group(0)), Markup("</span>")]
        at = m.end()
    return Markup("").join([*out, escape(s[at:])])


def year(y: int | None) -> str:
    return "" if y is None else (f"{-y} BC" if y < 0 else str(y))


def dates(wd: dict | None) -> str | None:
    if not wd or wd.get("status") != "matched":
        return None
    b, d = wd.get("born"), wd.get("died")
    if b is None and d is None:
        return None
    if b is None:
        return f"d. {year(d)}"
    if d is None:
        return f"b. {year(b)}"
    if b < 0 <= d:
        return f"{year(b)} – AD {d}"
    return f"{year(b)}–{year(d)}"


def tables_label() -> dict:
    p = citations._load(citations.ABBREV)["provenance"]
    checked = p.get("status") == "checked"
    review = f"checked by the {p['checked_by']} ({p['checked_date']})" if checked else "not yet reviewed"
    return {"label": f"machine draft ({p['model']}, {p['date']}), {review}",
            "short": f"expanded by rule; tables a machine draft ({p['model']}){', checked' if checked else ''}",
            "method": citations.METHOD}


def collect(units: list[str], shown: set[str] | None = None) -> tuple[dict, dict]:
    """Per-author page data and the index's counts, for the units in this build. `shown`: the sidenote ids
    the build rendered (the public profile withholds those inside Gowland's matter); others are left out."""
    t = citations.tables()
    stats = Counter()
    by: dict[str, dict] = {}
    for unit in units:  # reading order
        f = paths.LAYERS / "citations" / f"{unit}.json"
        if not f.exists():
            continue
        layer = json.loads(f.read_text(encoding="utf-8"))
        for nid in sorted(layer, key=lambda k: int(k.rsplit("-n", 1)[1])):  # the layer's keys sort as text
            rec = layer[nid]
            if shown is not None and nid not in shown:
                continue
            stats["notes"] += 1
            stats[{"no-citation": "none"}.get(rec["status"], rec["status"])] += 1
            for c in rec["citations"]:
                a = c.get("author")
                if a == "bible":
                    stats["bible"] += 1
                if not a or a in registry.NOT_AUTHORS:
                    continue
                stats["citations"] += 1
                d = by.setdefault(a, {"cites": [], "works": Counter(), "notes": set(), "status": Counter()})
                basis = BASIS.get(c.get("author_basis"))
                if c.get("resolved_from"):
                    basis = "Idem / ibid.: the author of the citation before"
                elif c.get("resolved_by") == "default":
                    basis = "the usual reading of an ambiguous abbreviation"
                d["cites"].append({"unit": unit, "note": nid, "raw": tagged(c["raw"]), "basis": basis,
                                   "where": f"{unit}, note {nid.rsplit('-n', 1)[1]}"})
                d["notes"].add(nid)
                d["status"][c["status"]] += 1
                if c.get("work"):
                    d["works"][c["work"]] += 1
    titles = {wid: spec["title"] for ws in t["works"].values() for wid, spec in ws}
    pages = {}
    for aid, d in by.items():
        rec = registry.load(aid)
        amb = [" ".join(f) for f, spec in t["forms"].items()
               if len(spec["candidates"]) > 1 and aid in spec["candidates"]]
        forms = list(t["authors"][aid]["forms"])
        draft = rec.get("draft")
        if draft:  # the model's prose may quote Greek ("Odyssey 4 (δ)"): mark it like the citations
            draft = {**draft, **{k: tagged(draft[k]) for k in ("identification", "why_cited", "identity_doubt")
                                 if draft.get(k)}}
        pages[aid] = {"id": aid, "name": t["authors"][aid]["name"],
                      "forms": ", ".join(forms + [f"{f} (also used for others)" for f in amb]),
                      "wikidata": rec.get("wikidata") if (rec.get("wikidata") or {}).get("status") == "matched"
                      else None,
                      "dates": dates(rec.get("wikidata")), "draft": draft,
                      "field": (draft or {}).get("field"),
                      "review_state": (rec.get("review") or {}).get("state", "unreviewed"),
                      "review": rec.get("review") or {},
                      "citations": len(d["cites"]), "notes": len(d["notes"]),
                      "parsed": d["status"]["parsed"], "partial": d["status"]["partial"],
                      "works": [(titles[w], n) for w, n in d["works"].most_common()], "cites": d["cites"]}
    stats["authors"] = len(pages)
    # every count the index prints, 0 when a partial build has none (1.1.1.2 alone cites no Scripture)
    return pages, {k: stats[k] for k in ("notes", "citations", "bible", "parsed", "partial", "unidentified",
                                         "none", "authors")} | dict(stats)
