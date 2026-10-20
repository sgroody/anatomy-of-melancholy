"""`burton adjudicate`: a model rules on runs the language rules could not decide (SPEC §6.1 step 5).

Input: italic runs the rules left `undetermined`, plus Latin-tagged passages with vernacular markers.
Output: data/layers/langid-adjudication.json, a machine layer keyed by sha1(unit|text), each record
labelled with model, prompt and date. `burton ingest` applies it only where the rules are undecided
(or to correct the language of a passage the rules tagged), with resp="#model".

Context sent to the model is the public text of the surrounding block: no Gowland matter.
Resumable: items already in the layer (same text, same prompt) are skipped; layer written atomically.
"""

import hashlib
import json
import os
import unicodedata
from datetime import UTC, datetime

import regex as re
from lxml import etree

from .. import paths
from ..tei import XML_LANG, T
from ..textview import public_text
from .runner import LOCK, acquire_lock, append, call_claude, release_lock

PROMPT = "la-v2"  # v2: English loan-words are en (v1 rulings stay valid, labelled v1)
LAYER = paths.LAYERS / "langid-adjudication.json"
LEDGER = paths.STATE / "adjudicate" / "ledger.jsonl"
LANGS = ["la", "grc", "it", "fr", "es", "de", "nl", "enm", "he", "en", "name", "citation", "mixed"]

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["key", "label", "kind", "foreign_part", "confidence", "reason"],
        "properties": {
            "key": {"type": "string"},
            "label": {"type": "string", "enum": LANGS},
            "kind": {"type": "string", "enum": ["phrase", "term", "title", "verse", "name", "citation", "english"]},
            "foreign_part": {"type": ["string", "null"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "reason": {"type": "string"},
        }}}},
}

SYSTEM = """You classify short italic runs from Robert Burton's *The Anatomy of Melancholy* (1651, modernised
English spelling). Burton italicises Latin quotations, but also proper names, book titles, citation
fragments and some English phrases. For each run, decide what it is, using the surrounding text.

label:
- la / grc / it / fr / es / de / nl / enm (Middle English) / he: the run is (mostly) in that language
- en: English (including English words Burton italicises for emphasis, and English loan-words)
- name: a proper name of a person, place, people, god, star, etc. (even if Latin in form)
- citation: an abbreviated reference, a book title used as a reference, a number or locator
- mixed: part English, part another language; give the non-English part exactly in foreign_part
kind: phrase | term (a single technical or Latin term, e.g. a disease name) | title | verse | name | citation | english
A Latin term used as a term (e.g. "Morbus Gallicus", "Scorbutum", "melancholia") is la/term, not name.
English loan-words and titles in ordinary English use (monsieur, signor, don, peccadillo, citadel,
bona-roba, verbatim, gratis) are en: label a vernacular word it/fr/es/... only when Burton quotes it
as a foreign word rather than using it in English.
foreign_part: only for mixed; copy it exactly from the run, otherwise null.
confidence: high only if you are sure. Be honest: "low" is better than a guess.
Return one entry per key, in order."""


def key(unit: str, text: str) -> str:
    return hashlib.sha1(f"{unit}|{norm(text)}".encode()).hexdigest()[:16]


def norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).split())


def read_layer() -> dict:
    return json.loads(LAYER.read_text(encoding="utf-8")) if LAYER.exists() else {}


def write_layer(data: dict) -> None:
    LAYER.parent.mkdir(parents=True, exist_ok=True)
    tmp = LAYER.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, LAYER)


VERNACULAR = {"it", "fr", "es", "de", "nl", "he"}
LATIN_NOUN_END = re.compile(r"(?:um|ica|icus|ia|ae|orum|ium|tas|tio)$")
VERN = {"it": set("che il della delle dello degli gli lo uno una è ma per con nel nella sono come più chi".split()),
        "fr": set("le les des du un une est que qui ne pas pour sur au aux dans ce cette son sa ses il elle".split()),
        "es": set("el los las del que y en un una es por con para su lo al como más".split())}


def candidates(units: list[str]) -> list[dict]:
    out, seen = [], set()
    for unit in units:
        rep = paths.STATE / "ingest" / f"{unit}.json"
        if not rep.exists():
            continue
        r = json.loads(rep.read_text(encoding="utf-8"))
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        blocks = [(b, public_text(b, notes=b.tag == T("note"))) for b in root.iter(T("p"), T("l"), T("note"))]
        todo = [d["text"] for d in r["langid_decisions"]
                if d["verdict"] == "undetermined" and not d["why"].startswith("roman text")]
        # capitalised runs the rules called names but that may be Latin terms ("Morbus Gallicus",
        # "Scorbutum", "Cachexia"): a Latin-attested word, or one word with a Latin common-noun ending
        for d in r["langid_decisions"]:
            if d["verdict"] != "name" or d["why"].startswith("model ruling"):
                continue
            w = re.findall(r"[^\W\d_]+", d["text"])
            if not w or len(w) > 4:
                continue
            from ..ingest import lexicon

            if any(lexicon.latinness(x) == "la" for x in w if len(x) >= 3) or \
                    (len(w) == 1 and LATIN_NOUN_END.search(w[0].lower())):
                todo.append(d["text"])
        # Latin-tagged passages that look vernacular
        for e in root.iter():
            if isinstance(e.tag, str) and e.get("ana") == "foreign" and e.get(XML_LANG) == "la":
                w = re.findall(r"\p{L}+", public_text(e).lower())
                if len(w) >= 4 and any(sum(x in v for x in w) >= max(2, 0.3 * len(w)) for v in VERN.values()):
                    todo.append(public_text(e))
        for text in todo:
            k = key(unit, text)
            if k in seen or len(norm(text)) < 2:
                continue
            seen.add(k)
            ctx = next((bt for b, bt in blocks if norm(text) in bt), "")
            i = ctx.find(norm(text))
            context = ctx[max(0, i - 220): i + len(norm(text)) + 160] if i >= 0 else ""
            out.append({"key": k, "unit": unit, "run": norm(text), "context": context})
    return out


def run(units: list[str], *, model: str, packet_size: int = 40, max_packets: int | None = None,
        refresh_vernacular: bool = False) -> int:
    acquire_lock()
    try:
        layer = read_layer()
        def wanted(c) -> bool:
            if c["key"] not in layer:
                return True
            old = layer[c["key"]]
            # older rulings stay valid (labelled with their prompt); refresh only what a prompt change targets
            return refresh_vernacular and old.get("prompt") != PROMPT and old["label"] in VERNACULAR \
                and len(c["run"].split()) == 1

        todo = [c for c in candidates(units) if wanted(c)]
        if refresh_vernacular:  # rulings already applied are no longer candidates: take them from the layer
            have = {c["key"] for c in todo}
            for k, v in layer.items():
                if k in have or v["unit"] not in units or not wanted({"key": k, "run": v["text"]}):
                    continue
                root = etree.parse(str(paths.TEXT / f"{v['unit']}.xml")).getroot()
                ctx = next((public_text(b) for b in root.iter(T("p"), T("l"), T("note"))
                            if v["text"] in public_text(b)), "")
                i = ctx.find(v["text"])
                todo.append({"key": k, "unit": v["unit"], "run": v["text"],
                             "context": ctx[max(0, i - 220): i + len(v["text"]) + 160] if i >= 0 else ""})
        print(f"adjudication: {len(todo)} run(s) to classify ({len(layer)} already in the layer)")
        done = 0
        for k in range(0, len(todo), packet_size):
            if max_packets is not None and done >= max_packets:
                break
            batch = todo[k:k + packet_size]
            user = "Classify these runs. Return one entry per key, in order.\n\n" + json.dumps(
                [{"key": b["key"], "run": b["run"], "context": b["context"]} for b in batch],
                ensure_ascii=False, indent=1)
            base = {"prompt": PROMPT, "model": model, "keys": [b["key"] for b in batch]}
            append(LEDGER, {**base, "ts": datetime.now(UTC).isoformat(timespec="seconds"), "status": "started"})
            res = call_claude(model, SYSTEM, user, SCHEMA)
            if not res["ok"]:
                status = "deferred" if res.get("limit") else "failed"
                append(LEDGER, {**base, "status": status, "error": res.get("error")})
                print(f"  packet {k // packet_size + 1}: {status}: {str(res.get('error'))[:160]}")
                if status == "deferred":
                    return 3
                continue
            got = {i["key"]: i for i in res["output"]["items"]}
            layer = read_layer()
            stored = 0
            for b in batch:
                g = got.get(b["key"])
                if not g:
                    continue
                part = g["foreign_part"]
                if g["label"] == "mixed" and (not part or norm(part) not in b["run"]):
                    g = {**g, "label": "undetermined", "confidence": "low",
                         "reason": g["reason"] + " [foreign_part not found in run: downgraded]"}
                layer[b["key"]] = {"unit": b["unit"], "text": b["run"], "label": g["label"], "kind": g["kind"],
                                   "foreign_part": part if g["label"] == "mixed" else None,
                                   "confidence": g["confidence"], "reason": g["reason"], "by": "machine",
                                   "model": model, "prompt": PROMPT,
                                   "date": datetime.now(UTC).date().isoformat()}
                stored += 1
            write_layer(layer)
            append(LEDGER, {**base, "status": "done", "stored": stored, "seconds": res.get("seconds"),
                            "usage": res.get("usage")})
            done += 1
            print(f"  packet {k // packet_size + 1}: {stored}/{len(batch)} stored ({res.get('seconds')}s)")
        return 0
    finally:
        release_lock()


def lookup(unit: str, text: str) -> dict | None:
    return _cached().get(key(unit, text))


_CACHE: dict | None = None


def _cached() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = read_layer()
    return _CACHE


__all__ = ["run", "lookup", "LOCK"]
