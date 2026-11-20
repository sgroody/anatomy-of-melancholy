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


def _read(path) -> dict:
    return {r["id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())} if path.exists() else {}


def run(model: str = "claude-opus-5-5", packet_size: int = 15) -> dict:
    doc = yaml.safe_load(DOC.read_text(encoding="utf-8"))
    pop = population()
    done = _read(OUT)
    todo = [{"id": i, **pop[k][i]} for k, ids in doc["samples"].items() for i in ids if i not in done and i in pop[k]]
    return _judge(todo, done, OUT, model, packet_size)


def _judge(todo: list[dict], done: dict, out, model: str, packet_size: int = 15, budget: float | None = None) -> dict:
    """Judge `todo` blind, a packet at a time, into `out` (resumable: what is in `out` is not asked again)."""
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
        atomic_write_text(out, "".join(json.dumps(done[x], ensure_ascii=False, sort_keys=True) + "\n"
                                       for x in sorted(done)))
        print(f"  {k + len(pk)}/{len(todo)} judged (${spent:.2f})", flush=True)
        if budget is not None and spent >= budget:
            print(f"  budget ${budget:.2f} reached; re-run to resume", flush=True)
            break
    return {"judged": len(done), "cost_usd_list": round(spent, 2)}


# ---- the remedy for a layer that failed its sample (owner, 2026-11-20, on the citation sweep: "clearly some things
# have been missed"): every record the reader would show is judged blind, as the translator notes were (2026-11-19);
# what is judged `wrong` or `doubtful` there, or in the first sample, is withheld; then a fresh sample of what is left,
# drawn with its rule fixed before any judgement, is judged blind by the stronger model under the same rule (at most 3 %
# wrong). The layer is shown, less what is withheld, only if that recheck passes.
RECHECK_SEED = 20261120
RECHECK_SIZE = 50
RECHECK_OUT = paths.ROOT / "data" / "eval" / "sweep-audit-recheck.jsonl"


def all_out(layer: str):
    return paths.ROOT / "data" / "eval" / f"sweep-audit-all-{layer}.jsonl"


def run_all(layer: str, model: str, budget: float | None = None) -> dict:
    pop = population()[layer]
    done = _read(all_out(layer))
    todo = [{"id": i, **pop[i]} for i in sorted(pop) if i not in done]
    print(f"  {len(pop)} {layer} records, {len(done)} judged, {len(todo)} to judge", flush=True)
    return _judge(todo, done, all_out(layer), model, budget=budget)


def withheld(layer: str) -> set[str]:
    """Ids judged `wrong` or `doubtful` by the full pass or the first sample: not shown."""
    out = {i for i, r in _read(all_out(layer)).items() if r["verdict"] != "right"}
    out |= {i for i, r in _read(OUT).items() if i.startswith(layer + ":") and r["verdict"] != "right"}
    out |= {i for i, r in _read(RECHECK_OUT).items() if i.startswith(layer + ":") and r["verdict"] != "right"}
    return out


def draw_recheck(layer: str) -> dict:
    doc = yaml.safe_load(DOC.read_text(encoding="utf-8"))
    if (doc.get("recheck") or {}).get(layer):
        raise SystemExit(f"the {layer} recheck is drawn already")
    pop = population()[layer]
    judged = _read(all_out(layer))
    if missing := [i for i in pop if i not in judged]:
        raise SystemExit(f"{len(missing)} {layer} records not yet judged in the full pass")
    gone = withheld(layer)
    first = set(doc["samples"].get(layer, []))
    left = sorted(i for i in pop if i not in gone and i not in first)  # the first sample is seen
    sample = sorted(random.Random(RECHECK_SEED).sample(left, min(RECHECK_SIZE, len(left))))
    doc.setdefault("recheck", {})[layer] = {
        "drawn": datetime.now(UTC).date().isoformat(), "seed": RECHECK_SEED,
        "full_pass": {"model": next(iter(judged.values()))["model"], "judged": len(judged),
                      **Counter(r["verdict"] for r in judged.values())},
        "withheld": len(gone), "population": len(left),
        "rater": "claude-opus-5-5, blind (prompt sweep-audit-v1), as the first sample",
        "rule": "at most 3 % of the sample judged `wrong`; the layer is then shown less what is withheld",
        "sample": sample, "outcome": None}
    atomic_write_text(DOC, yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=118))
    return {"population": len(left), "sample": len(sample), "withheld": len(gone)}


def run_recheck(layer: str, model: str = "claude-opus-5-5") -> dict:
    doc = yaml.safe_load(DOC.read_text(encoding="utf-8"))
    pop = population()[layer]
    done = _read(RECHECK_OUT)
    todo = [{"id": i, **pop[i]} for i in doc["recheck"][layer]["sample"] if i not in done]
    return _judge(todo, done, RECHECK_OUT, model)


def report_recheck(layer: str) -> dict:
    doc = yaml.safe_load(DOC.read_text(encoding="utf-8"))
    rc = doc["recheck"][layer]
    done = _read(RECHECK_OUT)
    got = [done[i] for i in rc["sample"] if i in done]
    c = Counter(r["verdict"] for r in got)
    rc["outcome"] = {"date": datetime.now(UTC).date().isoformat(), "judged": len(got), **c,
                     "passed": len(got) == len(rc["sample"]) and c["wrong"] <= 0.03 * len(rc["sample"]),
                     "wrong_items": [{"id": r["id"], "reason": r["reason"]} for r in got if r["verdict"] == "wrong"],
                     "doubtful_items": [{"id": r["id"], "reason": r["reason"]} for r in got
                                        if r["verdict"] == "doubtful"]}
    atomic_write_text(DOC, yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=118))
    return rc["outcome"]


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
    """Shown: the first sample passed, or the layer's recheck passed (then less what is withheld)."""
    if not DOC.exists():
        return False
    doc = yaml.safe_load(DOC.read_text(encoding="utf-8"))
    o = (doc.get("outcome") or {}).get(layer) or {}
    rc = ((doc.get("recheck") or {}).get(layer) or {}).get("outcome") or {}
    return o.get("passed") is True or rc.get("passed") is True
