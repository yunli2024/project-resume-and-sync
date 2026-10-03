"""Behavior tests use synthetic local projects. Temporary artifacts are retained."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import ledger_store as store
import local_ledger as app


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="project-ledger-test-"))
        self.ledger = self.root / ".project-ledger"
        self.cli("init")

    def cli(self, command, *args, ok=True, root=None):
        result = subprocess.run([sys.executable, str(SCRIPTS / "local_ledger.py"), command,
                                 "--project-root", str(root or self.root), *map(str, args)],
                                capture_output=True, encoding="utf-8", timeout=20)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def state(self):
        return store.read_json(self.ledger / "state.json")

    def save(self, state):
        store.atomic_json(self.ledger / "state.json", state)

    def payload(self, revision=None, **updates):
        return {"expected_revision": self.state().get("revision", 0) if revision is None else revision,
                "event": {"kind": "decision", "summary": "Use the stable adapter; streaming deferred.",
                          "source_kind": "user", "source_ref": "docs/decision.md"}, "set": updates}

    def sync(self, payload=None, compact=False):
        return app.sync(self.root, self.ledger, payload or self.payload(), compact)

    def hashes(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.ledger.iterdir() if p.is_file()}

    def test_resume_is_read_only_and_does_not_run_git_or_diagnosis(self):
        before = self.hashes()
        args = app.make_parser().parse_args(["resume", "--project-root", str(self.root)])
        with patch.object(app, "git_info", side_effect=AssertionError("unexpected Git")), patch.object(app, "doctor", side_effect=AssertionError("unexpected diagnosis")):
            output = app.execute(args)
        self.assertIn("revision: 0", output)
        self.assertEqual(before, self.hashes())

    def test_large_legacy_snapshot_is_bounded_without_mutation(self):
        state = self.state()
        state.pop("revision")
        state["status"]["completed"] = ["Historical result " + "详" * 2000] * 300
        state["decisions"] = ["Old decision " * 90] * 100
        state["next_action"] = "Keep the accepted final artifact."
        self.save(state)
        before = self.hashes()
        out = self.cli("resume").stdout
        self.assertLessEqual(len(out), app.DEFAULT_BUDGET + 1)
        self.assertIn(state["next_action"], out)
        self.assertEqual(before, self.hashes())
        self.assertTrue(app.warnings(state))

    def test_sync_updates_only_named_paths_and_records_provenance(self):
        state = self.state()
        state["domain_extension"] = {"keep": "unknown fields survive"}
        state["status"]["pending"] = ["unrelated work"]
        self.save(state)
        result = self.sync(self.payload(**{"status.in_progress": ["adapter"], "next_action": "Review parser."}))
        after = self.state()
        self.assertEqual(result["revision"], 1)
        self.assertEqual(after["domain_extension"], state["domain_extension"])
        self.assertEqual(after["status"]["pending"], ["unrelated work"])
        event = store.events(self.ledger, 1)[0]
        self.assertEqual(event["changes"]["next_action"], "Review parser.")
        self.assertEqual(event["source_ref"], "docs/decision.md")
        self.assertIn("Review parser.", (self.ledger / "HANDOFF.md").read_text())

    def test_stale_or_missing_revision_does_not_mutate_any_record(self):
        self.sync()
        before = self.hashes()
        with self.assertRaises(store.LedgerError):
            self.sync(self.payload(revision=0, next_action="stale overwrite"))
        payload = self.payload()
        payload.pop("expected_revision")
        with self.assertRaises(store.LedgerError):
            self.sync(payload)
        self.assertEqual(before, self.hashes())

    def test_reading_and_rendering_do_not_refresh_fact_time(self):
        state = self.state()
        state["project"]["updated_at"] = "2020-01-01T00:00:00Z"
        self.save(state)
        before = (self.ledger / "state.json").read_bytes()
        self.cli("render")
        self.cli("inspect")
        self.assertEqual(before, (self.ledger / "state.json").read_bytes())
        self.cli("record", "--kind", "note", "--summary", "Historical annotation", "--source-kind", "user")
        self.assertEqual(self.state()["project"]["updated_at"], "2020-01-01T00:00:00Z")
        self.assertIn("Historical annotation", (self.ledger / "HANDOFF.md").read_text())

    def test_failed_transaction_recovers_once(self):
        original = store.atomic_json
        def fail_state(path, value):
            if path.name == "state.json":
                raise OSError("simulated interruption after event append")
            return original(path, value)
        with patch.object(store, "atomic_json", side_effect=fail_state):
            with self.assertRaises(OSError):
                self.sync(self.payload(next_action="Recover this update."))
        self.assertTrue((self.ledger / ".pending.json").exists())
        self.cli("resume", ok=False)
        before_events = (self.ledger / "events.jsonl").read_bytes()
        self.cli("recover")
        self.cli("recover")
        self.assertEqual(before_events, (self.ledger / "events.jsonl").read_bytes())
        self.assertEqual(self.state()["next_action"], "Recover this update.")
        self.assertFalse((self.ledger / ".pending.json").exists())

    def test_torn_event_append_recovers_exact_bytes(self):
        original = store.recover
        with patch.object(store, "recover", side_effect=OSError("crash before append")):
            with self.assertRaises(OSError):
                self.sync(self.payload(next_action="保留中文记录"))
        pending = store.read_json(self.ledger / ".pending.json")
        encoded = (json.dumps(pending["event"], ensure_ascii=False) + "\n").encode()
        with (self.ledger / "events.jsonl").open("ab") as handle:
            handle.write(encoded[:len(encoded)//2])
        with store.lock(self.ledger):
            self.assertTrue(original(self.ledger, self.root))
        self.assertEqual(store.events(self.ledger, 1)[0]["changes"]["next_action"], "保留中文记录")
        self.assertEqual(len(store.events(self.ledger, 10)), 2)

    def test_recovery_refuses_unexpected_tail(self):
        with patch.object(store, "recover", side_effect=OSError("crash")):
            with self.assertRaises(OSError):
                self.sync()
        with (self.ledger / "events.jsonl").open("ab") as handle:
            handle.write(b'{"unexpected":true}\n')
        before = self.hashes()
        self.cli("recover", ok=False)
        self.assertEqual(before, self.hashes())

    def test_concurrent_writers_cannot_lose_updates(self):
        payload = self.payload(next_action="one winning update")
        path = self.root / "change.json"
        path.write_bytes(store.json_bytes(payload))
        command = [sys.executable, str(SCRIPTS / "local_ledger.py"), "sync", "--project-root", str(self.root), "--input", str(path)]
        a = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        b = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        a.communicate(timeout=20)
        b.communicate(timeout=20)
        self.assertEqual(sorted([a.returncode, b.returncode]), [0, 2])
        self.assertEqual(self.state()["revision"], 1)
        self.assertEqual(len(store.events(self.ledger, 10)), 2)

    def test_locked_writer_exits_promptly(self):
        path = self.root / "change.json"
        path.write_bytes(store.json_bytes(self.payload()))
        with store.lock(self.ledger):
            result = self.cli("sync", "--input", path, ok=False)
        self.assertIn("Another writer", result.stderr)

    def test_compaction_preserves_exact_prior_files_and_history(self):
        state = self.state()
        state["status"]["completed"] = ["historical " + str(i) for i in range(40)]
        state["old_domain"] = {"evidence": "keep exact old content"}
        state["unrelated"] = {"retain": True}
        self.save(state)
        old_state = (self.ledger / "state.json").read_bytes()
        old_handoff = (self.ledger / "HANDOFF.md").read_bytes()
        old_events = (self.ledger / "events.jsonl").read_bytes()
        payload = self.payload(**{"status.completed": ["current outcome"]})
        payload["archive_fields"] = ["old_domain"]
        result = self.sync(payload, compact=True)
        archive = self.root / result["archive"]
        self.assertEqual(archive.read_bytes(), old_state)
        self.assertEqual((archive.parent / "HANDOFF.md").read_bytes(), old_handoff)
        self.assertTrue((self.ledger / "events.jsonl").read_bytes().startswith(old_events))
        self.assertNotIn("old_domain", self.state())
        self.assertEqual(self.state()["unrelated"], {"retain": True})
        self.assertEqual(self.state()["history_archives"], [result["archive"]])

    def test_protected_fields_and_invalid_list_shape_are_rejected(self):
        before = self.hashes()
        for update in ({"revision": 90}, {"project.root": "/wrong"}, {"ledger_policy": {}}, {"status": []}, {"decisions": "not a list"}):
            with self.subTest(update=update), self.assertRaises(store.LedgerError):
                self.sync(self.payload(**update))
        self.assertEqual(before, self.hashes())

    def test_compact_cannot_archive_core_fields(self):
        payload = self.payload()
        payload["archive_fields"] = ["risks"]
        with self.assertRaises(store.LedgerError):
            self.sync(payload, compact=True)

    def test_wrong_project_root_is_rejected(self):
        state = self.state()
        state["project"]["root"] = str(self.root.parent / "some-other-project")
        self.save(state)
        before = self.hashes()
        self.assertIn("Wrong project root", self.cli("resume", ok=False).stderr)
        self.assertEqual(before, self.hashes())

    def test_nested_init_points_to_existing_parent(self):
        child = self.root / "module"
        child.mkdir()
        result = self.cli("init", root=child, ok=False)
        self.assertIn("Parent project ledger", result.stderr)
        self.assertFalse((child / ".project-ledger").exists())
        self.cli("init", "--allow-nested", root=child)
        self.assertEqual(store.read_json(child / ".project-ledger/state.json")["project"]["root"], str(child))

    def test_init_never_overwrites_existing_ledger(self):
        before = self.hashes()
        self.cli("init", ok=False)
        self.assertEqual(before, self.hashes())

    def test_remote_roots_and_ssh_are_rejected(self):
        for value in ("ssh://server/project", "//server/share", "\\\\server\\share"):
            with self.subTest(value=value), self.assertRaises(store.LedgerError):
                store.resolve(value)
        with patch.dict(os.environ, {"SSH_CONNECTION": "test"}):
            with self.assertRaises(store.LedgerError):
                store.resolve(str(self.root))
        with self.assertRaises(store.LedgerError):
            store.resolve(str(self.root), "../escaped-ledger")

    def test_ledger_child_symlink_escape_is_rejected(self):
        alias = Path(tempfile.mkdtemp(prefix="project-ledger-link-test-"))
        target = alias / ".project-ledger"
        target.mkdir()
        try:
            (target / "state.json").symlink_to(self.ledger / "state.json")
        except OSError:
            self.skipTest("Creating symlinks is not permitted on this host")
        with self.assertRaises(store.LedgerError):
            store.resolve(str(alias))

    def test_remote_observation_time_is_not_invented(self):
        event = {"kind": "remote-observation", "summary": "Job completed", "source_kind": "remote-observation", "source_ref": "cluster/job.log"}
        with self.assertRaises(store.LedgerError):
            app.new_event(event)
        event["observed_at"] = "2026-01-01T00:00:00"
        with self.assertRaises(store.LedgerError):
            app.new_event(event)
        event["observed_at"] = "2026-01-01T00:00:00Z"
        self.assertEqual(app.new_event(event)["observed_at"], event["observed_at"])

    def test_credential_like_event_is_rejected(self):
        payload = self.payload()
        payload["event"]["details"] = "token=example-secret"
        with self.assertRaises(store.LedgerError):
            self.sync(payload)

    def test_teammate_and_reproduction_metadata_survive(self):
        payload = self.payload()
        payload["event"].update(source_kind="teammate", actor="Example teammate", certainty="reported",
                                reproduce={"command": "python -m unittest", "inputs": ["fixture.json"]})
        self.sync(payload)
        event = store.events(self.ledger, 1)[0]
        self.assertEqual(event["certainty"], "reported")
        self.assertEqual(event["reproduce"]["inputs"], ["fixture.json"])

    def test_tail_reads_only_requested_events(self):
        with (self.ledger / "events.jsonl").open("a", encoding="utf-8") as handle:
            for i in range(20000):
                handle.write(json.dumps({"event_id": str(i), "summary": "中文" * 5}) + "\n")
        loads = json.loads
        with patch.object(store.json, "loads", wraps=loads) as mocked:
            found = store.events(self.ledger, 3)
            self.assertEqual(mocked.call_count, 3)
        self.assertEqual([e["event_id"] for e in found], ["19999", "19998", "19997"])

    def test_unicode_cli_and_topic_search(self):
        state = self.state()
        state["status"]["pending"] = ["ordinary work", "中文路径：继续核对版本"]
        self.save(state)
        result = self.cli("resume", "--topic", "核对").stdout
        self.assertIn("继续核对版本", result)
        self.assertNotIn("ordinary work", result)

    def test_reader_does_not_pair_old_snapshot_with_future_event(self):
        old = self.state()
        self.sync(self.payload(next_action="new state"))
        current = self.state()
        self.assertFalse(any(e.get("revision", 0) > old["revision"] for e in app.recent_for_state(self.ledger, old)))
        self.assertEqual(app.recent_for_state(self.ledger, current)[0]["revision"], current["revision"])

    def test_recovery_checks_recorded_root(self):
        with patch.object(store, "recover", side_effect=OSError("crash")):
            with self.assertRaises(OSError):
                self.sync()
        before = self.hashes()
        with self.assertRaises(store.LedgerError):
            store.recover(self.ledger, self.root.parent)
        self.assertEqual(before, self.hashes())

    def test_known_redirect_is_rejected_even_without_symlink_privilege(self):
        real = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda p: p.name == "state.json" or real(p)):
            with self.assertRaises(store.LedgerError):
                store.resolve(str(self.root))

    def test_history_filters_and_budget(self):
        self.sync(self.payload(next_action="needle update"))
        self.sync(self.payload(next_action="other update"))
        result = self.cli("history", "--topic", "needle", "--max-chars", "2000").stdout
        self.assertIn("needle update", result)
        self.assertNotIn("other update", result)
        self.assertLessEqual(len(result), 2001)
        self.assertIn("No matching", self.cli("history", "--since", "2099-01-01T00:00:00Z").stdout)

    def test_export_is_local_new_file_and_no_overwrite(self):
        destination = self.root / "review" / "handoff.md"
        before = self.hashes()
        self.cli("export", "--output", destination)
        self.assertIn("Nothing was uploaded", destination.read_text())
        self.cli("export", "--output", destination, ok=False)
        self.assertEqual(before, self.hashes())
        self.cli("export", "--output", self.ledger / "inside.md", ok=False)

    def test_doctor_reports_bad_history_without_rewriting_it(self):
        with (self.ledger / "events.jsonl").open("a") as handle:
            handle.write("{broken}\n")
        before = self.hashes()
        result = json.loads(self.cli("doctor", ok=False).stdout)
        self.assertFalse(result["valid"])
        self.assertIn("line 2", result["errors"][0])
        self.assertEqual(before, self.hashes())

    def test_doctor_detects_duplicate_ids(self):
        line = (self.ledger / "events.jsonl").read_bytes()
        with (self.ledger / "events.jsonl").open("ab") as handle:
            handle.write(line)
        self.assertFalse(app.doctor(self.root, self.ledger)["valid"])

    def test_non_git_installation_does_not_require_git(self):
        with patch.object(store, "git_run", return_value=None):
            self.assertIn("no Git", store.exclude_ledger(self.root, self.ledger))

    @unittest.skipUnless(shutil.which("git"), "Git is not installed")
    def test_git_project_and_linked_worktree_exclusion(self):
        root = Path(tempfile.mkdtemp(prefix="project-ledger-git-test-"))
        def git(*args):
            result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout
        git("init")
        (root / "README.md").write_text("Synthetic fixture\n")
        git("add", "README.md")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "fixture")
        self.cli("init", root=root)
        self.assertEqual(subprocess.run(["git", "-C", str(root), "check-ignore", "-q", ".project-ledger/state.json"]).returncode, 0)
        worktree = root.parent / (root.name + "-linked")
        git("worktree", "add", "-b", "fixture-linked", str(worktree))
        self.cli("init", root=worktree)
        self.assertEqual(subprocess.run(["git", "-C", str(worktree), "check-ignore", "-q", ".project-ledger/state.json"]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
