"""`burton census`: V5 by census (data/eval/CENSUS.md, decision D13).

The method:
1. Each block's text is Burton's own, with Gowland's matter left out, together with the edition's tags (detector 1)
   as a character mask.
2. Detector 2 (`claude-sonnet-5-5`, prompt census-v1) marks the foreign stretches of the same text blind.
3. Every stretch where the two disagree, word by word, goes to a blind judge (`claude-opus-5-5`, prompt judge-v1).
4. A random sample of the stretches both tag is judged as well, to estimate the false positives they share.
5. `report` estimates word precision and recall, capture-recapture for the words both miss, and bootstrap bounds.

Every call is ledgered and resumable (state/census/). Nothing of Gowland's is sent: his elements are left out, and a
packet that still contains one of his strings is refused.
"""

import json
import random
import re
from datetime import UTC, datetime

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..tei import ED, XML_ID, XML_LANG, T
from ..textview import is_gowland
from ..translate import packets, runner
from . import gold_audit

D2_PROMPT, JUDGE_PROMPT = "census-v1", "judge-v1"
D2_MODEL, JUDGE_MODEL = "claude-sonnet-5-5", "claude-opus-5-5"
DIR = paths.STATE / "census"
LEDGER = DIR / "ledger.jsonl"
D2_OUT, JUDGE_OUT = DIR / "detector2.jsonl", DIR / "judge.jsonl"
FOREIGN = {"la", "grc", "it", "fr", "es", "de", "nl", "enm", "he"}
LANGS = sorted(FOREIGN)
AGREED_SEED, AGREED_N = 20261123, 300
WORD = re.compile(r"[^\W\d_]+")
ETC = re.compile(r"&\s*c\b\.?")
BLOCKS = (T("p"), T("l"), T("note"))

D2_SCHEMA = {"type": "object", "required": ["blocks"], "additionalProperties": False, "properties": {
    "blocks": {"type": "array", "items": {
        "type": "object", "required": ["id", "spans"], "additionalProperties": False,
        "properties": {"id": {"type": "string"}, "spans": {"type": "array", "items": {
            "type": "object", "required": ["text", "lang"], "additionalProperties": False,
            "properties": {"text": {"type": "string"}, "lang": {"type": "string", "enum": LANGS}}}}}}}}}
JUDGE_SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "foreign_part", "lang", "confidence", "reason"],
        "properties": {"id": {"type": "string"}, "foreign_part": {"type": ["string", "null"]},
                       "lang": {"type": ["string", "null"], "enum": [*LANGS, None]},
                       "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                       "reason": {"type": "string"}}}}}}


# ---- block texts with the edition's tags as a mask

def _skip(x) -> bool:
    """Gowland's matter (every ed:* element, his supplied text, page breaks), a corrected reading's sic, and our own
    transcriptions of heading images."""
    return is_gowland(x) or x.get("facs") is not None or \
        (x.tag == T("sic") and x.getparent() is not None and x.getparent().tag == T("choice"))


def _foreign_el(x) -> bool:
    return x.get("ana") == "foreign" or (x.tag == T("foreign") and (x.get(XML_LANG) or "").split("-")[0] in FOREIGN)


def block_text(b) -> tuple[str, list[bool]]:
    """Burton's text of a block (other blocks inside it and Gowland's matter left out), whitespace collapsed, with a
    per-character flag: inside one of the edition's foreign passages."""
    chars: list[tuple[str, bool]] = []

    def walk(x, inside: bool):
        if x is not b and (x.tag in BLOCKS or _skip(x)):
            return
        inside = inside or _foreign_el(x)
        chars.extend((c, inside) for c in (x.text or ""))
        for c in x:
            if isinstance(c.tag, str):
                walk(c, inside)
            chars.extend((ch, inside) for ch in (c.tail or ""))

    walk(b, _foreign_el(b) or any(_foreign_el(a) for a in b.iterancestors()))
    # Chaucer (enm) is known from the source's own markup (span.lucida), not detected: left out of the count
    chaucer = [False] * len(chars)
    k = 0

    def mark(x, inside: bool):
        nonlocal k
        if x is not b and (x.tag in BLOCKS or _skip(x)):
            return
        inside = inside or (x.tag == T("foreign") and (x.get(XML_LANG) or "").startswith("enm"))
        for _ in x.text or "":
            chaucer[k] = inside
            k += 1
        for c in x:
            if isinstance(c.tag, str):
                mark(c, inside)
            for _ in c.tail or "":
                chaucer[k] = inside
                k += 1

    mark(b, any(a.tag == T("foreign") and (a.get(XML_LANG) or "").startswith("enm") for a in b.iterancestors()))
    chars = [(c, 2 if ch else int(f)) for (c, f), ch in zip(chars, chaucer, strict=True)]
    text, mask, space = [], [], False
    for c, f in chars:
        if c.isspace():
            space = bool(text)
            continue
        if space:
            text.append(" ")
            mask.append(f and bool(mask) and mask[-1])
            space = False
        text.append(c)
        mask.append(f)
    return "".join(text), mask


def _block_id(b) -> str:
    """The block's xml:id, or (verse lines have none) the nearest ancestor's id with the line's number in it."""
    if b.get(XML_ID):
        return b.get(XML_ID)
    anc = next((a for a in b.iterancestors() if a.get(XML_ID)), b.getroottree().getroot())
    k = next(i for i, x in enumerate(anc.iter(b.tag)) if x is b)
    return f"{anc.get(XML_ID) or 'root'}~{etree.QName(b).localname}{k}"


def units() -> list[str]:
    return sorted(p.stem for p in paths.TEXT.glob("*.xml") if "gowland" not in p.stem)


def blocks(unit: str) -> list[dict]:
    root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
    out = []
    body = root.find(T("text"))  # not the header ("Generated by burton ingest")
    for b in (body.iter(*BLOCKS) if body is not None else []):
        if any(a.tag in (ED("trans"), ED("verse-trans"), ED("block")) for a in [b, *b.iterancestors()]):
            continue
        text, mask = block_text(b)
        if WORD.search(text):
            out.append({"id": _block_id(b), "unit": unit, "text": text, "mask": mask})
    return out


def words(text: str) -> list[tuple[int, int]]:
    """Word spans; "&c" is not a word."""
    blank = ETC.sub(lambda m: " " * len(m.group(0)), text)
    return [(m.start(), m.end()) for m in WORD.finditer(blank)]


# ---- detector 2

def _read(path) -> dict:
    if not path.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


def _write(path, done: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, "".join(json.dumps(done[k], ensure_ascii=False, sort_keys=True) + "\n"
                                    for k in sorted(done)))


def place(text: str, spans: list[dict]) -> tuple[list[tuple[int, int, str]], int]:
    """Find each span in the block, in order (whitespace-insensitive). Returns the placed (start, end, lang) and the
    number not found."""
    out, pos, lost = [], 0, 0
    for s in spans:
        pat = r"\s*".join(re.escape(w) for w in s["text"].split())
        if not pat:
            continue
        m = re.compile(pat).search(text, pos) or re.compile(pat).search(text)
        if not m:
            lost += 1
            continue
        out.append((m.start(), m.end(), s["lang"]))
        pos = m.end()
    return out, lost


def detect(unit_list: list[str], *, model: str = D2_MODEL, words_per_packet: int = 1500,
           budget: float | None = None) -> dict:
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{D2_PROMPT}.md").read_text(encoding="utf-8")
    done = _read(D2_OUT)
    todo = [b for u in unit_list for b in blocks(u) if b["id"] not in done or done[b["id"]]["text"] != b["text"]]
    pk, n, spent, calls = [], 0, 0.0, 0

    def flush():
        nonlocal pk, n, spent, calls
        if not pk:
            return True
        bad = [(b["id"], g) for b in pk for g in gold_audit.leaks(b["unit"], b["text"])]
        if bad:
            raise SystemExit(f"packet refused: Gowland text in {bad[:3]}")
        send = [{"id": b["id"], "text": b["text"]} for b in pk]
        user = "Mark the foreign stretches of these blocks.\n\n" + json.dumps({"blocks": send}, ensure_ascii=False)
        meta = {"role": "detector2", "ids": [b["id"] for b in pk], "model": model, "prompt": D2_PROMPT,
                "input_hash": packets.input_hash({"blocks": send}, D2_PROMPT, model, 0)}
        res = runner.call_claude(model, sys_prompt, user, D2_SCHEMA)
        status = "done" if res["ok"] else ("deferred" if res.get("limit") else "failed")
        runner.append(LEDGER, {**meta, "ts": runner.now(), "status": status,
                               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}})
        if not res["ok"]:
            print(f"  call {status}: {str(res.get('error'))[:200]} (re-run to resume)")
            return False
        spent += res.get("cost_usd_list") or 0
        calls += 1
        got = {g["id"]: g["spans"] for g in res["output"]["blocks"]}
        date = datetime.now(UTC).date().isoformat()
        for b in pk:
            if b["id"] in got:
                done[b["id"]] = {"id": b["id"], "unit": b["unit"], "text": b["text"], "spans": got[b["id"]],
                                 "by": "machine", "model": model, "prompt": D2_PROMPT, "date": date}
        _write(D2_OUT, done)
        print(f"  packet {calls}: {len(pk)} blocks, {n} words (${spent:.2f} so far)", flush=True)
        pk, n = [], 0
        return budget is None or spent < budget

    for b in todo:
        pk.append(b)
        n += len(words(b["text"]))
        if n >= words_per_packet and not flush():
            break
    else:
        flush()
    return {"blocks": len(todo), "calls": calls, "cost_usd_list": round(spent, 2)}


# ---- comparison and the judge

def compare(unit_list: list[str]) -> list[dict]:
    """Per block: each word's tags by detector 1 (the edition) and detector 2."""
    d2 = _read(D2_OUT)
    out = []
    for u in unit_list:
        for b in blocks(u):
            r = d2.get(b["id"])
            if not r or r["text"] != b["text"]:
                continue
            spans, lost = place(b["text"], r["spans"])
            ws = [(s, e) for s, e in words(b["text"]) if b["mask"][s:e].count(2) * 2 <= e - s]  # Chaucer left out
            t1 = [b["mask"][s:e].count(1) * 2 > e - s for s, e in ws]
            t2 = [any(s < se and ss < e for ss, se, _ in spans) for s, e in ws]
            out.append({**b, "words": ws, "t1": t1, "t2": t2, "lost": lost})
    return out


def stretches(c: dict, which: str) -> list[dict]:
    """Maximal runs of consecutive words: `which` = "1" (detector 1 only), "2" (detector 2 only) or "both"."""
    want = {"1": (True, False), "2": (False, True), "both": (True, True)}[which]
    out, cur = [], None
    for k, pair in enumerate(zip(c["t1"], c["t2"], strict=True)):
        if pair == want:
            cur = [k, k] if cur is None else [cur[0], k]
        elif cur is not None:
            out.append(cur)
            cur = None
    if cur is not None:
        out.append(cur)
    res = []
    for a, z in out:
        s, e = c["words"][a][0], c["words"][z][1]
        res.append({"id": f"{c['id']}:{which}:{a}-{z}", "block": c["id"], "unit": c["unit"], "kind": which,
                    "first": a, "last": z, "text": c["text"][s:e],
                    "context": c["text"][max(0, s - 400): e + 300]})
    return res


def judge_items(cmp: list[dict]) -> list[dict]:
    items = [s for c in cmp for which in ("1", "2") for s in stretches(c, which)]
    agreed = [s for c in cmp for s in stretches(c, "both")]
    rng = random.Random(AGREED_SEED)
    items += rng.sample(agreed, min(AGREED_N, len(agreed)))
    return items


def judge(unit_list: list[str], *, model: str = JUDGE_MODEL, packet_size: int = 30, budget: float | None = None,
          agreed_n: int | None = None) -> dict:
    global AGREED_N
    if agreed_n is not None:
        AGREED_N = agreed_n
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{JUDGE_PROMPT}.md").read_text(encoding="utf-8")
    done = _read(JUDGE_OUT)
    todo = [i for i in judge_items(compare(unit_list)) if i["id"] not in done or done[i["id"]]["text"] != i["text"]]
    spent, calls = 0.0, 0
    for k in range(0, len(todo), packet_size):
        pk = todo[k:k + packet_size]
        bad = [(i["id"], g) for i in pk for g in gold_audit.leaks(i["unit"], i["context"])]
        if bad:
            raise SystemExit(f"packet refused: Gowland text in {bad[:3]}")
        send = [{"id": i["id"].replace(":1:", ":x:").replace(":2:", ":x:").replace(":both:", ":x:"),
                 "stretch": i["text"], "context": i["context"]} for i in pk]  # blind: the id does not say who marked it
        ids = {s["id"]: i for s, i in zip(send, pk, strict=True)}
        user = "Judge these stretches.\n\n" + json.dumps({"items": send}, ensure_ascii=False, indent=1)
        meta = {"role": "judge", "ids": [i["id"] for i in pk], "model": model, "prompt": JUDGE_PROMPT,
                "input_hash": packets.input_hash({"items": send}, JUDGE_PROMPT, model, 0)}
        res = runner.call_claude(model, sys_prompt, user, JUDGE_SCHEMA)
        status = "done" if res["ok"] else ("deferred" if res.get("limit") else "failed")
        runner.append(LEDGER, {**meta, "ts": runner.now(), "status": status,
                               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}})
        if not res["ok"]:
            print(f"  call {status}: {str(res.get('error'))[:200]} (re-run to resume)")
            break
        spent += res.get("cost_usd_list") or 0
        calls += 1
        date = datetime.now(UTC).date().isoformat()
        for g in res["output"]["items"]:
            i = ids.get(g["id"])
            if i:
                done[i["id"]] = {"id": i["id"], "block": i["block"], "unit": i["unit"], "kind": i["kind"],
                                 "text": i["text"], "foreign_part": g["foreign_part"], "lang": g["lang"],
                                 "confidence": g["confidence"], "reason": g["reason"], "by": "machine",
                                 "model": model, "prompt": JUDGE_PROMPT, "date": date}
        _write(JUDGE_OUT, done)
        print(f"  packet {calls}: {len(pk)} stretches (${spent:.2f} so far)", flush=True)
        if budget is not None and spent >= budget:
            break
    return {"stretches": len(todo), "calls": calls, "cost_usd_list": round(spent, 2)}


# ---- the estimate

def _judged_words(rec: dict, n_words: int) -> list[bool | None]:
    """Per word of a judged stretch: foreign by the judge (None if the judge was unsure)."""
    if rec["confidence"] == "low":
        return [None] * n_words
    ws = WORD.findall(ETC.sub(" ", rec["text"]))
    if not rec["foreign_part"]:
        return [False] * len(ws)
    fw = [w for piece in rec["foreign_part"].split("|") for w in WORD.findall(ETC.sub(" ", piece))]
    out, j = [], 0
    for w in ws:  # in order: the judge's words are a subsequence of the stretch
        if j < len(fw) and w == fw[j]:
            out.append(True)
            j += 1
        else:
            out.append(False)
    return out


def tally(cmp: list[dict], judged: dict) -> list[dict]:
    """Per block, the word counts the estimate needs."""
    rows = []
    for c in cmp:
        r = {"both": 0, "both_judged": 0, "both_true": 0, "only1": 0, "only1_true": 0, "only2": 0, "only2_true": 0,
             "unsure_tagged": 0, "unsure_untagged": 0, "unjudged": 0}
        for which in ("1", "2", "both"):
            for s in stretches(c, which):
                n = s["last"] - s["first"] + 1
                rec = judged.get(s["id"])
                key = {"1": "only1", "2": "only2", "both": "both"}[which]
                r[key] += n
                if rec is None or rec["text"] != s["text"]:
                    if which != "both":
                        r["unjudged"] += n
                    continue
                truth = _judged_words(rec, n)
                if len(truth) != n:
                    truth = (truth + [False] * n)[:n]
                if which == "both":
                    r["both_judged"] += n
                    r["both_true"] += sum(1 for t in truth if t is not False)  # unsure counts as true here
                    continue
                r[key + "_true"] += sum(1 for t in truth if t)
                unsure = sum(1 for t in truth if t is None)
                # CENSUS.md: a doubtful word counts against the edition (missed if left untagged, wrong if tagged);
                # after the fixes detector 1's stretches stay tagged, detector 2's are not taken
                r["unsure_tagged" if which == "1" else "unsure_untagged"] += unsure
        rows.append(r)
    return rows


def estimate(rows: list[dict]) -> dict:
    t = {k: sum(r[k] for r in rows) for k in rows[0]} if rows else {}
    if not t or not t["both_judged"]:
        return {"totals": t}
    p_both = t["both_true"] / t["both_judged"]
    m = t["both"] * p_both
    n1 = m + t["only1_true"]
    n2 = m + t["only2_true"]
    chapman = (n1 + 1) * (n2 + 1) / (m + 1) - 1
    found = n1 + n2 - m
    missed_both = max(0.0, chapman - found)
    # the edition after the fixes: both + judged-true of either; wrong = shared false + doubtful words it keeps
    tagged = t["both"] + t["only1_true"] + t["only2_true"] + t["unsure_tagged"]
    wrong = t["both"] * (1 - p_both) + t["unsure_tagged"]
    missed = missed_both + t["unsure_untagged"]
    return {"totals": t, "p_agreed": round(p_both, 4), "n1": round(n1), "n2": round(n2), "m": round(m),
            "foreign_estimate": round(chapman + t["unsure_untagged"]), "missed_by_both": round(missed_both, 1),
            "precision": round(1 - wrong / tagged, 4) if tagged else None,
            "recall": round(found / (found + missed), 4) if found + missed else None,
            "edition_now": {"precision": round(1 - (t["both"] * (1 - p_both) + t["only1"] - t["only1_true"]) /
                                               (t["both"] + t["only1"]), 4) if t["both"] + t["only1"] else None,
                            "recall": round(n1 / (found + missed), 4) if found + missed else None}}


def report(unit_list: list[str], resamples: int = 2000) -> dict:
    cmp = compare(unit_list)
    judged = _read(JUDGE_OUT)
    rows = tally(cmp, judged)
    est = estimate(rows)
    rng = random.Random(AGREED_SEED)
    ps, rs = [], []
    for _ in range(resamples):
        e = estimate([rows[rng.randrange(len(rows))] for _ in rows])
        if e.get("precision") is not None:
            ps.append(e["precision"])
            rs.append(e["recall"])
    ps.sort()
    rs.sort()
    lo = int(0.05 * len(ps))
    est["precision_90_lower"] = ps[lo] if ps else None
    est["recall_90_lower"] = rs[lo] if rs else None
    est["blocks"] = len(cmp)
    est["words"] = sum(len(c["words"]) for c in cmp)
    est["d2_spans_not_found"] = sum(c["lost"] for c in cmp)
    return est
