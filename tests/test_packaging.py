import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_release
import install


class PackagingTests(unittest.TestCase):
    def test_release_contains_only_allowlisted_files_and_matches_manifest(self):
        temp = Path(tempfile.mkdtemp(prefix="project-ledger-package-test-"))
        first, second = temp / "first.zip", temp / "second.zip"
        build_release.build(ROOT, first)
        build_release.build(ROOT, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            prefix = "project-resume-and-sync/"
            names = set(archive.namelist())
            expected = {prefix + p for p in build_release.RELEASE_FILES} | {prefix + "RELEASE_MANIFEST.json"}
            self.assertEqual(names, expected)
            manifest = json.loads(archive.read(prefix + "RELEASE_MANIFEST.json"))
            for path, digest in manifest.items():
                self.assertEqual(hashlib.sha256(archive.read(prefix + path)).hexdigest(), digest)
            self.assertFalse(any(".project-ledger/" in name or "__pycache__" in name for name in names))
        with self.assertRaises(FileExistsError):
            build_release.build(ROOT, first)

    def test_install_and_upgrade_preserve_old_files_and_unrelated_content(self):
        temp = Path(tempfile.mkdtemp(prefix="project-ledger-install-test-"))
        dest = temp / "skills/project-resume-and-sync"
        install.install(ROOT, dest)
        (dest / "SKILL.md").write_text("old customized skill", encoding="utf-8")
        (dest / "personal.txt").write_text("keep me", encoding="utf-8")
        with self.assertRaises(ValueError):
            install.install(ROOT, dest)
        result = install.install(ROOT, dest, upgrade=True)
        backup = Path(result["previous_files"])
        self.assertEqual((backup / "SKILL.md").read_text(), "old customized skill")
        self.assertEqual((dest / "personal.txt").read_text(), "keep me")
        version = subprocess.run([sys.executable, str(dest / "scripts/local_ledger.py"), "--version"], capture_output=True, text=True)
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertEqual(version.stdout.strip(), "0.3.1")

    def test_public_docs_links_resolve_locally(self):
        import re
        for name in ("SKILL.md", "README.md", "README.en.md", "docs/DESIGN.md"):
            path = ROOT / name
            for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if "://" not in target and not target.startswith("#"):
                    self.assertTrue((path.parent / target.split("#")[0]).exists(), (name, target))


if __name__ == "__main__":
    unittest.main()
