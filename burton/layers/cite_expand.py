"""`burton expand-citations`: the sidenote citations the rules leave `unidentified` or `partial`, expanded by a
model -> data/layers/citation-expansions/<unit>.json (owner, 2026-11-03: "All abbreviations in citations should be
expanded").

Through the ledgered `claude -p` runner with prompt `cite-v1`. The model sees the note, the citation, the rules'
reading, Burton's main text at the note's marker and the previous citation's expansion, all as public text
(Gowland's matter removed; a payload holding a bracket or brace is refused before any call), and the list of
authors in data/abbreviations.yaml.

Post-checks, by rule:
* the evidence must occur exactly in the note or the context it was given, unless the basis is `idem-previous`,
  which needs a previous citation with an author;
* `low` confidence, basis `none` or no author leave the citation `unidentified`;
* an `author_id` must be one the edition knows; one that is not is dropped and the author's name kept.
Status: `expanded` when the author is named in the note, at the anchor or by Idem; `probable` when he is inferred
from the work (`work-known`; the reader must say "probably"); `not-a-citation`; `unidentified`. Every record is
labelled `by: machine` with model, prompt, date and input hash. The rules' layer (data/layers/citations/) is never
written here; the reader prefers the rules' expansion where it is complete.
"""

import json
import re
from collections import Counter

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..ingest.epub import all_units
from ..tei import XML_ID, T, public_id
from ..textview import public_text
from ..translate import packets, runner
from . import citations as cit

PROMPT = "cite-v1"
LEDGER = paths.STATE / "citations" / "ledger.jsonl"
LAYER = "citation-expansions"
BLOCKS = (T("p"), T("l"), T("item"), T("head"), T("quote"))
BASES = ["named-in-note", "named-at-anchor", "idem-previous", "work-known", "none"]
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "is_citation", "author_id", "author_name", "basis", "evidence", "work", "locus",
                     "display", "confidence", "reason"],
        "properties": {"id": {"type": "string"}, "is_citation": {"type": "boolean"},
                       "author_id": {"type": ["string", "null"]}, "author_name": {"type": ["string", "null"]},
                       "basis": {"type": "string", "enum": BASES}, "evidence": {"type": ["string", "null"]},
                       "work": {"type": ["string", "null"]}, "locus": {"type": ["string", "null"]},
                       "display": {"type": ["string", "null"]},
                       "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                       "reason": {"type": "string"}}}}}}


def _context(note) -> str:
    """Burton's main text around the note's marker, ⟦sidenote⟧ standing for the marker."""
    b = note.getparent()
    while b is not None and b.tag not in BLOCKS:
        b = b.getparent()
    if b is None:
        return ""
    text = public_text(b, note_marker=note.get(XML_ID))
    i = text.find("⟦sidenote⟧")
    if i < 0:
        return ""
    return text[max(0, i - 400):i + 10 + 200]


def items(units: list[str] | None = None) -> list[dict]:
    """Every sidenote citation the rules left unidentified or partial, with what the model is shown."""
    out = []
    names = {a: s["name"] for a, s in cit.tables()["authors"].items()}
    for unit in units or all_units():
        f = paths.LAYERS / "citations" / f"{unit}.json"
        if not f.exists():
            continue
        layer = json.loads(f.read_text(encoding="utf-8"))
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        notes = {public_id(n.get(XML_ID)): n for n in root.iter(T("note")) if n.get("type") == "side"}
        prev = None
        for nid in sorted(layer, key=lambda k: list(notes).index(k) if k in notes else 10 ** 6):
            rec = layer[nid]
            for c in rec["citations"]:
                if c["status"] in ("unidentified", "partial") and nid in notes:
                    out.append({"id": c["id"], "unit": unit, "note": rec["raw"], "citation": c["raw"],
                                "rules": {"author": names.get(c.get("author")) if c.get("author") else None,
                                          "expansion": c.get("display")},
                                "context": _context(notes[nid]), "previous": prev})
                if c.get("display"):
                    prev = c["display"]
    return out


SEND = ("id", "note", "citation", "rules", "context", "previous")


def _send(i: dict) -> dict:
    return {k: i[k] for k in SEND}


def leak_check(batch: list[dict]) -> None:
    """Gowland's brackets and braces never reach a model: public text has none (V8t), so any is a bug."""
    for i in batch:
        texts = [i["note"], i["citation"], i["context"], i["previous"] or "", i["rules"]["expansion"] or ""]
        if any(re.search(r"[\[\]{}]", t) for t in texts):
            raise SystemExit(f"refusing to send {i['id']}: a bracket or brace in its text (Gowland's matter?)")


def postcheck(i: dict, a: dict, known: set[str]) -> tuple[str, dict]:
    """The record's status and the fields kept, by the rules in the module docstring."""
    if not a["is_citation"]:
        return "not-a-citation", {}
    aid = a["author_id"] if a["author_id"] in known else None
    name = a["author_name"]
    if a["basis"] == "none" or a["confidence"] == "low" or not (aid or name):
        return "unidentified", {}
    if a["basis"] == "idem-previous":
        if not i["previous"]:
            return "unidentified", {}
    elif not a["evidence"] or (a["evidence"] not in i["note"] and a["evidence"] not in i["context"]):
        return "failed-postcheck", {}
    status = "probable" if a["basis"] == "work-known" else "expanded"
    return status, {"author": aid, "author_name": name, "work": a["work"], "locus": a["locus"],
                    "display": a["display"], "basis": a["basis"], "evidence": a["evidence"]}


def run(*, model: str, packet_size: int = 25, budget_usd: float | None = None, max_packets: int | None = None,
        dry_run: bool = False, units: list[str] | None = None) -> Counter:
    stats: Counter = Counter()
    todo_all = items(units)
    stats["citations"] = len(todo_all)
    authors = cit.tables()["authors"]
    known = set(authors)
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
    book = "Authors the edition knows (id: name):\n" + \
        "\n".join(f"{a}: {s['name']}" for a, s in sorted(authors.items()))
    done = {}
    if LEDGER.exists():  # resume: answers already in the ledger for the same input
        for r in map(json.loads, LEDGER.read_text(encoding="utf-8").splitlines()):
            if r.get("status") == "done" and r.get("prompt") == PROMPT and r.get("model") == model:
                done.update({a["id"]: {**a, "_hash": r["item_hashes"][a["id"]], "_date": r["ts"][:10]}
                             for a in r.get("answers", []) if a["id"] in r.get("item_hashes", {})})
    hashes = {i["id"]: packets.input_hash(_send(i), PROMPT, model, 0) for i in todo_all}
    todo = [i for i in todo_all if (done.get(i["id"]) or {}).get("_hash") != hashes[i["id"]]]
    stats["to_ask"] = len(todo)
    if dry_run:
        leak_check(todo)
        return stats
    spent, sent = 0.0, 0
    for k in range(0, len(todo), packet_size):
        if budget_usd is not None and spent >= budget_usd:
            print(f"stopping: ${spent:.2f} list-equivalent spent, budget ${budget_usd:.2f} (--budget-usd)")
            break
        if max_packets is not None and sent >= max_packets:
            break
        pk = todo[k:k + packet_size]
        leak_check(pk)
        user = book + "\n\nItems:\n" + json.dumps({"items": [_send(i) for i in pk]}, ensure_ascii=False, indent=1)
        res = runner.call_claude(model, sys_prompt, user, SCHEMA)
        sent += 1
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
        for a in res["output"]["items"]:
            done[a["id"]] = {**a, "_hash": hashes.get(a["id"]), "_date": rec["ts"][:10]}
        print(f"  {sum(1 for i in todo_all if i['id'] in done)} answered (${spent:.2f})", flush=True)
    stats["cost_usd_list"] = round(spent, 2)
    write_layer(todo_all, done, hashes, known, model, stats)
    return stats


def write_layer(todo_all, done, hashes, known, model, stats) -> None:
    by_unit: dict[str, dict] = {}
    for i in todo_all:
        a = done.get(i["id"])
        if not a or a["_hash"] != hashes[i["id"]]:
            stats["unanswered"] += 1
            continue
        status, kept = postcheck(i, a, known)
        stats[status] += 1
        if a.get("author_id") and a["author_id"] not in known:
            stats["author_id_unknown_dropped"] += 1
        by_unit.setdefault(i["unit"], {})[i["id"]] = {
            "raw": i["citation"], "status": status, **kept, "confidence": a["confidence"], "reason": a["reason"],
            "by": "machine", "model": model, "prompt": PROMPT, "date": a["_date"], "input_hash": hashes[i["id"]]}
    for unit, recs in by_unit.items():
        out = paths.LAYERS / LAYER / f"{unit}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(out, json.dumps(recs, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
