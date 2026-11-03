"""`burton obsolete`: glosses of obsolete English words (M8, D6) -> data/layers/obsolete/<unit>.json.

Source order (SPEC §4.2): Gowland's endnote glosses (private build only, read from his endnotes when the
site is built, never copied here), then Webster 1913, then a model-drafted sense, then the editor's.

1. Candidates (rules, `rules/obs-v1`): every word of Burton's English main text (not a foreign passage,
   not Gowland's matter, not a sidenote) whose every sense in Webster 1913 is labelled obsolete or
   archaic, less the common archaisms in data/manual/gloss-stoplist.yaml. A word in Webster can be a
   homograph of an ordinary word Burton uses, so a candidate is only a candidate.
2. Ruling (model, prompt `obs-v1`, ledger state/obsolete/ledger.jsonl): for each occurrence, in its
   sentence, whether Burton uses one of Webster's obsolete senses (which one), uses the word in an
   ordinary sense (no gloss), or uses it in an obsolete sense Webster lacks (the model drafts it). The
   model sees Burton's words and Webster's senses only: nothing of Gowland's.

Each record is keyed by a registry id (`<unit>-gN`), carries a text-quote selector into its paragraph or
verse group, the headword, the sense, its source and the labels of who decided what.
"""

import json
import re
from collections import Counter
from datetime import UTC, datetime
from functools import cache

import yaml
from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..ids import Registry
from ..tei import XML_ID, XML_LANG, T, public_id
from ..textview import is_gowland, public_text
from ..translate import packets, runner
from . import webster

RULES = "rules/obs-v1"
PROMPT = "obs-v1"
LAYER = paths.LAYERS / "obsolete"
LEDGER = paths.STATE / "obsolete" / "ledger.jsonl"
WORD = re.compile(r"(?<![\w’'-])[a-z]+(?![\w’'-])")
CONTEXT = 24  # characters of selector context on each side (shortened at the container's edges)


@cache
def stoplist() -> dict[str, str]:
    data = yaml.safe_load((paths.MANUAL / "gloss-stoplist.yaml").read_text(encoding="utf-8"))
    return {w["word"]: w["reason"] for w in data["words"]}


def _units() -> list[str]:
    from ..site.book import is_gowland_unit, text_units  # the reading order the site uses
    return [u for u in text_units() if not is_gowland_unit(u)]


def _blocked_spans(e, text: str) -> list[tuple[int, int]]:
    """Where in the container's public text a foreign passage (or any non-English run) lies."""
    out, pos = [], 0
    for f in e.iter():
        if not isinstance(f.tag, str) or f is e:
            continue
        if f.get("ana") == "foreign" or (f.get(XML_LANG) and f.get(XML_LANG) != "en"):
            ft = public_text(f)
            k = text.find(ft, pos) if ft else -1
            if k >= 0:
                out.append((k, k + len(ft)))
                pos = k + len(ft)
    return out


def _selector(cid: str, text: str, a: int, b: int) -> dict | None:
    """The shortest context (up to CONTEXT characters each side) with which the word matches once."""
    for n in range(8, CONTEXT + 1, 4):
        pre, suf = text[max(0, a - n):a], text[b:b + n]
        if text.count(pre + text[a:b] + suf) == 1:
            return {"in": cid, "exact": text[a:b], "prefix": pre, "suffix": suf}
    return None


def _sentence(text: str, a: int, b: int, width: int = 220) -> str:
    """The occurrence in its sentence (or a window of it), the word marked ⟦…⟧, for the model."""
    s = max(text.rfind(". ", 0, a) + 2, a - width)
    e = text.find(". ", b)
    e = min(e + 1 if e >= 0 else len(text), b + width)
    return text[s:a] + "⟦" + text[a:b] + "⟧" + text[b:e]


def candidates() -> list[dict]:
    """Every occurrence of a candidate word, in reading order."""
    stop = stoplist()
    out = []
    for unit in _units():
        div = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot().find(f".//{T('div')}")
        for e in div.iter(T("p"), T("lg")):
            if not e.get(XML_ID) or any(is_gowland(a) for a in e.iterancestors()) or e.get("ana") == "foreign":
                continue
            if any(a.tag == T("note") for a in e.iterancestors()):
                continue
            text = public_text(e)
            blocked = _blocked_spans(e, text)
            cid = public_id(e.get(XML_ID))
            for m in WORD.finditer(text):
                w = m.group(0)
                if w in stop or not webster.wholly_obsolete(w):
                    continue
                if any(x <= m.start() < y for x, y in blocked):
                    continue
                sel = _selector(cid, text, m.start(), m.end())
                if sel is None:
                    continue
                out.append({"unit": unit, "word": w, "selector": sel,
                            "context": _sentence(text, m.start(), m.end())})
    return out


def webster_senses(word: str) -> list[dict]:
    """Webster's entries for the word, as numbered senses the model can name ("w1", "w2", …)."""
    out, k = [], 0
    for e in webster.wholly_obsolete(word) or []:
        for h in e.heads:
            k += 1
            out.append({"id": f"w{k}", "pos": e.pos, "sense": webster.clean_sense(h)})
    return out


# ---------------------------------------------------------------- the ruling
SCHEMA = {"type": "object", "required": ["rulings"], "additionalProperties": False, "properties": {
    "rulings": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["n", "verdict", "webster_sense", "sense", "confidence"],
        "properties": {
            "n": {"type": "integer"},
            "verdict": {"type": "string", "enum": ["webster", "ordinary", "other-obsolete", "not-english"]},
            "webster_sense": {"type": ["string", "null"]},
            "sense": {"type": ["string", "null"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]}}}}}}


def _item(n: int, c: dict) -> dict:
    return {"n": n, "word": c["word"], "context": c["context"], "webster": webster_senses(c["word"])}


def _hash(c: dict, model: str) -> str:
    return packets.input_hash({"word": c["word"], "context": c["context"], "webster": webster_senses(c["word"])},
                              PROMPT, model, 0)


def load_layer(unit: str) -> dict:
    f = LAYER / f"{unit}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def save_layer(unit: str, data: dict) -> None:
    LAYER.mkdir(parents=True, exist_ok=True)
    atomic_write_text(LAYER / f"{unit}.json", json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _key(c: dict) -> str:
    s = c["selector"]
    return f"{s['in']}|{s['prefix']}|{s['exact']}|{s['suffix']}"


def run(*, model: str, packet_size: int = 40, budget_usd: float | None = None, max_packets: int | None = None,
        dry_run: bool = False) -> Counter:
    cands = candidates()
    stats: Counter = Counter(candidates=len(cands), words=len({c["word"] for c in cands}))
    done = {}
    for unit in {c["unit"] for c in cands}:
        for rec in load_layer(unit).values():
            done[(rec["selector"]["in"], rec["selector"]["prefix"], rec["selector"]["exact"],
                  rec["selector"]["suffix"])] = rec.get("input_hash")
    todo = [c for c in cands if done.get(tuple(_key(c).split("|"))) != _hash(c, model)]
    stats["todo"] = len(todo)
    print(f"obsolete-word candidates: {len(cands)} occurrences of {stats['words']} words; {len(todo)} to rule on")
    if dry_run:
        return stats
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
    todo.sort(key=lambda c: (c["word"], c["unit"]))  # one word's occurrences together, so it is ruled on alike
    reg = Registry()
    spent = 0.0
    for n_pk, k in enumerate(range(0, len(todo), packet_size)):
        if max_packets is not None and n_pk >= max_packets:
            break
        if budget_usd is not None and spent >= budget_usd:
            print(f"stopping: ${spent:.2f} list-equivalent spent, budget ${budget_usd:.2f} (--budget-usd)")
            stats["stopped_at_budget"] += 1
            break
        pk = todo[k:k + packet_size]
        send = [_item(i, c) for i, c in enumerate(pk, 1)]
        user = "Rule on these occurrences.\n\n" + json.dumps({"occurrences": send}, ensure_ascii=False, indent=2)
        meta = {"model": model, "prompt": PROMPT, "n": len(pk),
                "input_hash": packets.input_hash({"occurrences": send}, PROMPT, model, 0)}
        res = runner.call_claude(model, sys_prompt, user, SCHEMA)
        status = "done" if res["ok"] else ("deferred" if res.get("limit") else "failed")
        runner.append(LEDGER, {**meta, "ts": runner.now(), "status": status,
                               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}})
        spent += res.get("cost_usd_list") or 0
        if not res["ok"]:
            stats[status] += 1
            print(f"  call {status}: {(res.get('error') or '')[:200]} (re-run to resume)")
            break
        got = {r["n"]: r for r in res["output"]["rulings"]}
        day = datetime.now(UTC).date().isoformat()
        by_unit: dict[str, list] = {}
        for i, c in enumerate(pk, 1):
            r = got.get(i)
            senses = {s["id"]: s for s in webster_senses(c["word"])}
            if r is None or (r["verdict"] == "webster" and r["webster_sense"] not in senses) or \
                    (r["verdict"] == "other-obsolete" and not (r["sense"] or "").strip()):
                stats["invalid_or_missing"] += 1
                continue
            by_unit.setdefault(c["unit"], []).append((c, r, senses))
        for unit, rows in by_unit.items():
            layer = load_layer(unit)
            index = {_key({"selector": v["selector"]}): k for k, v in layer.items()}
            for c, r, senses in rows:
                # by exact locator, with no fingerprint fallback, which would hand a second occurrence of a word
                # in the same block the first one's id
                rid = index.get(_key(c)) or reg.assign(unit, "g", _key(c))
                rec = {"headword": c["word"], "selector": c["selector"], "candidate": RULES,
                       "verdict": r["verdict"], "confidence": r["confidence"],
                       "ruling": {"by": "machine", "model": model, "prompt": PROMPT, "date": day},
                       "input_hash": _hash(c, model)}
                if r["verdict"] == "webster":
                    w = senses[r["webster_sense"]]
                    rec |= {"source": "webster1913", "sense": w["sense"],
                            "webster": {"sense": w["id"], "pos": w["pos"]}}
                elif r["verdict"] == "other-obsolete":
                    rec |= {"source": "machine", "sense": r["sense"].strip(), "by": "machine", "model": model,
                            "prompt": PROMPT, "date": day}
                layer[rid] = rec
                stats[f"verdict_{r['verdict']}"] += 1
            save_layer(unit, layer)
        reg.save()
        print(f"  packet {n_pk + 1}: {len(pk)} ruled (${spent:.2f})", flush=True)
    stats["cost_usd_list"] = round(spent, 2)
    return stats
