"""`burton translate`: resumable, ledgered translation runner driving `claude -p` (SPEC §6.4).

- Queue = foreign passages without a current machine record (same text hash, prompt, model).
- Each packet: build -> call `claude -p` from an empty temp dir (no project CLAUDE.md, no tools)
  -> validate (§6.5) -> retry once with the validator's message -> write the layer atomically.
- Every step is appended to state/translate/ledger.jsonl. Killing the process loses at most the
  in-flight packet; re-running continues from the layer files.
- Usage/rate limits: the packet is recorded as deferred and the run stops cleanly.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import UTC, datetime

import yaml

from .. import paths
from ..fsutil import atomic_write_text
from . import packets, schema, validate

PROMPT = "tr-v2"
LEDGER = paths.STATE / "translate" / "ledger.jsonl"
REVIEW = paths.STATE / "review" / "translate.jsonl"
LIMIT_WORDS = ("usage limit", "rate limit", "rate_limit", "overloaded", "quota")


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def append(path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def glossary() -> tuple[int, str, dict]:
    data = yaml.safe_load(paths.GLOSSARY.read_text(encoding="utf-8"))
    return data["version"], yaml.safe_dump(data, allow_unicode=True, sort_keys=False), data


def system_prompt(gloss_text: str) -> str:
    tmpl = (paths.ROOT / "burton" / "translate" / "prompts" / f"{PROMPT}.md").read_text(encoding="utf-8")
    return tmpl.replace("{glossary}", gloss_text)


# ------------------------------------------------------------------ layer file

def layer_path(unit: str, layer: str = "translations"):
    return paths.LAYERS / layer / f"{unit}.json"


def read_layer(unit: str, layer: str = "translations") -> dict:
    p = layer_path(unit, layer)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def write_layer(unit: str, data: dict, layer: str = "translations") -> None:
    atomic_write_text(layer_path(unit, layer), json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def is_current(rec: dict | None, sha: str, model: str) -> bool:
    if not rec or rec.get("text_sha1") != sha:
        return False
    return any(t.get("by") == "machine" and t.get("model") == model and t.get("prompt") == PROMPT
               for t in rec.get("translations", rec.get("glosses", [])))


def load_selection(path) -> dict[str, list[dict]]:
    """A pilot selection file (data/eval/m4-pilot.yaml): unit -> its items, in file order."""
    data = yaml.safe_load(open(path, encoding="utf-8"))
    out: dict[str, list[dict]] = {}
    for it in data["items"]:
        out.setdefault(it["id"].rsplit("-", 1)[0], []).append(it)
    return out


def unit_items(unit: str, selected: list[dict] | None) -> list[dict]:
    """The unit's foreign passages, or only the selected ones (plus selected gloss-only elements)."""
    all_p = packets.passages(unit)
    if selected is None:
        return all_p
    want = {s["id"] for s in selected if s.get("kind") != "gloss-only"}
    found = [p for p in all_p if p["packet_item"]["id"] in want]
    missing = want - {p["packet_item"]["id"] for p in found}
    if missing:
        raise SystemExit(f"selected ids not in the base text: {sorted(missing)}")
    return found + [packets.gloss_item(unit, s["id"]) for s in selected if s.get("kind") == "gloss-only"]


# ------------------------------------------------------------------ the model call

def call_claude(model: str, sys_prompt: str, user: str, out_schema: dict | None = None) -> dict:
    exe = shutil.which("claude")
    if not exe:
        raise SystemExit("`claude` CLI not found on PATH")
    work = tempfile.mkdtemp(prefix="burton-tr-")  # outside the repo: no CLAUDE.md is discovered
    try:
        sp = os.path.join(work, "system.md")
        with open(sp, "w", encoding="utf-8") as f:
            f.write(sys_prompt)
        cmd = [exe, "-p", "--model", model, "--output-format", "json",
               "--json-schema", json.dumps(out_schema or schema.PACKET_OUTPUT), "--tools", "", "--strict-mcp-config",
               "--no-session-persistence", "--system-prompt-file", sp]
        t0 = time.time()
        proc = subprocess.run(cmd, input=user, capture_output=True, text=True, encoding="utf-8",
                              cwd=work, timeout=1800)
        took = round(time.time() - t0, 1)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": (proc.stderr or proc.stdout)[-800:], "seconds": took, "limit": _is_limit(
            proc.stderr + proc.stdout)}
    meta = {"session_id": out.get("session_id"), "seconds": took,
            "usage": {k: out.get("usage", {}).get(k) for k in
                      ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")},
            "cost_usd_list": out.get("total_cost_usd"),
            "models": sorted((out.get("modelUsage") or {}).keys())}
    if out.get("is_error") or out.get("subtype") != "success" or out.get("structured_output") is None:
        msg = str(out.get("result") or out.get("api_error_status") or out.get("terminal_reason"))
        return {"ok": False, "error": msg[-800:], "limit": _is_limit(msg) or out.get("api_error_status") == 429,
                **meta}
    return {"ok": True, "output": out["structured_output"], **meta}


def _is_limit(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in LIMIT_WORDS)


# ------------------------------------------------------------------ main loop

LOCK = paths.STATE / "translate" / "runner.lock"


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
        return str(pid) in out.stdout
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def acquire_lock() -> None:
    """One runner at a time: a second runner would redo in-flight packets (found by the M1 kill test)."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        try:
            pid = int(LOCK.read_text().split()[0])
        except (ValueError, IndexError):
            pid = -1
        if pid > 0 and _pid_alive(pid):
            raise SystemExit(f"another translation runner is active (pid {pid}); not starting")
        print(f"removing stale runner lock (pid {pid} is not running)")
        LOCK.unlink()
    fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, f"{os.getpid()} {now()}\n".encode())
    os.close(fd)


def release_lock() -> None:
    if LOCK.exists() and LOCK.read_text().split()[0] == str(os.getpid()):
        LOCK.unlink()


def run(units: list[str], *, model: str, packet_size: int, max_packets: int | None, dry_run: bool,
        select=None) -> int:
    acquire_lock()
    try:
        return _run(units, model=model, packet_size=packet_size, max_packets=max_packets, dry_run=dry_run,
                    select=select)
    finally:
        release_lock()


def _run(units: list[str], *, model: str, packet_size: int, max_packets: int | None, dry_run: bool,
         select=None) -> int:
    gver, gtext, gdata = glossary()
    sys_prompt = system_prompt(gtext)
    selection = load_selection(select) if select else None
    if selection is not None:
        units = list(selection)
    done_packets = 0
    for unit in units:
        layer, glayer = read_layer(unit), read_layer(unit, "glosses")
        all_p = unit_items(unit, selection[unit] if selection is not None else None)
        queue = [p for p in all_p if not is_current(
            (glayer if p["packet_item"]["kind"] == "gloss-only" else layer).get(p["packet_item"]["id"]),
            p["text_sha1"], model)]
        print(f"{unit}: {len(all_p)} passages, {len(all_p) - len(queue)} current, {len(queue)} to translate")
        for k in range(0, len(queue), packet_size):
            if max_packets is not None and done_packets >= max_packets:
                print(f"stopping after {done_packets} packet(s) (--max-packets)")
                return 0
            batch = queue[k:k + packet_size]
            items = [b["packet_item"] for b in batch]
            ihash = packets.input_hash(items, PROMPT, model, gver)
            pid = f"{unit}:{ihash}"
            user = packets.render_packet(unit, batch[0]["title"], items)
            base = {"packet": pid, "unit": unit, "ids": [i["id"] for i in items], "prompt": PROMPT,
                    "model": model, "glossary": gver, "chars_in": len(sys_prompt) + len(user),
                    "selection": str(select) if select else None}
            if dry_run:
                d = paths.STATE / "translate" / "dry-run"
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{unit}-{ihash}.txt").write_text(sys_prompt + "\n\n=====\n\n" + user, encoding="utf-8")
                print(f"  dry run: wrote packet {pid} ({len(items)} passages)")
                continue
            append(LEDGER, {**base, "ts": now(), "status": "started"})
            res, errors = call_claude(model, sys_prompt, user), []
            if res["ok"]:
                errors = validate.check(res["output"], batch, gdata)
                if validate.blocking(errors, final=False):
                    retry_user = user + "\n\nYour previous answer failed these checks; fix them:\n- " + \
                        "\n- ".join(e["msg"] for e in validate.blocking(errors, final=False))
                    first = {k: res.get(k) for k in ("session_id", "seconds", "usage", "cost_usd_list", "models")}
                    append(LEDGER, {**base, **first, "ts": now(), "status": "retry", "errors": errors})
                    res = call_claude(model, sys_prompt, retry_user)
                    errors = validate.check(res["output"], batch, gdata) if res["ok"] else []
            meta = {k: res.get(k) for k in ("session_id", "seconds", "usage", "cost_usd_list", "models")}
            if not res["ok"]:
                status = "deferred" if res.get("limit") else "failed"
                append(LEDGER, {**base, **meta, "ts": now(), "status": status, "error": res.get("error")})
                print(f"  packet {pid}: {status}: {str(res.get('error'))[:200]}")
                if status == "deferred":
                    print("  usage or rate limit reached; stopping cleanly. Re-run later to continue.")
                    return 3
                continue
            if validate.blocking(errors, final=True):
                append(LEDGER, {**base, **meta, "ts": now(), "status": "invalid", "errors": errors})
                for e in validate.blocking(errors, final=True):
                    append(REVIEW, {"ts": now(), "packet": pid, **e})
                print(f"  packet {pid}: invalid after retry -> state/review/translate.jsonl")
                continue
            # re-read: never clobber concurrent edits by hand
            layer, glayer = read_layer(unit), read_layer(unit, "glosses")
            for entry in res["output"]["passages"]:
                b = next(x for x in batch if x["packet_item"]["id"] == entry["id"])
                if b["packet_item"]["kind"] == "gloss-only":
                    glayer[entry["id"]] = validate.to_gloss_record(glayer.get(entry["id"]), entry, b, model,
                                                                   PROMPT, res["models"], errors)
                else:
                    layer[entry["id"]] = validate.to_record(layer.get(entry["id"]), entry, b, model, PROMPT,
                                                            res["models"], errors)
            if layer:
                write_layer(unit, layer)
            if glayer:
                write_layer(unit, glayer, "glosses")
            append(LEDGER, {**base, **meta, "ts": now(), "status": "done", "issues": errors})
            done_packets += 1
            print(f"  packet {pid}: {len(items)} passages written ({res['seconds']}s, "
                  f"{len(errors)} issue(s) recorded)")
    return 0
