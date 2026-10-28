"""M5 spot-check of the translation layer: items for review and a blind second rater (`burton tr-audit`).

Items come from data/eval/m5-spotcheck.yaml (a random sample plus the records the post-checks flagged).
Each shows the passage, Burton's text around it and its sidenotes (public text: nothing of Gowland's) and
the machine record. The second rater, a model through `claude -p` with a schema, never sees the first
rater's labels; every call goes to a ledger and a run resumes from it. Its labels go to
data/eval/m5-spotcheck-rater2.jsonl with model, prompt and date.
"""

import json
from collections import Counter
from datetime import UTC, datetime

import yaml

from .. import paths
from ..fsutil import atomic_write_text
from . import packets, runner
from .validate import PRIMARY_MODEL, primary_machine

PROMPT = "tr-audit-v1"
SAMPLE = paths.ROOT / "data" / "eval" / "m5-spotcheck.yaml"
FIRST = paths.ROOT / "data" / "eval" / "m5-spotcheck-gold.jsonl"
OUT = paths.ROOT / "data" / "eval" / "m5-spotcheck-rater2.jsonl"
LEDGER = paths.STATE / "tr-audit" / "ledger.jsonl"
ASPECTS = {"translation": ["good", "minor", "error"], "self_translation": ["ok", "wrong"],
           "source": ["ok", "unsupported"]}
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", *ASPECTS, *(f"{a}_reason" for a in ASPECTS)],
        "properties": {"id": {"type": "string"},
                       **{a: {"type": "string", "enum": v} for a, v in ASPECTS.items()},
                       **{f"{a}_reason": {"type": "string"} for a in ASPECTS}}}}}}


def ids() -> list[str]:
    doc = yaml.safe_load(SAMPLE.read_text(encoding="utf-8"))
    return sorted(set(doc["sample"]) | set(doc["flagged"]))


def _around(para: str, width: int = 500) -> str:
    a, b = para.find("⟦"), para.find("⟧")
    if a < 0:
        return para[:2 * width]
    return ("…" if a > width else "") + para[max(0, a - width): b + 1 + width] + ("…" if b + width < len(para) else "")


def items(which: list[str] | None = None) -> list[dict]:
    out, cache = [], {}
    for pid in which or ids():
        unit = pid.rsplit("-", 1)[0]
        if unit not in cache:
            layer = json.loads((paths.LAYERS / "translations" / f"{unit}.json").read_text(encoding="utf-8"))
            cache[unit] = ({p["packet_item"]["id"]: p["packet_item"] for p in packets.passages(unit)}, layer)
        ps, layer = cache[unit]
        it, rec = ps[pid], layer[pid]
        m = primary_machine(rec)
        st = rec["self_translation"]
        out.append({
            "id": pid, "language": it["lang"], "kind": it["kind"], "location": it["location"],
            "passage": it["text"], "burton": _around(it["paragraph"]),
            "burton_before": (it.get("before") or "")[-400:], "burton_after": (it.get("after") or "")[:400],
            "main_text_at_note": it.get("main_text_at_note"),
            "sidenotes": it.get("sidenotes", [])[:8],
            "translation": m["text"], "note": m.get("note"),
            "self_translation": {"status": st["status"],
                                 "burton_rendering": (st.get("burton_span") or {}).get("exact")},
            "source": {k: rec["source"].get(k) for k in ("status", "author", "work", "locus", "basis")},
        })
    return out


def _done() -> dict[str, dict]:
    if not OUT.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, OUT.read_text(encoding="utf-8").splitlines()) if r["prompt"] == PROMPT}


def run(model: str = PRIMARY_MODEL, packet_size: int = 10, which: list[str] | None = None) -> dict:
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
    done = _done()
    todo = [i for i in items(which) if i["id"] not in done]
    for k in range(0, len(todo), packet_size):
        pk = todo[k:k + packet_size]
        user = "Check these items.\n\n" + json.dumps({"items": pk}, ensure_ascii=False, indent=2)
        meta = {"ids": [i["id"] for i in pk], "model": model, "prompt": PROMPT,
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
            done[i["id"]] = {**got[i["id"]], "by": "machine", "model": model, "prompt": PROMPT, "date": date}
        atomic_write_text(OUT, "".join(json.dumps(done[x], ensure_ascii=False, sort_keys=True) + "\n"
                                       for x in sorted(done)))
        print(f"  {len(done)} checked (${res.get('cost_usd_list') or 0:.2f})", flush=True)
    return {"checked": len(done)}


def compare() -> dict:
    first = {r["id"]: r for r in map(json.loads, FIRST.read_text(encoding="utf-8").splitlines())}
    second = _done()
    both = sorted(set(first) & set(second))
    rep = {"items": len(both)}
    for a in ASPECTS:
        pairs = Counter((first[i][a], second[i][a]) for i in both)
        rep[a] = {"agree": sum(n for (x, y), n in pairs.items() if x == y),
                  "pairs": {f"{x}/{y}": n for (x, y), n in sorted(pairs.items())},
                  "disagreements": [{"id": i, "first": first[i][a], "second": second[i][a],
                                     "first_reason": first[i].get(f"{a}_reason", ""),
                                     "second_reason": second[i][f"{a}_reason"]}
                                    for i in both if first[i][a] != second[i][a]]}
    return rep
