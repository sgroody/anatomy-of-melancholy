"""`burton xrefs-relative`: Burton's relative cross-references ("as I have said", "in his place") (M6).

Rules find the candidate phrases in the main text; obvious non-references are dropped and counted ("in the
first place" orders an argument; "in the first book of his …" is another author's book). A model, through the
ledgered `claude -p` runner with prompt `xref-rel-v1`, proposes a target unit from the book's outline with an
evidence quotation from the context. Post-checks: the target must be a unit and the evidence must occur in the
context exactly, else the record is `unresolved`. Records go to data/layers/xrefs-relative/<unit>.json as
`relative-proposed` (labelled `by: machine`) or `unresolved`; nothing is linked in the reader until the owner
confirms a proposal (`relative-confirmed`) in state/review/xrefs-relative.md's source file.
"""

import json
import re
from collections import Counter
from datetime import UTC, datetime

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..ingest.epub import all_units, nav
from ..tei import XML_ID, T, public_id
from ..textview import public_text
from ..translate import packets, runner

PROMPT = "xref-rel-v1"
LEDGER = paths.STATE / "xrefs-relative" / "ledger.jsonl"
REVIEW = paths.STATE / "review" / "xrefs-relative.md"
LAYER = "xrefs-relative"
PAT = re.compile(
    r"\b(as I (?:have|did|shall|will) (?:said|shown|showed|touched|noted|proved|declared|treated|told|insinuated|"
    r"specified|mentioned|cited|observed|discoursed|handled|show|treat|prove|declare|handle|discourse|speak)\b"
    r"|(?:before|above|aforesaid|afore) (?:said|mentioned|named|cited|specified|quoted|showed|shown|declared|"
    r"recited|noted|touched)"
    r"|in (?:the|my|our) (?:former|precedent|preceding|last|next|following|subsequent|other|first|second|third) "
    r"(?:partition|section|member|subsection|treatise|discourse|place|chapter|book)s?"
    r"|in (?:his|its|their) (?:proper )?place|hereafter (?:in|shall|to be|I)|in the sequel"
    r"|shall be (?:shown|said|treated|handled|discussed|declared|proved) (?:in|hereafter|more)"
    r"|as (?:shall|will) (?:appear|be shown|be proved)|which I have (?:formerly|before|already)"
    r"|(?:formerly|already|elsewhere) (?:said|shown|showed|touched|treated|handled|declared))", re.I)
NOT_REF = [(re.compile(r"^in the (?:first|second|third|last) place$", re.I), "orders the argument"),
           (re.compile(r"^in the (?:first|second|third) book$", re.I), "another author's book")]
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "is_reference", "target", "evidence", "reason", "confidence"],
        "properties": {"id": {"type": "string"}, "is_reference": {"type": "boolean"},
                       "target": {"type": ["string", "null"]}, "evidence": {"type": ["string", "null"]},
                       "reason": {"type": "string"},
                       "confidence": {"type": "string", "enum": ["high", "medium", "low"]}}}}}}


def outline() -> list[str]:
    return [f"{u['unit']}: {u.get('title', '')}" for u in nav()]


def candidates(units: list[str] | None = None) -> tuple[list[dict], Counter]:
    stats: Counter = Counter()
    out = []
    titles = {u["unit"]: u.get("title", "") for u in nav()}
    for unit in units or all_units():
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        div = root.find(f".//{T('div')}")
        if div.get("resp") == "#gowland":
            continue
        for b in div.iter(T("p"), T("l"), T("item")):
            if b.get(XML_ID) is None or any(a.tag == T("note") for a in b.iterancestors()):
                continue
            text = public_text(b)
            for m in PAT.finditer(text):
                phrase = m.group(1)
                why = next((w for rx, w in NOT_REF if rx.match(phrase)), None)
                if why or text[m.end():m.end() + 4] == " of ":
                    stats[f"dropped: {why or 'another book (of …)'}"] += 1
                    continue
                pre, suf = text[max(0, m.start() - 30):m.start()], text[m.end():m.end() + 30]
                if text.count(pre + phrase + suf) != 1:
                    stats["dropped: selector not unique"] += 1
                    continue
                bid = public_id(b.get(XML_ID))
                ctx = text[max(0, m.start() - 600):m.start()] + "⟦" + phrase + "⟧" + text[m.end():m.end() + 300]
                out.append({"id": f"{bid}-r{m.start()}", "unit": unit, "unit_title": titles.get(unit, ""),
                            "context": ctx, "selector": {"in": bid, "exact": phrase, "prefix": pre, "suffix": suf}})
                stats["candidates"] += 1
    return out, stats


def run(*, model: str, packet_size: int = 15, budget_usd: float | None = None, dry_run: bool = False) -> Counter:
    items, stats = candidates()
    units = {u["unit"] for u in nav()}
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
    book = "Outline of the book:\n" + "\n".join(outline())
    done = {}
    if LEDGER.exists():  # resume: answers already in the ledger for the same input
        for r in map(json.loads, LEDGER.read_text(encoding="utf-8").splitlines()):
            if r.get("status") == "done" and r.get("prompt") == PROMPT and r.get("model") == model:
                done.update({a["id"]: {**a, "_hash": r["item_hashes"][a["id"]], "_date": r["ts"][:10]}
                             for a in r.get("answers", []) if a["id"] in r.get("item_hashes", {})})
    send = lambda i: {k: i[k] for k in ("id", "unit", "unit_title", "context")}  # noqa: E731
    hashes = {i["id"]: packets.input_hash(send(i), PROMPT, model, 0) for i in items}
    todo = [i for i in items if (done.get(i["id"]) or {}).get("_hash") != hashes[i["id"]]]
    stats["to_ask"] = len(todo)
    if dry_run:
        return stats
    spent = 0.0
    for k in range(0, len(todo), packet_size):
        if budget_usd is not None and spent >= budget_usd:
            print(f"stopping: ${spent:.2f} list-equivalent spent, budget ${budget_usd:.2f} (--budget-usd)")
            break
        pk = todo[k:k + packet_size]
        user = book + "\n\nItems:\n" + json.dumps({"items": [send(i) for i in pk]}, ensure_ascii=False, indent=1)
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
        for a in res["output"]["items"]:
            done[a["id"]] = {**a, "_hash": hashes.get(a["id"]), "_date": rec["ts"][:10]}
        print(f"  {len(done)} answered (${spent:.2f})", flush=True)
    stats["cost_usd_list"] = round(spent, 2)
    # write the layer from every current answer
    by_unit: dict[str, dict] = {}
    for i in items:
        a = done.get(i["id"])
        if not a or a["_hash"] != hashes[i["id"]]:
            stats["unanswered"] += 1
            continue
        ok = a["is_reference"] and a["target"] in units and a["target"] != i["unit"] and \
            a["evidence"] and a["evidence"] in i["context"].replace("⟦", "").replace("⟧", "")
        if a["is_reference"] and not ok:
            stats["proposals_failed_postcheck"] += 1
        status = "relative-proposed" if ok else ("unresolved" if a["is_reference"] else "not-a-reference")
        stats[status] += 1
        by_unit.setdefault(i["unit"], {})[i["id"]] = {
            "selector": i["selector"], "status": status, "target": a["target"] if ok else None,
            "evidence": a["evidence"] if ok else None, "reason": a["reason"], "confidence": a["confidence"],
            "by": "machine", "model": model, "prompt": PROMPT, "date": a["_date"], "input_hash": hashes[i["id"]],
            "review": {"state": "unreviewed", "by": None, "date": None}}
    for unit, recs in by_unit.items():
        out = paths.LAYERS / LAYER / f"{unit}.json"
        old = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
        for key, r in recs.items():  # an owner's decision survives a re-run with the same input
            if key in old and old[key].get("review", {}).get("state") != "unreviewed" and \
                    old[key].get("input_hash") == r["input_hash"]:
                recs[key] = old[key]
        out.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(out, json.dumps(recs, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    review(by_unit)
    return stats


def review(by_unit: dict) -> None:
    rows = [(k, r) for u in sorted(by_unit) for k, r in sorted(by_unit[u].items()) if r["status"] != "not-a-reference"]
    lines = ["# Relative cross-references: owner review (M6)", "",
             f"Generated {datetime.now(UTC).date().isoformat()} by `uv run burton xrefs-relative`. Proposals are a",
             f"machine draft (prompt `{PROMPT}`); none is linked in the reader until you confirm it. To confirm, set",
             "the record's `status` to `relative-confirmed` and `review` to your name and date in",
             "`data/layers/xrefs-relative/<unit>.json`; to reject, set `status: unresolved`.", "",
             "| Phrase | In | Proposed target | Evidence | Reason | Confidence |", "|---|---|---|---|---|---|"]
    for k, r in rows:
        lines.append(f"| {r['selector']['exact']} | `{k}` | {r['target'] or '—'} | {r['evidence'] or '—'} | "
                     f"{r['reason']} | {r['confidence']} |")
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(REVIEW, "\n".join(lines) + "\n")
