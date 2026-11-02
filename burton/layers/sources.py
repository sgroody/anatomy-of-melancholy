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

CORPORA = paths.SOURCE / "corpora"
LAYER = "source-verification"
METHOD = "text-match-v1"
MIN_WORDS, MIN_RUN, MIN_COVER, N = 5, 5, 0.8, 4


def norm(s: str) -> list[str]:
    s = unicodedata.normalize("NFD", s.lower().replace("æ", "ae").replace("œ", "oe"))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).replace("j", "i").replace("v", "u")
    return re.findall(r"[a-z]+", s)


def load_corpora(root=CORPORA) -> list[dict]:
    """Every citable unit of every converted corpus: {corpus, author, work, locus, words}."""
    out = []
    if not root.exists():
        return out
    for f in sorted(root.glob("*/*/*.txt")):
        corpus, author, work = f.parent.parent.name, f.parent.name, f.stem
        for line in f.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                locus, text = line.split("\t", 1)
                out.append({"corpus": corpus, "author": author, "work": work, "locus": locus, "words": norm(text)})
    return out


def index(units: list[dict]) -> dict[tuple, set[int]]:
    ix: dict[tuple, set[int]] = defaultdict(set)
    for k, u in enumerate(units):
        w = u["words"]
        for i in range(len(w) - N + 1):
            ix[tuple(w[i:i + N])].add(k)
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


def match(words: list[str], units: list[dict], ix: dict) -> dict | None:
    if len(words) < MIN_WORDS:
        return None
    cands = Counter(k for i in range(len(words) - N + 1) for k in ix.get(tuple(words[i:i + N]), ()))
    best = None
    for k, _ in cands.most_common(20):
        run = longest_run(words, units[k]["words"])
        if run >= MIN_RUN and run / len(words) >= MIN_COVER and (best is None or run > best[1]):
            best = (k, run)
    if best is None:
        return None
    u = units[best[0]]
    return {"corpus": u["corpus"], "author": u["author"], "work": u["work"], "locus": u["locus"],
            "run": best[1], "words": len(words), "cover": round(best[1] / len(words), 3)}


def run(unit_ids: list[str] | None = None, root=CORPORA) -> Counter:
    corpus = load_corpora(root)
    stats: Counter = Counter(corpus_units=len(corpus), corpora=len({u["corpus"] for u in corpus}))
    if not corpus:
        print("no corpora under data/source/corpora/: nothing can be verified (downloads await the owner)")
        return stats
    ix = index(corpus)
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
            m = match(norm(public_text(foreign[pid])), corpus, ix)
            if not m:
                continue
            claim = rec["source"].get("author")
            status = "verified" if not claim or claim == m["author"] else "conflict"
            stats[status] += 1
            out[pid] = {**m, "status": status, "claim_author": claim, "claim_status": rec["source"]["status"],
                        "basis": f"text-match:{m['corpus']}:{m['author']}.{m['work']}:{m['locus']}",
                        "by": "rules", "method": METHOD, "date": date.today().isoformat()}
        p = paths.LAYERS / LAYER / f"{unit}.json"
        if out:
            p.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(p, json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        elif p.exists():
            p.unlink()
    return stats
