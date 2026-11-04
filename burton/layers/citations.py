"""`burton citations`: Burton's sidenote citations -> data/layers/citations/<unit>.json (rules only, SPEC §4.2).

The parser reads each sidenote's public text (Gowland's matter removed, so his brackets never reach a
layer). Working on text rather than markup merges the source's token-by-token italics
("<em>Scalig</em>. <em>exercit</em>. <em>365 sect</em>.", SURVEY §5) for free.

A citation starts at
* an author form from data/abbreviations.yaml ("Hor.", "Fr. Vales."), a Bible book followed by a number,
  or `Idem` / `ibid.`;
* a locator with a number ("Lib. 1 fol. 7"), or a title ("Lib. de atra bile", "De remed. fortuit."): the author
  is named in the main text;
* an unknown capitalised name followed closely by a locus ("Rosinus lib. 2"), after a cue ("Vide", "apud"),
  or standing alone as the whole note ("Wierus.").
It runs through work words and locus pairs and stops at a semicolon, at prose, or where the next one starts.

Statuses (SPEC §4.2): `parsed` when the author is known and every other token is understood (a work found in
data/works.yaml, or locus pairs); `partial` when the author is known but a work or token is not; `unidentified`
when the author is not known. A note with no citation-like text is `no-citation`.

Nothing is guessed:
* an ambiguous form ("Scaliger") resolves by its work, by a locator only one candidate uses ("exercit."), or by
  a default whose basis is written in the yaml; otherwise it stays unidentified with `ambiguous_with`;
* an author-less locus takes the author named in the main text at the note's anchor only when exactly one
  author form stands there (`author_basis: text-at-anchor`);
* an unknown name stays unidentified with its raw text. `display` holds only what was resolved.
"""

import json
import re
from collections import Counter
from functools import cache

import yaml
from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..ingest.epub import all_units
from ..tei import XML_ID, T, public_id
from ..textview import public_text

# v2 (2026-11-03): numbered Bible books ("1 Cor. 6. 5, 6.", the number recorded as `book_n`), a reference after
# "?" or "!" ("… sapietis? Psal. 94. 8."), and the chapter and verses of a Bible reference (`ref`)
METHOD = "rules/abbrev-v2"
ABBREV = paths.DATA / "abbreviations.yaml"
WORKS = paths.DATA / "works.yaml"

TOKEN = re.compile(r"[A-Za-zÀ-ÿĀ-žæœÆŒ’'\-]+\.?|\d+(?:\.\d+)*[a-z]?\.?|[,;:&()]|[^\sA-Za-z\d]")
NUM = re.compile(r"^(\d+[a-z]?|[ivxlc]+|[IVXLC]+)$")
WORK_GLUE = {"de", "in", "ad", "pro", "contra", "super", "adversus", "adv"}
NAME_GLUE = {"de", "a", "à", "ab", "van", "von", "del", "di", "da", "le", "la", "du", "&"}
CUES = {"vide", "vid", "see", "apud", "inquit", "ex", "e", "cf", "teste", "ait", "saith", "out", "of", "lege", "more"}
LOWER_HEADS = {"part", "memb", "subs", "subsect", "sect", "fol", "lib", "cap"}  # a locus may open in lower case
# Bible books that take a number, and the highest number each has ("Reg." is Kings, as Burton numbers it: "1 Reg. 11.
# 5" is Solomon going after Ashtoreth, 1 Kings 11:5); "Esdr." numbered is the Apocrypha's 1 and 2 Esdras
NUMBERED_BOOKS = {"samuel": 2, "kings": 2, "chronicles": 2, "ezra": 2, "corinthians": 2, "thessalonians": 2,
                  "timothy": 2, "peter": 2, "john": 3, "maccabees": 2}
STARTS = {";", ",", ":", "(", "?", "!"}  # a citation may start after these, as after a stop
# capitalised words that open prose, never a citation
PROSE = {"Si", "Qui", "Quae", "Quod", "Et", "Non", "Ut", "The", "Vide", "See", "Nam", "Sed", "Cum", "Quid", "Hic",
         "Haec", "Hoc", "Ego", "Est", "Sic", "Nec", "Ne", "Dum", "Omnes", "Omnia", "Omnis", "Nihil", "Nullus", "Nemo",
         "Modo", "Vel", "An", "As", "He", "They", "So", "If", "For", "Of", "Or", "Read", "Lege", "Ex", "E", "Deus",
         "Deo", "Deum", "Dei", "Ad", "Ab", "A", "In", "It", "This", "That", "Which", "Who", "What", "When", "Where",
         "But", "And", "Some", "Many", "All", "Tum", "Tam", "Ita", "Unde", "Inde", "Hinc", "Ubi", "Quis", "Quam",
         "Quum", "Quo", "Quibus", "Nisi", "Ac", "At", "Aut", "Neque", "Etiam", "Ille", "Illa", "Iste", "Is", "Ea",
         "Id", "Mr", "Mrs", "Sir", "Dr", "Lord", "Lady", "King", "Queen", "St", "Saint", "Anno", "Edit", "Vita"}


def _bare(tok: str) -> str:
    return tok.rstrip(".")


class _UniqueKeys(yaml.SafeLoader):
    """A hand-kept table must not silently lose an entry to a repeated key."""


def _no_duplicates(loader, node, deep=False):
    keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
    if dup := {k for k in keys if keys.count(k) > 1}:
        raise ValueError(f"repeated keys in {node.start_mark.name}: {sorted(dup)}")
    return loader.construct_mapping(node, deep)


_UniqueKeys.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


def _load(path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeys)


@cache
def tables() -> dict:
    a = _load(ABBREV)
    w = _load(WORKS) if WORKS.exists() else {"works": {}}
    loc = {f.lower(): name for name, spec in a["locators"].items() for f in spec["forms"]}
    forms: dict[tuple, dict] = {}
    for aid, spec in a["authors"].items():
        for f in spec["forms"]:
            if tuple(f.split()) in forms:
                raise ValueError(f"author form {f!r} listed twice ({aid}); put it under `ambiguous`")
            forms[tuple(f.split())] = {"candidates": [aid]}
    for f, spec in (a.get("ambiguous") or {}).items():
        if unknown := [x for x in spec["candidates"] if x not in a["authors"]]:
            raise ValueError(f"ambiguous form {f!r}: unknown candidates {unknown}")
        forms[tuple(f.split())] = spec
    for wid, spec in (w.get("works") or {}).items():
        if spec["author"] not in a["authors"]:
            raise ValueError(f"work {wid}: unknown author {spec['author']}")
    bible = {f: book for book, spec in a["bible"].items() for f in spec["forms"]}
    works: dict[str, list] = {}
    for wid, spec in (w.get("works") or {}).items():
        works.setdefault(spec["author"], []).append((wid, spec))
    return {"loc": loc, "loc_en": {k: v["en"] for k, v in a["locators"].items()} | {"n": ""},
            "authors": a["authors"], "forms": forms, "maxform": max(len(k) for k in forms),
            "bible": bible, "bible_books": a["bible"], "idem": set(a["special"]["idem"]),
            "ibid": {x.lower() for x in a["special"]["ibid"]}, "works": works}


def _is_num(tok: str) -> bool:
    """Arabic numbers, lower-case roman numerals, and upper-case ones of two letters or more ("C." is an
    initial, "II" a number)."""
    b = _bare(tok).rstrip(",")
    return bool(NUM.match(b)) and not (b.isupper() and len(b) == 1)


def _locator(toks: list[str], i: int) -> str | None:
    """The locator a token names ("lib." -> book), when a number follows it."""
    name = tables()["loc"].get(_bare(toks[i]).lower())
    return name if name and i + 1 < len(toks) and _is_num(toks[i + 1]) else None


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower().replace("æ", "ae").replace("œ", "oe")).split())


def _match_author(toks: list[str], i: int) -> tuple[int, dict] | None:
    """Longest author form starting at toks[i] (inner tokens may keep their stop: "Fr. Vales.")."""
    t = tables()
    if not toks[i][:1].isupper():
        return None
    for n in range(min(t["maxform"], len(toks) - i), 0, -1):
        key = tuple(_bare(x) for x in toks[i:i + n])
        if key in t["forms"]:
            return n, t["forms"][key]
    return None


def _work(author: str, words: list[str]) -> str | None:
    return _work_cached(author, tuple(words))


@cache
def _work_cached(author: str, words: tuple[str, ...]) -> str | None:
    """The work of `author` whose title (or a listed form) the work words abbreviate word by word; None unless
    exactly one work matches."""
    raw = _norm(" ".join(words)).split()
    while raw and raw[0] in {"lib", "liber", "libro", "tract", "tractat", "tractatu"} and len(raw) > 1:
        raw = raw[1:]  # "Lib. de anima": a book called "De anima"
    if not raw:
        return None
    hits = set()
    for wid, spec in tables()["works"].get(author, []):
        for form in [spec["title"], *spec.get("forms", [])]:
            fw = _norm(form).split()
            if len(raw) <= len(fw) and all(f.startswith(r) for r, f in zip(raw, fw, strict=False)):
                hits.add(wid)
    return hits.pop() if len(hits) == 1 else None


def _work_anywhere(words: list[str]) -> tuple[str, str] | None:
    """(author, work) when the words begin with one of a work's stand-alone forms (`alone:` in works.yaml,
    exact, e.g. "Eunuch." -> Terence). A prefix match is not enough: held-out round c1 found "Theog.",
    "Scot.", "Medea" and "Phar." resolved wrongly that way (data/eval/m6-citations-holdout.yaml)."""
    return _alone(tuple(_norm(" ".join(words)).split()))


@cache
def _alone(raw: tuple[str, ...]) -> tuple[str, str] | None:
    hits = {(spec["author"], wid) for a, ws in tables()["works"].items() for wid, spec in ws
            for form in spec.get("alone", []) if tuple(_norm(form).split()) == raw[:len(_norm(form).split())]}
    return hits.pop() if len(hits) == 1 else None


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text)


def _locus_soon(toks: list[str], i: int, within: int = 4) -> bool:
    """A locator with a number within `within` tokens after i, with only work-like tokens between."""
    for j in range(i + 1, min(len(toks), i + 1 + within)):
        if _locator(toks, j):
            return True
        tok = toks[j]
        if not (tok.endswith(".") or tok.lower() in WORK_GLUE or tok[:1].isupper() or tok == "," or _is_num(tok)):
            return False
    return False


def _name_note(toks: list[str]) -> bool:
    """The whole note is a short name ("Wierus.", "Leander Albertus.", "Bartholomaeus à Casa.")."""
    words = [x for x in toks if x not in {".", ","}]
    return 0 < len(words) <= 4 and words[0][:1].isupper() and words[0] not in PROSE and \
        all(w[:1].isupper() or w.lower() in NAME_GLUE for w in words) and toks[-1].endswith(".")


def _numbered_book(toks: list[str], i: int) -> tuple[str, int] | None:
    """(book, number) where toks[i:] read "1 Cor. 6": a number the book can have, its form, then a chapter."""
    if not re.fullmatch(r"[1-4]", toks[i]) or i + 2 >= len(toks) or not toks[i + 2][:1].isdigit():
        return None
    book = tables()["bible"].get(_bare(toks[i + 1]))
    return (book, int(toks[i])) if book and int(toks[i]) <= NUMBERED_BOOKS.get(book, 0) else None


def _segments(toks: list[str]) -> list[tuple[int, int, str, object]]:
    """Citation heads: (index, length of the head, kind, payload)."""
    t = tables()
    heads = []
    if _name_note(toks) and not _match_author(toks, 0) and _bare(toks[0]) not in t["bible"]:
        return [(0, 1, "unknown", None)]
    i = 0
    while i < len(toks):
        tok = toks[i]
        b = _bare(tok)
        prev = toks[i - 1] if i else "."
        at_start = i == 0 or prev.endswith(".") or prev in STARTS or _bare(prev).lower() in CUES
        if b in t["idem"] and tok[:1].isupper():
            heads.append((i, 1, "idem", None))
        elif b.lower() in t["ibid"] and (tok.endswith(".") or b.lower() == "ibidem"):
            heads.append((i, 1, "ibid", None))
        elif (book := _numbered_book(toks, i)) and at_start and not (i and _locator(toks, i - 1)):
            heads.append((i, 2, "bible", book))  # "1 Cor. 6.", not "lib. 1 Thes. 1." (a book and a title)
            i += 2
            continue
        elif b in t["bible"] and i + 1 < len(toks) and toks[i + 1][:1].isdigit() and at_start:
            heads.append((i, 1, "bible", (t["bible"][b], None)))
        elif m := _match_author(toks, i):
            heads.append((i, m[0], "author", m[1]))
            i += m[0]
            continue
        elif (tok[:1].isupper() or b.lower() in LOWER_HEADS) and _locator(toks, i) and at_start:
            heads.append((i, 0, "locus", None))
            i += 2
            continue
        elif at_start and b in {"Lib", "Libro", "Cap", "De", "Tract", "Epist", "Dial", "Comment", "Orat"} and \
                i + 1 < len(toks) and (toks[i + 1].lower() in WORK_GLUE or b == "De"):
            heads.append((i, 0, "title", None))  # a title, its author in the main text
        elif tok[:1].isupper() and b not in PROSE and len(b) > 2 and at_start and \
                (_locus_soon(toks, i) or (i + 1 < len(toks) and _is_num(toks[i + 1]))) and \
                not (prev[:1].islower() and prev.endswith(".") and len(prev) <= 8):
            # "Rosinus lib. 2", "Aen. 4"; not after a lower-case abbreviation: "De hist. Med. mirab."
            heads.append((i, 1, "unknown", None))
        elif tok[:1].isupper() and b not in PROSE and len(b) > 2 and i and (prev.endswith(".") or prev == ",") \
                and not (heads and i - heads[-1][0] <= 8) and \
                (i == len(toks) - 1 and tok.endswith(".") or
                 i == len(toks) - 2 and toks[-1].endswith(".") and toks[-1][:1].isupper()):
            heads.append((i, 1, "unknown", None))  # a name closing the note: "… annua. Arnold.", "Euphormio Satyr."
        elif at_start and tok[:1].isupper() and b not in PROSE and len(b) > 2 and \
                not (prev[:1].islower() and prev.endswith(".") and len(prev) <= 8) and \
                (_work_anywhere(toks[i:i + 2]) or _work_anywhere(toks[i:i + 1])):
            heads.append((i, 1, "unknown", None))  # a work title standing alone: "Mor. Encom.", "Eunuch."
        elif i == 0 and tok[:1].isupper() and b not in PROSE and len(b) > 3 and not tok.endswith(".") and \
                i + 1 < len(toks) and toks[i + 1][:1].islower() and toks[i + 1].endswith(".") and len(toks[i + 1]) <= 9:
            heads.append((i, 1, "unknown", None))  # a name and an abbreviated title: "Keckermann praefat. polit."
        elif tok[:1].isupper() and b not in PROSE and len(b) > 2 and i and _bare(prev).lower() in CUES:
            heads.append((i, 1, "unknown", None))
        i += 1
    return heads


def _body(toks: list[str], start: int, end: int) -> tuple[list[str], list[list[str]], int, list[str], list[str]]:
    """Work words, locus pairs, the end index, unclassified tokens, and the words after a locus once a title
    came before it (a chapter's own title: "lib. 1 cap. 10 de Melanc.")."""
    work, locus, odd, after = [], [], [], []
    i, in_locus, titling = start, False, False
    titled = False  # a title stood before the first locus
    # one or two lower-case title words up to a stop ("Plut. vita ejus.")
    j = next((k for k in range(start, min(end, start + 3)) if toks[k].endswith(".") or _locator(toks, k)
              or not toks[k][:1].islower()), None)
    if start < end and toks[start][:1].islower() and j is not None and toks[j].endswith(".") \
            and not _locator(toks, j):
        titling = True
    while i < end:
        tok = toks[i]
        b = _bare(tok)
        if tok == ";":
            break
        if tok in {",", "&", ":"} or (b in {"et", "and"} and in_locus):
            if tok == "," and i + 1 < end and not (_is_num(toks[i + 1]) or _locator(toks, i + 1)
                                                   or toks[i + 1].lower() in WORK_GLUE):
                break  # "Mercurialis, de affect. lib. 1 cap. 10, excepts …": prose follows
            i += 1
            continue
        name = None if _is_num(tok) else _locator(toks, i)
        if name:
            nums = [_bare(toks[i + 1]).rstrip(",")]
            j = i + 2
            while j + 1 < end and toks[j] in {",", "&"} and _is_num(toks[j + 1]):
                nums.append(_bare(toks[j + 1]).rstrip(","))
                j += 2
            titled = titled or (bool(work) and not locus)
            locus.append([name, ", ".join(nums)])
            i, in_locus, titling = j, True, False
            continue
        if _is_num(tok):
            titled = titled or (bool(work) and not locus)
            locus.append(["n", _bare(tok).rstrip(",")])
            i, in_locus, titling = i + 1, True, False
            continue
        if in_locus and b.lower() not in WORK_GLUE:
            # an abbreviated part title inside a locus ("lib. 1 Path. cap. 18")
            if tok.endswith(".") and tok[:1].isupper() and i + 1 < end and (_locator(toks, i + 1)
                                                                             or _is_num(toks[i + 1])):
                odd.append(tok)
                i += 1
                continue
            # a title after the locus ("Tom. 4 meret. dial.", "lib. 6 Hist. Scot."), else the citation ends
            if not (tok.endswith(".") and len(b) <= 12):
                break
        # a full lower-case word inside a title, before a locus or an abbreviation ("de affect. capitis lib. 1")
        inner = bool(work) and tok[:1].islower() and i + 1 < end and \
            (_locator(toks, i + 1) or toks[i + 1].endswith(".") and len(toks[i + 1]) <= 9)
        if b.lower() in WORK_GLUE or tok.endswith(".") or titling or inner:
            (after if titled else work).append(tok)
            titling = (b.lower() in WORK_GLUE or titling) and not tok.endswith(".")
            in_locus = False
            i += 1
            if tok.endswith(".") and i < end and toks[i][:1].isupper() and not _locator(toks, i) \
                    and _bare(toks[i]).lower() not in WORK_GLUE and not toks[i].endswith(".") \
                    and not (i + 1 < end and toks[i + 1].endswith(".")):
                break  # "Seneca. Nam quis …": a full capitalised word after a stop is prose
            if len(work) > 8:
                break
            continue
        break
    return work, locus, i, odd, after


def _resolve(spec: dict, work: list[str], locus: list[list[str]]) -> tuple[str | None, str | None]:
    """Author id and how an ambiguous form was resolved."""
    cands = spec["candidates"]
    if spec.get("needs_locus") and not any(name != "n" or not re.fullmatch(r"1[4-7]\d\d", n) for name, n in locus):
        return None, None  # "Basil." alone, or with a year ("Basil. 1553."), is Basle; "Basil. ep. 141" is St Basil
    if len(cands) == 1:
        return cands[0], None
    by_work = {a for a in cands if _work(a, work)}
    if len(by_work) == 1:
        return by_work.pop(), "work"
    names = {name for name, _ in locus}
    by_locus = {a for name, a in (spec.get("by_locus") or {}).items() if name in names}
    if len(by_locus) == 1:
        return by_locus.pop(), "locus"
    if spec.get("default") and not by_work and not by_locus:
        return spec["default"], "default"
    return None, None


def parse_note(text: str) -> list[dict]:
    """Citations in one sidenote's public text, in order, without Idem/ibid resolution."""
    toks = tokenize(text)
    heads = _segments(toks)
    out = []
    end = 0
    for k, (i, n, kind, payload) in enumerate(heads):
        if i < end:
            continue  # a locus or title the previous citation's body already took ("urb. cap. 6")
        # a body runs to the next head that names someone; loci and titles in between are its own
        nxt = next((h[0] for h in heads[k + 1:] if h[2] not in ("locus", "title")), len(toks))
        if kind == "unknown":  # the rest of a name ("Leander Albertus", "P. Martyr") belongs to the head
            while i + n < nxt and (toks[i + n][:1].isupper() and not toks[i + n].endswith(".")
                                   and not _locator(toks, i + n) or toks[i + n].lower() in NAME_GLUE - {"&"}):
                n += 1
        work, locus, end, odd, after = _body(toks, i + n, nxt)
        if kind == "locus" and not locus:
            continue
        c = {"kind": kind, "head": _join(toks[i:i + n]), "work_words": work, "locus": locus, "odd": odd,
             "raw": _join(toks[i:end]), "part_title": _join(after) if after else None}
        if kind == "author":
            c["author"], how = _resolve(payload, work, locus)
            if len(payload["candidates"]) > 1:
                c["ambiguous_with"] = payload["candidates"]
                c["resolved_by"] = how
        elif kind == "bible":
            c["author"], c["work"] = "bible", f"bible.{payload[0]}"
            if payload[1]:
                c["book_n"] = payload[1]
        out.append(c)
    return out


def _join(toks: list[str]) -> str:
    return re.sub(r" ([,;:.)])", r"\1", " ".join(toks)).replace("( ", "(")


BIBLE_REST = re.compile(r"(\d+)(?:(?:\s*[.:]\s*|\s*,?\s+v(?:er|ers)?\.\s*)"
                        r"(\d+(?:(?:\s*[,\-–]\s*|\s+and\s+)\d+)*))?[.,]?")
NUMBERED_NAMES = {"ezra": "Esdras"}  # "1 Esd." is the Apocrypha's First Book of Esdras, not Ezra


def bible_ref(raw: str) -> dict | None:
    """The chapter and verses of a Bible reference, read from Burton's words after the book ("Hag. 1. 9, 10" ->
    chapter 1, verses 9 and 10; "Psal. 94. 8."; "1 Cor. 6. 5, 6."). None where they are not that plain ("2 Reg. 3 &
    17, 23": a chapter and another chapter's verses, or two chapters), so nothing is shown for a reading not made."""
    toks = raw.split(None, 2 if re.match(r"[1-4] ", raw) else 1)
    if len(toks) < 2 or not (m := BIBLE_REST.fullmatch(toks[-1].strip())):
        return None
    verses: list[int] = []
    for part in re.split(r"\s*,\s*|\s+and\s+", m.group(2) or ""):
        if not part:
            continue
        bounds = [int(x) for x in re.split(r"\s*[\-–]\s*", part)]
        if len(bounds) > 2 or bounds[-1] < bounds[0] or bounds[-1] - bounds[0] > 30:
            return None
        verses += range(bounds[0], bounds[-1] + 1)
    return {"chapter": int(m.group(1)), "verses": verses}


def bible_label(book: str, n: int | None, ref: dict | None) -> str:
    """"1 Corinthians 6:5–6", "Haggai 1:9–10", "Psalms 94:8", "Samuel 20" (consecutive verses as a range)."""
    name = f"{n} {NUMBERED_NAMES.get(book, tables()['bible_books'][book]['name'])}" if n else \
        tables()["bible_books"][book]["name"]
    if not ref:
        return name
    runs: list[list[int]] = []
    for v in ref["verses"]:
        if runs and v == runs[-1][-1] + 1:
            runs[-1].append(v)
        else:
            runs.append([v])
    vs = ", ".join(f"{r[0]}–{r[-1]}" if len(r) > 1 else str(r[0]) for r in runs)
    return f"{name} {ref['chapter']}" + (f":{vs}" if vs else "")


def _display(c: dict) -> str | None:
    t = tables()
    parts = []
    if c.get("author") == "bible":
        book = c["work"].split(".", 1)[1]
        if ref := c.get("ref"):
            return bible_label(book, c.get("book_n"), ref)
        parts.append(bible_label(book, c.get("book_n"), None))
    elif c.get("author"):
        parts.append(t["authors"][c["author"]]["name"])
        if c.get("work"):
            parts.append(next(spec["title"] for wid, spec in t["works"][c["author"]] if wid == c["work"]))
    loc = ", ".join(f"{t['loc_en'][name]} {n}".strip() for name, n in c["locus"])
    return ", ".join(p for p in [*parts, loc] if p) or None


def _status(c: dict) -> str:
    if not c.get("author"):
        return "unidentified"
    if c.get("author") == "bible":
        return "parsed"
    if c["odd"] or (c["work_words"] and not c.get("work")):
        return "partial"
    return "parsed"


def _anchor_author(note) -> str | None:
    """The author named in the main text at a note's anchor. The marker stands before the words it glosses,
    so the first capitalised name in the 6 tokens after it must be an author form ("⟦n⟧ Gellius, are …");
    an unknown name there ("⟦n⟧ Aristides Milesius (mentioned by Plutarch)") resolves nothing. With no name
    after the marker, one author form in the 4 tokens before it is taken."""
    block = note.getparent()
    while block is not None and block.tag not in (T("p"), T("l"), T("item"), T("head"), T("quote")):
        block = block.getparent()
    if block is None:
        return None
    text = public_text(block, note_marker=note.get(XML_ID))
    if "⟦sidenote⟧" not in text:
        return None
    before, after = text.split("⟦sidenote⟧", 1)
    toks = tokenize(after)[:6]
    for i, tok in enumerate(toks):
        if tok[:1].isupper() and _bare(tok) not in PROSE:
            m = _match_author(toks, i)
            return m[1]["candidates"][0] if m and len(m[1]["candidates"]) == 1 else None
    toks = tokenize(before)[-4:]
    found = {tuple(m[1]["candidates"]) for i in range(len(toks)) if (m := _match_author(toks, i))}
    return found.pop()[0] if len(found) == 1 and len(next(iter(found))) == 1 else None


@cache
def decisions() -> dict[tuple[str, str], dict]:
    """Hand decisions for citations the rules cannot resolve, keyed by (sidenote id, exact citation text)."""
    f = paths.MANUAL / "citation-decisions.yaml"
    rows = (_load(f) or {}).get("decisions", []) if f.exists() else []
    return {(d["note"], d["raw"]): d for d in rows}


def build(units: list[str] | None = None) -> Counter:
    units = units or all_units()
    stats: Counter = Counter()
    for unit in units:
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        records = {}
        prev = None  # last citation in document order, for Idem/ibid
        for note in root.iter(T("note")):
            if note.get("type") != "side":
                continue
            nid = public_id(note.get(XML_ID))
            text = public_text(note, notes=True)
            cits = []
            for k, c in enumerate(parse_note(text), 1):
                if c["kind"] in ("idem", "ibid") and prev and prev.get("author"):
                    c["author"], c["resolved_from"] = prev["author"], prev["id"]
                    # ibid. repeats the work; Idem after a Bible book means that book
                    if (c["kind"] == "ibid" or prev["author"] == "bible") and prev.get("work"):
                        c["work"] = prev["work"]
                        if prev.get("book_n"):
                            c["book_n"] = prev["book_n"]
                    if c["kind"] == "ibid" and not c["locus"]:
                        c["locus"] = prev["locus"]
                if c["kind"] == "locus" and {n for n, _ in c["locus"]} <= {"part", "section", "member", "subsection",
                                                                          "n"} and \
                        {n for n, _ in c["locus"]} & {"member", "subsection"}:
                    # Burton's own divisions ("Part. 3 sect. 2 Memb. 1 Sub. 1"): a reference to this book
                    c["author"], c["work"], c["author_basis"] = "burton", "burton.anatomy", "own-divisions"
                elif c["kind"] in ("locus", "title") and k == 1:
                    if a := _anchor_author(note):
                        c["author"], c["author_basis"] = a, "text-at-anchor"
                if c["kind"] == "unknown":
                    # a work title standing as the head ("Eunuch.", "Faerie Queene"): its author, if the title
                    # belongs to the author named at the anchor or to only one author in data/works.yaml
                    words = [c["head"], *c["work_words"]]
                    a = _anchor_author(note) if k == 1 else None
                    if a and (w := _work(a, words)):
                        c["author"], c["work"], c["author_basis"] = a, w, "text-at-anchor"
                    elif hit := _work_anywhere(words):
                        c["author"], c["work"] = hit
                        c["author_basis"] = "work-title"
                    if c.get("work"):
                        c["work_words"] = words
                if d := decisions().get((nid, c["raw"])):  # data/manual/citation-decisions.yaml
                    c["author"], c["author_basis"] = d["author"], "decision"
                    stats["decisions_applied"] += 1
                if c.get("author") and c["author"] != "bible" and not c.get("work"):
                    c["work"] = _work(c["author"], c["work_words"])
                if c.get("author") == "bible" and c.get("work"):
                    c["ref"] = bible_ref(c["raw"])
                rec = {"id": f"{nid}-c{k}", "raw": c["raw"], "author": c.get("author"), "work": c.get("work"),
                       "locus": c["locus"], "status": _status(c), "method": METHOD, "display": _display(c)}
                for key in ("resolved_from", "ambiguous_with", "resolved_by", "author_basis", "part_title", "book_n",
                            "ref"):
                    if c.get(key):
                        rec[key] = c[key]
                if c["kind"] in ("idem", "ibid"):
                    rec["head"] = c["kind"]
                cits.append(rec)
                stats[f"citations_{rec['status']}"] += 1
                stats[f"kind_{c['kind']}"] += 1
                if rec.get("author_basis"):
                    stats["author_from_anchor"] += 1
                prev = {**c, "id": rec["id"]}
            if cits:
                sts = {c["status"] for c in cits}
                status = "parsed" if sts == {"parsed"} else "unidentified" if sts == {"unidentified"} else "partial"
            else:
                status = "no-citation"
            stats[f"notes_{status}"] += 1
            records[nid] = {"raw": text, "citations": cits, "status": status}
        out = paths.LAYERS / "citations" / f"{unit}.json"
        if records:
            out.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(out, json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        elif out.exists():
            out.unlink()
    return stats
