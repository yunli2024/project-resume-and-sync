import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import install
import ledger_setup as setup
import ledger_store as store
import local_ledger as app


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ledger-setup-"))

    def enable(self, *args):
        return app.execute(app.make_parser().parse_args(["enable", "--project-root", str(self.root), *args]))

    def test_enable_creates_routing_and_ledger_and_repeats_without_mutation(self):
        result = self.enable("--objective", "Ship CSV import")
        self.assertTrue(result["ledger_created"])
        self.assertTrue(result["instructions_changed"])
        ledger = self.root / ".project-ledger"
        state = store.read_json(ledger / "state.json")
        self.assertEqual(state["objective"], "Ship CSV import")
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        again = self.enable("--objective", "Do not replace the existing objective")
        self.assertFalse(again["ledger_created"])
        self.assertFalse(again["instructions_changed"])
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_existing_utf8_bom_crlf_and_unrelated_rules_are_preserved_and_backed_up(self):
        target = self.root / "AGENTS.md"
        before = b"\xef\xbb\xbf" + "# Rules\r\n保留项目规则。\r\n".encode("utf-8")
        target.write_bytes(before)
        result = self.enable()
        self.assertTrue(target.read_bytes().startswith(before))
        self.assertEqual(Path(result["previous_instructions"]).read_bytes(), before)
        self.assertNotIn(b"\n", target.read_bytes().replace(b"\r\n", b""))

    def test_existing_ledger_is_not_reinitialized_or_rewritten(self):
        app.execute(app.make_parser().parse_args(["init", "--project-root", str(self.root)]))
        ledger = self.root / ".project-ledger"
        before = {p.name: p.read_bytes() for p in ledger.iterdir() if p.is_file()}
        result = self.enable()
        self.assertFalse(result["ledger_created"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in ledger.iterdir() if p.is_file()})

    def test_auto_uses_effective_override_and_leaves_base_untouched(self):
        (self.root / "AGENTS.md").write_text("base policy\n", encoding="utf-8")
        (self.root / "AGENTS.override.md").write_text("override policy\n", encoding="utf-8")
        result = self.enable()
        self.assertEqual(Path(result["instructions"]).name, "AGENTS.override.md")
        self.assertEqual((self.root / "AGENTS.md").read_text(), "base policy\n")

    def test_custom_guidance_and_damaged_markers_need_review_before_any_write(self):
        target = self.root / "AGENTS.md"
        for content in ("Use project-resume-and-sync only when requested.", setup.START, setup.END + setup.START, setup.BLOCK * 2):
            with self.subTest(content=content):
                target.write_text(content, encoding="utf-8")
                with self.assertRaises(store.LedgerError):
                    self.enable()
                self.assertEqual(target.read_text(), content)
                self.assertFalse((self.root / ".project-ledger").exists())

    def test_redirected_instructions_and_non_utf8_are_refused_before_init(self):
        target = self.root / "AGENTS.md"
        target.write_bytes(b"\xff\xfe\x00")
        with self.assertRaisesRegex(store.LedgerError, "UTF-8"):
            self.enable()
        real = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda p: p == target or real(p)):
            with self.assertRaisesRegex(store.LedgerError, "redirect"):
                self.enable()
        self.assertFalse((self.root / ".project-ledger").exists())

    def test_explicit_claude_adapter_and_nested_project_boundary(self):
        with self.assertRaisesRegex(store.LedgerError, "custom project routing"):
            self.enable("--ledger-dir", "custom-records")
        self.assertFalse((self.root / "custom-records").exists())
        result = self.enable("--instructions", "CLAUDE.md")
        self.assertEqual(Path(result["instructions"]).name, "CLAUDE.md")
        self.assertFalse((self.root / "AGENTS.md").exists())
        nested = self.root / "nested"
        nested.mkdir()
        args = app.make_parser().parse_args(["enable", "--project-root", str(nested)])
        with self.assertRaisesRegex(store.LedgerError, "Parent project"):
            app.execute(args)
        self.assertFalse((nested / "AGENTS.md").exists())

    def test_install_and_enable_from_public_checkout(self):
        destination = self.root / "user-skills/project-resume-and-sync"
        project = self.root / "project"
        project.mkdir()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/install.py"), "--dest", str(destination), "--project-root", str(project)],
                                capture_output=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["project_setup"]["routing_present"])
        repeat = subprocess.run([sys.executable, str(destination / "scripts/local_ledger.py"), "enable", "--project-root", str(project)],
                                capture_output=True, encoding="utf-8", timeout=20)
        self.assertEqual(repeat.returncode, 0, repeat.stderr)
        self.assertFalse(json.loads(repeat.stdout)["instructions_changed"])

    def test_install_default_uses_new_user_scope_and_preserves_legacy_location(self):
        with patch.object(Path, "home", return_value=self.root), patch.dict(os.environ, {}, clear=True):
            self.assertEqual(install.default_destination(), self.root / ".agents/skills/project-resume-and-sync")
            legacy = self.root / ".codex/skills/project-resume-and-sync"
            legacy.mkdir(parents=True)
            self.assertEqual(install.default_destination(), legacy)
            with patch.dict(os.environ, {"CODEX_HOME": str(self.root / "custom")}):
                self.assertEqual(install.default_destination(), self.root / "custom/skills/project-resume-and-sync")


if __name__ == "__main__":
    unittest.main()
