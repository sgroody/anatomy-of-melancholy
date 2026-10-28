"""Post-hoc checks on every machine result (SPEC §6.5) and conversion to layer records.

Severity:
  structural - the packet answer is unusable (missing/extra ids, empty translation): retry, then invalid.
  retry      - worth one retry with the message (e.g. self-translation quote not found); if it
               persists, the item is downgraded, never accepted as claimed.
  warning    - recorded with the record and counted in reports.

Several models may translate the same passage (the M4 pilot runs two). Each machine translation keeps
its own self-translation verdict and source claim; the record's top-level `self_translation` and
`source` come from the primary model (PLAN D8) when it has a record, so the reader shows one coherent view.
"""

import re
import unicodedata
from datetime import UTC, datetime

from .. import paths

PRIMARY_MODEL = "claude-opus-5-5"  # the default until the owner decides D8


def _n(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s or "").replace("⟦", "").replace("⟧", "").split())


NEARBY = ("paragraph", "after", "burton_english_following", "main_text_at_note", "before")
CONTEXT = (*NEARBY, "sidenotes")
QUOTED = re.compile(r"“([^”]{2,})”|\"([^\"]{2,})\"|(?<![\w’'])['‘]([^'’]{2,})['’](?!\w)")


def quote_ok(item: dict, quote: str | None) -> bool:
    """The quote must be Burton's English copied exactly from the context given (the context fields
    overlap, so presence is checked per field). Uniqueness within the unit is checked by V7."""
    if not quote:
        return False
    q = _n(quote)
    if not q or q in _n(item["text"]):
        return False
    return any(_n(item.get(k, "")).count(q) == 1 for k in NEARBY)


def _context(item: dict) -> str:
    parts = []
    for k in CONTEXT:
        v = item.get(k)
        parts.extend(v if isinstance(v, list) else [v or ""])
    return _n(" ".join(parts)).lower()


def basis_quotes_context(item: dict, basis: str | None) -> bool:
    """A burton-cites basis must quote, in quotation marks, words that stand in the packet's context
    (Burton's sidenote or his attribution in the text): the claim is then checkable."""
    ctx = _context(item)
    for m in QUOTED.finditer(basis or ""):
        q = _n(next(g for g in m.groups() if g)).lower().strip(" .,;:")
        if len(q) >= 2 and q in ctx:
            return True
    return False


def _term_re(t: str) -> str:
    return rf"(?<!\w){re.escape(t)}(?!\w)"


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
        if item["kind"] == "gloss-only":
            errs.extend(_check_glosses(p, item))
            continue
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
        if src["status"] == "burton-cites" and not basis_quotes_context(item, src["basis"]):
            errs.append({"id": p["id"], "severity": "retry",
                         "msg": f"{p['id']}: burton-cites needs a basis that quotes, in double quotation marks, "
                                f"Burton's own words naming the source (his sidenote or his text); otherwise "
                                f"use unidentified or probable"})
        tr = p["translation"]
        # explanation belongs in `note`, never inside the translation ("Curable (salutary)")
        added = sum(tr.count(c) for c in "([") - sum(item["text"].count(c) for c in "([")
        if added > 0:
            errs.append({"id": p["id"], "severity": "retry",
                         "msg": f"{p['id']}: the translation adds {added} parenthesis or bracket(s) not in the "
                                f"source; put glosses, alternatives and explanations in note"})
        if re.search(r"\b(i\.e\.|that is to say|or rather)", tr, re.I) and \
                not re.search(r"\b(id est|i\.e\.|hoc est|scilicet)", item["text"], re.I):
            errs.append({"id": p["id"], "severity": "warning", "msg": "explanatory phrase in translation"})
        # warnings
        ratio = len(tr) / max(1, len(item["text"]))
        if not 0.4 <= ratio <= 3.5:
            errs.append({"id": p["id"], "severity": "warning", "msg": f"length ratio {ratio:.2f}"})
        src_words = re.findall(r"\w+", item["text"].lower())
        low = tr.lower()
        for i in range(len(src_words) - 3):
            if " ".join(src_words[i:i + 4]) in low:
                errs.append({"id": p["id"], "severity": "warning", "msg": "4+ source words left untranslated"})
                break
        for term in gdata.get("terms", []):
            if any(re.search(_term_re(t), item["text"], re.I) for t in term["latin"]):
                if not any(r.lower() in low for r in term["render"]):
                    errs.append({"id": p["id"], "severity": "warning",
                                 "msg": f"glossary: {term['latin'][0]} not rendered as {term['render']}"})
    return errs


def _check_glosses(p: dict, item: dict) -> list[dict]:
    errs = []
    if p["translation"].strip():
        errs.append({"id": p["id"], "severity": "retry",
                     "msg": f"{p['id']}: gloss-only items take glosses, not a translation; leave translation empty"})
    for g in p["glosses"]:
        if not g["word"].strip() or g["word"] not in item["text"]:
            errs.append({"id": p["id"], "severity": "retry",
                         "msg": f"{p['id']}: gloss word {g['word']!r} is not copied exactly from the text"})
    return errs


def blocking(errors: list[dict], final: bool) -> list[dict]:
    keep = ("structural",) if final else ("structural", "retry")
    return [e for e in errors if e["severity"] in keep]


def _flat(s: str) -> str:
    """Context text without the packet's markers, for building selectors against the unit's text."""
    return _n((s or "").replace("⟦sidenote⟧", " "))


def span_selector(item: dict, exact: str, unit_texts: tuple[str, str] | None) -> dict:
    """Burton's span as a text-quote selector: `exact`, plus a prefix and suffix taken from the context
    field it was found in, grown until the quote matches exactly once in the unit's text.
    `unit_texts` = (main text without sidenotes, text with sidenotes), both normalized by _n. The main
    text is tried first (a span may run across a note's anchor); `view: with-notes` marks a selector
    that matches only with the notes (Burton's rendering in a sidenote). Without unit_texts: `exact`."""
    sel = {"exact": exact}
    if unit_texts is None:
        return sel
    for view, text in zip(("main", "with-notes"), unit_texts, strict=True):
        tag = {} if view == "main" else {"view": view}
        if text.count(exact) == 1:
            return {**sel, "prefix": "", "suffix": "", **tag}
        for k in NEARBY:
            field = _flat(item.get(k, ""))
            if field.count(exact) != 1:
                continue
            at = field.index(exact)
            for n in range(8, len(field) + 8, 8):
                pre, suf = field[max(0, at - n):at], field[at + len(exact):at + len(exact) + n]
                for p, s in ((pre, suf), ("", suf), (pre, "")):
                    if text.count(p + exact + s) == 1:
                        return {**sel, "prefix": p, "suffix": s, **tag}
    return sel  # still ambiguous: V7 reports it


def _verdict(item: dict, p: dict, unit: str, unit_text: tuple[str, str] | None = None) -> dict:
    st = p["self_translation"]
    status = st["status"]
    if status != "none" and not quote_ok(item, st["burton_quote"]):
        status = "undetermined"  # claimed but not verifiable: downgrade, never accept
    span = None
    if status in ("full", "partial", "paraphrase"):
        span = {"in": unit, "near": item["id"], **span_selector(item, _n(st["burton_quote"]), unit_text)}
    out = {"status": status, "burton_span": span}
    if status == "undetermined":
        out["claimed"] = st["status"]
    return out


def _source(item: dict, p: dict) -> dict:
    src = dict(p["source"])
    downgraded = None
    if (src["status"] == "probable" and not (src["basis"] or "").strip()) or \
            (src["status"] == "burton-cites" and not basis_quotes_context(item, src["basis"])):
        downgraded, src = src["status"], {"status": "unidentified", "author": None, "work": None,
                                          "locus": None, "basis": None}
    src["verified"] = False
    if downgraded:
        src["downgraded_from"] = downgraded
    return src


def source_downgrades() -> dict[str, dict]:
    """Source claims withdrawn by a check (data/manual/source-downgrades.yaml), by passage id."""
    import yaml

    f = paths.ROOT / "data" / "manual" / "source-downgrades.yaml"
    return {d["id"]: d for d in (yaml.safe_load(f.read_text(encoding="utf-8")) or [])} if f.exists() else {}


def apply_downgrade(pid: str, src: dict, decisions: dict[str, dict] | None = None) -> dict:
    d = (source_downgrades() if decisions is None else decisions).get(pid)
    if not d or src["status"] == "unidentified":
        return src
    return {"status": "unidentified", "author": None, "work": None, "locus": None, "basis": None,
            "verified": False, "downgraded_from": src["status"], "decision": " ".join(d["reason"].split())}


def to_record(existing: dict | None, p: dict, b: dict, model: str, prompt: str, models_used: list,
              errors: list[dict], unit_text: tuple[str, str] | None = None) -> dict:
    item = b["packet_item"]
    mine = [e for e in errors if e.get("id") == p["id"]]
    verdict, src = _verdict(item, p, b["unit"], unit_text), _source(item, p)
    signals = ["no-gowland-bracket"] if not b["bracket_follows"] else []
    if item.get("burton_english_following"):
        signals.append("burton-english-verse-follows")
    machine = {
        "by": "machine", "model": model, "models_reported": models_used, "prompt": prompt,
        "date": datetime.now(UTC).date().isoformat(), "text": p["translation"], "literal": p["literal"],
        "confidence": p["confidence"], "flags": p["flags"], "note": p["note"],
        "self_translation": verdict, "source": src,
        "warnings": [e["msg"] for e in mine if e["severity"] == "warning"],
    }
    others = [t for t in (existing or {}).get("translations", [])
              if not (t.get("by") == "machine" and t.get("model") == model and t.get("prompt") == prompt)]
    primary_elsewhere = model != PRIMARY_MODEL and any(
        t.get("by") == "machine" and t.get("model") == PRIMARY_MODEL for t in others)
    if primary_elsewhere and existing:
        top_st, top_src = existing["self_translation"], existing["source"]
    else:
        top_st = {**verdict, "signals": signals, "method": f"model:{model}/{prompt}", "confidence": p["confidence"]}
        top_src = src
    rec = {
        "lang": item["lang"], "kind": item["kind"], "location": item["location"],
        "text": item["text"], "text_sha1": b["text_sha1"],
        "self_translation": top_st,
        "translations": others + [machine],
        "source": apply_downgrade(item["id"], top_src),
        "review": (existing or {}).get("review", {"state": "unreviewed", "by": None, "date": None}),
    }
    rec["preferred"] = preferred(rec)
    return rec


def selector(text: str, exact: str, room: int = 16) -> dict | None:
    """A text-quote selector for `exact` in `text`, with prefix/suffix grown until it matches once."""
    at = text.find(exact)
    if at < 0:
        return None
    for k in range(room, len(text) + room, 8):
        pre, suf = text[max(0, at - k):at], text[at + len(exact):at + len(exact) + k]
        if text.count(pre + exact + suf) == 1:
            return {"exact": exact, "prefix": pre, "suffix": suf}
    return None


def to_gloss_record(existing: dict | None, p: dict, b: dict, model: str, prompt: str, models_used: list,
                    errors: list[dict]) -> dict:
    item = b["packet_item"]
    mine = [e for e in errors if e.get("id") == p["id"]]
    items = []
    for g in p["glosses"]:
        sel = selector(item["text"], g["word"])
        if sel:
            items.append({"headword": g["word"], "sense": g["sense"], "selector": {"in": item["id"], **sel}})
    entry = {"by": "machine", "model": model, "models_reported": models_used, "prompt": prompt,
             "date": datetime.now(UTC).date().isoformat(), "items": items, "note": p["note"],
             "confidence": p["confidence"], "warnings": [e["msg"] for e in mine]}
    others = [g for g in (existing or {}).get("glosses", [])
              if not (g.get("by") == "machine" and g.get("model") == model and g.get("prompt") == prompt)]
    return {"lang": item["lang"], "kind": "gloss-only", "text": item["text"], "text_sha1": b["text_sha1"],
            "glosses": others + [entry]}


ORDER = ["burton", "editor", "djs1927", "machine"]


def preferred(rec: dict) -> str:
    if rec["self_translation"]["status"] == "full":
        return "burton"
    have = {t["by"] for t in rec["translations"]}
    return next(o for o in ORDER if o in have or o == "machine")


def primary_machine(rec: dict) -> dict | None:
    """The machine translation the reader shows: the primary model's latest, else the latest of any."""
    ms = [t for t in rec.get("translations", []) if t.get("by") == "machine"]
    prim = [t for t in ms if t.get("model") == PRIMARY_MODEL]
    return (prim or ms or [None])[-1]
