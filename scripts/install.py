#!/usr/bin/env python3
"""Install runtime files only; preserve existing files before an explicit upgrade."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

from build_release import ROOT, RUNTIME_FILES
from ledger_store import atomic_bytes, local_path


def default_destination():
    # Reuse an established installation; new users get the documented user scope.
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "skills/project-resume-and-sync"
    legacy = Path.home() / ".codex/skills/project-resume-and-sync"
    if legacy.is_dir():
        return legacy
    return Path.home() / ".agents/skills/project-resume-and-sync"


def install(source, destination, upgrade=False):
    source, destination = Path(source).resolve(), local_path(destination)
    if destination == source or destination.is_relative_to(source):
        raise ValueError("Choose an installation directory outside the source checkout.")
    if destination.exists() and not upgrade:
        raise ValueError("Destination exists. Use --upgrade to back up and replace runtime files.")
    if destination.exists() and not (destination / "SKILL.md").is_file():
        raise ValueError("Existing destination is not a skill directory.")
    files = []
    for name in RUNTIME_FILES:
        path = source / name
        target = destination / name
        if not path.is_file() or not path.resolve().is_relative_to(source):
            raise ValueError(f"Missing runtime file: {name}")
        if target.is_symlink() or not target.resolve().is_relative_to(destination):
            raise ValueError(f"Redirected installation target: {name}")
        files.append((name, path.read_bytes()))
    archive = None
    if destination.exists():
        archive = destination.parent.parent / "skills-archive" / (destination.name + "-" + uuid.uuid4().hex)
        archive.mkdir(parents=True)
        for name, _ in files:
            target = destination / name
            if target.is_file():
                saved = archive / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
    for name, data in files:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_bytes(target, data)
    return {"installed": str(destination), "runtime_files": len(files), "previous_files": str(archive) if archive else None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", default=str(default_destination()))
    parser.add_argument("--upgrade", action="store_true")
    parser.add_argument("--project-root", help="Also enable ongoing continuity in this one project")
    args = parser.parse_args()
    try:
        result = install(ROOT, args.dest, args.upgrade)
        if args.project_root:
            from local_ledger import execute, make_parser
            try:
                result["project_setup"] = execute(make_parser().parse_args(["enable", "--project-root", args.project_root]))
            except (OSError, RuntimeError, ValueError) as exc:
                result["project_setup_error"] = str(exc)
                print(json.dumps(result, indent=2))
                raise SystemExit(2)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
