"""`burton authors --wikidata`: match cited authors to Wikidata (CC0) for ids and dates. Rules only, no model.

For each author the English name (and the Latin form in brackets, if any) is searched. A candidate counts only
if it is a human (P31 = Q5) who died by 1651 (Burton's last edition), or, with no death date, was born by 1600.
The match is taken only when exactly one candidate counts; otherwise the candidates are recorded as
`ambiguous` (or `none`) and nothing is chosen. Every response is cached in state/wikidata/cache.json, so a
re-run asks only for what is missing. Matches are labelled `by: wikidata` with the method and date, and stay
part of the owner's top-100 review.
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date

from .. import paths
from ..fsutil import atomic_write_text
from . import authors, citations

API = "https://www.wikidata.org/w/api.php"
UA = "burton-anatomy-edition/0.1 (private research edition; rules-only author matching)"
CACHE = paths.STATE / "wikidata" / "cache.json"
METHOD = "wikidata-match-v1"


def _get(params: dict, cache: dict) -> dict:
    key = urllib.parse.urlencode(sorted(params.items()))
    if key not in cache:
        req = urllib.request.Request(f"{API}?{key}&format=json", headers={"User-Agent": UA})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    cache[key] = json.loads(r.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:  # 429: wait as long as the service asks, then try again
                if e.code != 429 or attempt == 4:
                    raise
                time.sleep(int(e.headers.get("Retry-After") or 30) + 1)
        time.sleep(1.5)  # be gentle with a public service
    return cache[key]


def _year(claims: dict, prop: str) -> int | None:
    for c in claims.get(prop, []):
        v = (c.get("mainsnak", {}).get("datavalue") or {}).get("value") or {}
        m = re.match(r"([+-])(\d+)-", v.get("time", ""))
        if m:
            return int(m.group(2)) * (-1 if m.group(1) == "-" else 1)
    return None


def _queries(name: str) -> list[str]:
    """'André du Laurens (Laurentius)' -> ['André du Laurens', 'Laurentius']."""
    m = re.match(r"(.*?)\s*\((.*)\)\s*$", name)
    return [m.group(1), m.group(2)] if m else [name]


def match(aid: str, name: str, cache: dict) -> dict:
    ids: list[str] = []
    for q in _queries(name):
        res = _get({"action": "wbsearchentities", "search": q, "language": "en", "limit": "7"}, cache)
        ids += [x["id"] for x in res.get("search", []) if x["id"] not in ids]
    if not ids:
        return {"status": "none", "candidates": []}
    ents = _get({"action": "wbgetentities", "ids": "|".join(ids), "props": "claims|labels|descriptions",
                 "languages": "en"}, cache).get("entities", {})
    ok = []
    for qid in ids:
        e = ents.get(qid, {})
        claims = e.get("claims", {})
        human = any((c.get("mainsnak", {}).get("datavalue") or {}).get("value", {}).get("id") == "Q5"
                    for c in claims.get("P31", []))
        born, died = _year(claims, "P569"), _year(claims, "P570")
        if human and ((died is not None and died <= 1651) or (died is None and born is not None and born <= 1600)):
            ok.append({"qid": qid, "label": e.get("labels", {}).get("en", {}).get("value"),
                       "description": e.get("descriptions", {}).get("en", {}).get("value"),
                       "born": born, "died": died})
    if len(ok) == 1:
        return {"status": "matched", **ok[0]}
    return {"status": "ambiguous" if ok else "none", "candidates": ok[:5]}


def run(limit: int | None = None) -> Counter:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    t = citations.tables()
    stats: Counter = Counter()
    try:
        for aid, _ in authors.ranked()[:limit]:
            rec = authors.load(aid)
            if rec.get("wikidata") and rec["wikidata"].get("method") == METHOD:
                stats["kept"] += 1
                continue
            m = match(aid, t["authors"][aid]["name"], cache)
            rec["wikidata"] = {**m, "by": "wikidata", "method": METHOD, "date": date.today().isoformat()}
            authors.save(aid, rec)
            stats[m["status"]] += 1
    finally:
        atomic_write_text(CACHE, json.dumps(cache, ensure_ascii=False, sort_keys=True) + "\n")
    return stats
