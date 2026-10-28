"""Second rater for the Dell & Jordan-Smith held-out labels (`burton djs-audit`).

A model labels a held-out round blind (it never sees the first rater's labels or the alignment score),
through `claude -p` with a schema, in packets; every call goes to a ledger, and a run resumes from it. The
labels go to data/eval/djs-holdout-rater2.jsonl, each with model, prompt and date, and are compared with the
first rater's in data/eval/djs-holdout-gold.jsonl. Nothing of Gowland's is sent: the passage and Burton's
text come from `public_text`, the rest from the 1927 OCR.
"""

import json
from collections import Counter
from datetime import UTC, datetime

import yaml

from .. import paths
from ..fsutil import atomic_write_text
from ..translate import packets, runner
from ..translate.validate import PRIMARY_MODEL
from . import djs as D

PROMPT = "djs-audit-v1"
LEDGER = paths.STATE / "djs-audit" / "ledger.jsonl"
OUT = paths.ROOT / "data" / "eval" / "djs-holdout-rater2.jsonl"
HOLDOUT = paths.ROOT / "data" / "eval" / "djs-holdout.yaml"
GOLD = paths.ROOT / "data" / "eval" / "djs-holdout-gold.jsonl"
LABELS = ["correct", "boundary", "wrong", "kept"]
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "required": ["id", "label", "reason"], "additionalProperties": False,
        "properties": {"id": {"type": "string"}, "label": {"type": "string", "enum": LABELS},
                       "reason": {"type": "string"}}}}}}


def _burton(item: dict, width: int = 450) -> str:
    para = item["paragraph"]
    at = para.find("⟦")
    return ("…" if at > width else "") + para[max(0, at - width): para.find("⟧") + 1 + width] + "…"


def items(round_: str) -> list[dict]:
    doc = yaml.safe_load(HOLDOUT.read_text(encoding="utf-8"))
    ids = doc["rounds"][round_]["sample"]["aligned"]
    djs, out, cache = D.load(), [], {}
    for pid in ids:
        unit = pid.rsplit("-", 1)[0]
        ps = cache.setdefault(unit, packets.passages(unit))
        item = next(p["packet_item"] for p in ps if p["packet_item"]["id"] == pid)
        others = [p["packet_item"]["text"] for p in ps if p["packet_item"]["text"] != item["text"]]
        before, span, after = D.context(item, others, djs)
        out.append({"id": pid, "language": item["lang"], "passage": item["text"], "burton": _burton(item),
                    "djs_before": before, "candidate": span, "djs_after": after})
    return out


def _done() -> dict[str, dict]:
    if not OUT.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, OUT.read_text(encoding="utf-8").splitlines())
            if r["prompt"] == PROMPT}


def run(round_: str = "h2", model: str = PRIMARY_MODEL, packet_size: int = 10) -> dict:
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
    done = _done()
    todo = [i for i in items(round_) if i["id"] not in done]
    for k in range(0, len(todo), packet_size):
        pk = todo[k:k + packet_size]
        user = "Label these items.\n\n" + json.dumps({"items": pk}, ensure_ascii=False, indent=2)
        meta = {"ids": [i["id"] for i in pk], "model": model, "prompt": PROMPT, "round": round_,
                "input_hash": packets.input_hash({"items": pk}, PROMPT, model, 0)}
        res = runner.call_claude(model, sys_prompt, user, SCHEMA)
        runner.append(LEDGER, {**meta, "ts": runner.now(), "status": "done" if res["ok"] else "failed",
                               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}})
        if not res["ok"]:
            raise SystemExit(f"call failed: {res.get('error')} (re-run to resume)")
        got = {r["id"]: r for r in res["output"]["items"]}
        if set(got) != set(meta["ids"]):
            raise SystemExit(f"answer ids do not match the packet: {sorted(set(got) ^ set(meta['ids']))}")
        date = datetime.now(UTC).date().isoformat()
        for i in pk:
            done[i["id"]] = {"id": i["id"], "round": round_, "label": got[i["id"]]["label"],
                             "reason": got[i["id"]]["reason"], "by": "machine", "model": model,
                             "prompt": PROMPT, "date": date}
        atomic_write_text(OUT, "".join(json.dumps(done[x], ensure_ascii=False, sort_keys=True) + "\n"
                                       for x in sorted(done)))
        print(f"  {len(done)} labelled (${res.get('cost_usd_list') or 0:.2f})")
    return compare(round_)


def compare(round_: str = "h2") -> dict:
    first = {r["id"]: r for r in map(json.loads, GOLD.read_text(encoding="utf-8").splitlines())
             if r["round"] == round_}
    second = {k: v for k, v in _done().items() if v["round"] == round_}
    both = sorted(set(first) & set(second))
    pairs = Counter((first[i]["label"], second[i]["label"]) for i in both)
    agree = sum(n for (a, b), n in pairs.items() if a == b)
    return {"items": len(both), "agree": agree, "pairs": {f"{a}/{b}": n for (a, b), n in sorted(pairs.items())},
            "disagreements": [{"id": i, "first": first[i]["label"], "second": second[i]["label"],
                               "reason": second[i]["reason"]} for i in both
                              if first[i]["label"] != second[i]["label"]]}
