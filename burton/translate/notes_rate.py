"""The notes the translation passes wrote, rated for the margin (owner, 2026-11-04: "The notes the Claude translation
passes wrote: add them (to the margin), after a spot check and an independent audit of their quality"; 2026-11-18,
stage 14: "the most useful ones").

Three steps, in order:
1. Spot check (`burton note-rate --draw`): a seeded random 2 % of the records with a note, with the pass rules fixed
   in data/eval/notes-spotcheck.yaml before any labelling. The first rater is Claude in session
   (data/eval/notes-spotcheck-gold.jsonl).
2. Independent audit (`burton note-rate --audit`): a blind second rater, a model through `claude -p` (prompt
   note-audit-v1), sees the passage, Burton's text around it, the translation and the note, never the first rater's
   labels, and judges the note's accuracy and its use to a reader -> data/eval/notes-spotcheck-rater2.jsonl.
   `--compare` reports agreement and the rules' outcome.
3. Rating (`burton note-rate --all`): every note rated (prompt note-rate-v1) for its use to a reader, 1 to 3, with its
   kind -> data/layers/note-ratings/<unit>.json. The reader shows a note in the margin only where it is rated 3 and
   not flagged doubtful, and only if the spot check passed (data/eval/notes-spotcheck.yaml `outcome`).

Items are built by `audit.items` (public text only: nothing of Gowland's). Every call is ledgered
(state/note-rate/ledger.jsonl) and a run resumes from the ledger.
"""

import json
import random
from collections import Counter
from datetime import UTC, datetime

import yaml

from .. import paths
from ..fsutil import atomic_write_text
from . import audit, packets, runner
from .validate import PRIMARY_MODEL, primary_machine

SAMPLE = paths.ROOT / "data" / "eval" / "notes-spotcheck.yaml"
FIRST = paths.ROOT / "data" / "eval" / "notes-spotcheck-gold.jsonl"
SECOND = paths.ROOT / "data" / "eval" / "notes-spotcheck-rater2.jsonl"
LAYER = paths.LAYERS / "note-ratings"
LEDGER = paths.STATE / "note-rate" / "ledger.jsonl"
AUDIT_PROMPT, RATE_PROMPT = "note-audit-v1", "note-rate-v1"
SEED = 20261118
ACCURACY = ["sound", "doubtful", "wrong"]
KINDS = ["allusion", "source", "context", "term", "textual", "translation"]
AUDIT_SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "accuracy", "accuracy_reason", "usefulness", "usefulness_reason"],
        "properties": {"id": {"type": "string"}, "accuracy": {"type": "string", "enum": ACCURACY},
                       "accuracy_reason": {"type": "string"}, "usefulness": {"type": "integer", "enum": [1, 2, 3]},
                       "usefulness_reason": {"type": "string"}}}}}}
RATE_SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "usefulness", "kind", "doubtful"],
        "properties": {"id": {"type": "string"}, "usefulness": {"type": "integer", "enum": [1, 2, 3]},
                       "kind": {"type": "string", "enum": KINDS}, "doubtful": {"type": "boolean"}}}}}}


def population() -> list[str]:
    """Ids of the passages whose primary machine translation carries a note."""
    out = []
    for f in sorted((paths.LAYERS / "translations").glob("*.json")):
        for pid, rec in json.loads(f.read_text(encoding="utf-8")).items():
            m = primary_machine(rec)
            if m and m.get("note"):
                out.append(pid)
    return out


def draw(share: float = 0.02) -> dict:
    if SAMPLE.exists():
        raise SystemExit(f"{SAMPLE.name} exists: the spot check is drawn once")
    pop = population()
    pick = sorted(random.Random(SEED).sample(pop, round(len(pop) * share)))
    doc = {
        "purpose": "Spot check of the notes the translation passes wrote, before any is shown in the margin. "
                   "Drawn, and the rules fixed, before any labelling.",
        "drawn": datetime.now(UTC).date().isoformat(), "seed": SEED, "population": len(pop),
        "raters": "first: Claude in session; second: a model blind via `burton note-rate --audit` (prompt "
                  f"{AUDIT_PROMPT}). The notes' writer is the same model family, so errors it makes systematically "
                  "may be missed by both raters.",
        "labels": {
            "accuracy": {"sound": "every claim of fact in the note is right, or hedged as it should be",
                         "doubtful": "a claim that may be wrong, or is stated more surely than the evidence allows",
                         "wrong": "a claim of fact that is wrong (a source, a date, a meaning, what Burton did)"},
            "usefulness": {3: "tells a reader something worth knowing beside the text: an allusion, the source and "
                              "how Burton bends it, a term's sense, context",
                           2: "correct but slight; a reader loses little without it",
                           1: "a translator's working note (word choice, grammar, literal sense) or a repetition of "
                              "the translation"}},
        "rules": {
            "R1": "accuracy: notes adjudicated `wrong` at most 3 % of the sample",
            "R2": "of the notes the rating pass would show (rated 3, not doubtful), none adjudicated `wrong`",
            "on_failure": "reported with its numbers; no note is shown in the margin until the owner decides"},
        "sample": pick,
        "outcome": None,
    }
    atomic_write_text(SAMPLE, yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=118))
    return {"population": len(pop), "sample": len(pick)}


def sample_ids() -> list[str]:
    return yaml.safe_load(SAMPLE.read_text(encoding="utf-8"))["sample"]


def _brief(i: dict, rate: bool) -> dict:
    keep = ("id", "language", "passage", "translation", "note") + (("burton",) if rate else
                                                                    ("burton", "burton_before", "burton_after",
                                                                     "main_text_at_note", "sidenotes"))
    return {k: i[k] for k in keep}


def _ask(prompt: str, schema: dict, todo: list[dict], model: str, packet_size: int, sink, budget_usd=None) -> float:
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{prompt}.md").read_text(encoding="utf-8")
    spent = 0.0
    for k in range(0, len(todo), packet_size):
        if budget_usd is not None and spent >= budget_usd:
            print(f"  budget reached (${spent:.2f}); re-run to continue")
            break
        pk = todo[k:k + packet_size]
        user = "Items:\n" + json.dumps({"items": pk}, ensure_ascii=False, indent=1)
        meta = {"ids": [i["id"] for i in pk], "model": model, "prompt": prompt,
                "input_hash": packets.input_hash({"items": pk}, prompt, model, 0)}
        res = runner.call_claude(model, sys_prompt, user, schema)
        spent += res.get("cost_usd_list") or 0
        status = "done" if res["ok"] else ("deferred" if res.get("limit") else "failed")
        rec = {**meta, "ts": runner.now(), "status": status,
               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}}
        if res["ok"]:
            rec["answers"] = [a for a in res["output"]["items"] if a["id"] in meta["ids"]]
        runner.append(LEDGER, rec)
        if not res["ok"]:
            print(f"  call {status}: {(res.get('error') or '')[:200]} (re-run to resume)")
            break
        sink(rec["answers"])
        print(f"  {k + len(pk)}/{len(todo)} ({prompt}, ${spent:.2f})", flush=True)
    return spent


def _jsonl(path) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = (json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip())
    return {r["id"]: r for r in rows}


def run_audit(model: str = PRIMARY_MODEL, packet_size: int = 12) -> dict:
    done = {k: v for k, v in _jsonl(SECOND).items() if v.get("prompt") == AUDIT_PROMPT}
    todo = [_brief(i, False) for i in audit.items(sample_ids()) if i["id"] not in done]
    date = datetime.now(UTC).date().isoformat()

    def sink(answers):
        for a in answers:
            done[a["id"]] = {**a, "by": "machine", "model": model, "prompt": AUDIT_PROMPT, "date": date}
        atomic_write_text(SECOND, "".join(json.dumps(done[x], ensure_ascii=False, sort_keys=True) + "\n"
                                          for x in sorted(done)))

    spent = _ask(AUDIT_PROMPT, AUDIT_SCHEMA, todo, model, packet_size, sink)
    return {"audited": len(done), "cost_usd_list": round(spent, 2)}


def _ratings() -> dict[str, dict]:
    out = {}
    if LEDGER.exists():
        for r in map(json.loads, LEDGER.read_text(encoding="utf-8").splitlines()):
            if r.get("status") == "done" and r.get("prompt") == RATE_PROMPT:
                out.update({a["id"]: {**a, "model": r["model"], "date": r["ts"][:10], "input_hash": r["input_hash"]}
                            for a in r.get("answers", [])})
    return out


def note_hash(pid: str, rec: dict) -> str:
    m = primary_machine(rec)
    return packets.sha1(json.dumps([rec.get("text_sha1"), m.get("text"), m.get("note")], ensure_ascii=False))


def run_rate(model: str = PRIMARY_MODEL, packet_size: int = 40, which: list[str] | None = None,
             budget_usd: float | None = None) -> dict:
    """Rate the notes (all, or `which`); a note whose translation or text changed since its rating is rated again."""
    layers = {}
    current = {}
    for pid in which or population():
        unit = pid.rsplit("-", 1)[0]
        if unit not in layers:
            layers[unit] = json.loads((paths.LAYERS / "translations" / f"{unit}.json").read_text(encoding="utf-8"))
        current[pid] = note_hash(pid, layers[unit][pid])
    have = _layer()
    todo_ids = [p for p in current if (have.get(p) or {}).get("note_hash") != current[p]]
    todo = [_brief(i, True) for i in audit.items(todo_ids)] if todo_ids else []
    # the ledger holds the answers; the layer is written from it once the run stops
    spent = _ask(RATE_PROMPT, RATE_SCHEMA, todo, model, packet_size, lambda answers: None, budget_usd)
    stats = write_layer(current, _ratings())
    return {"notes": len(current), "asked": len(todo), "cost_usd_list": round(spent, 2), **stats}


def _layer() -> dict[str, dict]:
    out = {}
    for f in LAYER.glob("*.json"):
        out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


def write_layer(current: dict[str, str], rated: dict[str, dict]) -> Counter:
    by_unit: dict[str, dict] = {}
    stats: Counter = Counter()
    have = _layer()
    for pid, h in current.items():
        a = rated.get(pid)
        if a is None:
            if pid in have and have[pid].get("note_hash") == h:
                by_unit.setdefault(pid.rsplit("-", 1)[0], {})[pid] = have[pid]
            continue
        rec = {"usefulness": a["usefulness"], "kind": a["kind"], "doubtful": a["doubtful"], "note_hash": h,
               "by": "machine", "model": a["model"], "prompt": RATE_PROMPT, "date": a["date"]}
        stats[f"usefulness_{rec['usefulness']}"] += 1
        stats["shown_if_passed"] += shows(rec)
        by_unit.setdefault(pid.rsplit("-", 1)[0], {})[pid] = rec
    for unit, recs in by_unit.items():
        LAYER.mkdir(parents=True, exist_ok=True)
        atomic_write_text(LAYER / f"{unit}.json", json.dumps(recs, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return stats


def shows(rec: dict | None) -> bool:
    return bool(rec) and rec["usefulness"] == 3 and not rec["doubtful"]


def passed() -> bool:
    """Whether the spot check's outcome allows notes in the margin (set by `compare` from the adjudicated labels)."""
    if not SAMPLE.exists():
        return False
    return (yaml.safe_load(SAMPLE.read_text(encoding="utf-8")).get("outcome") or {}).get("passed") is True


def compare() -> dict:
    """First rater (in session) against the blind second rater, and the rules' outcome on the first rater's labels
    (adjudicated: where the two disagree on accuracy, the first file holds the adjudicated label and its reason)."""
    first, second = _jsonl(FIRST), _jsonl(SECOND)
    both = sorted(set(first) & set(second))
    acc = Counter((first[i]["accuracy"], second[i]["accuracy"]) for i in both)
    use = Counter((first[i]["usefulness"], second[i]["usefulness"]) for i in both)
    rated = _layer()
    wrong = [i for i in both if first[i]["accuracy"] == "wrong"]
    shown_wrong = [i for i in wrong if shows(rated.get(i))]
    r1 = len(wrong) <= 0.03 * len(both)
    r2 = not shown_wrong
    return {"items": len(both),
            "accuracy": {"agree": sum(n for (a, b), n in acc.items() if a == b),
                         "pairs": {f"{a}/{b}": n for (a, b), n in sorted(acc.items())}},
            "usefulness": {"agree": sum(n for (a, b), n in use.items() if a == b),
                           "within_one": sum(n for (a, b), n in use.items() if abs(a - b) <= 1),
                           "pairs": {f"{a}/{b}": n for (a, b), n in sorted(use.items())}},
            "wrong": wrong, "R1": r1, "shown_wrong": shown_wrong, "R2": r2 if rated else None,
            "disagreements": [{"id": i, "first": first[i]["accuracy"], "second": second[i]["accuracy"],
                               "second_reason": second[i]["accuracy_reason"]} for i in both
                              if first[i]["accuracy"] != second[i]["accuracy"]]}
