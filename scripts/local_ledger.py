#!/usr/bin/env python3
"""Project Resume and Sync: small current context, durable local history."""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
from pathlib import Path
import re
import shutil
import sys
import uuid

from ledger_store import (LedgerError, atomic_bytes, commit, events, exclude_ledger,
                          git_info, initial_state, inside, json_bytes, load_state,
                          local_path, lock, now, read_json, recover, resolve)
from ledger_read import (archive_hits, entries, event_by_id, history_view,
                         resolve_ref, show_page)

VERSION = "0.3.1"
DEFAULT_BUDGET = 6000  # Unicode characters, not an estimate of model tokens.
SNAPSHOT_SOFT_LIMIT = 16000
KIND = {"decision", "progress", "risk", "blocker", "conflict", "pivot", "run", "remote-observation", "note"}
PROTECTED = {"schema_version", "revision", "ledger_policy", "project", "history_archives", "last_event_at"}
CORE = PROTECTED | {"objective", "next_action", "status", "decisions", "constraints", "risks", "blockers", "unverified", "sources", "git"}


def label(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        summary = value.get("summary") or value.get("name")
        if summary:
            suffix = "; ".join(f"{k}: {value[k]}" for k in ("status", "certainty", "observed_at", "source_ref") if value.get(k))
            return str(summary) + (f" [{suffix}]" if suffix else "")
    return json.dumps(value, ensure_ascii=False)


def clipped(text, size):
    text = " ".join(text.split())
    return text if len(text) <= size else text[:size - 17] + "… [excerpt only]"


def recent_for_state(ledger, state, query=None):
    # A reader can overlap a writer. Never pair an older snapshot with a newer
    # revision's events; the writer appends before replacing state.
    revision = state.get("revision", 0)
    return [e for e in events(ledger, 3, query) if e.get("revision", 0) <= revision]


def view(state, recent=(), budget=DEFAULT_BUDGET, query=None):
    """Bound output at presentation time; never cut stored facts to meet a budget."""
    project = state["project"]
    lines = [f"# {clipped(project['name'], 150)}",
             f"Snapshot: {project.get('updated_at', 'unknown')} | revision: {state.get('revision', 0)}",
             "Recorded context; verify sources for the current task."]
    prefix = f"state:{state.get('revision', 0)}#"
    candidates = {key: value for key, value in entries(state)
                  if key.split('/')[1] not in PROTECTED | {'git'} and value not in ('', None)}
    if query:
        candidates = {key: value for key, value in candidates.items()
                      if key in {'/objective', '/next_action'}
                      or query.casefold() in (key + ' ' + json.dumps(value, ensure_ascii=False)).casefold()}
    shown, excerpts = set(), 0
    def add(title, ref, item, width=650, state_key=None):
        nonlocal excerpts
        summary = label(item)
        short = clipped(summary, width)
        text = f"- {title} [{ref}]: {short}"
        if len("\n".join(lines)) + len(text) + 260 <= budget:
            lines.append(text)
            if state_key:
                shown.add(state_key)
            excerpts += int(short != summary or isinstance(item, dict))

    def field(title, key, limit=1, width=650):
        matches = [(k, v) for k, v in candidates.items() if k == key or k.startswith(key + '/')]
        for k, value in matches[:limit]:
            add(title, prefix + k, value, width, k)

    field("Next", "/next_action", width=650)
    field("Objective", "/objective", width=450)
    for event in recent:
        attribution = "; ".join(str(event[k]) for k in ("kind", "source_kind", "certainty") if event.get(k))
        add("Event", f"event:{event.get('event_id', '')}#",
            f"{event.get('recorded_at', '?')} [{attribution}] {event.get('summary', '')}", 300)
    if query:
        for key, value in candidates.items():
            if key not in {'/objective', '/next_action'}:
                add("Match", prefix + key, value, 1400, key)
    else:
        for title, key, limit, width in (
            ("Active", "/status/in_progress", 2, 300), ("Blocker", "/blockers", 2, 300),
            ("Pending", "/status/pending", 2, 250), ("Decision", "/decisions", 3, 300),
            ("Risk", "/risks", 2, 250), ("Constraint", "/constraints", 2, 250),
            ("Unverified", "/unverified", 1, 250), ("Source", "/sources/canonical_local", 3, 150),
            ("Completed", "/status/completed", 1, 250)):
            field(title, key, limit, width)
    notice = (f"\nCoverage: {len(shown)}/{len(candidates)} current items shown"
              f"{' for topic' if query else ''}; {excerpts} summary/excerpt rows. "
              f"Archives: {len(state.get('history_archives', []))}.\n"
              "Detail: show --ref '<ref>'. Find: --topic or history; old snapshots: history --source archives --topic '<words>'.\n")
    return "\n".join(lines) + notice


def check_snapshot(state):
    errors = []
    for key in ("objective", "next_action"):
        if not isinstance(state.get(key, ""), str):
            errors.append(f"{key} must be text")
    status = state.get("status", {})
    if not isinstance(status, dict) or any(not isinstance(status.get(k, []), list) for k in ("completed", "in_progress", "pending")):
        errors.append("status requires completed/in_progress/pending lists")
    for key in ("decisions", "constraints", "risks", "blockers", "unverified"):
        if not isinstance(state.get(key, []), list):
            errors.append(f"{key} must be a list")
    if not isinstance(state.get("sources", {}), dict):
        errors.append("sources must be an object")
    revision = state.get("revision", 0)
    if type(revision) is not int or revision < 0:
        errors.append("revision must be a nonnegative integer")
    if errors:
        raise LedgerError("; ".join(errors))


def warnings(state):
    result = []
    if len(json_bytes(state)) > SNAPSHOT_SOFT_LIMIT:
        result.append("Large snapshot: use compact with a reviewed current summary; full history stays local.")
    if len(state.get("status", {}).get("completed", [])) > 10:
        result.append("More than 10 completed items in current state; older work belongs in history.")
    return result


def new_event(raw):
    if not isinstance(raw, dict):
        raise LedgerError("event must be an object")
    event = copy.deepcopy(raw)
    if event.get("kind") not in KIND or not isinstance(event.get("summary"), str) or not event["summary"].strip():
        raise LedgerError("event needs a supported kind and a nonempty summary")
    if len(event["summary"]) > 1200:
        raise LedgerError("Keep event summary <=1200 characters; put detail in a source file or details.")
    if not isinstance(event.get("source_kind"), str) or not event["source_kind"].strip():
        raise LedgerError("event needs source_kind (for example user, local-artifact, teammate)")
    if event["kind"] == "remote-observation":
        if not event.get("source_ref") or not event.get("observed_at"):
            raise LedgerError("Remote observations need source_ref and observed_at; observation time is not inferred.")
        parse_time(event["observed_at"])
    text = json.dumps(event, ensure_ascii=False)
    if re.search(r"-----BEGIN (?:\w+ )?PRIVATE KEY-----|(?:password|passwd|token|secret)\s*=\s*\S+|Authorization:\s*(?:Bearer|Basic)\s+\S+", text, re.I):
        raise LedgerError("Possible credential in event. Remove it before recording.")
    event.update(event_id=str(uuid.uuid4()), recorded_at=now())
    return event


def parse_time(value):
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("timezone required")
        return result
    except (ValueError, AttributeError) as exc:
        raise LedgerError("Use an ISO timestamp with timezone, for example 2026-01-01T00:00:00Z.") from exc


def apply_set(state, updates):
    if not isinstance(updates, dict):
        raise LedgerError("set must be an object of dotted paths and replacement values")
    for path, value in updates.items():
        parts = path.split(".")
        if not all(parts) or parts[0] in PROTECTED:
            raise LedgerError(f"Cannot directly set {path!r}")
        target = state
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            if not isinstance(target[part], dict):
                raise LedgerError(f"Cannot descend through a non-object: {path}")
            target = target[part]
        target[parts[-1]] = copy.deepcopy(value)
    check_snapshot(state)


def sync(root, ledger, payload, compact=False):
    if not isinstance(payload, dict):
        raise LedgerError("Sync input must be a JSON object")
    with lock(ledger):
        if (ledger / ".pending.json").exists():
            raise LedgerError("Interrupted sync exists. Run recover, then resume before retrying.")
        state = load_state(root, ledger)
        revision = state.get("revision", 0)
        if type(payload.get("expected_revision")) is not int or payload["expected_revision"] != revision:
            raise LedgerError(f"Snapshot changed or expected_revision missing. Current revision is {revision}; resume and reconcile before writing.")
        event = new_event(payload.get("event"))
        previous = copy.deepcopy(state)
        apply_set(state, payload.get("set", {}))
        archive_fields = payload.get("archive_fields", [])
        if archive_fields and not compact:
            raise LedgerError("archive_fields is available only with compact")
        if not isinstance(archive_fields, list) or any(k in CORE or k not in state for k in archive_fields):
            raise LedgerError("archive_fields must name existing non-core top-level fields")
        if compact:
            archive = ledger / "archive" / ("snapshot-" + uuid.uuid4().hex)
            archive.mkdir(parents=True)
            shutil.copy2(ledger / "state.json", archive / "state.json")
            if (ledger / "HANDOFF.md").exists():
                shutil.copy2(ledger / "HANDOFF.md", archive / "HANDOFF.md")
            for key in archive_fields:
                state.pop(key)
            source = archive.relative_to(root).as_posix() + "/state.json"
            state.setdefault("history_archives", []).append(source)
            event["snapshot_archive"] = source
        state["revision"] = revision + 1
        state["last_event_at"] = event["recorded_at"]
        changed = payload.get("set") or compact
        if changed:
            state["project"]["updated_at"] = event["recorded_at"]
        event["revision"] = state["revision"]
        # Store only changed paths in history, not a copy of the entire snapshot.
        if payload.get("set"):
            event["changes"] = payload["set"]
        recent = [event] + events(ledger, 2)
        commit(ledger, state, event, view(state, recent))
    return {"synced": True, "revision": state["revision"], "event_id": event["event_id"],
            "snapshot_changed": state["project"]["updated_at"] != previous["project"]["updated_at"],
            "warnings": warnings(state), **({"archive": source} if compact else {})}


def doctor(root, ledger, check_git=False):
    errors, notes = [], []
    try:
        state = load_state(root, ledger)
        check_snapshot(state)
        notes += warnings(state)
    except (LedgerError, OSError) as exc:
        errors.append(str(exc))
        state = None
    count, ids = 0, set()
    log = ledger / "events.jsonl"
    if not log.exists():
        errors.append("Missing events.jsonl")
    else:
        with log.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise ValueError("expected an object")
                    key = event.get("event_id")
                    if key in ids:
                        errors.append(f"Duplicate event_id at line {line_no}")
                    if key:
                        ids.add(key)
                    if not key or not event.get("summary"):
                        notes.append(f"Legacy incomplete metadata at event line {line_no}; preserve and inspect when relevant.")
                    count += 1
                except ValueError as exc:
                    errors.append(f"Invalid event at line {line_no}: {exc}")
        if log.stat().st_size:
            with log.open("rb") as handle:
                handle.seek(-1, 2)
                if handle.read(1) != b"\n":
                    errors.append("Event log lacks its final newline; inspect for a torn append.")
    if (ledger / ".pending.json").exists():
        errors.append("Interrupted transaction: run recover")
    if not (ledger / "HANDOFF.md").exists():
        notes.append("Missing generated handoff; run render if needed")
    if check_git:
        from ledger_store import git_run
        top = git_run(root, "rev-parse", "--show-toplevel")
        if top and not top.returncode:
            relative = ledger.relative_to(Path(top.stdout.strip()).resolve()).as_posix()
            result = git_run(Path(top.stdout.strip()), "ls-files", "--", relative)
            if result and result.stdout.strip():
                errors.append("Ledger is tracked by Git")
    return {"valid": not errors, "events": count, "errors": errors, "warnings": notes}


def initialize(root, ledger, objective="", allow_nested=False):
    if ledger.exists():
        raise LedgerError("Ledger already exists; resume it instead of overwriting it.")
    for parent in root.parents:
        if (parent / ".project-ledger/state.json").exists() and not allow_nested:
            raise LedgerError(f"Parent project ledger found at {parent}; use that root, or --allow-nested for an intentionally independent project.")
    exclude = exclude_ledger(root, ledger)
    ledger.mkdir(parents=True)
    state = initial_state(root)
    state["objective"] = objective
    (ledger / "events.jsonl").touch(exist_ok=False)
    event = new_event({"kind": "note", "summary": "Initialized local project ledger", "source_kind": "user"})
    with lock(ledger):
        commit(ledger, state, event, view(state, [event]))
    return {"created": True, "revision": 0, "git_exclude": exclude}


def make_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    commands = ("resume", "init", "enable", "sync", "history", "show", "compact", "export", "doctor", "recover", "inspect", "record", "render", "validate")
    for name in commands:
        p = sub.add_parser(name)
        p.add_argument("--project-root", required=True)
        p.add_argument("--ledger-dir", default=".project-ledger")
    for name in ("resume", "inspect", "export", "render", "history"):
        sub.choices[name].add_argument("--max-chars", type=int, default=DEFAULT_BUDGET)
        sub.choices[name].add_argument("--topic")
    sub.choices["show"].add_argument("--max-chars", type=int, default=DEFAULT_BUDGET)
    sub.choices["show"].add_argument("--ref", required=True, help="Exact ref returned by resume/history; quote it")
    sub.choices["show"].add_argument("--offset", type=int, default=0, help="Continue an exact JSON value at this Unicode offset")
    for name in ("resume", "inspect", "doctor", "validate"):
        sub.choices[name].add_argument("--git", action="store_true", help="Explicitly inspect Git")
    for name in ("init", "enable"):
        sub.choices[name].add_argument("--objective", default="")
        sub.choices[name].add_argument("--allow-nested", action="store_true", help="Intentionally create a separate project below a parent ledger")
    sub.choices["enable"].add_argument("--instructions", choices=("auto", "AGENTS.md", "AGENTS.override.md", "CLAUDE.md"), default="auto",
                                       help="Project instruction file; auto respects a nonempty AGENTS.override.md")
    for name in ("sync", "compact"):
        sub.choices[name].add_argument("--input", required=True, help="UTF-8 JSON file, or - for stdin")
    history = sub.choices["history"]
    history.add_argument("--limit", type=int, default=10)
    history.add_argument("--since")
    history.add_argument("--event-id")
    history.add_argument("--source", choices=("events", "archives"), default="events", help="Archives are historical snapshots, not current conclusions")
    sub.choices["export"].add_argument("--output", required=True, help="New local Markdown review draft; never uploaded")
    record = sub.choices["record"]
    record.add_argument("--kind", required=True, choices=sorted(KIND))
    record.add_argument("--summary", required=True)
    record.add_argument("--details", default="")
    record.add_argument("--source-kind", required=True)
    record.add_argument("--source-ref", default="")
    record.add_argument("--observed-at")
    return parser


def execute(args):
    root, ledger = resolve(args.project_root, args.ledger_dir)
    name = args.command
    if hasattr(args, "max_chars") and not 1000 <= args.max_chars <= 100000:
        raise LedgerError("--max-chars must be between 1000 and 100000")
    if name == "init":
        return initialize(root, ledger, args.objective, args.allow_nested)
    if name == "enable":
        from ledger_setup import enable
        return enable(root, ledger, initialize, args.objective, args.allow_nested, args.instructions)
    if name == "recover":
        with lock(ledger):
            recovered = recover(ledger, root)
        return {"recovered": recovered}
    if name in {"doctor", "validate"}:
        return doctor(root, ledger, args.git)
    if (ledger / ".pending.json").exists():
        raise LedgerError("Interrupted sync pending; run recover before reading or writing current state.")
    state = load_state(root, ledger)
    check_snapshot(state)
    if name == "show":
        return show_page(resolve_ref(root, ledger, state, args.ref), args.ref, args.max_chars, args.offset)
    if name in {"sync", "compact"}:
        payload = json.load(sys.stdin) if args.input == "-" else read_json(local_path(args.input))
        return sync(root, ledger, payload, compact=name == "compact")
    if name == "record":
        event = {key: getattr(args, key) for key in ("kind", "summary", "details", "source_kind", "source_ref")}
        if args.observed_at:
            event["observed_at"] = args.observed_at
        return sync(root, ledger, {"expected_revision": state.get("revision", 0), "event": event})
    if name == "history":
        if not 1 <= args.limit <= 1000:
            raise LedgerError("--limit must be between 1 and 1000")
        since = parse_time(args.since) if args.since else None
        if args.event_id and (args.topic or args.since or args.source != "events"):
            raise LedgerError("--event-id is an exact lookup; omit topic/since/archive filters.")
        if args.source == "archives":
            hits = archive_hits(root, ledger, state, args.topic, args.limit, since)
        else:
            selected = [event_by_id(ledger, args.event_id)] if args.event_id else events(ledger, args.limit, args.topic, since)
            hits = ((f"event:{e.get('event_id', '')}#", e) for e in selected)
        return history_view(hits, args.max_chars)
    recent = recent_for_state(ledger, state, args.topic)
    result = view(state, recent, args.max_chars, args.topic)
    if name == "render":
        with lock(ledger):
            # Re-read inside the lock to avoid replacing a newer generated view.
            if (ledger / ".pending.json").exists():
                raise LedgerError("Interrupted sync pending; run recover before render.")
            state = load_state(root, ledger)
            result = view(state, recent_for_state(ledger, state, args.topic), args.max_chars, args.topic)
            atomic_bytes(ledger / "HANDOFF.md", result.encode("utf-8"))
        return {"rendered": True, "snapshot_updated_at": state["project"]["updated_at"], "characters": len(result)}
    if name == "export":
        output = local_path(args.output)
        if inside(output, ledger):
            raise LedgerError("Export to a new local review draft outside the private ledger.")
        output.parent.mkdir(parents=True, exist_ok=True)
        header = "<!-- Local review draft. Review names, paths, and private details before sharing. Nothing was uploaded. -->\n"
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(header + result)
        return {"exported": str(output), "sharing_status": "local draft; not automatically redacted or uploaded"}
    if args.git:
        result += "\nGit (explicit live observation): " + json.dumps(git_info(root), ensure_ascii=False)
    return result


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = make_parser().parse_args()
    try:
        result = execute(args)
        print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if isinstance(result, dict) and result.get("valid") is False else 0
    except (LedgerError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
