"""Gold sample for language identification (SPEC §6.1 step 6, V5).

`draw()` picks a reproducible stratified sample of spans from the base text and writes them to
data/eval/langid-sample.jsonl WITHOUT the detector's verdicts (labels must be made blind).
Labels are then added to data/eval/langid-gold.jsonl; `evaluate()` compares the detector's output
(read from the XML, not from ingest logs) with the labels.

Held-out samples are drawn in rounds (`HOLDOUTS`). Only the newest round has never been seen while
the rules were changed, so V5 gates on it; earlier rounds are kept, excluded from later draws, and
still scored and reported (as "seen"). A round is retired by drawing a new one, never by relabelling.
"""

import json
import random
import re
import unicodedata

from lxml import etree

from .. import paths
from ..tei import ED, XML_LANG, T

STRATA = {"italic": 300, "roman-before-bracket": 100, "sidenote": 100, "verse": 50, "english": 50}
SEED = 20261020
GOLD = paths.DATA / "eval" / "langid-gold.jsonl"
SAMPLE = paths.DATA / "eval" / "langid-sample.jsonl"
FOREIGN_LABELS = {"la", "grc", "it", "fr", "es", "de", "nl", "enm", "he"}


def norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).split())


def text_no_notes(e) -> str:
    out = []

    def walk(x):
        if x.tag in (T("note"), ED("trans"), ED("verse-trans"), ED("enref"), T("pb")):
            return
        if x.text:
            out.append(x.text)
        for c in x:
            walk(c)
            if c.tail:
                out.append(c.tail)

    walk(e)
    return norm("".join(out))


def _units() -> list[str]:
    from ..ingest.epub import FRONT, all_units

    return [u for u in all_units() if not (u in FRONT and FRONT[u][2] == "#gowland")]


def _gowlandish(e) -> bool:
    return any(a.tag in (ED("trans"), ED("verse-trans"), ED("block")) for a in [e, *e.iterancestors()])


def _text_before(block, stop) -> str:
    """Block text (no notes, no Gowland matter) from its start up to the element `stop`."""
    out: list[str] = []

    class Done(Exception):
        pass

    def walk(x):
        if x is stop:
            raise Done
        if x.tag in (T("note"), ED("trans"), ED("verse-trans"), ED("enref"), T("pb")):
            return
        if x.text:
            out.append(x.text)
        for c in x:
            walk(c)
            if c.tail:
                out.append(c.tail)

    try:
        walk(block)
    except Done:
        pass
    return "".join(out)


def candidates() -> dict[str, list[dict]]:
    out = {k: [] for k in STRATA}
    for unit in _units():
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        div = root.find(f".//{T('div')}")
        for block in div.iter(T("p"), T("l"), T("note")):
            if _gowlandish(block):
                continue
            ctx = text_no_notes(block) if block.tag != T("note") else norm("".join(block.itertext()))
            in_note = block.tag == T("note") or any(a.tag == T("note") for a in block.iterancestors())
            # italic runs: every italic element of this block, tagged or not (sampling must not depend on
            # the detector), excluding those inside nested notes or Gowland matter
            for h in block.iter(T("hi")):
                owners = [a for a in h.iterancestors() if a.tag in (T("note"), T("p"), T("l"))]
                if owners[:1] != [block] or _gowlandish(h) or any(a.tag == T("hi") for a in h.iterancestors()):
                    continue
                if h.get("rend") == "i":
                    t = text_no_notes(h)
                    if len(t) >= 2:
                        out["sidenote" if in_note else "italic"].append(
                            {"unit": unit, "text": t, "context": ctx[:600], "kind": "hi"})
            # roman text directly before a Gowland bracket: the last clause before it
            for tr in block.iter(ED("trans")):
                before = _text_before(block, tr)
                clause = re.split(r"[;:()!?]|(?<=[a-z])\. ", before.rstrip())[-1].strip(" ,")
                if len(clause.split()) >= 2:
                    out["roman-before-bracket"].append(
                        {"unit": unit, "text": norm(clause), "context": ctx[:600], "kind": "roman"})
            if block.tag == T("l") and not in_note:
                t = text_no_notes(block)
                if len(t.split()) >= 3:
                    out["verse"].append({"unit": unit, "text": t, "context": "", "kind": "line"})
            if block.tag == T("p") and not in_note and block.getparent().tag == T("div"):
                for sent in re.split(r"(?<=[.;?!])\s+", text_no_notes(block)):
                    if 8 <= len(sent.split()) <= 40:
                        out["english"].append({"unit": unit, "text": sent, "context": "", "kind": "sentence"})
    return out


HOLDOUTS = [  # in the order drawn; the last is the gate (never seen while tuning), earlier ones are seen
    {"name": "h1", "seed": 20261021, "prefix": "h-",
     "strata": {"italic": 70, "roman-before-bracket": 30, "sidenote": 30, "verse": 10, "english": 10},
     "sample": paths.DATA / "eval" / "langid-holdout-sample.jsonl",
     "gold": paths.DATA / "eval" / "langid-holdout-gold.jsonl",
     "seen": "2026-10-20: its errors were studied to change the rules (M2 hardening)"},
    {"name": "h2", "seed": 20261022, "prefix": "h2-",
     "strata": {"italic": 150, "roman-before-bracket": 50, "sidenote": 50, "verse": 25, "english": 25},
     "sample": paths.DATA / "eval" / "langid-holdout2-sample.jsonl",
     "gold": paths.DATA / "eval" / "langid-holdout2-gold.jsonl",
     "seen": "2026-11-18: its errors were studied to change the rules (the sidenote-title rule)"},
    # 2026-11-18: drawn after the rules changed, labelled blind by the second rater (gold-audit-v1), the V5 gate
    {"name": "h3", "seed": 20261118, "prefix": "h3-",
     "strata": {"italic": 150, "roman-before-bracket": 50, "sidenote": 50, "verse": 25, "english": 25},
     "sample": paths.DATA / "eval" / "langid-holdout3-sample.jsonl",
     "gold": paths.DATA / "eval" / "langid-holdout3-gold.jsonl",
     "seen": "2026-11-18: its errors were studied to change the rules (Latin titles, possessives, mixed italics)"},
    # 2026-11-18: drawn after the second cycle's rules changed, labelled blind by the second rater, the V5 gate
    {"name": "h4", "seed": 20261119, "prefix": "h4-",
     "strata": {"italic": 150, "roman-before-bracket": 50, "sidenote": 50, "verse": 25, "english": 25},
     "sample": paths.DATA / "eval" / "langid-holdout4-sample.jsonl",
     "gold": paths.DATA / "eval" / "langid-holdout4-gold.jsonl",
     "seen": "2026-11-19: its errors were studied to change the rules (naturalised words, locators, Author in Work, "
             "lowercase Latin lists; the scorer measures '|' labels stretch by stretch)"},
    # 2026-11-19: drawn after the third cycle's rules changed, labelled blind by the second rater, the V5 gate
    {"name": "h5", "seed": 20261120, "prefix": "h5-",
     "strata": {"italic": 150, "roman-before-bracket": 50, "sidenote": 50, "verse": 25, "english": 25},
     "sample": paths.DATA / "eval" / "langid-holdout5-sample.jsonl",
     "gold": paths.DATA / "eval" / "langid-holdout5-gold.jsonl",
     "seen": "2026-11-20: its errors were studied to change the rules (short runs decided on thin evidence take the "
             "model's ruling)"},
    # 2026-11-20 (owner: "just do the remainder of V5 yourself; I can't hand check it"): drawn after the fourth cycle's
    # change, labelled blind by the first rater (gold-audit-v1, opus) and again blind by a second (gold-audit-v1,
    # sonnet); where they disagree on whether an item is foreign, Claude settled it in session from the text, recorded
    # with a reason (data/eval/langid-holdout6-settled.yaml). That stands in for the owner's hand check (PLAN D7).
    {"name": "h6", "seed": 20261121, "prefix": "h6-",
     "strata": {"italic": 150, "roman-before-bracket": 50, "sidenote": 50, "verse": 25, "english": 25},
     "sample": paths.DATA / "eval" / "langid-holdout6-sample.jsonl",
     "gold": paths.DATA / "eval" / "langid-holdout6-gold.jsonl"},
]
GATE = HOLDOUTS[-1]["name"]
HOLDOUT_SAMPLE, HOLDOUT_GOLD = HOLDOUTS[-1]["sample"], HOLDOUTS[-1]["gold"]


def holdout_round(name: str) -> dict:
    return next(h for h in HOLDOUTS if h["name"] == name)


def read_sample(path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x] if path.exists() else []


def _already_drawn() -> set[tuple[str, str]]:
    """Every item in any sample or gold file (tuning and all hold-out rounds), labelled or not."""
    rows = read_gold() + read_sample(SAMPLE)
    for h in HOLDOUTS:
        rows += read_gold(h["gold"]) + read_sample(h["sample"])
    return {(r["unit"], norm(r["text"])) for r in rows}


def draw_holdout(name: str) -> dict:
    """Draw a hold-out round as specified in HOLDOUTS (refuses to overwrite a labelled round)."""
    h = holdout_round(name)
    if h["gold"].exists():
        raise SystemExit(f"hold-out {name} is already labelled ({h['gold'].name}); draw a new round instead")
    return draw(h["strata"], h["seed"], h["sample"], h["prefix"])


def draw(strata: dict | None = None, seed: int = SEED, out=None, prefix: str = "") -> dict:
    """Draw a stratified sample, excluding everything already drawn (tuning set and every hold-out)."""
    strata, out = strata or STRATA, out or SAMPLE
    rng = random.Random(seed)
    labelled = _already_drawn()
    labelled -= {(r["unit"], norm(r["text"])) for r in read_sample(out)}  # redrawing the same file
    pools = candidates()
    rows = []
    for stratum, n in strata.items():
        pool = [c for c in pools[stratum] if (c["unit"], c["text"]) not in labelled]
        seen, picked = set(), []
        for c in rng.sample(pool, len(pool)):
            key = (c["unit"], c["text"])
            if key not in seen:
                seen.add(key)
                picked.append(c)
            if len(picked) == n:
                break
        for i, c in enumerate(picked, 1):
            rows.append({"sid": f"{prefix}{stratum}-{i:03d}", "stratum": stratum, **c})
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return {s: sum(1 for r in rows if r["stratum"] == s) for s in strata}


def read_gold(path=None) -> list[dict]:
    path = path or GOLD
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()[1:] if x.strip()]


FOREIGN_LANGS = FOREIGN_LABELS


def _is_foreign_el(e) -> bool:
    return isinstance(e.tag, str) and (e.get("ana") == "foreign" or (e.tag == T("foreign") and e.get(XML_LANG)) or
                                       (e.get(XML_LANG) or "en") in FOREIGN_LANGS)


def _foreign_ancestor(e, stop) -> bool:
    x = e
    while x is not None:
        if _is_foreign_el(x):
            return True
        if x is stop:
            return False
        x = x.getparent()
    return False


def _words(s: str) -> list[str]:
    # "&c" is "etc.", not a word of the passage: a detected passage that runs on to "&c" still covers a target
    # that stops before it (2026-11-18: "quaedam credenda, quaedam admiranda, &c" was scored as a miss)
    return re.findall(r"[^\W\d_]+", re.sub(r"&\s*c\b\.?", " ", norm(s)).lower())


def _contains_words(hay: str, needle: str) -> bool:
    """Word-boundary containment (so 'lib' is not found inside 'libenter')."""
    h, n = _words(hay), _words(needle)
    if not n:
        return False
    return any(h[k:k + len(n)] == n for k in range(len(h) - len(n) + 1))


class UnitIndex:
    """The detector's output for one unit, organised by block, read from the XML."""

    def __init__(self, unit: str):
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        self.div = root.find(f".//{T('div')}")
        self.blocks = []
        for block in self.div.iter(T("p"), T("l"), T("note")):
            if _gowlandish(block):
                continue
            ctx = text_no_notes(block) if block.tag != T("note") else norm("".join(block.itertext()))
            foreign = [text_no_notes(e) for e in block.iter() if e is not block and _is_foreign_el(e)]
            if _foreign_ancestor(block, None) and block.tag != T("note"):
                foreign.append(text_no_notes(block))
            self.blocks.append((block, ctx, foreign))

    def by_context(self, context: str):
        c = norm(context)[:600]
        return [b for b in self.blocks if b[1][:600] == c] or [b for b in self.blocks if c and c[:200] in b[1]]

    def italic_tagged(self, block, text: str) -> bool | None:
        """Is the italic element with this text in this block tagged foreign? None if not found."""
        found = None
        for h in block.iter(T("hi")):
            if h.get("rend") == "i" and text_no_notes(h) == norm(text):
                tagged = _foreign_ancestor(h, block if block.tag == T("note") else None) or any(_is_foreign_el(d) and
                                                          len(text_no_notes(d)) >= 0.6 * len(norm(text))
                                                          for d in h.iter() if d is not h)
                found = bool(found) or tagged
        return found


def evaluate(units: list[str] | None = None, *, holdout: bool | str = False) -> dict:
    """Score the detector on the tuning sample (default), on a named hold-out round, or (True) on the
    gate round, the newest hold-out (never seen while tuning)."""
    name = (GATE if holdout is True else holdout) or "tuning"
    if holdout:
        h = holdout_round(name)
        gold_path, sample_path = h["gold"], h["sample"]
    else:
        gold_path, sample_path = GOLD, SAMPLE
    rows = read_gold(gold_path)
    if units is not None:
        rows = [r for r in rows if r["unit"] in units]
    sample = {r["sid"]: r for r in read_sample(sample_path)}
    idx: dict[str, UnitIndex] = {}
    tally: dict[str, dict] = {}
    misses, unlocated, inexact = [], [], []
    for r in rows:
        ui = idx.setdefault(r["unit"], UnitIndex(r["unit"]))
        stratum = r.get("stratum", "m1")
        t = tally.setdefault(stratum, {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "boundary_ok": 0})
        part = r.get("foreign_part")
        positive = r["gold"] in FOREIGN_LABELS or bool(part)
        target = part or r["text"]
        ctx = (sample.get(r.get("sid"), {}) or {}).get("context", "")
        blocks = ui.by_context(ctx) if ctx else [b for b in ui.blocks if _contains_words(b[1], r["text"])]
        if not blocks:
            unlocated.append(r.get("sid") or r["text"][:40])
            continue
        detected = False
        exact = False
        for block, _btext, foreign in blocks:
            # an italic item is judged as a whole, unless only part of it is foreign ("…Cooks are
            # Gentlemen: Venter Deus"): then, as elsewhere, by the foreign passages covering that part
            if r.get("kind") in (None, "phrase", "term", "verse") and stratum in ("italic", "sidenote") \
                    and not part:
                tagged = ui.italic_tagged(block, r["text"])
                if tagged is None:
                    continue
                detected |= tagged
                exact |= tagged
            elif positive:
                # detected if the block's foreign passages cover >= 75 % of the target's words
                # (a note or an attribution may split or extend the Latin); exactness is measured apart.
                # A label of separate stretches joined by "|" is measured stretch by stretch: exact only if
                # every stretch is a passage of its own (2026-11-19, settled before round h5 was drawn)
                n_words = n_covered = 0
                bx = True
                for piece in (x for x in target.split("|") if _words(x)):
                    tw = _words(piece)
                    covered = [False] * len(tw)
                    piece_exact = False
                    for f in foreign:
                        fw = _words(f)
                        if fw and _contains_words(f, piece):
                            covered = [True] * len(tw)
                            piece_exact |= norm(f).strip(" ,.;:—&c") == norm(piece).strip(" ,.;:—&c")
                            continue
                        for k in range(len(tw) - len(fw) + 1):
                            if fw and tw[k:k + len(fw)] == fw:
                                covered[k:k + len(fw)] = [True] * len(fw)
                    n_words += len(tw)
                    n_covered += sum(covered)
                    bx &= piece_exact
                if n_words and n_covered >= 0.75 * n_words:
                    detected = True
                    exact |= bx
            else:
                detected |= any(_contains_words(r["text"], f) for f in foreign if _words(f))
        if positive:
            if detected:
                t["tp"] += 1
                t["boundary_ok"] += exact
                if not exact:
                    inexact.append(f"boundary {r['gold']}: {target[:60]!r} ({r.get('sid') or r['unit']})")
            else:
                t["fn"] += 1
                where = r.get("sid") or r["unit"]
                misses.append(f"missed {r['gold']} {r.get('kind') or ''}: {target[:60]!r} ({where})")
        else:
            if detected:
                t["fp"] += 1
                misses.append(f"false foreign [{r['gold']}]: {r['text'][:60]!r} ({r.get('sid') or r['unit']})")
            else:
                t["tn"] += 1
    total = {k: sum(t[k] for t in tally.values()) for k in ("tp", "fp", "fn", "tn", "boundary_ok")}
    for t in tally.values():
        t.update(_rates(t))
    return {"sample": name, "labelled": gold_path.exists(), "items": len(rows), "unlocated": len(unlocated),
            **total, **_rates(total), "by_stratum": tally, "misses": misses, "inexact": inexact,
            "unlocated_items": unlocated}


def _rates(t: dict) -> dict:
    """Precision, recall and boundary exact-match (None where undefined: no positives or detections)."""
    def ratio(a, b):
        return round(a / b, 3) if b else None
    return {"precision": ratio(t["tp"], t["tp"] + t["fp"]), "recall": ratio(t["tp"], t["tp"] + t["fn"]),
            "boundary_exact": ratio(t["boundary_ok"], t["tp"])}


def summary(r: dict) -> str:
    return (f"P={r['precision']} R={r['recall']} B={r['boundary_exact']} n={r['items']} "
            f"tp={r['tp']} fp={r['fp']} fn={r['fn']}")
