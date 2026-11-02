"""`burton verify-sources`: check quotation sources against local public-domain or open corpora (M6).

A source becomes `identified` only through this verifier, and only on a verified text match (CLAUDE.md). The
translation layer is never edited: results go to data/layers/source-verification/<unit>.json, keyed by passage
id, and the reader and V7 read them from there.

Corpora (gitignored, under data/source/corpora/, each pinned in CORPORA.lock) are converted to one plain file
per work: data/source/corpora/<corpus>/<author-id>/<work-id>.txt, one `locus<TAB>text` line per citable unit.
Until the owner approves a download there are none, and the verifier reports 0 corpora and verifies nothing.

Matching, on normalised text (lower case, i/j and u/v merged, æ/œ spelled out, accents and punctuation
dropped): a candidate unit shares a 4-word sequence with the passage; the match is `verified` when the passage
(at least 5 words) and the corpus text share a run of at least 5 consecutive words that covers at least 80 % of
the passage's words. A verified match whose author differs from the record's own claim is a `conflict` for
review, not an upgrade.
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..ingest.epub import all_units
from ..tei import XML_ID, public_id
from ..textview import public_text
from ..translate.packets import sha1

CORPORA = paths.SOURCE / "corpora"
LAYER = "source-verification"
METHOD = "text-match-v1"
MIN_WORDS, MIN_RUN, MIN_COVER, N = 5, 5, 0.8, 4


SPELLING = {"quum": "cum", "nihil": "nil", "mihi": "mi"}  # early-modern and classical spellings of one word


def norm(s: str) -> list[str]:
    """Words for comparison only (never stored text): i/j, u/v, ae/oe/e and y/i merged ("coelum" = "caelum",
    "foelix" = "felix"), accents and punctuation dropped."""
    s = unicodedata.normalize("NFD", s.lower().replace("æ", "ae").replace("œ", "oe"))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).replace("j", "i").replace("v", "u")
    s = s.replace("ae", "e").replace("oe", "e").replace("y", "i")
    return [SPELLING.get(w, w) for w in re.findall(r"[a-z]+", s)]


def load_corpora(root=CORPORA) -> list[dict]:
    """Every citable unit of every converted corpus: {corpus, author, work, locus, words}."""
    out = []
    if not root.exists():
        return out
    titles = {}
    for ix in root.glob("*/index.json"):  # work titles from the corpus catalogue, written by `burton corpora`
        cat = json.loads(ix.read_text(encoding="utf-8"))
        titles |= {f"{ix.parent.name}/{k}": v.get("title") for k, v in cat.items()}
    for f in sorted(root.glob("*/*/*.txt")):
        corpus, author, work = f.parent.parent.name, f.parent.name, f.stem
        title = titles.get(f"{corpus}/{author}/{f.name}")
        for line in f.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                locus, text = line.split("\t", 1)
                out.append({"corpus": corpus, "author": author, "work": work, "title": title, "locus": locus,
                            "words": norm(text)})
    return out


def index(units: list[dict]) -> dict[int, set[int]]:
    """Hashed 4-word sequences at every second position: a shared run of 5 words always contains one of
    them, and the index is half the size (the Perseus Latin corpus has about 7 million words)."""
    ix: dict[int, set[int]] = defaultdict(set)
    for k, u in enumerate(units):
        w = u["words"]
        for i in range(0, len(w) - N + 1, 2):
            ix[hash(tuple(w[i:i + N]))].add(k)
    return ix


def longest_run(a: list[str], b: list[str]) -> int:
    best, prev = 0, [0] * (len(b) + 1)
    for x in a:
        cur = [0] * (len(b) + 1)
        for j, y in enumerate(b, 1):
            if x == y:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


def match(words: list[str], units: list[dict], ix: dict, prefer: set[str] = frozenset()) -> dict | None:
    """The best passing unit, or the best passing unit by an author in `prefer` (the claimed author) if there is
    one: a line of Horace also stands, quoted, in Seneca's letters, and a match there is not a conflict."""
    if len(words) < MIN_WORDS:
        return None
    cands = Counter(k for i in range(len(words) - N + 1) for k in ix.get(hash(tuple(words[i:i + N])), ()))
    passing = []
    for k, _ in cands.most_common(40):
        run = longest_run(words, units[k]["words"])
        if run >= MIN_RUN and run / len(words) >= MIN_COVER:
            passing.append((run, units[k]["author"] in prefer, k))
    if not passing:
        return None
    pick = max(passing, key=lambda x: (x[1], x[0]))
    best = (pick[2], pick[0])
    u = units[best[0]]
    return {"corpus": u["corpus"], "author": u["author"], "work": u["work"], "title": u.get("title"),
            "locus": u["locus"],
            "run": best[1], "words": len(words), "cover": round(best[1] / len(words), 3)}


def claim_ids(name: str | None) -> set[str]:
    """Edition author ids a claimed name ("Virgil", "Seneca", "Pliny the Elder") can mean, from the tables."""
    from . import citations

    if not name:
        return set()
    t = citations.tables()
    key = name.lower().rstrip(".")
    ids = {aid for aid, spec in t["authors"].items()
           if key == spec["name"].lower() or key in (f.lower() for f in spec["forms"])}
    ids |= {c for f, spec in t["forms"].items() if " ".join(f).lower() == key for c in spec["candidates"]}
    return ids


def run(unit_ids: list[str] | None = None, root=CORPORA) -> Counter:
    corpus = load_corpora(root)
    stats: Counter = Counter(corpus_units=len(corpus), corpora=len({u["corpus"] for u in corpus}))
    if not corpus:
        print("no corpora under data/source/corpora/: nothing can be verified (downloads await the owner)")
        return stats
    ix = index(corpus)
    from . import citations

    names = {aid: spec["name"] for aid, spec in citations.tables()["authors"].items()}
    for unit in unit_ids or all_units():
        f = paths.LAYERS / "translations" / f"{unit}.json"
        if not f.exists():
            continue
        layer = json.loads(f.read_text(encoding="utf-8"))
        root_el = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        foreign = {public_id(e.get(XML_ID)): e for e in root_el.iter()
                   if isinstance(e.tag, str) and e.get("ana") == "foreign"}
        out = {}
        for pid, rec in layer.items():
            if pid not in foreign or rec["lang"] not in ("la", "grc"):
                continue
            stats["passages"] += 1
            claim = rec["source"].get("author")
            ids = claim_ids(claim)
            m = match(norm(public_text(foreign[pid])), corpus, ix, prefer=ids)
            if not m:
                continue
            if m["author"].startswith("perseus-"):
                status = "matched-unmapped"  # a corpus author the edition has no id for: reported, no upgrade
            elif not claim or m["author"] in ids:
                status = "verified"
            else:
                status = "conflict" if ids else "unchecked"  # unchecked: the claimed name is not in the tables
            stats[status] += 1
            out[pid] = {**m, "status": status, "claim_author": claim, "claim_status": rec["source"]["status"],
                        "text_sha1": sha1(public_text(foreign[pid])),
                        "author_name": names.get(m["author"]),
                        "basis": f"text-match:{m['corpus']}:{m['author']}.{m['work']}:{m['locus']}",
                        "by": "rules", "method": METHOD, "date": date.today().isoformat()}
        p = paths.LAYERS / LAYER / f"{unit}.json"
        if out:
            p.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(p, json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        elif p.exists():
            p.unlink()
    return stats
