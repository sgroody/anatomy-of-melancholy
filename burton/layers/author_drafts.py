"""`burton author-drafts`: model-drafted author entries (identification, field, "why Burton cites them").

Input per author: the edition's name for them, Burton's forms and up to six of
Burton's own sidenote citations (public text from the citation layer: nothing of Gowland's). The model answers
through `claude -p` with a JSON schema; every call goes to state/authors/ledger.jsonl and a run resumes from
the author files. Each draft is written into data/authors/<id>.yaml under `draft`, labelled `by: machine` with
model, prompt and date, and the entry's status stays `machine-draft` until the owner checks it.
"""

import json
from collections import Counter
from datetime import UTC, datetime

from .. import paths
from ..translate import packets, runner
from . import authors, citations

PROMPT = "authors-v1"
LEDGER = paths.STATE / "authors" / "ledger.jsonl"
FIELDS = ["identification", "field", "why_cited", "identity_doubt", "confidence"]
SCHEMA = {"type": "object", "required": ["authors"], "additionalProperties": False, "properties": {
    "authors": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", *FIELDS],
        "properties": {"id": {"type": "string"}, "identification": {"type": "string"}, "field": {"type": "string"},
                       "why_cited": {"type": "string"}, "identity_doubt": {"type": ["string", "null"]},
                       "confidence": {"type": "string", "enum": ["high", "medium", "low"]}}}}}}


def item(aid: str, d: dict) -> dict:
    # The Wikidata match is not sent: the draft stays independent of it, so the owner can compare the two
    t = citations.tables()
    return {"id": aid, "name": t["authors"][aid]["name"], "burton_forms": t["authors"][aid]["forms"],
            "citations": d["citations"], "examples": [e["raw"] for e in d["examples"][:6]]}


def todo(top: int | None, model: str) -> list[dict]:
    out = []
    for aid, d in authors.ranked()[:top]:
        it = item(aid, d)
        h = packets.input_hash(it, PROMPT, model, 0)
        dr = authors.load(aid).get("draft") or {}
        if not (dr.get("prompt") == PROMPT and dr.get("model") == model and dr.get("input_hash") == h):
            out.append({**it, "_hash": h})
    return out


def run(*, top: int | None, model: str, packet_size: int = 15, budget_usd: float | None = None,
        max_packets: int | None = None) -> Counter:
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
    items = todo(top, model)
    stats: Counter = Counter(todo=len(items))
    spent = 0.0
    for n, k in enumerate(range(0, len(items), packet_size)):
        if max_packets is not None and n >= max_packets:
            break
        if budget_usd is not None and spent >= budget_usd:
            print(f"stopping: ${spent:.2f} list-equivalent spent, budget ${budget_usd:.2f} (--budget-usd)")
            break
        pk = items[k:k + packet_size]
        send = [{x: v for x, v in i.items() if x != "_hash"} for i in pk]
        user = "Draft entries for these authors.\n\n" + json.dumps({"authors": send}, ensure_ascii=False, indent=2)
        meta = {"ids": [i["id"] for i in pk], "model": model, "prompt": PROMPT,
                "input_hash": packets.input_hash({"authors": send}, PROMPT, model, 0)}
        res = runner.call_claude(model, sys_prompt, user, SCHEMA)
        status = "done" if res["ok"] else ("deferred" if res.get("limit") else "failed")
        runner.append(LEDGER, {**meta, "ts": runner.now(), "status": status,
                               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}})
        spent += res.get("cost_usd_list") or 0
        if not res["ok"]:
            stats[status] += 1
            print(f"  call {status}: {(res.get('error') or '')[:200]} (re-run to resume)")
            break
        got = {r["id"]: r for r in res["output"]["authors"]}
        day = datetime.now(UTC).date().isoformat()
        for i in pk:
            if i["id"] not in got:
                stats["missing_in_answer"] += 1
                continue
            rec = authors.load(i["id"])
            rec["draft"] = {**{f: got[i["id"]][f] for f in FIELDS}, "by": "machine", "model": model,
                            "prompt": PROMPT, "date": day, "input_hash": i["_hash"], "status": "machine-draft"}
            authors.save(i["id"], rec)
            stats["drafted"] += 1
        print(f"  {stats['drafted']} drafted (${spent:.2f})", flush=True)
    stats["cost_usd_list"] = round(spent, 2)
    return stats
