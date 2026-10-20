"""A Latin/English lexicon learned from the book itself (no external word lists, no detector library).

Latin: lowercase word forms inside passages that the rules tagged Latin with high confidence, which
is nearly always because a Gowland bracket follows them (an independent signal).
English: word forms of Burton's roman, untagged running text outside notes and italics.

Built by `burton lexicon` from a rules-only ingest and stored in data/lexicon/ so that later ingests
are reproducible; rebuild it only deliberately (it changes language decisions).
"""

import json
from collections import Counter
from functools import cache

import regex as re
from lxml import etree

from .. import paths
from ..tei import ED, XML_LANG, T

WORD = re.compile(r"[\p{L}\p{M}]+(?:['’][\p{L}]+)?")
DIR = paths.DATA / "lexicon"


def _text_outside(e, skip) -> list[str]:
    out = []
    if e.text and not skip(e):
        out.append(e.text)
    for c in e:
        if isinstance(c.tag, str) and not skip(c):
            out += _text_outside(c, skip)
        if c.tail and not skip(e):
            out.append(c.tail)
    return out


def build(units: list[str]) -> dict:
    la, en = Counter(), Counter()

    def not_english(x) -> bool:
        return x.tag in (T("note"), T("foreign"), T("hi"), ED("trans"), ED("verse-trans"), ED("block"),
                         T("supplied"), T("head")) or x.get("ana") == "foreign" or x.get(XML_LANG) not in (None, "en")

    for unit in units:
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        if root.find(f".//{T('div')}").get("resp") == "#gowland":
            continue
        for f in root.iter():
            if isinstance(f.tag, str) and f.get("ana") == "foreign" and f.get(XML_LANG) == "la" \
                    and f.get("cert") == "high" and f.get("resp") == "#rules":
                text = "".join(t for t in _text_outside(f, lambda x: x.tag == T("note")))
                la.update(w for w in WORD.findall(text) if w.islower())
        div = root.find(f".//{T('div')}")
        for p in div.iter(T("p"), T("l")):
            if any(a.tag in (T("note"), ED("block")) or a.get("ana") == "foreign" for a in p.iterancestors()):
                continue
            text = "".join(_text_outside(p, not_english))
            en.update(w.lower() for w in WORD.findall(text))
    DIR.mkdir(parents=True, exist_ok=True)
    for name, c in (("latin", la), ("english", en)):
        (DIR / f"{name}.json").write_text(
            json.dumps(dict(sorted(c.items())), ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    load.cache_clear()
    return {"latin_forms": len(la), "latin_tokens": sum(la.values()),
            "english_forms": len(en), "english_tokens": sum(en.values())}


@cache
def load() -> tuple[Counter, Counter] | None:
    try:
        la = Counter(json.loads((DIR / "latin.json").read_text(encoding="utf-8")))
        en = Counter(json.loads((DIR / "english.json").read_text(encoding="utf-8")))
    except FileNotFoundError:
        return None
    return la, en


def latinness(word: str) -> str:
    """'la' if the form is attested in Burton's Latin and not (or far less) in his English,
    'en' for the reverse, '' if unknown or ambiguous."""
    lex = load()
    if lex is None:
        return ""
    la, en = lex
    w = word.lower()
    a, b = la.get(w, 0), en.get(w, 0)
    if a and a >= 3 * b:
        return "la"
    if b >= 2 and b >= 3 * a:
        return "en"
    return ""
