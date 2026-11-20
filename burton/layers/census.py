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
import time
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

    # a verse line inherits its group's passage; a sidenote is Burton's own matter, read on its own even inside a
    # Latin passage (the ingest tags notes separately: langid.tag_latin)
    walk(b, _foreign_el(b) or (b.tag != T("note") and any(_foreign_el(a) for a in b.iterancestors())))
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


def raw_index(b) -> list[int]:
    """For each character of block_text(b), its offset in the block's counted text before whitespace is collapsed
    (the offsets census_apply works in)."""
    raw: list[str] = []

    def walk(x):
        if x is not b and (x.tag in BLOCKS or _skip(x)):
            return
        raw.extend(x.text or "")
        for c in x:
            if isinstance(c.tag, str):
                walk(c)
            raw.extend(c.tail or "")

    walk(b)
    out, space, started = [], False, False
    for i, c in enumerate(raw):
        if c.isspace():
            space = started
            continue
        if space:
            out.append(i - 1)  # the collapsed space stands for the whitespace just before this character
            space = False
        out.append(i)
        started = True
    return out


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


def _call(model: str, sys_prompt: str, user: str, out_schema: dict, meta: dict) -> dict:
    """One call; at the plan's usage limit it waits (runner.LIMIT_POLL) and tries again, and a transient failure is
    retried twice. Each wait is ledgered."""
    tries = 0
    while True:
        res = runner.call_claude(model, sys_prompt, user, out_schema)
        if res["ok"]:
            return res
        if res.get("limit"):
            runner.append(LEDGER, {**meta, "ts": runner.now(), "status": "waiting on the usage limit",
                                   "error": str(res.get("error"))[:300]})
            print(f"  usage limit: waiting {runner.LIMIT_POLL // 60} min", flush=True)
            time.sleep(runner.LIMIT_POLL)
            continue
        tries += 1
        if res.get("transient") and tries <= 2:
            time.sleep(runner.TRANSIENT_WAITS[tries - 1])
            continue
        return res


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
        res = _call(model, sys_prompt, user, D2_SCHEMA, meta)
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
        # many short blocks (Burton's Table) in one packet: the model drops some, so cap the count too
        if (n >= words_per_packet or len(pk) >= 60) and not flush():
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
        res = _call(model, sys_prompt, user, JUDGE_SCHEMA, meta)
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


# ---- the rulings layer, and a snapshot of the edition before they are applied

SNAPSHOT = DIR / "snapshot.jsonl"


def snapshot(unit_list: list[str]) -> dict:
    """The comparison as it stands before any ruling is applied (the estimate is measured against it). Written once:
    it is refused if one exists, so a later run cannot overwrite the 'before'."""
    if SNAPSHOT.exists():
        raise SystemExit(f"{SNAPSHOT} exists: the edition before the rulings is already recorded")
    cmp = compare(unit_list)
    rows = [{"id": c["id"], "unit": c["unit"], "text": c["text"], "words": c["words"], "t1": c["t1"], "t2": c["t2"]}
            for c in cmp]
    atomic_write_text(SNAPSHOT, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return {"blocks": len(rows), "words": sum(len(r["words"]) for r in rows)}


def read_snapshot() -> list[dict]:
    return [json.loads(x) for x in SNAPSHOT.read_text(encoding="utf-8").splitlines()]


def rulings() -> dict:
    """data/layers/langid-census.json: the judge's answers on the disagreements, located by block text."""
    from ..ingest import census_apply

    judged = _read(JUDGE_OUT)
    snap = read_snapshot()
    nth: dict[tuple, int] = {}
    pos: dict[str, tuple] = {}
    for c in snap:  # occurrence of the same block text within its unit, in document order
        k = (c["unit"], census_apply.sha(c["text"]))
        pos[c["id"]] = (k[1], nth.get(k, 0))
        nth[k] = nth.get(k, 0) + 1
    by_id = {c["id"]: c for c in snap}
    current = {s["id"] for c in snap for which in ("1", "2") for s in stretches(c, which)}
    layer, kinds = {}, {"1": 0, "2": 0}
    for i, r in judged.items():
        if r["kind"] not in ("1", "2") or i not in current:
            continue  # judged against another comparison: not a ruling on this one
        first, last = (int(x) for x in i.rsplit(":", 1)[1].split("-"))
        c = by_id[r["block"]]
        if last >= len(c["words"]) or c["text"][c["words"][first][0]:c["words"][last][1]] != r["text"]:
            continue  # judged against another comparison (stale): not a ruling on this one
        foreign = bool(r["foreign_part"])
        if (r["kind"] == "2" and not foreign) or (r["kind"] == "1" and foreign and
                                                    all(_judged_words(r, last - first + 1))):
            continue  # the judge sides with the edition: nothing to change
        sha_, n = pos[r["block"]]
        layer[i] = {"unit": r["unit"], "block": r["block"], "block_sha": sha_, "nth": n, "kind": r["kind"],
                    "first": first, "last": last, "text": r["text"], "foreign_part": r["foreign_part"],
                    "lang": r["lang"], "confidence": r["confidence"], "reason": r["reason"], "by": "machine",
                    "model": r["model"], "prompt": r["prompt"], "date": r["date"], "id": i}
        kinds[r["kind"]] += 1
    census_apply.LAYER.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(census_apply.LAYER, json.dumps(layer, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {"rulings": len(layer), "tag": kinds["2"], "narrow": kinds["1"],
            "low (not applied)": sum(1 for v in layer.values() if v["confidence"] == "low")}


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


def _now_rows(snap: list[dict], judged: dict) -> list[dict]:
    """Per block, counts for the edition as it stands now, against the truth recorded before the rulings: the judge's
    words where the detectors disagreed, the agreed sample's rate where they agreed, capture-recapture where neither
    tagged. A doubtful word counts against the edition; a word tagged now that neither detector tagged is counted
    wrong (it has no ruling)."""
    cur = {}
    for u in sorted({c["unit"] for c in snap}):
        for b in blocks(u):
            cur[b["id"]] = b
    rows = []
    for c in snap:
        b = cur.get(c["id"])
        r = {"tagged": 0, "tagged_dis_true": 0, "tagged_dis_wrong": 0, "tagged_both": 0, "tagged_none": 0,
             "dis_true": 0, "unsure_untagged": 0, "both": 0, "both_judged": 0, "both_true": 0, "only1_true": 0,
             "only2_true": 0, "changed": 0}
        if b is None or b["text"] != c["text"]:
            r["changed"] = 1
            rows.append(r)
            continue
        now = [b["mask"][s:e].count(1) * 2 > e - s for s, e in c["words"]]
        truth: list = [None] * len(c["words"])
        cc = {**c, "t1": c["t1"], "t2": c["t2"]}
        for which in ("1", "2", "both"):
            for s in stretches(cc, which):
                rec = judged.get(s["id"])
                n = s["last"] - s["first"] + 1
                if which == "both":
                    r["both"] += n
                    if rec and rec["text"] == s["text"]:
                        r["both_judged"] += n
                        r["both_true"] += sum(1 for t in _judged_words(rec, n) if t is not False)
                    for k in range(s["first"], s["last"] + 1):
                        truth[k] = "both"
                    continue
                t = _judged_words(rec, n) if rec and rec["text"] == s["text"] else [None] * n
                for k, v in zip(range(s["first"], s["last"] + 1), t, strict=False):
                    truth[k] = v
                    if v:
                        r["only1_true" if which == "1" else "only2_true"] += 1
        for k, tag in enumerate(now):
            v = truth[k]
            if v is True:
                r["dis_true"] += 1
            if tag:
                r["tagged"] += 1
                if v == "both":
                    r["tagged_both"] += 1
                elif v is True:
                    r["tagged_dis_true"] += 1
                elif v is None and not (c["t1"][k] or c["t2"][k]):
                    r["tagged_none"] += 1
                else:
                    r["tagged_dis_wrong"] += 1
            elif v is None and (c["t1"][k] or c["t2"][k]):
                r["unsure_untagged"] += 1
        rows.append(r)
    return rows


def _now_estimate(rows: list[dict]) -> dict:
    t = {k: sum(r[k] for r in rows) for k in rows[0]}
    if not t["both_judged"] or not t["tagged"]:
        return {"totals": t}
    p = t["both_true"] / t["both_judged"]
    m = t["both"] * p
    n1, n2 = m + t["only1_true"], m + t["only2_true"]
    missed_both = max(0.0, (n1 + 1) * (n2 + 1) / (m + 1) - 1 - (n1 + n2 - m))
    right = t["tagged_dis_true"] + t["tagged_both"] * p
    foreign = t["dis_true"] + t["both"] * p + t["unsure_untagged"] + missed_both
    return {"totals": t, "p_agreed": round(p, 4), "missed_by_both": round(missed_both, 1),
            "precision": round(right / t["tagged"], 4), "recall": round(right / foreign, 4) if foreign else None}


def final_report(resamples: int = 2000) -> dict:
    """V5's gate (CENSUS.md): the edition as it stands now, with 90% bootstrap lower bounds over blocks."""
    snap = read_snapshot()
    rows = _now_rows(snap, _read(JUDGE_OUT))
    est = _now_estimate(rows)
    rng = random.Random(AGREED_SEED)
    ps, rs = [], []
    for _ in range(resamples):
        e = _now_estimate([rows[rng.randrange(len(rows))] for _ in rows])
        if e.get("precision") is not None:
            ps.append(e["precision"])
            rs.append(e["recall"])
    ps.sort()
    rs.sort()
    lo = int(0.05 * len(ps))
    est.update({"precision_90_lower": ps[lo] if ps else None, "recall_90_lower": rs[lo] if rs else None,
                "blocks": len(rows), "words": sum(len(c["words"]) for c in snap),
                "blocks_changed_since": est["totals"]["changed"],
                "passes": bool(ps and rs and ps[lo] >= 0.98 and rs[lo] >= 0.97)})
    atomic_write_text(DIR / "report.json", json.dumps(est, indent=1, sort_keys=True) + "\n")
    return est


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
