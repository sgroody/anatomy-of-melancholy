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


def _done(prompt: str = PROMPT) -> dict[str, dict]:
    if not OUT.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, OUT.read_text(encoding="utf-8").splitlines()) if r["prompt"] == prompt}


def round_prompt(h: dict) -> str:
    """The rater prompt of a hold-out round: gold-audit-v1 up to h6; from h7, gold-audit-v2, which spells out what
    belongs to a reference and how separate foreign stretches are given (2026-11-20, set before h7 was drawn)."""
    return h.get("prompt", PROMPT)


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


def label_round(name: str, model: str = PRIMARY_MODEL, packet_size: int = 40) -> dict:
    """Label a hold-out round that has no gold yet (2026-11-18: round h3, the V5 gate after the rules changed):
    the same blind rater and prompt as the audit, item text and context only, never the detector's output; the
    labels become the round's gold file, with their provenance in its header."""
    from ..verify import gold as goldmod

    h = goldmod.holdout_round(name)
    if h["gold"].exists():
        raise SystemExit(f"round {name} already has gold ({h['gold'].name})")
    sample = goldmod.read_sample(h["sample"])
    prompt = round_prompt(h)
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{prompt}.md").read_text(encoding="utf-8")
    done = _done(prompt)
    todo = [{"id": f"{name}:{r['sid']}", "unit": r["unit"], "in_sidenote": r["stratum"] == "sidenote",
             "text": clean(r["unit"], r["text"]), "context": clean(r["unit"], r.get("context", ""))}
            for r in sample]
    ask = [i for i in todo if i["id"] not in done]
    spent = 0.0
    for k in range(0, len(ask), packet_size):
        pk = ask[k:k + packet_size]
        bad = [(i["id"], g) for i in pk for g in leaks(i["unit"], i["text"] + " " + i["context"])]
        if bad:
            raise SystemExit(f"packet refused: Gowland text in {bad[:3]}")
        user = "Label these items.\n\n" + json.dumps({"items": pk}, ensure_ascii=False, indent=2)
        meta = {"ids": [i["id"] for i in pk], "model": model, "prompt": prompt,
                "input_hash": packets.input_hash({"items": pk}, prompt, model, 0)}
        res = runner.call_claude(model, sys_prompt, user, SCHEMA)
        status = "done" if res["ok"] else ("deferred" if res.get("limit") else "failed")
        runner.append(LEDGER, {**meta, "ts": runner.now(), "status": status,
                               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}})
        spent += res.get("cost_usd_list") or 0
        if not res["ok"]:
            raise SystemExit(f"call {status}: {res.get('error')} (re-run to resume)")
        date = datetime.now(UTC).date().isoformat()
        for g in res["output"]["items"]:
            done[g["id"]] = {"id": g["id"], "label": g["label"], "kind": g["kind"], "foreign_part": g["foreign_part"],
                             "reason": g["reason"], "by": "machine", "model": model, "prompt": prompt, "date": date}
        atomic_write_text(OUT, "".join(json.dumps(done[x], ensure_ascii=False, sort_keys=True) + "\n"
                                       for x in sorted(done)))
        print(f"  {k + len(pk)}/{len(ask)} labelled (${spent:.2f})", flush=True)
    rows = [{"_meta": {"round": name, "seed": h["seed"], "date": datetime.now(UTC).date().isoformat(),
                       "labelled_by": f"machine, blind (prompt {prompt}, model {model}): item text and context only, "
                                      "detector output not shown",
                       "purpose": f"held-out round {name} (V5 gate): never used to tune the rules",
                       "mixed_lang": "a 'mixed' item's foreign part is taken as Latin (the rater names no language)",
                       "owner_review": "pending (PLAN D7)"}}]
    for r in sample:
        a = done.get(f"{name}:{r['sid']}")
        if not a:
            continue
        row = {"sid": r["sid"], "stratum": r["stratum"], "unit": r["unit"], "text": r["text"], "gold": a["label"],
               "kind": a["kind"]}
        if r["stratum"] == "sidenote":
            row["in_note"] = True
        if a["label"] == "mixed":
            row["foreign_part"], row["mixed_lang"] = a["foreign_part"], "la"
        rows.append(row)
    atomic_write_text(h["gold"], "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in rows))
    return {"labelled": len(rows) - 1, "of": len(sample), "cost_usd_list": round(spent, 2)}


# ---- a second rater on a round, and the settlement of their disagreements (2026-11-20, round h6: the owner cannot
# hand-check, so a different model labels the round blind as well, and Claude settles in session, from the text, each
# item where the two disagree on whether it is foreign; every settlement is recorded with its reason)
FOREIGN = {"la", "grc", "it", "fr", "es", "de", "nl", "enm", "he", "mixed"}


def rater2_path(name: str):
    return EVAL / f"langid-holdout{name.removeprefix('h')}-rater2.jsonl"


def settled_path(name: str):
    return EVAL / f"langid-holdout{name.removeprefix('h')}-settled.yaml"


def second_rater(name: str, model: str = "claude-sonnet-5-5", packet_size: int = 40) -> dict:
    from ..verify import gold as goldmod

    h = goldmod.holdout_round(name)
    sample = goldmod.read_sample(h["sample"])
    out = rater2_path(name)
    done = {r["sid"]: r for r in map(json.loads, out.read_text(encoding="utf-8").splitlines())} if out.exists() else {}
    prompt = round_prompt(h)
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{prompt}.md").read_text(encoding="utf-8")
    ask = [{"id": f"{name}:{r['sid']}", "unit": r["unit"], "in_sidenote": r["stratum"] == "sidenote",
            "text": clean(r["unit"], r["text"]), "context": clean(r["unit"], r.get("context", ""))}
           for r in sample if r["sid"] not in done]
    spent = 0.0
    for k in range(0, len(ask), packet_size):
        pk = ask[k:k + packet_size]
        bad = [(i["id"], g) for i in pk for g in leaks(i["unit"], i["text"] + " " + i["context"])]
        if bad:
            raise SystemExit(f"packet refused: Gowland text in {bad[:3]}")
        user = "Label these items.\n\n" + json.dumps({"items": pk}, ensure_ascii=False, indent=2)
        res = runner.call_claude(model, sys_prompt, user, SCHEMA)
        status = "done" if res["ok"] else ("deferred" if res.get("limit") else "failed")
        runner.append(LEDGER, {"ids": [i["id"] for i in pk], "model": model, "prompt": prompt, "role": "second rater",
                               "input_hash": packets.input_hash({"items": pk}, prompt, model, 0), "ts": runner.now(),
                               "status": status,
                               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}})
        spent += res.get("cost_usd_list") or 0
        if not res["ok"]:
            raise SystemExit(f"call {status}: {res.get('error')} (re-run to resume)")
        date = datetime.now(UTC).date().isoformat()
        for g in res["output"]["items"]:
            sid = g["id"].split(":", 1)[1]
            done[sid] = {"sid": sid, "label": g["label"], "kind": g["kind"], "foreign_part": g["foreign_part"],
                         "reason": g["reason"], "by": "machine", "model": model, "prompt": prompt, "date": date}
        atomic_write_text(out, "".join(json.dumps(done[x], ensure_ascii=False, sort_keys=True) + "\n"
                                       for x in sorted(done)))
        print(f"  {k + len(pk)}/{len(ask)} labelled (${spent:.2f})", flush=True)
    return {"labelled": len(done), "of": len(sample), "cost_usd_list": round(spent, 2)}


def disagreements(name: str) -> list[dict]:
    """Items where the two raters disagree on whether the item is foreign, or on the foreign part of a mixed one."""
    from ..verify import gold as goldmod

    h = goldmod.holdout_round(name)
    first = {r["sid"]: r for r in goldmod.read_gold(h["gold"])}
    second = {r["sid"]: r for r in map(json.loads, rater2_path(name).read_text(encoding="utf-8").splitlines())}
    sample = {r["sid"]: r for r in goldmod.read_sample(h["sample"])}
    out = []
    for sid, a in first.items():
        b = second.get(sid)
        if not b:
            continue
        fa, fb = a["gold"] in FOREIGN, b["label"] in FOREIGN
        part = a["gold"] == b["label"] == "mixed" and \
            " ".join((a.get("foreign_part") or "").split()) != " ".join((b.get("foreign_part") or "").split())
        if fa != fb or part:
            out.append({"sid": sid, "unit": a["unit"], "text": sample[sid]["text"],
                        "context": sample[sid].get("context", ""), "first": [a["gold"], a.get("foreign_part")],
                        "second": [b["label"], b.get("foreign_part"), b["reason"]]})
    return out


def apply_settlement(name: str) -> dict:
    """Write the settled labels into the round's gold, each marked as settled, with its reason."""
    import yaml

    from ..verify import gold as goldmod

    h = goldmod.holdout_round(name)
    settled = yaml.safe_load(settled_path(name).read_text(encoding="utf-8"))["items"]
    lines = h["gold"].read_text(encoding="utf-8").splitlines()
    rows = [json.loads(x) for x in lines if x]
    n = 0
    for r in rows:
        if "_meta" in r:
            r["_meta"]["owner_review"] = ("replaced (owner, 2026-11-20: \"just do the remainder of V5 yourself\"): a "
                                          "second blind rater (claude-sonnet-5-5) and, where the raters disagree, "
                                          f"Claude's settlement in session ({settled_path(name).name})")
            continue
        st = settled.get(r["sid"])
        if not st:
            continue
        r["gold"], r["settled"] = st["gold"], st["reason"]
        r.pop("foreign_part", None)
        r.pop("mixed_lang", None)
        if st["gold"] == "mixed":
            r["foreign_part"], r["mixed_lang"] = st["foreign_part"], "la"
        n += 1
    atomic_write_text(h["gold"], "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in rows))
    return {"settled": n, "of": len(settled)}
