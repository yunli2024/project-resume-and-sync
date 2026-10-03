#!/usr/bin/env python3
"""Run a synthetic continuity story in a new local temp directory. No API calls."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/local_ledger.py"


def run_demo():
    project = Path(tempfile.mkdtemp(prefix="project-resume-demo-"))
    checks = []

    def cli(command, *args, payload=None, expected=0):
        result = subprocess.run([sys.executable, str(HELPER), command, "--project-root", str(project), *args],
                                input=json.dumps(payload) if payload is not None else None,
                                capture_output=True, encoding="utf-8", timeout=20)
        if result.returncode != expected:
            raise RuntimeError(result.stderr or result.stdout)
        return result.stdout

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    def sync(revision, summary, values):
        return json.loads(cli("sync", "--input", "-", payload={
            "expected_revision": revision,
            "event": {"kind": "decision", "summary": summary, "source_kind": "user", "source_ref": "docs/api.md"},
            "set": values}))

    cli("init", "--objective", "Ship an offline report importer.")
    (project / "docs").mkdir()
    (project / "docs/api.md").write_text(
        "# API decision\nInitial proposal: stream results.\n"
        "Owner decision: use local CSV, because field teams work without a network.\n", encoding="utf-8")
    first = sync(0, "Propose streaming for early previews.", {"decisions": ["Streaming proposed; not accepted."]})
    cli("sync", "--input", "-", payload={
        "expected_revision": 1,
        "event": {"kind": "progress", "summary": "Teammate reports the adapter passes their tests.",
                  "source_kind": "teammate", "certainty": "reported; not locally verified"},
        "set": {"unverified": ["Teammate adapter test result awaits local evidence."]}})
    sync(2, "Reject streaming: field teams need offline operation.", {
        "decisions": ["Local CSV accepted; streaming rejected for offline operation."],
        "next_action": "Implement CSV import against docs/api.md."})
    resumed = cli("resume")
    check("resume carries the new decision, next action and remaining uncertainty",
          "Local CSV accepted" in resumed and "Implement CSV" in resumed and "awaits local evidence" in resumed)
    check("default resume fits the 6000-character budget", len(resumed.rstrip("\n")) <= 6000)
    stale = {"expected_revision": 1, "event": {"kind": "note", "summary": "stale update", "source_kind": "user"}}
    cli("sync", "--input", "-", payload=stale, expected=2)
    check("stale writer cannot replace the accepted decision", "Local CSV accepted" in cli("resume"))
    check("the earlier proposal remains retrievable",
          "Propose streaming" in cli("show", "--ref", "event:" + first["event_id"] + "#"))

    # Simulate a legacy note predating event capture. Compaction must preserve it.
    path = project / ".project-ledger/state.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["legacy_notes"] = {"reason": "CSV chosen for field teams; preserve leading zeros in account IDs."}
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    old_bytes = path.read_bytes()
    compacted = json.loads(cli("compact", "--input", "-", payload={
        "expected_revision": 3,
        "event": {"kind": "note", "summary": "Archive reviewed legacy notes; keep current work small.", "source_kind": "user"},
        "archive_fields": ["legacy_notes"], "set": {}}))
    check("compaction keeps exact prior snapshot bytes", (project / compacted["archive"]).read_bytes() == old_bytes)
    found = cli("history", "--source", "archives", "--topic", "leading zeros")
    ref = re.search(r"Ref: (\S+)", found).group(1)
    check("an archive-only reason is discoverable and readable", "leading zeros" in cli("show", "--ref", ref))
    cli("export", "--output", str(project / "handoff-draft.md"))
    check("handoff is a local review draft", "Nothing was uploaded" in (project / "handoff-draft.md").read_text(encoding="utf-8"))
    return {"passed": len(checks), "checks": checks, "project": str(project), "resume": resumed}


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = run_demo()
    print(result["resume"])
    for name in result["checks"]:
        print("PASS:", name)
    print(f"\n{result['passed']} checks passed. Synthetic files retained at {result['project']}")
