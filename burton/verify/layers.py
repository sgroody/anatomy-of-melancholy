"""V7: layer integrity (SPEC §9). Reads layer JSON and the base text; imports nothing from ingest."""

import json

from lxml import etree

from .. import paths
from ..tei import XML_ID, XML_LANG, T, public_id
from ..textview import public_text
from ..translate.packets import sha1
from ..translate.validate import source_downgrades


def _inside_brackets(text: str, a: int, b: int) -> bool:
    """Does text[a:b] start inside a bracket or brace opened before it?"""
    depth = 0
    for ch in text[:a]:
        if ch in "[{":
            depth += 1
        elif ch in "]}" and depth:
            depth -= 1
    return depth > 0 and a < b


def _selftrans(unit: str, root, foreign: dict, r, c: dict) -> None:
    """Self-translation signals (a rules layer): one current, labelled record per foreign passage, and every
    candidate selector matching exactly once in the public text of the element it names."""
    def add(k, n=1):
        c[k] = c.get(k, 0) + n

    f = paths.LAYERS / "selftrans" / f"{unit}.json"
    if not f.exists():
        add("selftrans_units_missing")
        r.fail(f"{unit}: no self-translation layer; run `burton selftrans --unit {unit}`")
        return
    layer = json.loads(f.read_text(encoding="utf-8"))
    by_id = {public_id(e.get(XML_ID)): e for e in root.iter()
             if isinstance(e.tag, str) and (e.get(XML_ID) or "").startswith("u")}
    for key, rec in layer.items():
        if key not in foreign:
            add("selftrans_orphan_keys")
            r.fail(f"{unit}: self-translation key {key} not in base text")
            continue
        add("selftrans_records")
        if rec["text_sha1"] != sha1(public_text(foreign[key])):
            add("selftrans_stale")
            r.fail(f"{key}: self-translation record is stale (base text changed); re-run `burton selftrans`")
        for item in [rec, *rec["candidates"]]:
            if item.get("by") != "rules" and not (item.get("by") == "machine" and
                                                  all(item.get(k) for k in ("model", "prompt", "date"))):
                r.fail(f"{key}: self-translation item without a rules or machine label")
        for cand in rec["candidates"]:
            sel = cand["selector"]
            el = by_id.get(sel["in"])
            n, text, quote = 0, "", sel["prefix"] + sel["exact"] + sel["suffix"]
            if el is not None and sel["exact"].strip():
                text = public_text(el, notes=el.tag == T("note"))
                n = text.count(quote)
            if n == 1:
                add("selftrans_selectors_ok")
            else:
                add("selftrans_selectors_bad")
                r.fail(f"{key}: self-translation candidate in {sel['in']} matches {n} times")
                continue
            # Burton writes no [ ] or { }: any left in the public view are Gowland's, unseparated (rule 5)
            at = text.index(quote)
            if any(ch in "[]{}" for ch in quote) or _inside_brackets(text, at, at + len(quote)):
                add("selftrans_gowland_overlap")
                r.fail(f"{key}: self-translation candidate in {sel['in']} overlaps bracketed (Gowland) text")
    missing = [k for k in foreign if k not in layer]
    if missing:
        add("selftrans_missing", len(missing))
        r.fail(f"{unit}: {len(missing)} foreign passages without a self-translation record, e.g. {missing[0]}")


def _glosses(unit: str, root, r, c: dict) -> None:
    """Glosses of obsolete English (M4 pilot: Chaucer): keys are element ids in the base text, records are
    current and labelled, and every selector matches exactly once in its element's public text."""
    f = paths.LAYERS / "glosses" / f"{unit}.json"
    if not f.exists():
        return
    by_id = {public_id(e.get(XML_ID)): e for e in root.iter()
             if isinstance(e.tag, str) and (e.get(XML_ID) or "").startswith("u")}
    for key, rec in json.loads(f.read_text(encoding="utf-8")).items():
        c["gloss_records"] = c.get("gloss_records", 0) + 1
        el = by_id.get(key)
        if el is None:
            r.fail(f"{unit}: gloss key {key} not in base text")
            continue
        text = public_text(el)
        if rec["text_sha1"] != sha1(text):
            r.fail(f"{key}: gloss record is stale (base text changed)")
        for g in rec["glosses"]:
            if g.get("by") == "machine" and not all(g.get(k) for k in ("model", "prompt", "date")):
                r.fail(f"{key}: machine gloss without model/prompt/date")
            for it in g["items"]:
                sel = it["selector"]
                n = text.count(sel["prefix"] + sel["exact"] + sel["suffix"]) if sel["in"] == key else 0
                k = "gloss_selectors_ok" if n == 1 else "gloss_selectors_bad"
                c[k] = c.get(k, 0) + 1
                if n != 1:
                    r.fail(f"{key}: gloss selector {sel['exact']!r} matches {n} times")


DJS_STATUSES = {"aligned", "omitted", "kept-original", "no-anchor", "not-found", "below-threshold",
                "implausible-length", "ocr-noise", "broken-span"}


def _djs(unit: str, foreign: dict, r, c: dict) -> None:
    """Dell & Jordan-Smith alignments: keyed by foreign passages, current, labelled with their method, and a
    text for every aligned or omitted record (never for a discarded candidate)."""
    f = paths.LAYERS / "djs" / f"{unit}.json"
    if not f.exists():
        return
    for key, rec in json.loads(f.read_text(encoding="utf-8")).items():
        c["djs_records"] = c.get("djs_records", 0) + 1
        if key not in foreign:
            c["djs_orphan_keys"] = c.get("djs_orphan_keys", 0) + 1
            r.fail(f"{unit}: Dell & Jordan-Smith key {key} not in base text")
            continue
        if rec["text_sha1"] != sha1(public_text(foreign[key])):
            c["djs_stale"] = c.get("djs_stale", 0) + 1
            r.fail(f"{key}: Dell & Jordan-Smith record is stale (base text changed); re-run `burton align-djs`")
        st = rec["status"]
        c[f"djs_{st}"] = c.get(f"djs_{st}", 0) + 1
        if st not in DJS_STATUSES or rec.get("by") != "djs1927" or not rec.get("method"):
            r.fail(f"{key}: Dell & Jordan-Smith record without a known status, source or method")
        if (st in ("aligned", "kept-original")) != bool(rec.get("text")):
            r.fail(f"{key}: Dell & Jordan-Smith text present on a {st} record, or missing on an aligned one")


CITATION_STATUSES = {"parsed", "partial", "unidentified"}
NOTE_STATUSES = CITATION_STATUSES | {"no-citation"}


def _registries() -> tuple[set, set, set]:
    """Author ids, work ids and Bible books, read straight from the yaml (not through the parser)."""
    import yaml

    a = yaml.safe_load((paths.DATA / "abbreviations.yaml").read_text(encoding="utf-8"))
    w = yaml.safe_load((paths.DATA / "works.yaml").read_text(encoding="utf-8"))
    return set(a["authors"]), set(w["works"]), set(a["bible"])


def _citations(unit: str, root, r, c: dict) -> None:
    """Sidenote citations (M6): one current record per sidenote, known statuses, every author and work id in
    the registries, Idem/ibid pointing at an earlier citation, and nothing displayed that was not resolved."""
    def add(k, n=1):
        c[k] = c.get(k, 0) + n

    notes = {public_id(n.get(XML_ID)): n for n in root.iter(T("note")) if n.get("type") == "side"}
    f = paths.LAYERS / "citations" / f"{unit}.json"
    layer = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    authors, works, books = _registries()
    order = {k: i for i, k in enumerate(notes)}  # document order; the layer's keys are sorted as text
    ids = {cit["id"]: (order.get(k, -1), j) for k, rec in layer.items() for j, cit in enumerate(rec["citations"])}
    for key, rec in layer.items():
        if key not in notes:
            add("citation_orphan_keys")
            r.fail(f"{unit}: citation key {key} is not a sidenote in the base text")
            continue
        if rec["raw"] != public_text(notes[key], notes=True):
            add("citation_stale")
            r.fail(f"{key}: citation record is stale (base text changed); re-run `burton citations`")
        if rec["status"] not in NOTE_STATUSES or (rec["status"] == "no-citation") != (not rec["citations"]):
            r.fail(f"{key}: sidenote status {rec['status']!r} does not fit its citations")
        add(f"sidenotes_{rec['status']}")
        for cit in rec["citations"]:
            add(f"citations_{cit['status']}")
            if cit["status"] not in CITATION_STATUSES or not cit.get("method"):
                r.fail(f"{cit['id']}: citation without a known status or method")
            a, w = cit.get("author"), cit.get("work")
            if a and a != "bible" and a not in authors:
                r.fail(f"{cit['id']}: author {a} is not in data/abbreviations.yaml")
            if w and not (w in works or (a == "bible" and w.split(".", 1)[1] in books)):
                r.fail(f"{cit['id']}: work {w} is not in data/works.yaml")
            if (cit["status"] == "unidentified") != (not a):
                r.fail(f"{cit['id']}: status {cit['status']} with author {a}")
            if cit.get("display") and not (a or cit["locus"]):
                r.fail(f"{cit['id']}: display text with nothing resolved")
            src = cit.get("resolved_from")
            if src and not (src in ids and ids[src] < ids[cit["id"]]):
                r.fail(f"{cit['id']}: Idem/ibid resolved from {src}, not an earlier citation")
            if cit.get("author_basis"):
                add(f"citation_author_{cit['author_basis']}")
    missing = [k for k in notes if k not in layer]
    if missing:
        add("citation_sidenotes_missing", len(missing))
        r.fail(f"{unit}: {len(missing)} sidenotes without a citation record, e.g. {missing[0]}; run `burton citations`")


def v7_layers(units: list[str]):
    from .checks import Result

    r = Result("V7", "layers keyed, labelled and honest")
    c = {"foreign": 0, "with_record": 0, "machine_labelled": 0, "stale": 0, "orphan_keys": 0,
         "selectors_ok": 0, "selectors_bad": 0, "sources_unidentified": 0, "sources_other": 0,
         "selftrans_records": 0, "selftrans_selectors_ok": 0, "selftrans_selectors_bad": 0, "selftrans_stale": 0,
         "selftrans_missing": 0, "selftrans_orphan_keys": 0, "selftrans_units_missing": 0,
         "selftrans_gowland_overlap": 0}
    downgrades = source_downgrades()
    for unit in units:
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        foreign = {public_id(e.get(XML_ID)): e for e in root.iter()
                   if isinstance(e.tag, str) and e.get("ana") == "foreign"}
        # spans match in the main text, or (view: with-notes) in the text with its sidenotes
        main_text = " ".join(public_text(root.find(f".//{T('div')}")).split())
        span_text = " ".join(public_text(root.find(f".//{T('div')}"), notes=True).split())
        f = paths.LAYERS / "translations" / f"{unit}.json"
        layer = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        c["foreign"] += len(foreign)
        for key, rec in layer.items():
            if key not in foreign:
                c["orphan_keys"] += 1
                r.fail(f"{unit}: layer key {key} not in base text")
                continue
            c["with_record"] += 1
            if rec["text_sha1"] != sha1(public_text(foreign[key])):
                c["stale"] += 1
                r.fail(f"{key}: record is stale (base text changed); re-run translate")
            elif rec["lang"] != foreign[key].get(XML_LANG):
                c["stale"] += 1
                r.fail(f"{key}: record is stale (language now {foreign[key].get(XML_LANG)}); re-run translate")
            spans = [rec["self_translation"].get("burton_span")]
            claims = [rec["source"]]
            for t in rec["translations"]:
                if t["by"] == "machine":
                    if all(t.get(k) for k in ("model", "prompt", "date")):
                        c["machine_labelled"] += 1
                    else:
                        r.fail(f"{key}: machine translation without model/prompt/date")
                    # each model's own verdict and source claim (M4: two models per passage)
                    spans.append((t.get("self_translation") or {}).get("burton_span"))
                    if t.get("source"):
                        claims.append(t["source"])
            for sel in spans:
                if not sel:
                    continue
                text = span_text if sel.get("view") == "with-notes" else main_text
                n = text.count(sel.get("prefix", "") + sel["exact"] + sel.get("suffix", ""))
                if n == 1:
                    c["selectors_ok"] += 1
                else:
                    c["selectors_bad"] += 1
                    r.fail(f"{key}: Burton-span selector matches {n} times")
            src = rec["source"]
            c["sources_unidentified" if src["status"] == "unidentified" else "sources_other"] += 1
            for src in claims:
                if src["status"] != "unidentified" and not (src.get("basis") or "").strip():
                    r.fail(f"{key}: source {src['status']} without basis")
                if src["status"] == "identified" and not src.get("verified"):
                    r.fail(f"{key}: identified without verification")
        for key in (k for k in downgrades if k.rsplit("-", 1)[0] == unit):
            if key not in layer or layer[key]["source"]["status"] != "unidentified":
                r.fail(f"{key}: source downgrade in data/manual/source-downgrades.yaml is not applied")
            else:
                c["source_downgrades"] = c.get("source_downgrades", 0) + 1
        missing = [k for k in foreign if k not in layer]
        # Completeness is a count until the full translation pass (M5 exit: untranslated = 0);
        # integrity problems above always fail.
        c["untranslated"] = c.get("untranslated", 0) + len(missing)
        c["units_without_layer"] = c.get("units_without_layer", 0) + (0 if layer else 1)
        # cross-reference layer: resolved targets must exist; selectors must be found in the unit
        xf = paths.LAYERS / "xrefs" / f"{unit}.json"
        if xf.exists():
            full = public_text(root.find(f".//{T('div')}"), notes=True)
            for key, rec in json.loads(xf.read_text(encoding="utf-8")).items():
                c["xrefs"] = c.get("xrefs", 0) + 1
                if rec["status"] == "explicit-resolved":
                    if not (paths.TEXT / f"{rec['target']}.xml").exists():
                        r.fail(f"{key}: cross-reference target {rec['target']} does not exist")
                    c["xrefs_resolved"] = c.get("xrefs_resolved", 0) + 1
                else:
                    c["xrefs_unresolved"] = c.get("xrefs_unresolved", 0) + 1
                if rec["selector"]["exact"] not in full:
                    r.fail(f"{key}: cross-reference text {rec['selector']['exact']!r} not found in {unit}")
        _selftrans(unit, root, foreign, r, c)
        _glosses(unit, root, r, c)
        _djs(unit, foreign, r, c)
        _citations(unit, root, r, c)
    r.counts = c
    return r
