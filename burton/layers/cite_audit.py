"""`burton cite-audit`: an independent check of the model's citation expansions (data/layers/citation-expansions/),
on a held-out sample drawn after the expansion run, with Gowland's notes as evidence (owner, 2026-11-03: "employ
him in auditing"). Private-only work: the rater sees Gowland's entries near the note's marker, and its output is
verdicts and flags, never text for the reader (CLAUDE.md rule 5).

The sample and the pass rule are written to data/eval/cite-audit-a1.yaml before any answer is read. Prompt
`cite-audit-v1`, ledger state/citations/audit-ledger.jsonl, report state/review/cite-audit.md.
"""

import json
import random
from collections import Counter

import yaml
from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..site import gowland_notes
from ..tei import XML_ID, T, public_id
from ..translate import packets, runner
from . import cite_expand

PROMPT = "cite-audit-v1"
ROUND = "a1"
SAMPLE = paths.DATA / "eval" / f"cite-audit-{ROUND}.yaml"
LEDGER = paths.STATE / "citations" / "audit-ledger.jsonl"
REPORT = paths.STATE / "review" / "cite-audit.md"
STRATA = {"named-in-note": 50, "named-at-anchor": 50, "idem-previous": 20, "work-known": 30}
SEED = 20261103
RULE = ("PASS if the rater finds at most 5 % of the sampled authors wrong overall and no stratum above 10 %; "
        "'unsure' is reported, not counted as wrong. A wrong author is one Burton is not citing there. Works and "
        "loci are reported, not gated. Gowland's agreement is reported per stratum.")
VERDICT = {"type": "string", "enum": ["correct", "wrong", "unsure"]}
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "author", "work", "locus", "gowland", "correction", "reason"],
        "properties": {"id": {"type": "string"}, "author": VERDICT,
                       "work": {"type": "string", "enum": ["correct", "wrong", "unsure", "none"]},
                       "locus": {"type": "string", "enum": ["correct", "wrong", "none"]},
                       "gowland": {"type": "string", "enum": ["agrees", "disagrees", "silent"]},
                       "correction": {"type": ["string", "null"]}, "reason": {"type": "string"}}}}}}


def draw() -> dict:
    """The held-out sample, by the basis the expander gave; written once and never redrawn."""
    if SAMPLE.exists():
        return yaml.safe_load(SAMPLE.read_text(encoding="utf-8"))
    recs = []
    for f in sorted((paths.LAYERS / cite_expand.LAYER).glob("*.json")):
        for cid, r in json.loads(f.read_text(encoding="utf-8")).items():
            if r["status"] in ("expanded", "probable"):
                recs.append((cid, r["basis"]))
    rnd = random.Random(SEED)
    ids = []
    for basis, n in STRATA.items():
        pool = sorted(c for c, b in recs if b == basis)
        ids += [{"id": c, "stratum": basis} for c in rnd.sample(pool, min(n, len(pool)))]
    doc = {"round": ROUND, "written": runner.now()[:10], "method_under_test": f"{cite_expand.PROMPT} (model)",
           "design": f"Random expanded or probable citations, seed {SEED}, stratified by basis {STRATA}; drawn after "
                     "the expansion run, before any rater answer was read.", "rule": RULE,
           "rater": f"{PROMPT}, blind to the expander's reason and confidence, with Gowland's notes as evidence",
           "items": ids}
    SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(SAMPLE, yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=120))
    return doc


def _gowland_near(unit: str, nid: str, stats: Counter) -> list[dict]:
    """Gowland's entries on words in the same block as the note's marker (private-only evidence)."""
    root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
    note = next((n for n in root.iter(T("note")) if public_id(n.get(XML_ID)) == nid), None)
    b = note.getparent() if note is not None else None
    while b is not None and b.tag not in cite_expand.BLOCKS:
        b = b.getparent()
    if b is None or not b.get(XML_ID):
        return []
    bid = public_id(b.get(XML_ID))
    out = []
    for e in gowland_notes.entries(unit, stats):
        if e["selector"] and e["selector"]["in"] == bid and e["kind"] in ("source", "identity", "explanation"):
            out.append({"lemma": e["lemma"], "kind": e["kind"],
                        "note": gowland_notes.note_text(e["endnote"], e["seg"])})
    return out


def items() -> list[dict]:
    sample = draw()
    by_unit: dict[str, dict] = {}
    for f in (paths.LAYERS / cite_expand.LAYER).glob("*.json"):
        by_unit[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    shown = {i["id"]: i for i in cite_expand.items()}
    stats: Counter = Counter()
    out = []
    for s in sample["items"]:
        cid = s["id"]
        unit = shown[cid]["unit"]
        r = by_unit[unit][cid]
        nid = cid.rsplit("-c", 1)[0]
        out.append({"id": cid, "stratum": s["stratum"], "note": shown[cid]["note"], "citation": r["raw"],
                    "context": shown[cid]["context"], "previous": shown[cid]["previous"],
                    "expansion": {k: r.get(k) for k in ("author_name", "work", "locus", "display", "basis")},
                    "gowland": _gowland_near(unit, nid, stats)})
    return out


SEND = ("id", "note", "citation", "context", "previous", "expansion", "gowland")


def run(*, model: str, packet_size: int = 15, budget_usd: float | None = None, dry_run: bool = False) -> Counter:
    stats: Counter = Counter()
    todo_all = items()
    stats["sampled"] = len(todo_all)
    stats["with_gowland_evidence"] = sum(1 for i in todo_all if i["gowland"])
    send = lambda i: {k: i[k] for k in SEND}  # noqa: E731
    hashes = {i["id"]: packets.input_hash(send(i), PROMPT, model, 0) for i in todo_all}
    done = _done(model)
    todo = [i for i in todo_all if (done.get(i["id"]) or {}).get("_hash") != hashes[i["id"]]]
    stats["to_ask"] = len(todo)
    if dry_run:
        return stats
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
    spent = 0.0
    for k in range(0, len(todo), packet_size):
        if budget_usd is not None and spent >= budget_usd:
            break
        pk = todo[k:k + packet_size]
        user = "Items:\n" + json.dumps({"items": [send(i) for i in pk]}, ensure_ascii=False, indent=1)
        res = runner.call_claude(model, sys_prompt, user, SCHEMA)
        spent += res.get("cost_usd_list") or 0
        rec = {"ids": [i["id"] for i in pk], "model": model, "prompt": PROMPT, "ts": runner.now(), "round": ROUND,
               "status": "done" if res["ok"] else ("deferred" if res.get("limit") else "failed"),
               "item_hashes": {i["id"]: hashes[i["id"]] for i in pk},
               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}}
        if res["ok"]:
            rec["answers"] = res["output"]["items"]
        runner.append(LEDGER, rec)
        if not res["ok"]:
            print(f"  call {rec['status']}: {(res.get('error') or '')[:200]} (re-run to resume)")
            break
        print(f"  {k + len(pk)}/{len(todo)} rated (${spent:.2f})", flush=True)
    stats["cost_usd_list"] = round(spent, 2)
    return stats


def _done(model: str) -> dict:
    done = {}
    if LEDGER.exists():
        for r in map(json.loads, LEDGER.read_text(encoding="utf-8").splitlines()):
            if r.get("status") == "done" and r.get("prompt") == PROMPT and r.get("model") == model:
                done.update({a["id"]: {**a, "_hash": r["item_hashes"][a["id"]]} for a in r.get("answers", [])
                             if a["id"] in r.get("item_hashes", {})})
    return done


def report(model: str = "claude-opus-5-5") -> dict:
    todo_all = items()
    done = _done(model)
    by: dict[str, Counter] = {}
    rows = []
    for i in todo_all:
        a = done.get(i["id"])
        if not a:
            continue
        c = by.setdefault(i["stratum"], Counter())
        c["rated"] += 1
        for k in ("author", "work", "locus", "gowland"):
            c[f"{k}_{a[k]}"] += 1
        if a["author"] != "correct" or a["gowland"] == "disagrees":
            rows.append((i, a))
    total = sum(by.values(), Counter())
    wrong = total["author_wrong"] / max(1, total["rated"])
    worst = max((c["author_wrong"] / max(1, c["rated"]) for c in by.values()), default=0)
    verdict = "PASS" if total["rated"] == len(todo_all) and wrong <= 0.05 and worst <= 0.10 else \
        ("INCOMPLETE" if total["rated"] < len(todo_all) else "FAIL")
    L = [f"# Citation expansions: held-out audit {ROUND}", "", f"Rule (written before rating): {RULE}", "",
         f"**{verdict}**: {total['author_wrong']}/{total['rated']} authors wrong "
         f"({wrong:.1%}), {total['author_unsure']} unsure; worst stratum {worst:.1%}.", "",
         "| Stratum | rated | author ok | wrong | unsure | work ok | work wrong | locus wrong | Gowland agrees | "
         "disagrees | silent |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s, c in by.items():
        L.append(f"| {s} | {c['rated']} | {c['author_correct']} | {c['author_wrong']} | {c['author_unsure']} | "
                 f"{c['work_correct']} | {c['work_wrong']} | {c['locus_wrong']} | {c['gowland_agrees']} | "
                 f"{c['gowland_disagrees']} | {c['gowland_silent']} |")
    L += ["", "## Flagged items", "", "| Citation | Expansion | Author | Gowland | Correction | Reason |",
          "|---|---|---|---|---|---|"]
    for i, a in rows:
        L.append(f"| `{i['id']}` {i['citation']} | {i['expansion']['display']} | {a['author']} | {a['gowland']} | "
                 f"{a['correction'] or '—'} | {a['reason']} |")
    atomic_write_text(REPORT, "\n".join(L) + "\n")
    return {"verdict": verdict, **total}
