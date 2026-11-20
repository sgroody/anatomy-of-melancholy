"""Apply the census judge's rulings to the edition at ingest (V5 by census, data/eval/CENSUS.md, D13).

The rulings are a machine layer, data/layers/langid-census.json, built by `burton census --rulings` from the judge's
answers. Each ruling is keyed by the stretch it judged and located again by its block's text, so it does not depend
on xml:ids, which are assigned after language-ID. Two kinds:
- a stretch only detector 2 tagged, which the judge found foreign: its foreign part becomes a passage (resp="#model");
- a stretch only the edition tagged, which the judge found not foreign (or only partly foreign): the passage it lies in
  is narrowed to what remains foreign, or removed.
Markup only: the text is never changed. A block where a ruling cannot be placed cleanly is restored as it was, and the
decision says why. A doubtful (low) ruling is never applied. Passages holding Greek or Hebrew script, Chaucer and the
owner's own decisions (resp="#editor") are never narrowed.
"""

import copy
import functools
import hashlib
import json

import regex as re

from .. import paths
from ..tei import ED, XML_LANG, T, el, put_items, take_items

LAYER = paths.LAYERS / "langid-census.json"
BLOCK_TAGS = (T("p"), T("l"), T("note"))
SPLITTABLE = (T("hi"), T("quote"), T("q"))
SCRIPT = re.compile(r"[\p{Script=Greek}\p{Script=Hebrew}]")


class NotPlaced(Exception):
    pass


@functools.cache
def _layer() -> dict:
    return json.loads(LAYER.read_text(encoding="utf-8")) if LAYER.exists() else {}


def sha(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def _census():
    from ..layers import census  # the census reads data/text only through these helpers; no model call here

    return census


def inner_len(x, top) -> int:
    c = _census()
    if not isinstance(x.tag, str) or (x is not top and (x.tag in BLOCK_TAGS or c._skip(x))):
        return 0
    return len(x.text or "") + sum(inner_len(k, top) + len(k.tail or "") for k in x)


def _len(it, top) -> int:
    return len(it) if isinstance(it, str) else inner_len(it, top)


def split_el(x, off: int, top):
    """Split an inline element at an inner offset (0 < off < its length); x keeps the left part, the right part is
    returned as a copy of x (same tag and attributes). Only italics and quotations without an id may be split."""
    if x.tag not in SPLITTABLE or x.get("{http://www.w3.org/XML/1998/namespace}id") or x.get("ana") == "foreign":
        raise NotPlaced(f"would split <{x.tag.split('}')[1]}>")
    items = take_items(x)
    pos, left, right = 0, items, []
    for k, it in enumerate(items):
        n = _len(it, top)
        if pos + n > off:
            local = off - pos
            if isinstance(it, str):
                left, right = items[:k] + [it[:local]], [it[local:]] + items[k + 1:]
            elif local == 0:
                left, right = items[:k], items[k:]
            else:
                r = split_el(it, local, top)
                left, right = items[:k + 1], [r] + items[k + 1:]
            break
        pos += n
    put_items(x, left)
    x2 = x.makeelement(x.tag, dict(x.attrib))
    put_items(x2, right)
    return x2


def _cut(items: list, off: int, top, skip_empty: bool) -> int:
    """Make a boundary at `off` in the top-level items; returns the index of the first item after it."""
    pos = 0
    for k, it in enumerate(items):
        n = _len(it, top)
        if pos == off and (n > 0 or not skip_empty):
            return k
        if pos < off < pos + n:
            local = off - pos
            if isinstance(it, str):
                items[k:k + 1] = [it[:local], it[local:]]
            else:
                items.insert(k + 1, split_el(it, local, top))
            return k + 1
        pos += n
    if pos == off:
        return len(items)
    raise NotPlaced("offset beyond the block")


def wrap(top, a: int, b: int, lang: str) -> None:
    items = take_items(top)
    try:
        i = _cut(items, a, top, True)
        j = _cut(items, b, top, False)
        inner = items[i:j]
        for it in inner:
            if not isinstance(it, str) and any(
                    d.tag in (T("foreign"), T("p"), T("l"), T("lg")) or d.get("ana") == "foreign" for d in it.iter()):
                raise NotPlaced("would nest a passage or cross a verse line")
        if not any(_len(it, top) for it in inner):
            raise NotPlaced("empty")
        f = el("foreign", {"lang-tmp": lang, "resp": "#model", "cert": "medium", "ana": "foreign"})
        put_items(f, inner)
        items[i:j] = [f]
    finally:
        put_items(top, items)


def passages(top) -> list[tuple]:
    """(element, start, end) of every passage inside the block, in counted-text offsets."""
    out, pos = [], 0

    def walk(x):
        nonlocal pos
        c = _census()
        if x is not top and (x.tag in BLOCK_TAGS or c._skip(x)):
            return
        start = pos
        pos += len(x.text or "")
        for k in x:
            if isinstance(k.tag, str):
                walk(k)
            pos += len(k.tail or "")
        if x is not top and x.get("ana") == "foreign":
            out.append((x, start, pos))

    walk(top)
    return out


def unwrap(f) -> None:
    parent = f.getparent()
    items = take_items(parent)
    k = next(i for i, x in enumerate(items) if x is f)
    items[k:k + 1] = take_items(f)
    put_items(parent, items)


def _blocks(div) -> list:
    return [b for b in div.iter(*BLOCK_TAGS)
            if not any(a.tag in (ED("trans"), ED("verse-trans"), ED("block")) for a in [b, *b.iterancestors()])]


def apply(div, decisions: list, unit: str) -> None:
    rulings = [r for r in _layer().values() if r["unit"] == unit and r["confidence"] != "low"]
    if not rulings:
        return
    c = _census()
    by_text: dict[str, list] = {}
    for b in _blocks(div):
        text, _ = c.block_text(b)
        by_text.setdefault(sha(text), []).append(b)
    for r in sorted(rulings, key=lambda r: (r["block_sha"], r["nth"], -r["first"])):
        found = by_text.get(r["block_sha"], [])
        if r["nth"] >= len(found):
            decisions.append(_dec(unit, r, "census ruling not applied: block text changed"))
            continue
        b = found[r["nth"]]
        backup = copy.deepcopy(b)
        try:
            what = _apply_one(b, r)
            decisions.append(_dec(unit, r, f"census ruling applied: {what}", "la" if r["kind"] == "2" else "en"))
        except NotPlaced as e:
            b.getparent().replace(b, backup)
            by_text[r["block_sha"]][r["nth"]] = backup
            decisions.append(_dec(unit, r, f"census ruling not placed ({e}); the block left as it was"))


def _dec(unit: str, r: dict, why: str, verdict: str = "undetermined") -> dict:
    return {"unit": unit, "text": r["text"], "verdict": verdict, "confidence": "medium", "in_note": False,
            "why": f"{why} ({r['model']}/{r['prompt']}, stretch {r['id']})"}


def _apply_one(b, r: dict) -> str:
    c = _census()
    text, _ = c.block_text(b)
    idx = c.raw_index(b)
    ws = c.words(text)
    if r["last"] >= len(ws):
        raise NotPlaced("stretch beyond the block")
    cs, ce = ws[r["first"]][0], ws[r["last"]][1]
    if text[cs:ce] != r["text"]:
        raise NotPlaced("stretch text differs")
    if r["kind"] == "2":
        pieces = [p for p in (r["foreign_part"] or "").split("|") if c.WORD.search(c.ETC.sub(" ", p))]
        if not pieces:
            raise NotPlaced("no foreign words")
        spans, pos = [], cs
        for p in pieces:
            pat = r"\s*".join(re.escape(w) for w in p.split())
            m = re.compile(pat).search(text, pos, ce)
            if not m:
                raise NotPlaced("foreign part not found in the stretch")
            spans.append((m.start(), m.end()))
            pos = m.end()
        for s, e in reversed(spans):  # from the end, so earlier offsets stay valid
            wrap(b, idx[s], idx[e - 1] + 1, r["lang"] or "la")
        return f"tagged {len(spans)} stretch(es)"
    # kind 1: the edition's words the judge found not foreign
    truth = c._judged_words(r, r["last"] - r["first"] + 1)
    drop = [(idx[ws[r["first"] + k][0]], idx[ws[r["first"] + k][1] - 1] + 1)
            for k, t in enumerate(truth) if t is False]
    if not drop:
        raise NotPlaced("nothing to remove")
    touched = 0
    for f, f0, f1 in passages(b):
        if not any(s < f1 and f0 < e for s, e in drop):
            continue
        lang = f.get("lang-tmp") or f.get(XML_LANG) or "la"
        if f.get("resp") == "#editor" or lang.startswith("enm") or SCRIPT.search("".join(f.itertext())):
            raise NotPlaced("a passage that is not narrowed (editor's, Chaucer, or Greek/Hebrew script)")
        keep, cur = [], None
        raw = _raw_text(b)
        for k in range(f0, f1):
            dropped = any(s <= k < e for s, e in drop)
            if not dropped and cur is None:
                cur = [k, k + 1]
            elif not dropped:
                cur[1] = k + 1
            elif cur is not None:
                keep.append(cur)
                cur = None
        if cur is not None:
            keep.append(cur)
        keep = [_trim(raw, s, e) for s, e in keep]
        keep = [(s, e) for s, e in keep if e > s and c.WORD.search(c.ETC.sub(" ", raw[s:e]))]
        unwrap(f)
        for s, e in reversed(keep):
            wrap(b, s, e, lang)
        touched += 1
    if not touched:
        raise NotPlaced("no passage overlaps the stretch")
    return f"narrowed {touched} passage(s)"


def _raw_text(b) -> str:
    out: list[str] = []
    c = _census()

    def walk(x):
        if x is not b and (x.tag in BLOCK_TAGS or c._skip(x)):
            return
        out.append(x.text or "")
        for k in x:
            if isinstance(k.tag, str):
                walk(k)
            out.append(k.tail or "")

    walk(b)
    return "".join(out)


def _trim(raw: str, s: int, e: int) -> tuple[int, int]:
    while s < e and (raw[s].isspace() or raw[s] in ",;:()"):
        s += 1
    while e > s and (raw[e - 1].isspace() or raw[e - 1] in ",;:("):
        e -= 1
    return s, e
