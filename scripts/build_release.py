#!/usr/bin/env python3
"""Build a new release archive from explicit public files only."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (
    "SKILL.md", "LICENSE", "agents/openai.yaml",
    "references/local-ledger-schema.md", "references/reconciliation-rules.md",
    "scripts/local_ledger.py", "scripts/ledger_store.py", "scripts/ledger_read.py", "scripts/ledger_setup.py",
)
RELEASE_FILES = RUNTIME_FILES + (
    "README.md", "README.en.md", "CHANGELOG.md", "AGENTS.md", ".gitignore", ".gitattributes",
    "docs/DESIGN.md", "docs/VALIDATION.md", "docs/RELATED_WORK.md", "docs/EVALUATION.md",
    "scripts/install.py", "scripts/build_release.py", "scripts/benchmark.py", "examples/demo.py",
    "tests/test_ledger.py", "tests/test_packaging.py", "tests/test_retrieval.py", "tests/test_demo.py", "tests/test_setup.py",
    ".github/workflows/tests.yml", ".github/ISSUE_TEMPLATE/bug_report.md",
)


def build(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    inputs = []
    for name in RELEASE_FILES:
        path = root / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Missing or redirected release input: {name}")
        inputs.append((name, path.read_bytes()))
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in inputs}
    inputs.append(("RELEASE_MANIFEST.json", (json.dumps(manifest, indent=2) + "\n").encode()))
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in inputs:
            info = zipfile.ZipInfo("project-resume-and-sync/" + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return {"output": str(output), "files": len(inputs), "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build(ROOT, args.output), indent=2))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
