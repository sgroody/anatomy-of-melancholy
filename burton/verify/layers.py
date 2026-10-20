"""V7: layer integrity (SPEC §9). Reads layer JSON and the base text; imports nothing from ingest."""

import json

from lxml import etree

from .. import paths
from ..tei import XML_ID, T, public_id
from ..textview import public_text
from ..translate.packets import sha1


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


def v7_layers(units: list[str]):
    from .checks import Result

    r = Result("V7", "layers keyed, labelled and honest")
    c = {"foreign": 0, "with_record": 0, "machine_labelled": 0, "stale": 0, "orphan_keys": 0,
         "selectors_ok": 0, "selectors_bad": 0, "sources_unidentified": 0, "sources_other": 0,
         "selftrans_records": 0, "selftrans_selectors_ok": 0, "selftrans_selectors_bad": 0, "selftrans_stale": 0,
         "selftrans_missing": 0, "selftrans_orphan_keys": 0, "selftrans_units_missing": 0,
         "selftrans_gowland_overlap": 0}
    for unit in units:
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        foreign = {public_id(e.get(XML_ID)): e for e in root.iter()
                   if isinstance(e.tag, str) and e.get("ana") == "foreign"}
        unit_text = public_text(root.find(f".//{T('div')}"))
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
            for t in rec["translations"]:
                if t["by"] == "machine":
                    if all(t.get(k) for k in ("model", "prompt", "date")):
                        c["machine_labelled"] += 1
                    else:
                        r.fail(f"{key}: machine translation without model/prompt/date")
            sel = rec["self_translation"].get("burton_span")
            if sel:
                n = unit_text.count(sel["exact"])
                if n == 1:
                    c["selectors_ok"] += 1
                else:
                    c["selectors_bad"] += 1
                    r.fail(f"{key}: Burton-span selector matches {n} times")
            src = rec["source"]
            if src["status"] == "unidentified":
                c["sources_unidentified"] += 1
            else:
                c["sources_other"] += 1
                if not (src.get("basis") or "").strip():
                    r.fail(f"{key}: source {src['status']} without basis")
                if src["status"] == "identified" and not src.get("verified"):
                    r.fail(f"{key}: identified without verification")
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
    r.counts = c
    return r
