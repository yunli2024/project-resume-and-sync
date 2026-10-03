"""Local ledger storage. Standard library only; no network operations."""
from __future__ import annotations

import contextlib
import ctypes
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import uuid


class LedgerError(RuntimeError):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def inside(path, parent):
    return path.resolve().is_relative_to(parent.resolve())


def local_path(raw):
    raw = str(raw)
    if "://" in raw or raw.startswith(("\\\\", "//")):
        raise LedgerError("Use a local filesystem path, not a URI or network share.")
    path = Path(raw).expanduser().resolve()
    if os.name == "nt":
        if ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor)) == 4:
            raise LedgerError("Network drives are not supported.")
    elif Path("/proc/mounts").exists():
        matches = []
        for line in Path("/proc/mounts").read_text().splitlines():
            parts = line.split()
            if len(parts) >= 3:
                mount = Path(parts[1].replace("\\040", " ").replace("\\134", "\\"))
                if inside(path, mount):
                    matches.append((len(str(mount)), parts[2]))
        if matches and max(matches)[1] in {"nfs", "nfs4", "cifs", "smbfs", "sshfs", "fuse.sshfs", "fuse.rclone", "davfs", "9p"}:
            raise LedgerError("Network filesystems are not supported.")
    return path


def resolve(root, ledger_dir=".project-ledger"):
    if any(os.environ.get(k) for k in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY")):
        raise LedgerError("Run this helper on the local machine, outside SSH.")
    root = local_path(root)
    if not root.is_dir():
        raise LedgerError(f"Project directory does not exist: {root}")
    if "://" in ledger_dir or ledger_dir.startswith(("\\\\", "//")):
        raise LedgerError("Ledger directory must be local.")
    ledger = local_path(root / ledger_dir)
    if ledger == root or not inside(ledger, root):
        raise LedgerError("Ledger must be a directory inside the selected project.")
    # Existing child symlinks must not redirect reads or writes out of the ledger.
    for name in ("state.json", "events.jsonl", "HANDOFF.md", ".lock", ".pending.json", "archive"):
        if (ledger / name).is_symlink() or not inside(ledger / name, ledger):
            raise LedgerError(f"Ledger child must not be a symlink: {name}")
    return root, ledger


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise LedgerError(f"Invalid UTF-8 JSON: {path.name}: {exc}") from exc


def atomic_bytes(path, data):
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()  # One exact file created by this operation.


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic_json(path, value):
    atomic_bytes(path, json_bytes(value))


@contextlib.contextmanager
def lock(ledger):
    """OS releases this lock if a process crashes; the tiny lock file stays."""
    path = ledger / ".lock"
    with path.open("a+b") as handle:
        if path.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise LedgerError("Another writer is syncing. Retry after it finishes.") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_state(root, ledger):
    path = ledger / "state.json"
    if not path.exists():
        raise LedgerError("No ledger here. Use init with the intended project root.")
    state = read_json(path)
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise LedgerError("Expected ledger schema_version 1.")
    policy = state.get("ledger_policy", {})
    if policy != {"storage": "local-only", "remote_writes_allowed": False, "git_tracking_allowed": False}:
        raise LedgerError("Ledger must retain its local-only policy.")
    recorded = state.get("project", {}).get("root", "")
    if not recorded or Path(recorded).resolve() != root:
        raise LedgerError(f"Wrong project root: ledger records {recorded!r}. Select that root; do not initialize a second ledger.")
    return state


def initial_state(root):
    timestamp = now()
    return {
        "schema_version": 1,
        "revision": 0,
        "ledger_policy": {"storage": "local-only", "remote_writes_allowed": False, "git_tracking_allowed": False},
        "project": {"name": root.name, "root": str(root), "created_at": timestamp, "updated_at": timestamp},
        "objective": "", "next_action": "",
        "status": {"completed": [], "in_progress": [], "pending": []},
        "decisions": [], "constraints": [], "risks": [], "blockers": [], "unverified": [],
        "sources": {"canonical_local": [], "remote_observations": []},
        "git": {},
    }


def reverse_lines(path, block_size=8192):
    """Read newest lines first, without loading the full history."""
    if not path.exists():
        return
    with path.open("rb") as handle:
        handle.seek(0, 2)
        pos, rest = handle.tell(), b""
        while pos:
            count = min(pos, block_size)
            pos -= count
            handle.seek(pos)
            parts = (handle.read(count) + rest).split(b"\n")
            rest = parts.pop(0)
            for line in reversed(parts):
                if line.strip():
                    yield line
        if rest.strip():
            yield rest


def events(ledger, limit=5, query=None, since=None):
    if limit <= 0:
        return []
    found = []
    for line in reverse_lines(ledger / "events.jsonl"):
        try:
            item = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise LedgerError("Malformed event history; run doctor for the line number.") from exc
        if not isinstance(item, dict):
            raise LedgerError("An event must be a JSON object.")
        if query and query.casefold() not in json.dumps(item, ensure_ascii=False).casefold():
            continue
        if since:
            stamp = item.get("recorded_at", "")
            try:
                if dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")) < since:
                    continue
            except ValueError:
                continue
        found.append(item)
        if len(found) >= limit:
            break
    return found


def git_run(root, *args):
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=10)
    except FileNotFoundError:
        return None


def git_info(root):
    top = git_run(root, "rev-parse", "--show-toplevel")
    if top is None or top.returncode:
        return {"detected": False}
    head = git_run(root, "rev-parse", "--verify", "HEAD")
    status = git_run(root, "status", "--short", "--untracked-files=no")
    return {"detected": True, "root": top.stdout.strip(),
            "head": head.stdout.strip() if head and not head.returncode else "",
            "tracked_changes": status.stdout.splitlines()[:20] if status else [], "observed_at": now()}


def exclude_ledger(root, ledger):
    top = git_run(root, "rev-parse", "--show-toplevel")
    if top is None or top.returncode:
        return "no Git repository; no exclusion needed"
    git_root = Path(top.stdout.strip()).resolve()
    relative = ledger.relative_to(git_root).as_posix()
    tracked = git_run(git_root, "ls-files", "--", relative)
    if tracked and tracked.stdout.strip():
        raise LedgerError("Ledger is tracked by Git; inspect the index before changing it.")
    result = git_run(root, "rev-parse", "--git-path", "info/exclude")
    if result is None or result.returncode:
        raise LedgerError("Cannot locate Git's local exclude file.")
    path = Path(result.stdout.strip())
    if not path.is_absolute():
        path = root / path
    pattern = "/" + relative.replace("[", "\\[").replace("*", "\\*").replace("?", "\\?") + "/"
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    if pattern not in content.splitlines():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(("\n" if content and not content.endswith("\n") else "") + pattern + "\n")
    return "local Git exclusion present"


def recover(ledger, expected_root=None):
    """Finish an interrupted transaction once. Caller holds the writer lock."""
    path = ledger / ".pending.json"
    if not path.exists():
        return False
    pending = read_json(path)
    if expected_root is not None and Path(pending["state"]["project"]["root"]).resolve() != expected_root:
        raise LedgerError("Recovery journal belongs to a different project root.")
    event = pending["event"]
    log = ledger / "events.jsonl"
    # Offset is captured before any append. It also lets recovery replace a torn tail.
    offset = pending["event_offset"]
    if log.stat().st_size < offset:
        raise LedgerError("Event log was shortened since the transaction; restore its backup before recovery.")
    expected = (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")
    with log.open("r+b") as handle:
        handle.seek(offset)
        tail = handle.read()
        if tail != expected:
            if not expected.startswith(tail):
                raise LedgerError("Event log changed after interrupted sync; inspect before recovery.")
            handle.seek(offset)
            handle.write(expected)
            handle.flush()
            os.fsync(handle.fileno())
    atomic_json(ledger / "state.json", pending["state"])
    atomic_bytes(ledger / "HANDOFF.md", pending["handoff"].encode("utf-8"))
    path.unlink()  # Only this completed transaction journal.
    return True


def commit(ledger, state, event, handoff):
    log = ledger / "events.jsonl"
    if not log.exists():
        raise LedgerError("Missing events.jsonl; run doctor before writing.")
    if log.stat().st_size:
        with log.open("rb") as handle:
            handle.seek(-1, 2)
            if handle.read(1) != b"\n":
                raise LedgerError("History has an incomplete last line; run doctor before writing.")
    atomic_json(ledger / ".pending.json", {
        "state": state, "event": event, "handoff": handoff,
        "event_offset": log.stat().st_size,
    })
    recover(ledger, Path(state["project"]["root"]).resolve())
