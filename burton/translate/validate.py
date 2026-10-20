"""Post-hoc checks on every machine result (SPEC §6.5) and conversion to layer records.

Severity:
  structural - the packet answer is unusable (missing/extra ids, empty translation): retry, then invalid.
  retry      - worth one retry with the message (e.g. self-translation quote not found); if it
               persists, the item is downgraded, never accepted as claimed.
  warning    - recorded with the record and counted in reports.
"""

import re
import unicodedata
from datetime import UTC, datetime


def _n(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s or "").replace("⟦", "").replace("⟧", "").split())


NEARBY = ("paragraph", "after", "burton_english_following", "main_text_at_note", "before")


def quote_ok(item: dict, quote: str | None) -> bool:
    """The quote must be Burton's English copied exactly from the context given (the context fields
    overlap, so presence is checked per field). Uniqueness within the unit is checked by V7."""
    if not quote:
        return False
    q = _n(quote)
    if not q or q in _n(item["text"]):
        return False
    return any(_n(item.get(k, "")).count(q) == 1 for k in NEARBY)


def check(output: dict, batch: list[dict], gdata: dict) -> list[dict]:
    errs: list[dict] = []
    want = [b["packet_item"]["id"] for b in batch]
    got = [p["id"] for p in output.get("passages", [])]
    if sorted(got) != sorted(want) or len(got) != len(set(got)):
        errs.append({"id": None, "severity": "structural",
                     "msg": f"ids returned {got} do not match the packet ids {want}"})
        return errs
    by_id = {b["packet_item"]["id"]: b["packet_item"] for b in batch}
    for p in output["passages"]:
        item = by_id[p["id"]]
        if not p["translation"].strip():
            errs.append({"id": p["id"], "severity": "structural", "msg": f"{p['id']}: empty translation"})
            continue
        st = p["self_translation"]
        if st["status"] != "none" and not quote_ok(item, st["burton_quote"]):
            errs.append({"id": p["id"], "severity": "retry",
                         "msg": f"{p['id']}: burton_quote {st['burton_quote']!r} does not occur exactly once "
                                f"in Burton's nearby English; copy it exactly or use status none"})
        src = p["source"]
        if src["status"] == "probable" and not (src["basis"] or "").strip():
            errs.append({"id": p["id"], "severity": "retry",
                         "msg": f"{p['id']}: source status probable needs a basis"})
        if src["status"] == "burton-cites" and not (item.get("sidenotes") or item["location"] == "sidenote"):
            errs.append({"id": p["id"], "severity": "retry",
                         "msg": f"{p['id']}: burton-cites but no sidenote was given for this passage"})
        # warnings
        ratio = len(p["translation"]) / max(1, len(item["text"]))
        if not 0.4 <= ratio <= 3.5:
            errs.append({"id": p["id"], "severity": "warning", "msg": f"length ratio {ratio:.2f}"})
        src_words = re.findall(r"\w+", item["text"].lower())
        tr = p["translation"].lower()
        for i in range(len(src_words) - 3):
            if " ".join(src_words[i:i + 4]) in tr:
                errs.append({"id": p["id"], "severity": "warning", "msg": "4+ source words left untranslated"})
                break
        for term in gdata.get("terms", []):
            if any(re.search(rf"\b{re.escape(t)}\b", item["text"], re.I) for t in term["latin"]):
                if not any(r.lower() in tr for r in term["render"]):
                    errs.append({"id": p["id"], "severity": "warning",
                                 "msg": f"glossary: {term['latin'][0]} not rendered as {term['render']}"})
    return errs


def blocking(errors: list[dict], final: bool) -> list[dict]:
    keep = ("structural",) if final else ("structural", "retry")
    return [e for e in errors if e["severity"] in keep]


def to_record(existing: dict | None, p: dict, b: dict, model: str, prompt: str, models_used: list,
              errors: list[dict]) -> dict:
    item = b["packet_item"]
    mine = [e for e in errors if e.get("id") == p["id"]]
    st = dict(p["self_translation"])
    st_status = st["status"]
    if st_status != "none" and not quote_ok(item, st["burton_quote"]):
        st_status = "undetermined"  # claimed but not verifiable: downgrade, never accept
    src = dict(p["source"])
    downgraded = None
    if (src["status"] == "probable" and not (src["basis"] or "").strip()) or \
            (src["status"] == "burton-cites" and not (item.get("sidenotes") or item["location"] == "sidenote")):
        downgraded, src = src["status"], {"status": "unidentified", "author": None, "work": None,
                                          "locus": None, "basis": None}
    src["verified"] = False
    if downgraded:
        src["downgraded_from"] = downgraded
    selector = None
    if st_status in ("full", "partial", "paraphrase"):
        selector = {"in": b["unit"], "near": item["id"], "exact": _n(st["burton_quote"])}
    signals = ["no-gowland-bracket"] if not b["bracket_follows"] else []
    if item.get("burton_english_following"):
        signals.append("burton-english-verse-follows")
    machine = {
        "by": "machine", "model": model, "models_reported": models_used, "prompt": prompt,
        "date": datetime.now(UTC).date().isoformat(), "text": p["translation"], "literal": p["literal"],
        "confidence": p["confidence"], "flags": p["flags"], "note": p["note"],
        "warnings": [e["msg"] for e in mine if e["severity"] == "warning"],
    }
    others = [t for t in (existing or {}).get("translations", [])
              if not (t.get("by") == "machine" and t.get("model") == model and t.get("prompt") == prompt)]
    rec = {
        "lang": item["lang"], "kind": item["kind"], "location": item["location"],
        "text": item["text"], "text_sha1": b["text_sha1"],
        "self_translation": {"status": st_status, "signals": signals, "burton_span": selector,
                             "method": f"model:{model}/{prompt}", "confidence": p["confidence"]},
        "translations": others + [machine],
        "source": src,
        "review": (existing or {}).get("review", {"state": "unreviewed", "by": None, "date": None}),
    }
    rec["preferred"] = preferred(rec)
    return rec


ORDER = ["burton", "editor", "djs1927", "machine"]


def preferred(rec: dict) -> str:
    if rec["self_translation"]["status"] == "full":
        return "burton"
    have = {t["by"] for t in rec["translations"]}
    return next(o for o in ORDER if o in have or o == "machine")
