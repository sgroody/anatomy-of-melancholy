"""`burton restored-read`: the restored notes read for the reader (owner, 2026-11-04 and 2026-11-18: "Restored
(Gutenberg) sidenotes: translate them"; stage 14: tie each to Burton's own English first, translate only what that
leaves out, expand its citations, label its kind) -> data/layers/restored-read/<unit>.json, keyed by the restored
note's id.

Gowland cut most of these notes because Burton renders their Latin in his own English beside the marker ("A Note on
the Text"; reader-stages.md, Finding 2026-11-04). So the tie comes first:

1. Rules (`rules/restored-tie-v1`, the selftrans clause rules): the clause of Burton's text that the note's marker
   stands before, and the clause before the marker, each with its cognates with the note (`infinita`/`infinite`).
2. A model (prompt `restored-v1`, ledgered in state/restored-read/ledger.jsonl) sees the note, the text around its
   marker and those clauses, and returns: the note's kind (`cites`, `note`, or `both`); whether Burton's English
   renders the note's Latin (`full`, `partial`, `none`, or `no-latin`), with the exact words of his that do; an English
   rendering of only the Latin his words leave out; and each reference in the note expanded (`expanded`, `probable`,
   `unidentified`), never guessed.

Checks: Burton's words must be found in his text near the marker (else the tie is `undetermined` and the translation is
withheld); a reference's `raw` must be in the note (else it is dropped). Every record is labelled machine with model,
prompt and date. Independent of Gowland: his matter is not sent (CLAUDE.md rule 5).
"""

import json
from collections import Counter

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..tei import XML_ID, public_id
from ..textview import public_text
from ..translate import packets, runner
from . import selftrans

PROMPT = "restored-v1"
RULES = "rules/restored-tie-v1"
LAYER = paths.LAYERS / "restored-read"
LEDGER = paths.STATE / "restored-read" / "ledger.jsonl"
CONTEXT = 700
KINDS = ("cites", "note", "both")
TIES = ("full", "partial", "none", "no-latin")
CITE_STATUS = ("expanded", "probable", "unidentified")
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "kind", "tie", "burton_quote", "translation", "citations", "confidence"],
        "properties": {
            "id": {"type": "string"}, "kind": {"type": "string", "enum": list(KINDS)},
            "tie": {"type": "string", "enum": list(TIES)},
            "burton_quote": {"type": ["string", "null"]}, "translation": {"type": ["string", "null"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "citations": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["raw", "display", "status"],
                "properties": {"raw": {"type": "string"}, "display": {"type": ["string", "null"]},
                               "status": {"type": "string", "enum": list(CITE_STATUS)}}}}}}}}}


def _flat(s: str) -> str:
    return " ".join(s.replace("­", "").split())


def _block_texts(unit: str) -> dict[str, str]:
    root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
    return {public_id(e.get(XML_ID)): _flat(public_text(e)) for e in root.iter() if isinstance(e.tag, str)
            and e.get(XML_ID)}


def tie_signals(text: str, at: int, note: str) -> dict:
    """The rules' candidates for Burton's English: the clause the marker stands before, and the clause before it."""
    out = {}
    for name, cand in (("following", selftrans.following(text, at, len(text))),
                       ("preceding", selftrans.preceding(text, at, 0))):
        if cand:
            s, e = cand["span"]
            out[name] = {"text": text[s:e], "cognates": selftrans.cognates(note, text[s:e])}
    return out


def items() -> list[dict]:
    out = []
    for f in sorted(paths.LAYERS.joinpath("restored-notes").glob("*.json")):
        unit = f.stem
        recs = json.loads(f.read_text(encoding="utf-8"))
        texts = _block_texts(unit)
        for rid, rec in sorted(recs.items()):
            sel = rec["selector"]
            text = texts.get(sel["in"], "")
            probe = _flat(sel["prefix"] + sel["exact"] + sel["suffix"])
            k = text.find(probe)
            at = k + len(_flat(sel["prefix"])) if k >= 0 else -1
            note = _flat(rec["text"])
            if at < 0:
                out.append({"id": rid, "unit": unit, "note": note, "context": "", "signals": {}, "located": False})
                continue
            ctx = text[max(0, at - CONTEXT):at] + "⟦°⟧" + text[at:at + CONTEXT]
            out.append({"id": rid, "unit": unit, "note": note, "context": ctx, "signals": tie_signals(text, at, note),
                        "located": True})
    return out


SEND = ("id", "note", "context", "signals")


def quote_ok(item: dict, quote: str | None) -> bool:
    """Burton's words: copied exactly from the text around the marker, and not the note itself."""
    if not quote:
        return False
    q = _flat(quote).strip(" ,.;:")
    return len(q.split()) >= 2 and q in item["context"].replace("⟦°⟧", "") and q not in item["note"]


def run(*, model: str, packet_size: int = 20, budget_usd: float | None = None, dry_run: bool = False,
        limit: int | None = None) -> Counter:
    stats: Counter = Counter()
    todo_all = [i for i in items() if i["located"]]
    stats["notes"] = len(todo_all)
    gver, gtext, _ = runner.glossary()
    send = lambda i: {k: i[k] for k in SEND}  # noqa: E731
    hashes = {i["id"]: packets.input_hash(send(i), PROMPT, model, gver) for i in todo_all}
    done = _done(model)
    todo = [i for i in todo_all if (done.get(i["id"]) or {}).get("_hash") != hashes[i["id"]]]
    if limit is not None:
        todo = todo[:limit]
    stats["to_ask"] = len(todo)
    if not dry_run:
        tmpl = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
        sys_prompt = tmpl.replace("{glossary}", gtext)
        spent = 0.0
        for k in range(0, len(todo), packet_size):
            if budget_usd is not None and spent >= budget_usd:
                print(f"  budget reached (${spent:.2f}); re-run to continue")
                break
            pk = todo[k:k + packet_size]
            user = "Notes:\n" + json.dumps({"items": [send(i) for i in pk]}, ensure_ascii=False, indent=1)
            res = runner.call_claude(model, sys_prompt, user, SCHEMA)
            spent += res.get("cost_usd_list") or 0
            status = "done" if res["ok"] else ("deferred" if res.get("limit") else "failed")
            rec = {"ids": [i["id"] for i in pk], "model": model, "prompt": PROMPT, "glossary": gver,
                   "ts": runner.now(), "status": status,
                   "item_hashes": {i["id"]: hashes[i["id"]] for i in pk},
                   **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}}
            if res["ok"]:
                rec["answers"] = res["output"]["items"]
            runner.append(LEDGER, rec)
            if not res["ok"]:
                print(f"  call {rec['status']}: {(res.get('error') or '')[:200]} (re-run to resume)")
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


def to_record(i: dict, a: dict, model: str, stats: Counter) -> dict:
    tie, quote, translation = a["tie"], a["burton_quote"], a["translation"]
    if tie in ("full", "partial") and not quote_ok(i, quote):
        stats["tie_quote_not_found"] += 1
        tie, quote, translation = "undetermined", None, None  # never show words as Burton's that are not his
    elif tie in ("none", "no-latin"):
        quote = None
    if tie == "full":
        translation = None  # his English covers it: not translated over again
    cites = []
    for c in a["citations"]:
        if _flat(c["raw"]) and _flat(c["raw"]) in i["note"]:
            cites.append({"raw": _flat(c["raw"]), "status": c["status"],
                          "display": c["display"] if c["status"] != "unidentified" else None})
        else:
            stats["citation_raw_not_in_note"] += 1
    rec = {"kind": a["kind"], "tie": tie, "confidence": a["confidence"], "citations": cites,
           "signals": {k: v["cognates"] for k, v in i["signals"].items()}, "rules": RULES,
           "by": "machine", "model": model, "prompt": PROMPT, "date": a["_ts"][:10]}
    if quote:
        rec["burton_quote"] = _flat(quote).strip(" ,;:")
    if translation:
        rec["translation"] = translation
    return rec


def write(model: str, todo_all: list[dict], stats: Counter) -> None:
    done = _done(model)
    by_unit: dict[str, dict] = {}
    for i in todo_all:
        a = done.get(i["id"])
        if not a:
            continue
        rec = to_record(i, a, model, stats)
        stats[f"kind_{rec['kind']}"] += 1
        stats[f"tie_{rec['tie']}"] += 1
        stats["citations"] += len(rec["citations"])
        stats["translated"] += "translation" in rec
        by_unit.setdefault(i["unit"], {})[i["id"]] = rec
    for f in LAYER.glob("*.json"):  # a note no longer restored leaves no reading behind
        if f.stem not in by_unit:
            f.unlink()
    for unit, recs in by_unit.items():
        out = LAYER / f"{unit}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(out, json.dumps(recs, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
