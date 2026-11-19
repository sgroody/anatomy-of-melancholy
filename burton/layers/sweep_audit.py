"""`burton sweep-audit`: a blind check of what the stage-14 sweeps would show, before the reader shows it.

The translator notes' spot check (data/eval/notes-spotcheck.yaml) found that a model's own "doubtful" flag misses
errors a blind second reader catches. So each sweep's shown output is checked the same way: a seeded sample of the
records the reader would show (obscure-name identifications, citations found and expanded, restored-note readings),
drawn with its rule fixed before any judgement, is read by a blind model (prompt sweep-audit-v1) that sees the
evidence (Burton's text) and the claim, never how it was made, and judges it `right`, `doubtful` or `wrong`.

Rule, per layer: at most 3 % of the sample wrong. The outcome is written to data/eval/sweep-audit.yaml; the reader
shows a layer only if its outcome passed (`passed(layer)`). Ledgered (state/sweep-audit/ledger.jsonl).
"""

import json
import random
from collections import Counter
from datetime import UTC, datetime

import yaml

from .. import paths
from ..fsutil import atomic_write_text
from ..translate import packets, runner

PROMPT = "sweep-audit-v1"
DOC = paths.ROOT / "data" / "eval" / "sweep-audit.yaml"
OUT = paths.ROOT / "data" / "eval" / "sweep-audit-rater.jsonl"
LEDGER = paths.STATE / "sweep-audit" / "ledger.jsonl"
SEED = 20261119
SIZES = {"names": 60, "cites": 50, "restored": 50}
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "verdict", "reason"],
        "properties": {"id": {"type": "string"}, "verdict": {"type": "string", "enum": ["right", "doubtful", "wrong"]},
                       "reason": {"type": "string"}}}}}}


def population() -> dict[str, dict[str, dict]]:
    """layer -> id -> what is checked (claim and evidence), for the records the reader would show."""
    from . import cite_sweep, names_sweep, restored_read

    out: dict[str, dict[str, dict]] = {"names": {}, "cites": {}, "restored": {}}
    if names_sweep.LAYER.exists():
        items = {i["form"]: i for i in names_sweep.items()}
        for form, v in json.loads(names_sweep.LAYER.read_text(encoding="utf-8")).items():
            if names_sweep.shown(v) and form in items:
                out["names"][f"names:{form}"] = {
                    "kind": "name", "claim": {"name": form, "identification": v["who"],
                                              "certainty": "probable" if v["status"] == "probable" else "sure"},
                    "evidence": {"passages": items[form]["passages"]}}
    for f in sorted(cite_sweep.LAYER.glob("*.json")):
        for k, v in json.loads(f.read_text(encoding="utf-8")).items():
            sel = v["selector"]
            out["cites"][f"cites:{k}"] = {
                "kind": "citation", "claim": {"reference": v["raw"], "written_out": v["display"],
                                              "certainty": "probable" if v["status"] == "probable" else "sure"},
                "evidence": {"text": sel["prefix"] + "⟦" + sel["exact"] + "⟧" + sel["suffix"]}}
    reads = {}
    for f in sorted(restored_read.LAYER.glob("*.json")):
        reads.update(json.loads(f.read_text(encoding="utf-8")))
    if reads:
        for i in restored_read.items():
            r = reads.get(i["id"])
            if not r or not (r.get("burton_quote") or r.get("translation") or r.get("citations")):
                continue
            out["restored"][f"restored:{i['id']}"] = {
                "kind": "restored-note", "claim": {
                    "burtons_english_for_it": r.get("burton_quote"), "translation_of_the_rest": r.get("translation"),
                    "references_written_out": [c["display"] for c in r["citations"] if c.get("display")]},
                "evidence": {"note": i["note"], "text_at_marker": i["context"]}}
    return out


def draw() -> dict:
    if DOC.exists():
        raise SystemExit(f"{DOC.name} exists: the samples are drawn once")
    pop = population()
    rng = random.Random(SEED)
    samples = {k: sorted(rng.sample(sorted(v), min(SIZES[k], len(v)))) for k, v in pop.items()}
    doc = {"purpose": "Blind check of what the stage-14 sweeps would show, before the reader shows it. Drawn, and the "
                      "rule fixed, before any judgement.",
           "drawn": datetime.now(UTC).date().isoformat(), "seed": SEED,
           "population": {k: len(v) for k, v in pop.items()},
           "rater": f"a model, blind (prompt {PROMPT}): the claim and Burton's text only, never how the claim was "
                    "made. Same model family as the sweeps, so errors they share may be missed.",
           "rule": "per layer, at most 3 % of the sample judged `wrong`; a failed layer is not shown until the owner "
                   "decides", "samples": samples, "outcome": None}
    atomic_write_text(DOC, yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=118))
    return {k: len(v) for k, v in samples.items()}


def run(model: str = "claude-opus-5-5", packet_size: int = 15) -> dict:
    doc = yaml.safe_load(DOC.read_text(encoding="utf-8"))
    pop = population()
    done = {r["id"]: r for r in map(json.loads, OUT.read_text(encoding="utf-8").splitlines())} if OUT.exists() else {}
    todo = [{"id": i, **pop[k][i]} for k, ids in doc["samples"].items() for i in ids if i not in done and i in pop[k]]
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
    spent = 0.0
    date = datetime.now(UTC).date().isoformat()
    for k in range(0, len(todo), packet_size):
        pk = todo[k:k + packet_size]
        user = "Items:\n" + json.dumps({"items": pk}, ensure_ascii=False, indent=1)
        res = runner.call_claude(model, sys_prompt, user, SCHEMA)
        spent += res.get("cost_usd_list") or 0
        status = "done" if res["ok"] else ("deferred" if res.get("limit") else "failed")
        runner.append(LEDGER, {"ids": [i["id"] for i in pk], "model": model, "prompt": PROMPT, "ts": runner.now(),
                               "status": status, "input_hash": packets.input_hash({"items": pk}, PROMPT, model, 0),
                               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}})
        if not res["ok"]:
            raise SystemExit(f"call {status}: {res.get('error')} (re-run to resume)")
        ids = {i["id"] for i in pk}
        for a in res["output"]["items"]:
            if a["id"] in ids:
                done[a["id"]] = {**a, "by": "machine", "model": model, "prompt": PROMPT, "date": date}
        atomic_write_text(OUT, "".join(json.dumps(done[x], ensure_ascii=False, sort_keys=True) + "\n"
                                       for x in sorted(done)))
        print(f"  {k + len(pk)}/{len(todo)} judged (${spent:.2f})", flush=True)
    return {"judged": len(done), "cost_usd_list": round(spent, 2)}


def report() -> dict:
    doc = yaml.safe_load(DOC.read_text(encoding="utf-8"))
    done = {r["id"]: r for r in map(json.loads, OUT.read_text(encoding="utf-8").splitlines())} if OUT.exists() else {}
    out = {}
    for layer, ids in doc["samples"].items():
        got = [done[i] for i in ids if i in done]
        c = Counter(r["verdict"] for r in got)
        out[layer] = {"sample": len(ids), "judged": len(got), **c, "passed": bool(got) and len(got) == len(ids)
                      and c["wrong"] <= 0.03 * len(ids),
                      "wrong_items": [{"id": r["id"], "reason": r["reason"]} for r in got if r["verdict"] == "wrong"]}
    doc["outcome"] = {"date": datetime.now(UTC).date().isoformat(),
                      **{k: {x: v[x] for x in ("sample", "judged", "passed")} | {"wrong": v.get("wrong", 0),
                                                                                 "doubtful": v.get("doubtful", 0)}
                         for k, v in out.items()}}
    atomic_write_text(DOC, yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=118))
    return out


def passed(layer: str) -> bool:
    if not DOC.exists():
        return False
    o = (yaml.safe_load(DOC.read_text(encoding="utf-8")).get("outcome") or {}).get(layer) or {}
    return o.get("passed") is True
