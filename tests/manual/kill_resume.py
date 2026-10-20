"""Manual M1 test: kill the translation runner mid-run, resume it, and check nothing is lost or doubled.

Uses real `claude -p` calls (subscription usage), so it is not collected by pytest.
    uv run python tests/manual/kill_resume.py [unit]
"""

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNIT = sys.argv[1] if len(sys.argv) > 1 else "1.1.1.2"
LEDGER = ROOT / "state" / "translate" / "ledger.jsonl"
LAYER = ROOT / "data" / "layers" / "translations" / f"{UNIT}.json"


def ledger_rows() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]


def main() -> int:
    start_rows = len(ledger_rows())
    cmd = ["uv", "run", "burton", "translate", "--unit", UNIT, "--packet-size", "2"]
    print("run 1:", " ".join(cmd))
    proc = subprocess.Popen(cmd, cwd=ROOT)
    while True:  # wait until one packet is done and the next has started, then kill
        rows = ledger_rows()[start_rows:]
        if any(r["status"] == "done" for r in rows) and rows[-1]["status"] == "started":
            break
        if proc.poll() is not None:
            print("runner finished before it could be killed; test inconclusive")
            return 2
        time.sleep(2)
    time.sleep(5)
    # `uv run` starts burton as a child process: kill the whole tree, as a user's Ctrl+C or a crash would
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()
    proc.wait()
    time.sleep(2)
    print("runner lock left behind by the kill:", (ROOT / "state/translate/runner.lock").exists())
    rows = ledger_rows()[start_rows:]
    killed_in_flight = rows[-1]
    done_before = {i for r in rows if r["status"] == "done" for i in r["ids"]}
    print(f"killed with packet {killed_in_flight['packet']} in flight; done before kill: {sorted(done_before)}")

    print("run 2: resume")
    subprocess.run(cmd, cwd=ROOT, check=True)
    rows = ledger_rows()[start_rows:]
    layer = json.loads(LAYER.read_text(encoding="utf-8"))
    done_ids = [i for r in rows if r["status"] == "done" for i in r["ids"]]
    machine = {k: sum(1 for t in v["translations"] if t["by"] == "machine") for k, v in layer.items()}
    report = {
        "passages_in_layer": len(layer),
        "each_has_exactly_one_machine_translation": all(v == 1 for v in machine.values()),
        "ids_translated_twice": sorted({i for i in done_ids if done_ids.count(i) > 1}),
        "done_before_kill_redone": sorted(done_before & {i for r in rows[len(rows) - 0:] for i in r["ids"]}),
        "ledger_statuses": [r["status"] for r in rows],
    }
    print(json.dumps(report, indent=2))
    ok = report["each_has_exactly_one_machine_translation"] and not report["ids_translated_twice"]
    print("KILL/RESUME:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
