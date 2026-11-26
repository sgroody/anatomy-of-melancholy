"""`burton names-sweep`: obscure names in Burton's text, identified for the reader (owner, 2026-11-18, stage 14: "a
sweep for obscure names to underline") -> data/layers/names/forms.json.

The reader already links a name when the abbreviation tables give its form to one author with an entry
(`site/names.py`). Every other name Burton sets in italics (the language rules' `name` verdicts,
state/ingest/<unit>.json) is a candidate here: comma lists are split into their names, and forms that are not
capitalised, are Bible books or are linked already are left out. For each form a model sees up to three passages
where it stands and rules: what kind of name it is, whether a well-read modern reader would need help with it
("obscure"), whether the passages mean one bearer, and who or what it is, or "unidentified". The reader underlines
an obscure form only where the ruling is `identified` or `probable` and the passages agree, and its window gives the
identification with the machine label (◇: model, prompt, date) and, for `probable`, the word "probably".

Independent of Gowland: his notes are not sent (CLAUDE.md rule 5), so the records carry no `informed_by`. Ledgered and
resumable (state/names-sweep/ledger.jsonl), prompt `names-v1`.
"""

import json
import re
from collections import Counter, defaultdict

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..tei import T
from ..textview import public_text
from ..translate import packets, runner

PROMPT = "names-v1"
LAYER = paths.LAYERS / "names" / "forms.json"
LEDGER = paths.STATE / "names-sweep" / "ledger.jsonl"
KINDS = ("person", "place", "people", "deity", "book", "not-a-name")
STATUSES = ("identified", "probable", "unidentified")
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "kind", "obscure", "same", "status", "who", "basis"],
        "properties": {"id": {"type": "string"}, "kind": {"type": "string", "enum": list(KINDS)},
                       "obscure": {"type": "boolean"}, "same": {"type": "boolean"},
                       "status": {"type": "string", "enum": list(STATUSES)},
                       "who": {"type": ["string", "null"]}, "basis": {"type": ["string", "null"]}}}}}}
WORD = re.compile(r"[^\W\d_][\w’'\-]*")
PARTICLES = {"de", "of", "à", "a", "van", "von", "la", "le", "du", "di", "da", "&", "the"}


def _forms_of(run: str) -> list[str]:
    """The names in a name run: a comma list is split, a possessive "’s" and edge punctuation are dropped."""
    out = []
    for piece in re.split(r",|\band\b|&", run):
        p = " ".join(piece.split()).strip(" .;:()[]")
        p = re.sub(r"[’']s?$", "", p)  # "Pandora’s", "Acestes’"
        words = WORD.findall(p)
        if not words or not words[0][:1].isupper() or len(p) < 3:
            continue
        if not all(w[:1].isupper() or w.lower() in PARTICLES or len(w) <= 2 for w in words):
            continue
        out.append(p)
    return out


def candidates() -> dict[str, list[str]]:
    """form -> units it stands in (reading order), for forms the reader does not link already."""
    from ..ingest.epub import all_units
    from ..site import names
    from . import citations

    pat, _, _ = names.index()
    bible = set(citations.tables()["bible"])
    found: dict[str, list[str]] = defaultdict(list)
    for unit in all_units():
        f = paths.STATE / "ingest" / f"{unit}.json"
        if not f.exists():
            continue
        for d in json.loads(f.read_text(encoding="utf-8")).get("langid_decisions", []):
            if d.get("verdict") != "name":
                continue
            for form in _forms_of(d["text"]):
                if (pat and pat.fullmatch(form)) or form in bible:
                    continue
                if unit not in found[form]:
                    found[form].append(unit)
    return dict(found)


def _contexts(form: str, units: list[str], texts: dict) -> list[str]:
    rx = re.compile(rf"(?<![\w’'-]){re.escape(form)}(?![\w’'-])")
    out = []
    for unit in units:
        if unit not in texts:
            div = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot().find(f".//{T('div')}")
            texts[unit] = " ".join(public_text(div, notes=True).split()) if div is not None else ""
        t = texts[unit]
        for m in rx.finditer(t):
            out.append("…" + t[max(0, m.start() - 220):m.end() + 160] + "…")
            break
        if len(out) == 3:
            break
    return out


def items() -> list[dict]:
    texts: dict = {}
    out = []
    for k, (form, units) in enumerate(sorted(candidates().items())):
        ctx = _contexts(form, units, texts)
        if ctx:
            out.append({"id": f"n{k}", "form": form, "units": units, "passages": ctx})
    return out


SEND = ("id", "form", "passages")


def run(*, model: str, packet_size: int = 40, budget_usd: float | None = None, dry_run: bool = False,
        limit: int | None = None) -> Counter:
    stats: Counter = Counter()
    todo_all = items()
    stats["forms"] = len(todo_all)
    send = lambda i: {k: i[k] for k in SEND}  # noqa: E731
    hashes = {i["form"]: packets.input_hash({k: i[k] for k in ("form", "passages")}, PROMPT, model, 0)
              for i in todo_all}
    done = _done(model)
    todo = [i for i in todo_all if (done.get(i["form"]) or {}).get("_hash") != hashes[i["form"]]]
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
            by_id = {i["id"]: i for i in pk}
            rec = {"forms": [i["form"] for i in pk], "model": model, "prompt": PROMPT, "ts": runner.now(),
                   "status": "done" if res["ok"] else ("deferred" if res.get("limit") else "failed"),
                   "item_hashes": {i["form"]: hashes[i["form"]] for i in pk},
                   **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}}
            if res["ok"]:
                rec["answers"] = [{**a, "form": by_id[a["id"]]["form"]} for a in res["output"]["items"]
                                  if a["id"] in by_id]
            runner.append(LEDGER, rec)
            if not res["ok"]:
                print(f"  call {rec['status']}: {(res.get('error') or '')[:200]} (re-run to resume)")
                break
            print(f"  {k + len(pk)}/{len(todo)} ruled (${spent:.2f})", flush=True)
        stats["cost_usd_list"] = round(spent, 2)
    write(model, todo_all, stats)
    return stats


def _done(model: str) -> dict:
    done = {}
    if LEDGER.exists():
        for r in map(json.loads, LEDGER.read_text(encoding="utf-8").splitlines()):
            if r.get("status") == "done" and r.get("prompt") == PROMPT and r.get("model") == model:
                done.update({a["form"]: {**a, "_hash": r["item_hashes"][a["form"]], "_ts": r["ts"]}
                             for a in r.get("answers", []) if a["form"] in r.get("item_hashes", {})})
    return done


def shown(rec: dict) -> bool:
    """Whether the reader underlines the form: obscure, one bearer, identified or probable, with an identification."""
    return bool(rec.get("obscure") and rec.get("same") and rec.get("status") in ("identified", "probable")
                and rec.get("who") and rec.get("kind") != "not-a-name")


def reader_index() -> tuple[dict[str, re.Pattern], dict[str, dict]]:
    """For the reader: per unit, a pattern over the forms shown there, and what each form's window says
    (with its machine label). Unambiguous forms (multi-word or never lower-case in Burton) apply across
    all text units so later citations of an identified name are underlined too; ambiguous single-word
    forms stay scoped to the units where the ruling saw them stand as names."""
    if not LAYER.exists():
        return {}, {}
    from ..ingest.epub import all_units
    from ..site.names import lower_words

    recs = {k: v for k, v in json.loads(LAYER.read_text(encoding="utf-8")).items() if shown(v)}
    info = {k: {"who": v["who"], "probable": v["status"] == "probable",
                "label": f"Identified by machine ({v['model']}, prompt {v['prompt']}, {v['date']})"}
            for k, v in recs.items()}
    low = lower_words()
    global_forms: list[str] = []
    by_unit: dict[str, list[str]] = defaultdict(list)
    for form, v in recs.items():
        words = WORD.findall(form)
        if len(words) >= 2 or not any(w.lower() in low for w in words):
            global_forms.append(form)
        else:
            for u in v["units"]:
                by_unit[u].append(form)

    def compile_pat(forms: list[str]) -> re.Pattern | None:
        if not forms:
            return None
        return re.compile(
            r"(?<![\w’'-])(?:" + "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True)) + r")(?![\w’'-])"
        )

    global_pat = compile_pat(global_forms)
    pats: dict[str, re.Pattern] = {}
    for u in all_units():
        extra = by_unit.get(u)
        if extra:
            p = compile_pat(global_forms + extra)
            if p is not None:
                pats[u] = p
        elif global_pat is not None:
            pats[u] = global_pat
    for u, extra in by_unit.items():
        if u not in pats:
            p = compile_pat(global_forms + extra)
            if p is not None:
                pats[u] = p
    return pats, info


def write(model: str, todo_all: list[dict], stats: Counter) -> None:
    done = _done(model)
    out = {}
    for i in todo_all:
        a = done.get(i["form"])
        if not a:
            continue
        rec = {"kind": a["kind"], "obscure": a["obscure"], "same": a["same"], "status": a["status"],
               "who": a["who"] if a["status"] != "unidentified" else None, "basis": a["basis"],
               "units": i["units"], "by": "machine", "model": model, "prompt": PROMPT, "date": a["_ts"][:10]}
        stats[f"status_{rec['status']}"] += 1
        stats["shown"] += shown(rec)
        out[i["form"]] = rec
    stats["ruled"] = len(out)
    if out:
        LAYER.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(LAYER, json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
