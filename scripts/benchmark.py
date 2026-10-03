#!/usr/bin/env python3
"""Reproduce context-volume and CLI latency measurements with synthetic records."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

from ledger_store import initial_state, json_bytes
from local_ledger import VERSION, view


def benchmark(runs):
    helper = Path(__file__).with_name("local_ledger.py")
    results = []
    for name, completed, event_count in (("small", 3, 100), ("long_history", 3, 20000), ("legacy_snapshot", 1000, 20000)):
        root = Path(tempfile.mkdtemp(prefix="ledger-benchmark-"))
        ledger = root / ".project-ledger"
        ledger.mkdir()
        state = initial_state(root)
        state["objective"] = "Ship the offline CSV importer."
        state["next_action"] = "Check Unicode column labels with the parser fixture."
        state["decisions"] = ["CSV accepted; streaming rejected for offline users."]
        state["status"]["completed"] = [f"Task {i}: " + "Recorded synthetic evidence. " * 10 for i in range(completed)]
        state["unverified"] = ["Teammate performance report awaits local evidence."]
        (ledger / "state.json").write_bytes(json_bytes(state))
        (ledger / "HANDOFF.md").write_text(view(state), encoding="utf-8")
        with (ledger / "events.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for i in range(event_count):
                handle.write(json.dumps({"event_id": f"synthetic-{i}", "recorded_at": "2026-01-01T00:00:00Z",
                                         "kind": "progress", "source_kind": "local-artifact", "summary": f"Synthetic task {i}"}) + "\n")
        paths = [ledger / name for name in ("state.json", "HANDOFF.md", "events.jsonl")]
        before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
        timings = []
        for _ in range(runs):
            start = time.perf_counter()
            process = subprocess.run([sys.executable, str(helper), "resume", "--project-root", str(root)],
                                     capture_output=True, encoding="utf-8", timeout=30, check=True)
            timings.append(time.perf_counter() - start)
        text = process.stdout.rstrip("\n")
        after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
        if before != after or len(text) > 6000:
            raise AssertionError("Read-only/context-budget contract failed")
        results.append({"case": name, "completed_items": completed, "events": event_count,
                        "state_bytes": paths[0].stat().st_size, "event_bytes": paths[2].stat().st_size,
                        "resume_characters": len(text), "resume_utf8_bytes": len(text.encode("utf-8")),
                        "median_process_seconds": round(statistics.median(timings), 4), "input_unchanged": before == after})
    return {"helper_version": VERSION, "os": platform.system(), "python": platform.python_version(),
            "fresh_processes_per_case": runs, "includes": "Python startup + local IO + resume formatting",
            "measures_tokens": False, "cases": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.runs <= 100:
        parser.error("--runs must be between 1 and 100")
    print(json.dumps(benchmark(args.runs), indent=2))
