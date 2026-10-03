"""Continuity failures: omitted facts, archived-only reasons and stale references."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ledger_read as read
import ledger_store as store
import local_ledger as app


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ledger-retrieval-"))
        self.ledger = self.root / ".project-ledger"
        self.run_command("init")

    def run_command(self, name, *args):
        return app.execute(app.make_parser().parse_args([name, "--project-root", str(self.root), *args]))

    def state(self):
        return store.read_json(self.ledger / "state.json")

    def save(self, value):
        store.atomic_json(self.ledger / "state.json", value)

    def update(self, values, compact=False, **extra):
        return app.sync(self.root, self.ledger, {
            "expected_revision": self.state()["revision"],
            "event": {"kind": "decision", "summary": "Reviewed current facts", "source_kind": "user"},
            "set": values, **extra}, compact)

    def test_view_reports_omissions_and_exact_reference_recovers_hidden_details(self):
        state = self.state()
        state["decisions"] = [{"summary": "Accepted API", "reason": "offline operation"}] + ["other"] * 20
        self.save(state)
        output = self.run_command("resume")
        self.assertIn("3/21 current items", output)
        self.assertIn("state:0#/decisions/0", output)
        self.assertIn("offline operation", self.run_command("show", "--ref", "state:0#/decisions/0"))
        self.assertLessEqual(len(self.run_command("resume", "--max-chars", "1000")), 1000)
        before = (self.ledger / "state.json").read_bytes()
        with patch.object(read, "read_archive", side_effect=AssertionError("no archive on resume")):
            self.run_command("resume")
        self.assertEqual(before, (self.ledger / "state.json").read_bytes())

    def test_old_state_references_never_silently_change_meaning(self):
        self.update({"decisions": ["old choice"]})
        self.update({"decisions": ["new choice"]})
        with self.assertRaisesRegex(store.LedgerError, "stale"):
            self.run_command("show", "--ref", "state:1#/decisions/0")
        self.assertIn("new choice", self.run_command("show", "--ref", "state:2#/decisions/0"))

    def test_archive_only_reason_survives_compaction_and_is_searchable(self):
        state = self.state()
        state["legacy"] = {"choice": "禁止流式传输 because offline customers have no network"}
        self.save(state)
        before = (self.ledger / "state.json").read_bytes()
        result = self.update({"next_action": "ship importer"}, compact=True, archive_fields=["legacy"])
        self.assertEqual(before, (self.root / result["archive"]).read_bytes())
        output = self.run_command("history", "--source", "archives", "--topic", "禁止流式")
        ref = re.search(r"Ref: (\S+)", output).group(1)
        self.assertIn("historical_value", output)
        self.assertIn("offline customers", self.run_command("show", "--ref", ref))
        self.assertIn("No matching", self.run_command("history", "--topic", "禁止流式"))
        self.assertIn("No matching", self.run_command("history", "--source", "archives", "--topic", "禁止流式", "--since", "2099-01-01T00:00:00Z"))

    def test_unicode_json_pages_reassemble_exactly_with_escaped_pointer(self):
        state = self.state()
        value = {"reason": '中文🙂\n"quoted"' * 1300, "certainty": "unverified"}
        state["domain"] = {"a/b~c": value}
        self.save(state)
        ref = "state:0#/domain/a~1b~0c"
        offset, chunks = 0, []
        while True:
            output = self.run_command("show", "--ref", ref, "--offset", str(offset), "--max-chars", "1000")
            self.assertLessEqual(len(output), 1000)
            body = output.split("offsets):\n", 1)[1].rsplit("\nRange:", 1)[0]
            chunks.append(body)
            end, total = map(int, re.search(r"Range: \d+:(\d+)/(\d+)", output).groups())
            if end == total:
                break
            offset = end
        self.assertEqual(json.loads("".join(chunks)), value)
        for ref in ("state:0#/domain/a~2b", "state:0#/decisions/-1", "file:/etc/passwd#", "state:0"):
            with self.assertRaises(store.LedgerError):
                self.run_command("show", "--ref", ref)

    def test_exact_event_lookup_ignores_keyword_match_limit(self):
        result = self.update({"next_action": "original"})
        event_id = result["event_id"]
        with (self.ledger / "events.jsonl").open("a", encoding="utf-8") as handle:
            for i in range(1005):
                handle.write(json.dumps({"event_id": str(i), "summary": event_id}) + "\n")
        output = self.run_command("history", "--event-id", event_id)
        self.assertIn('"next_action": "original"', output)

    def test_large_history_hit_keeps_reference_instead_of_empty_result(self):
        self.update({"next_action": "reason " * 5000})
        output = self.run_command("history", "--topic", "reason", "--max-chars", "1000")
        self.assertLessEqual(len(output), 1000)
        ref = re.search(r"Ref: (\S+)", output).group(1)
        self.assertIn("excerpt", output)
        self.assertIn("reason", self.run_command("show", "--ref", ref + "/changes/next_action", "--max-chars", "1000"))

    def test_archive_read_rejects_redirects_and_wrong_project(self):
        result = self.update({"next_action": "current"}, compact=True)
        archived = self.root / result["archive"]
        state = store.read_json(archived)
        state["project"]["root"] = str(self.root.parent / "other")
        store.atomic_json(archived, state)
        with self.assertRaisesRegex(store.LedgerError, "different project"):
            self.run_command("history", "--source", "archives", "--topic", "anything")
        state = self.state()
        state["history_archives"] = ["../outside/state.json"]
        self.save(state)
        with self.assertRaisesRegex(store.LedgerError, "inside the ledger"):
            self.run_command("history", "--source", "archives", "--topic", "anything")


if __name__ == "__main__":
    unittest.main()
