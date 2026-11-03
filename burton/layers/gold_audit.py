"""`burton gold-audit`: an independent second rater for the language-ID gold labels (D7).

All 1,127 labels (tuning sample, held-out h1 and h2) were drafted by Claude in session. Here a model labels the
same items blind: it sees each item's text and its context, never the first labels, the detector's output or the
sample's stratum. Through `claude -p` with a schema, in packets; every call goes to state/gold-audit/ledger.jsonl
and a run resumes from data/eval/langid-rater2.jsonl. `--report` compares the two raters and writes the list of
disagreements for the owner (state/review/d7-gold-audit.md).

Nothing of Gowland's is sent: the contexts already leave out his translations; his interpolations, unbracketed
blocks and any bracket or brace are removed here, and a packet that still contains one of his strings is refused.
"""

import json
import re
from collections import Counter
from datetime import UTC, datetime
from functools import cache

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..tei import ED, T
from ..translate import packets, runner
from ..translate.validate import PRIMARY_MODEL

PROMPT = "gold-audit-v1"
EVAL = paths.ROOT / "data" / "eval"
LEDGER = paths.STATE / "gold-audit" / "ledger.jsonl"
OUT = EVAL / "langid-rater2.jsonl"
REVIEW = paths.STATE / "review" / "d7-gold-audit.md"
ROUNDS = {"tuning": ("langid-gold.jsonl", "langid-sample.jsonl"),
          "h1": ("langid-holdout-gold.jsonl", "langid-holdout-sample.jsonl"),
          "h2": ("langid-holdout2-gold.jsonl", "langid-holdout2-sample.jsonl")}
LABELS = ["la", "grc", "it", "fr", "es", "de", "nl", "enm", "he", "en", "name", "citation", "mixed"]
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "required": ["id", "label", "kind", "foreign_part", "reason"], "additionalProperties": False,
        "properties": {"id": {"type": "string"}, "label": {"type": "string", "enum": LABELS},
                       "kind": {"type": ["string", "null"], "enum": ["phrase", "term", "verse", None]},
                       "foreign_part": {"type": ["string", "null"]}, "reason": {"type": "string"}}}}}}


def _rows(name: str) -> list[dict]:
    f = EVAL / name
    return [r for r in map(json.loads, f.read_text(encoding="utf-8").splitlines()) if "_meta" not in r]


@cache
def gowland_strings(unit: str) -> tuple[str, ...]:
    """Every piece of Gowland's matter in a unit, for removal and for the leak test."""
    f = paths.TEXT / f"{unit}.xml"
    if not f.exists():
        return ()
    root = etree.parse(str(f)).getroot()
    out = set()
    for e in root.iter(ED("trans"), ED("verse-trans"), ED("block"), T("supplied")):
        if e.tag == T("supplied") and e.get("resp") != "#gowland":
            continue
        s = " ".join("".join(e.itertext()).split())
        if len(s) >= 4:
            out.add(s)
    return tuple(sorted(out, key=len, reverse=True))


def clean(unit: str, s: str) -> str:
    for g in gowland_strings(unit):
        s = s.replace(g, " ")
    s = re.sub(r"\{[^{}]*\}|\[[^\[\]]*\]", " ", s)
    return " ".join(s.split())


def leaks(unit: str, s: str) -> list[str]:
    return [g for g in gowland_strings(unit) if len(g) >= 12 and g in s]


def items() -> list[dict]:
    out = []
    for rnd, (gold, sample) in ROUNDS.items():
        ctx = {r["sid"]: r for r in _rows(sample)}
        for i, g in enumerate(_rows(gold)):
            iid = f"{rnd}:{g.get('sid') or f'm1-{i:03d}'}"
            c = ctx.get(g.get("sid"), {}).get("context", "")
            out.append({"id": iid, "unit": g["unit"], "in_sidenote": bool(g.get("in_note")),
                        "text": clean(g["unit"], g["text"]), "context": clean(g["unit"], c),
                        "_gold": g, "_round": rnd})
    return out


def _done() -> dict[str, dict]:
    if not OUT.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, OUT.read_text(encoding="utf-8").splitlines()) if r["prompt"] == PROMPT}


def run(model: str = PRIMARY_MODEL, packet_size: int = 40, budget_usd: float | None = None) -> dict:
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
    done = _done()
    todo = [i for i in items() if i["id"] not in done]
    spent = 0.0
    print(f"gold audit: {len(todo)} of {len(items())} items to label")
    for k in range(0, len(todo), packet_size):
        if budget_usd is not None and spent >= budget_usd:
            print(f"stopping: ${spent:.2f} spent, budget ${budget_usd:.2f}")
            break
        pk = todo[k:k + packet_size]
        send = [{x: v for x, v in i.items() if not x.startswith("_")} for i in pk]
        bad = [(i["id"], g) for i in send for g in leaks(i["unit"], i["text"] + " " + i["context"])]
        if bad:
            raise SystemExit(f"packet refused: Gowland text in {bad[:3]}")
        user = "Label these items.\n\n" + json.dumps({"items": send}, ensure_ascii=False, indent=2)
        meta = {"ids": [i["id"] for i in pk], "model": model, "prompt": PROMPT,
                "input_hash": packets.input_hash({"items": send}, PROMPT, model, 0)}
        res = runner.call_claude(model, sys_prompt, user, SCHEMA)
        status = "done" if res["ok"] else ("deferred" if res.get("limit") else "failed")
        runner.append(LEDGER, {**meta, "ts": runner.now(), "status": status,
                               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}})
        spent += res.get("cost_usd_list") or 0
        if not res["ok"]:
            raise SystemExit(f"call {status}: {res.get('error')} (re-run to resume)")
        got = {r["id"]: r for r in res["output"]["items"]}
        date = datetime.now(UTC).date().isoformat()
        for i in pk:
            if i["id"] in got:
                g = got[i["id"]]
                done[i["id"]] = {"id": i["id"], "label": g["label"], "kind": g["kind"],
                                 "foreign_part": g["foreign_part"], "reason": g["reason"], "by": "machine",
                                 "model": model, "prompt": PROMPT, "date": date}
        atomic_write_text(OUT, "".join(json.dumps(done[x], ensure_ascii=False, sort_keys=True) + "\n"
                                       for x in sorted(done)))
        print(f"  {len(done)} labelled (${spent:.2f})", flush=True)
    return {"labelled": len(done), "cost_usd_list": round(spent, 2)}


def report() -> dict:
    second = _done()
    rows, pairs, by_round = [], Counter(), Counter()
    for i in items():
        if i["id"] not in second:
            continue
        a, b = i["_gold"]["gold"], second[i["id"]]["label"]
        pairs[(a, b)] += 1
        by_round[(i["_round"], a == b)] += 1
        if a != b:
            rows.append((i, second[i["id"]]))
    n = sum(pairs.values())
    agree = sum(v for (a, b), v in pairs.items() if a == b)
    lines = ["# D7: second rater on the language-ID gold labels", "",
             f"Second rater: {PROMPT}, blind (text and context only; no first labels, detector output or stratum). "
             "Same model family as the first rater, so agreement is not independent proof; the disagreements "
             "are the ones worth your eye.", "",
             f"**Agreement {agree}/{n} ({100 * agree / max(n, 1):.1f} %).** By round: " +
             ", ".join(f"{r} {by_round[(r, True)]}/{by_round[(r, True)] + by_round[(r, False)]}" for r in ROUNDS), "",
             "| first → second | n |", "|---|---|"]
    lines += [f"| {a} → {b} | {v} |" for (a, b), v in sorted(pairs.items(), key=lambda x: -x[1]) if a != b]
    lines += ["", "## Disagreements", "", "| item | unit | text | first | second | second rater's reason |",
              "|---|---|---|---|---|---|"]
    for i, s in rows:
        t = i["text"].replace("|", "/")
        lines.append(f"| {i['id']} | {i['unit']} | {t[:90]}{'…' if len(t) > 90 else ''} | {i['_gold']['gold']} | "
                     f"{s['label']} | {s['reason'].replace('|', '/')[:160]} |")
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(REVIEW, "\n".join(lines) + "\n")
    return {"items": n, "agree": agree, "disagree": len(rows),
            "by_round": {r: f"{by_round[(r, True)]}/{by_round[(r, True)] + by_round[(r, False)]}" for r in ROUNDS}}
