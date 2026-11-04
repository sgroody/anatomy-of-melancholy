"""The names of cited authors in Burton's running text, for the name windows (owner, 2026-11-03: stage 5, R5 C).

A form is linked only when nothing is guessed: data/abbreviations.yaml gives it to one author, that author has an
entry in data/authors/, it is a capitalised word or phrase of four letters or more, it is not a Bible book's form,
and Burton never uses it as an ordinary lower-case word (so "Cato" is linked; a name that is also an English word
is not). What a window shows comes from the entry: name, Wikidata dates, the identification (a machine draft the
owner checked, labelled so), and the Wikidata item for a Wikipedia link.
"""

import re
from functools import cache

import yaml
from lxml import etree

from .. import paths
from ..ingest.epub import all_units
from ..layers import citations
from ..tei import T
from ..textview import public_text
from .authors_pages import dates

WORD = re.compile(r"[^\W\d_][\w’'-]*")


@cache
def lower_words() -> frozenset[str]:
    """Every word Burton's text uses in lower case."""
    out = set()
    for unit in all_units():
        div = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot().find(f".//{T('div')}")
        if div is not None:
            out.update(w for w in WORD.findall(public_text(div, notes=True)) if w.islower())
    return frozenset(out)


@cache
def index() -> tuple[re.Pattern | None, dict[str, str], dict[str, dict]]:
    """(pattern over the forms, form -> author id, author id -> what its window shows)."""
    t = citations.tables()
    bible = set(t["bible"])
    low = lower_words()
    ids, info = {}, {}
    for words, spec in t["forms"].items():
        cands = spec.get("candidates") or []
        if len(cands) != 1:
            continue
        aid, form = cands[0], " ".join(words)
        f = paths.DATA / "authors" / f"{aid}.yaml"
        if not f.exists() or len(form) < 4 or not form[:1].isupper() or form in bible:
            continue
        if not all(WORD.fullmatch(w) for w in words) or any(w.lower() in low for w in words):
            continue
        ids[form] = aid
        if aid not in info:
            e = yaml.safe_load(f.read_text(encoding="utf-8"))
            d = e.get("draft") or {}
            about = e.get("identification") or d.get("identification")
            wd = e.get("wikidata") or {}
            info[aid] = {"name": e["name"], "dates": dates(wd), "about": about,
                         "by": None if e.get("identification") else d.get("model"),
                         "checked": (e.get("review") or {}).get("state") == "accepted",
                         "qid": wd.get("qid") if wd.get("status") == "matched" else None}
    if not ids:
        return None, {}, {}
    alt = "|".join(re.escape(f) for f in sorted(ids, key=len, reverse=True))
    return re.compile(rf"(?<![\w’'-])(?:{alt})(?![\w’'-])"), ids, info
