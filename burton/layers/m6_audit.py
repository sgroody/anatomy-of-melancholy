"""`burton m6-audit`: independent model checkers for what M6 left to the owner (owner, 2026-11-02:
"Run independent checkers for these").

* `authors`: the 100 drafted author entries, audited for identity and factual errors (prompt `author-audit-v1`);
  the checker sees the draft, Burton's citations and the Wikidata match.
* `xrefs`: the 83 relative cross-reference candidates, re-rated blind (prompt `xref-audit-v1`): the checker does
  the task again without seeing the first proposals, and the two are compared.
* `sources`: the 19 source matches that disagree with a claim (prompt `source-audit-v1`).

The checker is a fresh `claude -p` call with its own versioned prompt, so it shares no context with the drafter;
it is the same model family, so an error both make systematically can escape both. Answers go to
data/eval/m6-audit-<kind>.jsonl, labelled with model, prompt and date; every call is in
state/m6-audit/ledger.jsonl and a run resumes from the answers file. Nothing here changes a layer: the results
feed the owner's review lists. Gowland's matter is never sent (all text is public text).
"""

import json
from collections import Counter
from datetime import UTC, datetime

from .. import paths
from ..fsutil import atomic_write_text
from ..translate import packets, runner
from ..translate.audit import _around
from . import authors, xrefs_relative

LEDGER = paths.STATE / "m6-audit" / "ledger.jsonl"
PROMPTS = {"authors": "author-audit-v1", "xrefs": "xref-audit-v1", "sources": "source-audit-v1"}


def _obj(props: dict) -> dict:
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


S, SN, CONF = {"type": "string"}, {"type": ["string", "null"]}, {"type": "string", "enum": ["high", "medium", "low"]}
ANSWER = {
    "authors": _obj({"id": S, "identity": {"type": "string", "enum": ["ok", "doubtful", "wrong"]},
                     "facts": {"type": "string", "enum": ["ok", "minor", "error"]},
                     "errors": {"type": "array", "items": S},
                     "wikidata": {"type": "string", "enum": ["ok", "wrong", "none"]}, "reason": S}),
    "xrefs": _obj({"id": S, "kind": {"type": "string",
                                     "enum": ["reference", "same-place", "not-a-reference", "too-vague"]},
                   "target": SN, "reason": S, "confidence": CONF}),
    "sources": _obj({"id": S, "verdict": {"type": "string", "enum": ["claim-quoted-in-match", "match-is-source",
                                                                       "both-share", "unclear"]},
                     "source_author": SN, "source_work": SN, "reason": S, "confidence": CONF}),
}
KEY = {"authors": "authors", "xrefs": "items", "sources": "items"}


def out_path(kind: str):
    return paths.ROOT / "data" / "eval" / f"m6-audit-{kind}.jsonl"


def items(kind: str) -> tuple[list[dict], str]:
    """Items to check and a preamble sent with every packet."""
    if kind == "authors":
        out = []
        for aid, d in authors.ranked()[:100]:
            rec = authors.load(aid)
            dr = rec.get("draft")
            if not dr:
                continue
            wd = rec.get("wikidata") or {}
            out.append({"id": aid, "name": authors.citations.tables()["authors"][aid]["name"],
                        "burton_forms": authors.citations.tables()["authors"][aid]["forms"],
                        "examples": [e["raw"] for e in d["examples"][:6]],
                        "wikidata": ({k: wd.get(k) for k in ("qid", "label", "description", "born", "died")}
                                     if wd.get("status") == "matched" else None),
                        "draft": {k: dr.get(k) for k in ("identification", "field", "why_cited", "identity_doubt")}})
        return out, ""
    if kind == "xrefs":
        cands, _ = xrefs_relative.candidates()
        return ([{k: i[k] for k in ("id", "unit", "unit_title", "context")} for i in cands],
                "Outline of the book:\n" + "\n".join(xrefs_relative.outline()) + "\n\n")
    if kind == "sources":
        from . import sources as S_

        corpus = {(u["author"], u["work"], u["locus"]): u for u in S_.load_corpora()}
        out = []
        for f in sorted((paths.LAYERS / "source-verification").glob("*.json")):
            unit = f.stem
            ps = {p["packet_item"]["id"]: p["packet_item"] for p in packets.passages(unit)}
            layer = json.loads((paths.LAYERS / "translations" / f"{unit}.json").read_text(encoding="utf-8"))
            for pid, r in json.loads(f.read_text(encoding="utf-8")).items():
                if r["status"] == "verified":
                    continue
                w = corpus[(r["author"], r["work"], r["locus"])]["words"]
                n, end = S_.run_at(S_.norm(ps[pid]["text"]), w)  # centre the excerpt on the matched run
                at = end - n // 2
                src = layer[pid]["source"]
                out.append({"id": pid, "passage": ps[pid]["text"], "context": _around(ps[pid]["paragraph"], 400),
                            "sidenotes": ps[pid].get("sidenotes", [])[:4],
                            "claim": {"author": src.get("author"), "work": src.get("work"), "status": src["status"]},
                            "match": {"author": r.get("author_name") or r["author"], "work": r.get("title"),
                                      "locus": r["locus"]},
                            "corpus_text": " ".join(w[max(0, at - 40):at + 40])})
        return out, ""
    raise SystemExit(f"unknown audit kind {kind!r}")


def _done(kind: str) -> dict:
    f = out_path(kind)
    if not f.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, f.read_text(encoding="utf-8").splitlines())
            if r["prompt"] == PROMPTS[kind]}


def run(kind: str, *, model: str, packet_size: int = 15, budget_usd: float | None = None,
        dry_run: bool = False) -> Counter:
    prompt = PROMPTS[kind]
    sys_prompt = (paths.ROOT / "burton" / "translate" / "prompts" / f"{prompt}.md").read_text(encoding="utf-8")
    its, pre = items(kind)
    done = _done(kind)
    hashes = {i["id"]: packets.input_hash(i, prompt, model, 0) for i in its}
    todo = [i for i in its if (done.get(i["id"]) or {}).get("input_hash") != hashes[i["id"]]]
    stats: Counter = Counter(items=len(its), to_check=len(todo))
    if dry_run:
        return stats
    schema = _obj({KEY[kind]: {"type": "array", "items": ANSWER[kind]}})
    spent = 0.0
    for k in range(0, len(todo), packet_size):
        if budget_usd is not None and spent >= budget_usd:
            print(f"stopping: ${spent:.2f} list-equivalent spent, budget ${budget_usd:.2f} (--budget-usd)")
            break
        pk = todo[k:k + packet_size]
        user = pre + "Check these.\n\n" + json.dumps({KEY[kind]: pk}, ensure_ascii=False, indent=1)
        res = runner.call_claude(model, sys_prompt, user, schema)
        spent += res.get("cost_usd_list") or 0
        runner.append(LEDGER, {"kind": kind, "ids": [i["id"] for i in pk], "model": model, "prompt": prompt,
                               "ts": runner.now(), "status": "done" if res["ok"] else "failed",
                               **{x: res.get(x) for x in ("seconds", "cost_usd_list", "usage", "error")}})
        if not res["ok"]:
            print(f"  call failed: {(res.get('error') or '')[:200]} (re-run to resume)")
            stats["failed"] += 1
            break
        day = datetime.now(UTC).date().isoformat()
        for a in res["output"][KEY[kind]]:
            if a["id"] in hashes:
                done[a["id"]] = {**a, "by": "machine", "model": model, "prompt": prompt, "date": day,
                                 "input_hash": hashes[a["id"]]}
        atomic_write_text(out_path(kind), "".join(json.dumps(done[x], ensure_ascii=False, sort_keys=True) + "\n"
                                                  for x in sorted(done)))
        print(f"  {kind}: {len(done)} checked (${spent:.2f})", flush=True)
    stats["checked"] = len(done)
    stats["cost_usd_list"] = round(spent, 2)
    return stats


REPORT = paths.STATE / "review" / "m6-audit.md"


def report() -> dict:
    """state/review/m6-audit.md: each checker's answers beside the first results, disagreements listed."""
    rep: dict = {}
    L = ["# M6 independent checks (owner, 2026-11-02: \"Run independent checkers for these\")", "",
         "Each checker is a fresh `claude -p` call with its own versioned prompt and no shared context with the",
         "first pass; it is the same model family, so a shared systematic error could escape both. Answers:",
         "`data/eval/m6-audit-<kind>.jsonl`. Nothing here changes a layer.", ""]
    a = _done("authors")
    if a:
        rows = sorted(a.values(), key=lambda r: r["id"])
        c = {f: dict(Counter(r[f] for r in rows)) for f in ("identity", "facts", "wikidata")}
        rep["authors"] = {"checked": len(rows), **c}
        L += [f"## Author drafts ({len(rows)}, prompt `{PROMPTS['authors']}`)", "",
              f"Identity: {c['identity']}. Facts: {c['facts']}. Wikidata match: {c['wikidata']}.", "",
              "| Author | Identity | Facts | Wikidata | Problems | Reason |", "|---|---|---|---|---|---|"]
        for r in rows:
            if r["identity"] != "ok" or r["facts"] != "ok" or r["wikidata"] == "wrong":
                L.append(f"| `{r['id']}` | {r['identity']} | {r['facts']} | {r['wikidata']} | "
                         f"{'; '.join(r['errors']).replace('|', '/') or '—'} | {r['reason'].replace('|', '/')} |")
        L.append("")
    x = _done("xrefs")
    if x:
        first = {}
        for f in (paths.LAYERS / "xrefs-relative").glob("*.json"):
            first |= json.loads(f.read_text(encoding="utf-8"))
        pairs = Counter()
        dis = []
        for k, r in sorted(x.items()):
            f = first.get(k)
            if not f:
                continue
            ft = f["target"] if f["status"] in ("relative-proposed", "relative-confirmed") else None
            st = r["target"] if r["kind"] == "reference" else None
            cls = ("same target" if ft and ft == st else "first only" if ft and not st else
                   "second only" if st and not ft else "different targets" if ft and st else "neither")
            pairs[cls] += 1
            if cls != "neither" and cls != "same target":
                dis.append(f"| `{k}` | {f['selector']['exact']} | {ft or '—'} | {st or '—'} ({r['kind']}) | "
                           f"{r['reason'].replace('|', '/')} |")
        rep["xrefs"] = {"checked": len(x), **pairs, "second_kinds": dict(Counter(r["kind"] for r in x.values()))}
        L += [f"## Relative cross-references ({len(x)}, blind second rater, prompt `{PROMPTS['xrefs']}`)", "",
              f"Targets: {dict(pairs)}. Second rater's kinds: {rep['xrefs']['second_kinds']}.", "",
              "| Item | Phrase | First proposal | Second rater | Second rater's reason |", "|---|---|---|---|---|",
              *dis, ""]
    s = _done("sources")
    if s:
        rows = sorted(s.values(), key=lambda r: r["id"])
        rep["sources"] = {"checked": len(rows), **Counter(r["verdict"] for r in rows)}
        L += [f"## Source conflicts ({len(rows)}, prompt `{PROMPTS['sources']}`)", "",
              f"Verdicts: {dict(Counter(r['verdict'] for r in rows))}.", "",
              "| Passage | Verdict | Source named | Confidence | Reason |", "|---|---|---|---|---|"]
        for r in rows:
            who = ", ".join(x for x in (r["source_author"], r["source_work"]) if x) or "—"
            L.append(f"| `{r['id']}` | {r['verdict']} | {who} | {r['confidence']} | {r['reason'].replace('|', '/')} |")
        L.append("")
    atomic_write_text(REPORT, "\n".join(L) + "\n")
    return rep
