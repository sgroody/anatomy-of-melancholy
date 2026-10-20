"""V7: layer integrity (SPEC §9). Reads layer JSON and the base text; imports nothing from ingest."""

import json

from lxml import etree

from .. import paths
from ..tei import XML_ID, T, public_id
from ..textview import public_text
from ..translate.packets import sha1


def v7_layers(units: list[str]):
    from .checks import Result

    r = Result("V7", "layers keyed, labelled and honest")
    c = {"foreign": 0, "with_record": 0, "machine_labelled": 0, "stale": 0, "orphan_keys": 0,
         "selectors_ok": 0, "selectors_bad": 0, "sources_unidentified": 0, "sources_other": 0}
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
        if missing:
            r.fail(f"{unit}: {len(missing)} foreign passage(s) without a translation record: {missing}")
    r.counts = c
    return r
