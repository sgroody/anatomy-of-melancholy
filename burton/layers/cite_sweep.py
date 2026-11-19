"""`burton cite-sweep`: citations in Burton's running text that the rules missed (owner, 2026-11-18, stage 14) ->
data/layers/citations-inline-model/<unit>.json.

The rules layer (`citations-inline`, rules/inline-v2) takes a citation only where an author form from the tables and a
numbered locator anchor it twice over, so a citation by an author the tables do not know, a title alone ("in his
book de atra bile") or a locator without a number is left out. The language rules have already judged those runs:
an italic run in the running text with the verdict `citation` (state/ingest/<unit>.json) that no rules record covers
is a candidate here. A model (prompt `cite-sweep-v1`, ledgered in state/cite-sweep/ledger.jsonl) sees the run and
the sentence around it and says whether it is a reference, which words of the text make up the whole citation
(author's name included), and how it reads written out (`expanded`, `probable`, or `unidentified`), never guessed.

Checks before a record is written: the citation's words must be in the block's public text, contain the candidate
run, match exactly once with their context, and not overlap a rules record. Records are labelled machine (model,
prompt, date); the reader marks them as the rules' in-line citations are marked, with the ◇. Keys are the block's
public id and the citation's character offset ("<block>-icm<offset>"). Independent of Gowland (rule 5).
"""

import json
import re
from collections import Counter

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..ingest.epub import all_units
from ..tei import XML_ID, public_id
from ..textview import public_text
from ..translate import packets, runner
from . import citations_inline, selftrans

PROMPT = "cite-sweep-v1"
LAYER = paths.LAYERS / "citations-inline-model"
LEDGER = paths.STATE / "cite-sweep" / "ledger.jsonl"
WINDOW = 260
STATUS = ("expanded", "probable", "unidentified")
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "is_citation", "exact", "display", "status"],
        "properties": {"id": {"type": "string"}, "is_citation": {"type": "boolean"},
                       "exact": {"type": ["string", "null"]}, "display": {"type": ["string", "null"]},
                       "status": {"type": "string", "enum": list(STATUS)}}}}}}


def _flat(s: str) -> str:
    return " ".join(s.replace("­", "").split())


def items() -> list[dict]:
    out = []
    for unit in all_units():
        rep = paths.STATE / "ingest" / f"{unit}.json"
        if not rep.exists():
            continue
        runs = []
        for d in json.loads(rep.read_text(encoding="utf-8")).get("langid_decisions", []):
            t = _flat(d["text"]).strip(" ,.;:")
            if d.get("verdict") == "citation" and not d.get("in_note") and len(t) >= 3 and t not in runs:
                runs.append(t)
        if not runs:
            continue
        rf = paths.LAYERS / "citations-inline" / f"{unit}.json"
        rules = json.loads(rf.read_text(encoding="utf-8")) if rf.exists() else {}
        covered: dict[str, list[tuple[int, int]]] = {}
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        texts = {public_id(e.get(XML_ID)): _flat(public_text(e)) for e in root.iter(*citations_inline.BLOCKS)
                 if e.get(XML_ID)}
        for r in rules.values():
            t = texts.get(r["selector"]["in"], "")
            k = t.find(_flat(r["selector"]["prefix"] + r["selector"]["exact"]))
            if k >= 0:
                s = k + len(_flat(r["selector"]["prefix"]))
                covered.setdefault(r["selector"]["in"], []).append((s, s + len(_flat(r["selector"]["exact"]))))
        for run in runs:
            for bid, t in texts.items():
                k = t.find(run)
                if k < 0:
                    continue
                if any(a < k + len(run) and k < b for a, b in covered.get(bid, [])):
                    break
                out.append({"id": f"{bid}-icm{k}", "unit": unit, "block": bid, "run": run,
                            "text": t[max(0, k - WINDOW):k] + "⟦" + run + "⟧" + t[k + len(run):k + len(run) + WINDOW]})
                break
    return out


SEND = ("id", "run", "text")


def run(*, model: str, packet_size: int = 30, budget_usd: float | None = None, dry_run: bool = False,
        limit: int | None = None) -> Counter:
    stats: Counter = Counter()
    todo_all = items()
    stats["candidates"] = len(todo_all)
    send = lambda i: {k: i[k] for k in SEND}  # noqa: E731
    hashes = {i["id"]: packets.input_hash(send(i), PROMPT, model, 0) for i in todo_all}
    done = _done(model)
    todo = [i for i in todo_all if (done.get(i["id"]) or {}).get("_hash") != hashes[i["id"]]]
    if limit is not None:
        todo = todo[:limit]
    stats["to_ask"] = len(todo)
    if not dry_run:
        sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
        spent = 0.0
        for k in range(0, len(todo), packet_size):
            if budget_usd is not None and spent >= budget_usd:
                print(f"  budget reached (${spent:.2f}); re-run to continue")
                break
            pk = todo[k:k + packet_size]
            user = "Items:\n" + json.dumps({"items": [send(i) for i in pk]}, ensure_ascii=False, indent=1)
            res = runner.call_claude(model, sys_prompt, user, SCHEMA)
            spent += res.get("cost_usd_list") or 0
            status = "done" if res["ok"] else ("deferred" if res.get("limit") else "failed")
            rec = {"ids": [i["id"] for i in pk], "model": model, "prompt": PROMPT, "ts": runner.now(),
                   "status": status, "item_hashes": {i["id"]: hashes[i["id"]] for i in pk},
                   **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}}
            if res["ok"]:
                rec["answers"] = res["output"]["items"]
            runner.append(LEDGER, rec)
            if not res["ok"]:
                print(f"  call {status}: {(res.get('error') or '')[:200]} (re-run to resume)")
                break
            print(f"  {k + len(pk)}/{len(todo)} read (${spent:.2f})", flush=True)
        stats["cost_usd_list"] = round(spent, 2)
    write(model, todo_all, stats)
    return stats


def _done(model: str) -> dict:
    done = {}
    if LEDGER.exists():
        for r in map(json.loads, LEDGER.read_text(encoding="utf-8").splitlines()):
            if r.get("status") == "done" and r.get("prompt") == PROMPT and r.get("model") == model:
                done.update({a["id"]: {**a, "_hash": r["item_hashes"][a["id"]], "_ts": r["ts"]}
                             for a in r.get("answers", []) if a["id"] in r.get("item_hashes", {})})
    return done


def write(model: str, todo_all: list[dict], stats: Counter) -> None:
    done = _done(model)
    texts: dict[tuple[str, str], str] = {}
    by_unit: dict[str, dict] = {}
    for i in todo_all:
        a = done.get(i["id"])
        if not a:
            continue
        if not a["is_citation"]:
            stats["not_a_citation"] += 1
            continue
        if a["status"] == "unidentified" or not a["display"]:
            stats["unidentified"] += 1
            continue
        exact = _flat(a["exact"] or "").strip(" ,;:")
        key = (i["unit"], i["block"])
        if key not in texts:
            root = etree.parse(str(paths.TEXT / f"{i['unit']}.xml")).getroot()
            el = next(e for e in root.iter() if isinstance(e.tag, str) and e.get(XML_ID)
                      and public_id(e.get(XML_ID)) == i["block"])
            texts[key] = _flat(public_text(el))
        t = texts[key]
        run_at = int(i["id"].rsplit("-icm", 1)[1])
        run_end = run_at + len(i["run"])
        # the occurrence of the given words that overlaps the marked run (the model may trim the run to the reference
        # itself: "ver. 23" out of a run that carried Burton's English with it)
        s = next((m.start() for m in re.finditer(re.escape(exact), t) if m.start() < run_end and run_at < m.end()),
                 -1) if exact else -1
        if s < 0:
            stats["exact_rejected"] += 1  # the words given are not the text's at the run
            continue
        sel = selftrans.selector(t, s, s + len(exact), i["block"])
        if sel is None:
            stats["selector_not_unique"] += 1
            continue
        rec = {"raw": exact, "display": a["display"], "status": a["status"], "selector": sel,
               "by": "machine", "model": model, "prompt": PROMPT, "date": a["_ts"][:10]}
        stats[f"status_{a['status']}"] += 1
        by_unit.setdefault(i["unit"], {})[f"{i['block']}-icm{s}"] = rec
    for f in LAYER.glob("*.json"):
        if f.stem not in by_unit:
            f.unlink()
    for unit, recs in by_unit.items():
        LAYER.mkdir(parents=True, exist_ok=True)
        atomic_write_text(LAYER / f"{unit}.json", json.dumps(recs, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
