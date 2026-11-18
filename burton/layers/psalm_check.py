"""`burton psalm-check`: which KJV verse each of Burton's Psalm citations means (owner, 2026-11-18: "Psalm verses should
be checked against Burton's words") -> data/layers/psalm-check/<unit>.json.

Burton sometimes numbers the Psalms as the Vulgate does, so the KJV verse of his number can be the wrong one. For every
Psalm citation with a chapter and verse (sidenote citations and citations in the running text), a model sees his words
around it, English renderings of the Latin there, and the KJV verse of his number with its Vulgate-numbered
alternatives, and rules which one he means, or none, or unsure. The reader shows a Psalm verse only where the ruling
confirms one.

Private-only check (CLAUDE.md rule 5): the English given as evidence includes Gowland's translations of the Latin, so
every record is `informed_by: gowland`; the output is a verdict, and what the reader shows is the KJV's text. Ledgered
and resumable (state/psalm-check/ledger.jsonl), prompt `psalm-check-v1`.
"""

import json
from collections import Counter

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..site import kjv
from ..site.render import gowland_versions
from ..tei import XML_ID, T, public_id
from ..textview import public_text
from ..translate import packets, runner

PROMPT = "psalm-check-v1"
LAYER = "psalm-check"
LEDGER = paths.STATE / "psalm-check" / "ledger.jsonl"
BLOCKS = (T("p"), T("l"), T("lg"), T("quote"), T("item"), T("head"))
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "verdict", "reason"],
        "properties": {"id": {"type": "string"}, "verdict": {"type": "string"}, "reason": {"type": "string"}}}}}}


def vulgate_to_kjv(c: int) -> list[int]:
    """The KJV Psalm(s) a Vulgate-numbered Psalm can be."""
    if c < 9 or c > 147:
        return [c]
    if c == 9:
        return [9, 10]
    if c <= 112 or 116 <= c <= 145:
        return [c + 1]
    return {113: [114, 115], 114: [116], 115: [116]}.get(c, [147])


def candidates(ref: dict) -> list[dict]:
    out = []
    own = kjv.verses("psalms", None, ref)
    if own:
        out.append({"id": "kjv", "chapter": ref["chapter"], "verses": ref["verses"], "text": _join(own)})
    for ch in vulgate_to_kjv(ref["chapter"]):
        for dv in (0, 1, -1):
            vs = [v + dv for v in ref["verses"]]
            if (ch, dv) == (ref["chapter"], 0) or min(vs) < 1:
                continue
            if v := kjv.verses("psalms", None, {"chapter": ch, "verses": vs}):
                out.append({"id": f"vulg-{ch}-{'-'.join(map(str, vs))}", "chapter": ch, "verses": vs, "text": _join(v)})
    return out


def _join(vs) -> str:
    return " ".join(f"{n} {t}" for n, t in vs)


def _context(div, gv: dict, layer: dict, block_id: str | None, note_id: str | None,
             exact: str | None = None) -> tuple[str, list[str]]:
    el = None
    for x in div.iter():
        if x.get(XML_ID) and public_id(x.get(XML_ID)) in (block_id, note_id):
            el = x
            break
    if el is None:
        return "", []
    if note_id and el.tag == T("note"):  # a sidenote: the note, and the text at its marker
        block = next((a for a in el.iterancestors() if a.tag in BLOCKS), None)
        text = public_text(el, notes=True)
        if block is not None:
            text += " ⟦text at the note's marker⟧ " + public_text(block)[:900]
        scope = [el] + ([block] if block is not None else [])
    else:  # Burton's words around the citation (2026-11-18: the paragraph's opening missed it in long paragraphs)
        text, scope = public_text(el), [el]
        if exact and (i := text.find(exact)) >= 0:
            text = text[max(0, i - 900):i + len(exact) + 300]
    eng = []
    for s in scope:
        for x in s.iter():
            if x.get("ana") == "foreign" and x.get(XML_ID):
                fid = public_id(x.get(XML_ID))
                trs = (layer.get(fid) or {}).get("translations", [])
                eng += [gv[fid]] if fid in gv else [t["text"] for t in trs[:1]]
    return " ".join(text.split())[:1800], [e for e in eng if e][:6]


def items() -> list[dict]:
    out = []
    for f in sorted((paths.LAYERS / "citations").glob("*.json")):
        unit = f.stem
        cits = json.loads(f.read_text(encoding="utf-8"))
        inline_f = paths.LAYERS / "citations-inline" / f"{unit}.json"
        inline = json.loads(inline_f.read_text(encoding="utf-8")) if inline_f.exists() else {}
        found = [(c["id"], c, None, nid) for nid, r in cits.items() for c in r["citations"]]
        found += [(k, r, r["selector"]["in"], None) for k, r in inline.items()]
        found = [x for x in found if x[1].get("work") == "bible.psalms" and (x[1].get("ref") or {}).get("verses")]
        if not found:
            continue
        div = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot().find(f".//{T('div')}")
        gv = gowland_versions(div)
        tf = paths.LAYERS / "translations" / f"{unit}.json"
        layer = json.loads(tf.read_text(encoding="utf-8")) if tf.exists() else {}
        for cid, c, block, nid in found:
            ctx, eng = _context(div, gv, layer, block, nid, c.get("selector", {}).get("exact"))
            out.append({"id": cid, "unit": unit, "citation": c["raw"], "ref": c["ref"], "context": ctx,
                        "english": eng, "candidates": candidates(c["ref"])})
    return out


SEND = ("id", "citation", "context", "english", "candidates")


def run(*, model: str, packet_size: int = 15, budget_usd: float | None = None, dry_run: bool = False) -> Counter:
    stats: Counter = Counter()
    todo_all = [i for i in items() if i["candidates"]]
    stats["citations"] = len(todo_all)
    send = lambda i: {k: i[k] for k in SEND}  # noqa: E731
    hashes = {i["id"]: packets.input_hash(send(i), PROMPT, model, 0) for i in todo_all}
    done = _done(model)
    todo = [i for i in todo_all if (done.get(i["id"]) or {}).get("_hash") != hashes[i["id"]]]
    stats["to_ask"] = len(todo)
    if not dry_run:
        sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
        spent = 0.0
        for k in range(0, len(todo), packet_size):
            if budget_usd is not None and spent >= budget_usd:
                break
            pk = todo[k:k + packet_size]
            user = "Items:\n" + json.dumps({"items": [send(i) for i in pk]}, ensure_ascii=False, indent=1)
            res = runner.call_claude(model, sys_prompt, user, SCHEMA)
            spent += res.get("cost_usd_list") or 0
            rec = {"ids": [i["id"] for i in pk], "model": model, "prompt": PROMPT, "ts": runner.now(),
                   "status": "done" if res["ok"] else ("deferred" if res.get("limit") else "failed"),
                   "item_hashes": {i["id"]: hashes[i["id"]] for i in pk},
                   **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}}
            if res["ok"]:
                rec["answers"] = res["output"]["items"]
            runner.append(LEDGER, rec)
            if not res["ok"]:
                print(f"  call {rec['status']}: {(res.get('error') or '')[:200]} (re-run to resume)")
                break
            print(f"  {k + len(pk)}/{len(todo)} checked (${spent:.2f})", flush=True)
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
    """The layer: one record per checked citation, with the verse it confirms (or none)."""
    done = _done(model)
    by_unit: dict[str, dict] = {}
    for i in todo_all:
        a = done.get(i["id"])
        if not a:
            continue
        cand = {c["id"]: c for c in i["candidates"]}
        v = a["verdict"] if a["verdict"] in cand or a["verdict"] in ("none", "unsure") else "unsure"
        rec = {"citation": i["citation"], "verdict": "kjv" if v == "kjv" else ("vulgate" if v in cand else v),
               "reason": a["reason"], "by": "machine", "model": model, "prompt": PROMPT, "date": a["_ts"][:10],
               "informed_by": "gowland"}
        if v in cand:
            rec["chapter"], rec["verses"] = cand[v]["chapter"], cand[v]["verses"]
        stats[f"verdict_{rec['verdict']}"] += 1
        by_unit.setdefault(i["unit"], {})[i["id"]] = rec
    for unit, recs in by_unit.items():
        out = paths.LAYERS / LAYER / f"{unit}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(out, json.dumps(recs, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

