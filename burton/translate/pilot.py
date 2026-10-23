"""M4 pilot report (`burton pilot-report`): verdicts against the drafted expectations, honesty counts,
per-packet time and usage from the ledger, the Dell & Jordan-Smith alignment, and the owner's review page.

Everything is read from the layers, the ledger and the selection file; nothing calls a model.
"""

import html
import json
import math
from collections import Counter, defaultdict
from statistics import mean, median

import yaml

from .. import paths
from ..fsutil import atomic_write_text
from . import packets, runner

MODELS = ["claude-opus-5-5", "claude-sonnet-5-5"]


def _load(path, layer: str, unit: str) -> dict:
    f = paths.LAYERS / layer / f"{unit}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def collect(selection_path) -> list[dict]:
    """One row per pilot item: the selection entry, the passage, each model's record, the DJS alignment."""
    sel = yaml.safe_load(open(selection_path, encoding="utf-8"))
    rows = []
    cache: dict[str, dict] = {}
    for it in (i for i in sel["items"] if not i.get("retired")):
        unit = it["id"].rsplit("-", 1)[0]
        if unit not in cache:
            cache[unit] = {"tr": _load(selection_path, "translations", unit),
                           "gl": _load(selection_path, "glosses", unit),
                           "djs": _load(selection_path, "djs", unit),
                           "items": {p["packet_item"]["id"]: p["packet_item"] for p in packets.passages(unit)}}
        c = cache[unit]
        gloss = it.get("kind") == "gloss-only"
        item = packets.gloss_item(unit, it["id"])["packet_item"] if gloss else c["items"][it["id"]]
        rec = (c["gl"] if gloss else c["tr"]).get(it["id"], {})
        per_model = {}
        for m in MODELS:
            if gloss:
                g = [x for x in rec.get("glosses", []) if x.get("model") == m and x.get("prompt") == runner.PROMPT]
                per_model[m] = g[-1] if g else None
            else:
                t = [x for x in rec.get("translations", []) if x.get("by") == "machine" and x.get("model") == m
                     and x.get("prompt") == runner.PROMPT]
                per_model[m] = t[-1] if t else None
        rows.append({"sel": it, "unit": unit, "item": item, "models": per_model, "djs": c["djs"].get(it["id"])})
    return rows


def verdicts(rows: list[dict]) -> dict:
    out = {}
    for m in MODELS:
        c = Counter()
        wrong = []
        for r in rows:
            t, exp = r["models"][m], r["sel"].get("expected_st")
            if not t or exp is None:
                continue
            got = t["self_translation"]["status"]
            ok = got in exp
            draft_ok = got in r["sel"].get("expected_st_draft", exp)  # as labelled before the runs
            c["all_ok" if ok else "all_wrong"] += 1
            c["all_ok_as_drafted"] += draft_ok
            if r["sel"].get("gate"):
                c["gate_ok" if ok else "gate_wrong"] += 1
                c["gate_ok_as_drafted"] += draft_ok
                c["gate_items"] += 1
            if not ok:
                wrong.append({"id": r["sel"]["id"], "got": got, "claimed": t["self_translation"].get("claimed"),
                              "expected": exp, "gate": bool(r["sel"].get("gate"))})
        out[m] = {**c, "wrong": wrong}
    return out


def honesty(rows: list[dict]) -> dict:
    out = {}
    for m in MODELS:
        status, flags, warn = Counter(), Counter(), Counter()
        downgraded, attributions = [], []
        for r in rows:
            t = r["models"][m]
            if not t or "source" not in t:
                continue
            s = t["source"]
            status[s["status"]] += 1
            if s.get("downgraded_from"):
                downgraded.append(r["sel"]["id"])
            if s["status"] != "unidentified":
                attributions.append({"id": r["sel"]["id"], "status": s["status"], "author": s.get("author"),
                                     "work": s.get("work"), "locus": s.get("locus"), "basis": s.get("basis")})
            flags.update(t.get("flags", []))
            warn.update(w.split(":")[0] for w in t.get("warnings", []))
        out[m] = {"source_status": dict(status), "downgraded": downgraded, "flags": dict(flags),
                  "warnings": dict(warn), "attributions": attributions}
    return out


def ledger_rows(selection_path) -> list[dict]:
    rows = []
    for line in runner.LEDGER.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if (r.get("selection") or "").replace("\\", "/").endswith(str(selection_path).replace("\\", "/")) \
                and r.get("prompt") == runner.PROMPT:
            rows.append(r)
    return rows


def throughput(selection_path) -> dict:
    """Per-packet time and reported usage; a retry's first call is added to its packet."""
    rows = ledger_rows(selection_path)
    out = {}
    for m in MODELS:
        per = defaultdict(lambda: {"seconds": 0.0, "calls": 0, "cost": 0.0, "out": 0, "in": 0, "cache_read": 0,
                                   "cache_write": 0, "status": None, "n": 0, "chars_in": 0})
        for r in rows:
            if r["model"] != m or r["status"] not in ("done", "retry", "invalid", "failed", "deferred"):
                continue
            p = per[r["packet"]]
            p["n"], p["chars_in"] = len(r["ids"]), r.get("chars_in", 0)
            if r.get("seconds") is not None:
                u = r.get("usage") or {}
                p["seconds"] += r["seconds"]
                p["calls"] += 1
                p["cost"] += r.get("cost_usd_list") or 0
                p["out"] += u.get("output_tokens") or 0
                p["in"] += u.get("input_tokens") or 0
                p["cache_read"] += u.get("cache_read_input_tokens") or 0
                p["cache_write"] += u.get("cache_creation_input_tokens") or 0
            if r["status"] != "retry":
                p["status"] = r["status"]
        ps = [p for p in per.values() if p["status"] == "done"]
        if not ps:
            continue
        n = sum(p["n"] for p in ps)
        out[m] = {
            "packets": len(per), "packets_done": len(ps), "passages": n,
            "statuses": dict(Counter(p["status"] for p in per.values())),
            "calls": sum(p["calls"] for p in ps), "retried_packets": sum(1 for p in ps if p["calls"] > 1),
            "seconds_total": round(sum(p["seconds"] for p in ps), 1),
            "seconds_per_packet_median": round(median(p["seconds"] for p in ps), 1),
            "seconds_per_passage": round(sum(p["seconds"] for p in ps) / n, 1),
            "output_tokens_per_passage": round(sum(p["out"] for p in ps) / n),
            "input_tokens_per_packet_mean": round(mean(p["in"] + p["cache_read"] + p["cache_write"] for p in ps)),
            "cache_write_per_packet_mean": round(mean(p["cache_write"] for p in ps)),
            "cost_usd_list_total": round(sum(p["cost"] for p in ps), 4),
            "cost_usd_list_per_passage": round(sum(p["cost"] for p in ps) / n, 4),
            "per_packet": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in p.items()} for p in ps],
        }
    return out


def full_pass_packets(packet_size: int = 20) -> dict:
    """How many packets the full pass needs: per unit, ceil(foreign passages / packet size)."""
    from ..ingest.epub import all_units

    counts = {}
    for u in all_units():
        f = paths.LAYERS / "selftrans" / f"{u}.json"
        counts[u] = len(json.loads(f.read_text(encoding="utf-8"))) if f.exists() else 0
    return {"passages": sum(counts.values()), "units": len(counts),
            "packets": sum(math.ceil(n / packet_size) for n in counts.values() if n)}


def djs_counts(rows: list[dict]) -> dict:
    c = Counter(r["djs"]["status"] for r in rows if r["djs"])
    return {"by_status": dict(c), "aligned_or_omitted": c["aligned"] + c["omitted"],
            "foreign_items": sum(1 for r in rows if r["sel"].get("kind") != "gloss-only")}


def report(selection_path) -> dict:
    rows = collect(selection_path)
    return {"items": len(rows), "strata": dict(Counter(r["sel"]["stratum"] for r in rows)),
            "translated": {m: sum(1 for r in rows if r["models"][m]) for m in MODELS},
            "verdicts": verdicts(rows), "honesty": honesty(rows), "throughput": throughput(selection_path),
            "djs": djs_counts(rows), "full_pass": full_pass_packets()}


# ------------------------------------------------------------------ the owner's review page

RUBRIC = [
    ("accuracy", "Accuracy", "Says what the original says: nothing added, dropped or mistranslated."),
    ("register", "Register", "Reads as English for Burton's book: plain, period-appropriate, not modern slang."),
    ("glossary", "Glossary", "Uses the glossary renderings, or the note explains why not."),
    ("attribution", "Honest attribution", "No invented source; Burton's own citation recorded as such; "
                                          "'probably' only with a real basis; notes make no unsupported claims."),
]


def _e(s) -> str:
    return html.escape(str(s or ""), quote=True)


def _version(label: str, key: str, t: dict | None, gloss: bool) -> str:
    if not t:
        return f'<div class="v missing"><h4>{_e(label)}</h4><p>No record.</p></div>'
    head = (f'<h4>{_e(label)}</h4><p class="lbl">Machine translation · model {_e(t["model"])} · prompt '
            f'{_e(t["prompt"])} · {_e(t["date"])} · confidence {_e(t.get("confidence"))}</p>')
    if gloss:
        body = "".join(f"<li><b>{_e(g['headword'])}</b>: {_e(g['sense'])}</li>" for g in t["items"])
        body = body or "<li>(none)</li>"
        body = f"<ul class='gl'>{body}</ul>"
    else:
        st, src = t["self_translation"], t["source"]
        sp = (st.get("burton_span") or {}).get("exact")
        srcs = ", ".join(x for x in (src.get("author"), src.get("work"), src.get("locus")) if x)
        word = {"burton-cites": "Burton cites", "probable": "Probably", "unidentified": "Unidentified"}.get(
            src["status"], src["status"])
        body = (f'<p class="tr">{_e(t["text"])}</p>'
                + (f'<p class="lit"><i>Literal:</i> {_e(t["literal"])}</p>' if t.get("literal") else "")
                + f'<p class="meta"><i>Self-translation:</i> {_e(st["status"])}'
                + (f' (claimed {_e(st["claimed"])}, quote not found)' if st.get("claimed") else "")
                + (f' — “{_e(sp)}”' if sp else "") + "</p>"
                + f'<p class="meta"><i>Source:</i> {_e(word)}{": " + _e(srcs) if srcs else ""}'
                + (f' <span class="basis">basis: {_e(src.get("basis"))}</span>' if src.get("basis") else "")
                + (f' <b>(downgraded from {_e(src["downgraded_from"])})</b>' if src.get("downgraded_from") else "")
                + "</p>"
                + (f'<p class="meta"><i>Flags:</i> {_e(", ".join(t["flags"]))}</p>' if t.get("flags") else ""))
    note = f'<p class="note"><i>Note:</i> {_e(t["note"])}</p>' if t.get("note") else ""
    warn = f'<p class="warn"><i>Checks:</i> {_e("; ".join(t["warnings"]))}</p>' if t.get("warnings") else ""
    return f'<div class="v" data-v="{key}">{head}{body}{note}{warn}{_rubric_inputs(key)}</div>'


def _rubric_inputs(key: str) -> str:
    cells = "".join(
        f'<label title="{_e(desc)}">{_e(name)} <select data-c="{c}"><option value="">–</option>'
        f'<option>pass</option><option>minor</option><option>fail</option></select></label>'
        for c, name, desc in RUBRIC)
    return f'<div class="rub" data-v="{key}">{cells}<input type="text" data-c="comment" placeholder="comment"></div>'


def _djs(d: dict | None) -> str:
    if not d:
        return '<div class="v missing"><h4>Dell &amp; Jordan-Smith (1927)</h4><p>Not aligned.</p></div>'
    s = d["status"]
    head = '<h4>Dell &amp; Jordan-Smith (1927)</h4>'
    if s == "aligned":
        return (f'<div class="v" data-v="djs">{head}<p class="lbl">Human translation, public domain (USA) · '
                f'{_e(d["where"])} · alignment score {d["align_score"]}</p><p class="tr">{_e(d["text"])}</p>'
                f'<div class="rub" data-v="djs"><label>Alignment correct? <select data-c="aligned">'
                f'<option value="">–</option><option>yes</option><option>partly</option><option>no</option>'
                f'</select></label><input type="text" data-c="comment" placeholder="comment"></div></div>')
    why = {"omitted": "Dell &amp; Jordan-Smith print nothing here: they dropped the foreign words "
                      f"({_e(d.get('where'))}, anchor score {d.get('align_score')}).",
           "below-threshold": f"Candidate discarded: anchor score {d.get('align_score')} is below the threshold.",
           "implausible-length": f"Candidate discarded: {d.get('gap_words')} words between the anchors is too long "
                                 f"to be a rendering of this passage.",
           "not-found": "Burton's surrounding English was not found in their text.",
           "no-anchor": _e(d.get("reason") or "No English of Burton's next to the passage to anchor on.")}[s]
    return f'<div class="v missing">{head}<p>{why}</p></div>'


def review_page(selection_path, out_path) -> None:
    rows = collect(selection_path)
    parts = []
    for n, r in enumerate(rows, 1):
        it, s = r["item"], r["sel"]
        gloss = s.get("kind") == "gloss-only"
        ctx = it.get("main_text_at_note") or it["paragraph"]
        ctx = _e(ctx).replace("⟦", "<mark>").replace("⟧", "</mark>")
        exp = ", ".join(s.get("expected_st") or []) or "—"
        sidenotes = "".join(f"<li>{_e(x)}</li>" for x in it.get("sidenotes", []))
        parts.append(
            f'<section id="{_e(s["id"])}" data-id="{_e(s["id"])}"><h3>{n}. {_e(s["id"])} '
            f'<span class="tag">{_e(s["stratum"])}</span> <span class="tag">{_e(it["lang"])} · {_e(it["kind"])} · '
            f'{_e(it["location"])}</span></h3>'
            f'<p class="why">{_e(s["reason"])}</p>'
            f'<p class="orig" lang="{_e(it["lang"])}">{_e(it["text"])}</p>'
            f'<details><summary>Context (Burton’s text; the passage is highlighted)</summary><p class="ctx">{ctx}</p>'
            + (f'<p><i>Sidenotes in this paragraph:</i></p><ul>{sidenotes}</ul>' if sidenotes else "")
            + f'</details><p class="exp"><i>Expected self-translation verdict (Claude’s draft):</i> {_e(exp)}'
            + (" · <b>exit gate</b>" if s.get("gate") else "")
            + (f'<br><b>Revised after the runs</b> (draft: {_e(", ".join(s["expected_st_draft"]))}): '
               f'{_e(s.get("revised"))}' if s.get("expected_st_draft") else "") + "</p>"
            f'<div class="vs">{_version("Opus", "opus", r["models"]["claude-opus-5-5"], gloss)}'
            f'{_version("Sonnet", "sonnet", r["models"]["claude-sonnet-5-5"], gloss)}'
            + ("" if gloss else _djs(r["djs"])) + "</div></section>")
    rubric = "".join(f"<li><b>{_e(name)}</b>: {_e(desc)}</li>" for _, name, desc in RUBRIC)
    page = PAGE.replace("{RUBRIC}", rubric).replace("{ITEMS}", "\n".join(parts)).replace("{N}", str(len(rows)))
    atomic_write_text(out_path, page)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>M4 pilot review</title>
<style>
:root{--bg:#fbfaf7;--fg:#1d1b18;--mut:#6b655c;--line:#ddd6ca;--card:#fff;--mark:#f3e3a6;--bad:#a33}
@media (prefers-color-scheme:dark){:root{--bg:#191816;--fg:#ece8e1;--mut:#a39d93;--line:#3a3631;--card:#22211e;
--mark:#5a4b18;--bad:#e88}}
body{background:var(--bg);color:var(--fg);font:16px/1.5 Georgia,'EB Garamond',serif;margin:0 auto;max-width:1200px;
padding:16px}
h1{font-size:1.6rem}h3{font-size:1.1rem;margin:.2rem 0}h4{margin:0 0 .2rem}
section{border-top:1px solid var(--line);padding:1rem 0}
.tag{font:12px system-ui,sans-serif;color:var(--mut);border:1px solid var(--line);border-radius:4px;padding:0 4px}
.why,.exp,.lbl,.meta,.note,.warn{font-size:.9rem;color:var(--mut)}.warn{color:var(--bad)}
.orig{font-style:italic;font-size:1.05rem}.ctx mark{background:var(--mark);color:inherit}
.vs{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.v{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px}.v.missing{opacity:.8}
.tr{font-size:1.02rem}.rub{display:flex;flex-wrap:wrap;gap:6px;font:13px system-ui,sans-serif;margin-top:6px}
.rub input{flex:1 1 100%;font:inherit}select{font:inherit}
.bar{position:sticky;top:0;background:var(--bg);padding:6px 0;border-bottom:1px solid var(--line);z-index:1;
font:14px system-ui,sans-serif}
</style></head><body>
<h1>M4 translation pilot: review</h1>
<p>{N} passages. Each shows the original, Burton’s context, and every version with its source label:
two machine translations (Opus and Sonnet, prompt tr-v2) and, where the alignment found it, Dell &amp; Jordan-Smith
(1927). Gowland’s translations are not shown. Rate each version on the rubric; ratings stay in this browser and
the button below saves them as a file to hand back.</p>
<ul>{RUBRIC}</ul>
<p>pass = no problem · minor = a small fault a reader would not be misled by ·
fail = wrong, misleading, or dishonest.</p>
<div class="bar"><button id="save">Save ratings (JSON)</button> <span id="done"></span></div>
{ITEMS}
<script>
const KEY='m4-pilot-ratings';let R={};try{R=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
function put(){try{localStorage.setItem(KEY,JSON.stringify(R))}catch(e){}count()}
function count(){let n=0;document.querySelectorAll('section').forEach(s=>{const r=R[s.dataset.id];
if(r&&Object.values(r).some(v=>Object.values(v).some(x=>x)))n++});document.getElementById('done').textContent=
n+' of {N} passages rated'}
document.querySelectorAll('section').forEach(s=>{const id=s.dataset.id;s.querySelectorAll('.rub').forEach(b=>{
const v=b.dataset.v;b.querySelectorAll('[data-c]').forEach(el=>{const c=el.dataset.c;
el.value=((R[id]||{})[v]||{})[c]||'';el.addEventListener('change',()=>{R[id]=R[id]||{};R[id][v]=R[id][v]||{};
R[id][v][c]=el.value;put()})})})});
document.getElementById('save').onclick=()=>{const a=document.createElement('a');
a.href=URL.createObjectURL(new Blob([JSON.stringify(R,null,2)],{type:'application/json'}));
a.download='m4-pilot-ratings.json';a.click()};count();
</script></body></html>
"""
