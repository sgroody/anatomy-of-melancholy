"""`burton syn-audit`: a blind second reading of the synopsis structure (M7 spot check, round s1).

The sample (data/eval/m7-structure-sample.yaml) was drawn before any structure file existed. For each sheet
holding sampled strings, a fresh `claude -p` call (prompt `syn-audit-v1`, no tools) gets the image and the
sheet's hidden-table strings, never the structure file or the built tree, and names each sampled string's
parent. Answers go to data/eval/m7-structure-rater.jsonl, labelled with model, prompt and date; every call is
in state/syn-audit/ledger.jsonl and a run resumes from the answers file. `report()` compares the answers
with data/synopses/<pN>.json and writes the agreement into the sample file; disagreements are settled by
re-reading the image, by hand, and recorded there. The synopses carry no Gowland matter (no bracketed text).
A packet lists the strings of the hidden table behind its image only; the EPUB files a few strings under the
next sheet's table (round s1: "from his friends", "Sect. 3. A consolatory ..."), so a rater may name those by text.
"""

import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import UTC, datetime

import yaml
from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..ingest.synopses import FILES, GLYPHS
from ..translate import runner

PROMPT = "syn-audit-v1"
SAMPLE = paths.ROOT / "data" / "eval" / "m7-structure-sample.yaml"
OUT = paths.ROOT / "data" / "eval" / "m7-structure-rater.jsonl"
LEDGER = paths.STATE / "syn-audit" / "ledger.jsonl"
SCHEMA = {"type": "object", "required": ["items"], "additionalProperties": False, "properties": {
    "items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "parent", "reason", "confidence"],
        "properties": {"id": {"type": "string"}, "parent": {"type": "string"}, "reason": {"type": "string"},
                       "confidence": {"type": "string", "enum": ["high", "medium", "low"]}}}}}}


def sheets(part: str) -> dict[str, list[tuple[str, str]]]:
    """image name -> [(id, text)] of the non-glyph strings in the hidden table behind it."""
    d = etree.parse(str(paths.XHTML / f"{FILES[part]}.xhtml"))
    out = {}
    for img in d.iter("{*}img"):
        table = d.find(f".//*[@id='{img.get('aria-describedby')}']") if img.get("aria-describedby") else None
        if table is None:
            continue
        rows = [(p.get("id"), " ".join("".join(p.itertext()).split())) for p in table.iter("{*}p")]
        out[img.get("src").rsplit("/", 1)[-1].removesuffix(".png")] = [r for r in rows if r[1] not in GLYPHS]
    return out


def packets() -> list[dict]:
    items = yaml.safe_load(SAMPLE.read_text(encoding="utf-8"))["items"]
    out = []
    for part in FILES:
        for img, rows in sheets(part).items():
            ids = {r[0] for r in rows}
            ask = [i for i in items if i["part"] == part and i["id"] in ids]
            if ask:
                out.append({"part": part, "image": img, "strings": rows, "ask": [i["id"] for i in ask]})
    return out


def call(model: str, packet: dict) -> dict:
    exe = shutil.which("claude")
    if not exe:
        raise SystemExit("`claude` CLI not found on PATH")
    data = base64.b64encode((paths.IMAGES / f"{packet['image']}.png").read_bytes()).decode()
    text = ("Strings on this sheet (id: text):\n" + "\n".join(f"{i}: {t}" for i, t in packet["strings"])
            + "\n\nName the parent of each of these items: " + ", ".join(packet["ask"]))
    msg = {"type": "user", "message": {"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}},
        {"type": "text", "text": text}]}}
    work = tempfile.mkdtemp(prefix="burton-syn-")  # outside the repo: no CLAUDE.md is discovered
    try:
        sp = os.path.join(work, "system.md")
        with open(sp, "w", encoding="utf-8") as f:
            f.write((paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8"))
        cmd = [exe, "-p", "--model", model, "--input-format", "stream-json", "--output-format", "stream-json",
               "--verbose", "--json-schema", json.dumps(SCHEMA), "--tools", "", "--strict-mcp-config",
               "--no-session-persistence", "--system-prompt-file", sp]
        t0 = time.time()
        proc = subprocess.run(cmd, input=json.dumps(msg) + "\n", capture_output=True, text=True, encoding="utf-8",
                              cwd=work, timeout=runner.CALL_TIMEOUT)
        took = round(time.time() - t0, 1)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("{")]
    out = json.loads(lines[-1]) if lines else {}
    if out.get("type") != "result" or out.get("is_error") or out.get("structured_output") is None:
        err = str(out.get("result") or proc.stderr or proc.stdout)[-800:]
        return {"ok": False, "error": err, "limit": runner._is_limit(err), "seconds": took}
    return {"ok": True, "output": out["structured_output"], "seconds": took, "cost_usd_list": out.get("total_cost_usd"),
            "models": sorted((out.get("modelUsage") or {}).keys())}


def run(model: str = "claude-opus-5-5", dry_run: bool = False) -> dict:
    done = {json.loads(ln)["id"] for ln in OUT.read_text(encoding="utf-8").splitlines()} if OUT.exists() else set()
    todo = [p for p in packets() if set(p["ask"]) - done]
    if dry_run:
        return {"packets": len(todo), "items": sum(len(p["ask"]) for p in todo)}
    stats = {"packets": 0, "answers": 0, "cost_usd_list": 0.0}
    for p in todo:
        res = call(model, p)
        runner.append(LEDGER, {"ts": runner.now(), "prompt": PROMPT, "model": model, "image": p["image"],
                               "ask": p["ask"], **{k: v for k, v in res.items() if k != "output"},
                               "answers": res.get("output")})
        if not res["ok"]:
            if res.get("limit"):
                print("usage limit reached; run again later to resume")
                return stats | {"stopped": "limit"}
            print(f"{p['image']}: failed: {res['error'][:200]}")
            continue
        stats["packets"] += 1
        stats["cost_usd_list"] += res.get("cost_usd_list") or 0
        with OUT.open("a", encoding="utf-8", newline="\n") as f:
            for a in res["output"]["items"]:
                if a["id"] in p["ask"] and a["id"] not in done:
                    done.add(a["id"])
                    stats["answers"] += 1
                    f.write(json.dumps({**a, "part": p["part"], "image": p["image"], "by": "machine", "model": model,
                                        "prompt": PROMPT, "date": datetime.now(UTC).date().isoformat()},
                                       ensure_ascii=False) + "\n")
    return stats


def structure_parents(part: str) -> dict[str, list[str]]:
    """Paragraph id -> the parents the structure gives it: a node's parent node (or 'root'); a head or label
    paragraph counts as its node, so its node's parent and the node itself are both accepted."""
    tree = json.loads((paths.DATA / "synopses" / f"{part}.json").read_text(encoding="utf-8"))
    out = {}

    def visit(n: dict, parent: str):
        out[n["src_p"]] = [parent]
        for k in ("head", "label"):
            if k in n:
                out[n[k]["src_p"]] = [parent, n["src_p"]]
        for c in n["children"]:
            visit(c, n["src_p"])

    for t in tree["children"]:
        visit(t, "root")
    return out


def report() -> dict:
    doc = yaml.safe_load(SAMPLE.read_text(encoding="utf-8"))
    answers = {}
    if OUT.exists():
        for ln in OUT.read_text(encoding="utf-8").splitlines():
            a = json.loads(ln)
            answers[a["id"]] = a
    parents = {part: structure_parents(part) for part in FILES}
    tally = {part: {"agree": 0, "disagree": 0, "unanswered": 0} for part in FILES}
    for it in doc["items"]:
        a = answers.get(it["id"])
        want = parents[it["part"]].get(it["id"])
        it["structure_parent"] = want[0] if want else None
        if a is None:
            it["parent"], it["label"] = None, None
            tally[it["part"]]["unanswered"] += 1
            continue
        it["parent"] = a["parent"]
        it["rater"] = {k: a[k] for k in ("reason", "confidence", "model", "prompt", "date")}
        it["label"] = "agree" if a["parent"] in (want or []) else "disagree"
        tally[it["part"]][it["label"]] += 1
    doc["result"] = tally
    head = "# M7 held-out spot check of the synopsis structure. Sample and rule fixed before labelling.\n"
    atomic_write_text(SAMPLE, head + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=120))
    return tally
