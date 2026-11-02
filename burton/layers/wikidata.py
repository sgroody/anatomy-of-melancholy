"""`burton authors --wikidata`: match cited authors to Wikidata (CC0) for ids and dates. Rules only, no model.

Each author's English name, and the Latin form in brackets if any ("André du Laurens (Laurentius)"), is looked
up as an exact label or alias (English or Latin) in a few batched SPARQL queries. A candidate counts only if it
is a human (P31 = Q5) who died by 1651 (Burton's last edition) or, with no death date, was born by 1600. The
match is taken only when exactly one candidate counts; otherwise the candidates are recorded as `ambiguous`
(or `none`) and nothing is chosen. Responses are cached in state/wikidata/cache.json. Matches are labelled
`by: wikidata` with the method and date, and are part of the owner's top-100 review.

(v1 used the search API one author at a time; the service throttled it to a few authors an hour.)
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date

from .. import paths
from ..fsutil import atomic_write_text
from . import authors, citations

SPARQL = "https://query.wikidata.org/sparql"
UA = "burton-anatomy-edition/0.1 (private research edition; rules-only author matching)"
CACHE = paths.STATE / "wikidata" / "cache.json"
METHOD = "wikidata-match-v2"
QUERY = """SELECT ?name ?item ?itemLabel ?itemDescription ?birth ?death WHERE {
  VALUES ?name { %s }
  ?item rdfs:label|skos:altLabel ?name ; wdt:P31 wd:Q5 .
  OPTIONAL { ?item wdt:P569 ?birth } OPTIONAL { ?item wdt:P570 ?death }
  OPTIONAL { ?item rdfs:label ?itemLabel FILTER(lang(?itemLabel) = "en") }
  OPTIONAL { ?item schema:description ?itemDescription FILTER(lang(?itemDescription) = "en") }
}"""


def _sparql(query: str, cache: dict) -> list[dict]:
    if query not in cache:
        url = f"{SPARQL}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}"
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=70) as r:
                    cache[query] = json.loads(r.read().decode("utf-8"))["results"]["bindings"]
                break
            except urllib.error.HTTPError as e:  # 429: wait as asked (at most 2 min), then try again
                if e.code != 429 or attempt == 3:
                    raise
                wait = min(int(e.headers.get("Retry-After") or 60), 120) + 1
                print(f"  wikidata: throttled, waiting {wait} s", flush=True)
                time.sleep(wait)
        time.sleep(2)
    return cache[query]


def _year(b: dict, key: str) -> int | None:
    m = re.match(r"(-?)(\d+)-", (b.get(key) or {}).get("value", ""))
    return (-int(m.group(2)) if m.group(1) else int(m.group(2))) if m else None


def names(name: str) -> list[str]:
    """'André du Laurens (Laurentius)' -> ['André du Laurens', 'Laurentius']."""
    m = re.match(r"(.*?)\s*\((.*)\)\s*$", name)
    return [m.group(1), m.group(2)] if m else [name]


def _lit(s: str, lang: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + f'"@{lang}'


def run(batch: int = 10) -> Counter:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    t = citations.tables()
    todo = {aid: names(t["authors"][aid]["name"]) for aid, _ in authors.ranked()}
    strings = sorted({s for ns in todo.values() for s in ns})
    found: dict[str, dict[str, dict]] = defaultdict(dict)  # name -> qid -> candidate
    failed: set[str] = set()  # names whose lookup failed: their authors are left for a re-run
    for k in range(0, len(strings), batch):
        vals = " ".join(_lit(s, lang) for s in strings[k:k + batch] for lang in ("en", "la"))
        print(f"  wikidata: names {k + 1}-{min(k + batch, len(strings))} of {len(strings)}", flush=True)
        try:
            rows = _sparql(QUERY % vals, cache)
        except (OSError, ValueError) as e:  # URLError, timeouts, HTTP errors, bad JSON
            print(f"  wikidata: batch failed ({type(e).__name__}: {e}); left for a re-run", flush=True)
            failed.update(strings[k:k + batch])
            continue
        atomic_write_text(CACHE, json.dumps(cache, ensure_ascii=False, sort_keys=True) + "\n")
        for b in rows:
            qid = b["item"]["value"].rsplit("/", 1)[1]
            c = found[b["name"]["value"]].setdefault(qid, {
                "qid": qid, "label": b.get("itemLabel", {}).get("value"),
                "description": b.get("itemDescription", {}).get("value"), "born": None, "died": None})
            for key, f in (("birth", "born"), ("death", "died")):  # several dates: keep the earliest
                y = _year(b, key)
                if y is not None and (c[f] is None or y < c[f]):
                    c[f] = y
    stats: Counter = Counter()
    for aid, ns in todo.items():
        if failed & set(ns):
            stats["lookup-failed"] += 1
            continue
        cands = {q: c for n in ns for q, c in found.get(n, {}).items()}
        ok = [c for c in cands.values() if (c["died"] is not None and c["died"] <= 1651)
              or (c["died"] is None and c["born"] is not None and c["born"] <= 1600)]
        m = {"status": "matched", **ok[0]} if len(ok) == 1 else \
            {"status": "ambiguous" if ok else "none", "candidates": sorted(ok, key=lambda c: c["qid"])[:5]}
        rec = authors.load(aid)
        rec["wikidata"] = {**m, "by": "wikidata", "method": METHOD, "date": date.today().isoformat()}
        authors.save(aid, rec)
        stats[m["status"]] += 1
    return stats
