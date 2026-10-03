"""On-demand retrieval; resume never opens archived snapshots."""
from __future__ import annotations

import json
import re
from pathlib import Path

from ledger_store import LedgerError, inside, read_json, reverse_lines


def pointer_part(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def entries(value, path=""):
    """A list item is one fact; object keys use JSON Pointer escaping."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from entries(child, path + "/" + pointer_part(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield path + f"/{index}", child
    else:
        yield path, value


def at_pointer(value, pointer):
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise LedgerError("Reference needs a JSON Pointer after #, for example #/decisions/0")
    try:
        for part in pointer[1:].split("/"):
            if re.search(r"~(?![01])", part):
                raise ValueError("invalid pointer escape")
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", part):
                    raise ValueError("invalid list index")
                value = value[int(part)]
            elif isinstance(value, dict):
                value = value[part]
            else:
                raise ValueError("cannot descend into scalar")
        return value
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise LedgerError(f"No value at pointer {pointer!r}") from exc


def archived(root, ledger, state):
    """Yield registered snapshots newest first; never follow arbitrary paths."""
    for raw in reversed(state.get("history_archives", [])):
        path = root / raw
        base = ledger / "archive"
        if (path.name != "state.json" or not inside(path, base)
                or not re.fullmatch(r"snapshot-[0-9a-f]{32}", path.parent.name)
                or path.parent.parent != base
                or path.is_symlink() or path.parent.is_symlink()):
            raise LedgerError("Archive reference must point to a local snapshot inside the ledger.")
        yield path.parent.name, path


def read_archive(root, path):
    value = read_json(path)
    if not isinstance(value, dict) or Path(value.get("project", {}).get("root", "")).resolve() != root:
        raise LedgerError("Archived snapshot belongs to a different project root.")
    return value


def event_by_id(ledger, event_id):
    for line in reverse_lines(ledger / "events.jsonl"):
        try:
            value = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise LedgerError("Malformed history; use doctor for details.") from exc
        if not isinstance(value, dict):
            raise LedgerError("An event must be a JSON object.")
        if value.get("event_id") == event_id:
            return value
    raise LedgerError(f"Event not found: {event_id}")


def resolve_ref(root, ledger, state, ref):
    identity, mark, pointer = ref.partition("#")
    kind, colon, key = identity.partition(":")
    if not mark or not colon:
        raise LedgerError("Use the complete ref returned by resume/history, including #.")
    if kind == "state":
        if key != str(state.get("revision", 0)):
            raise LedgerError("State reference is stale; resume again or search history before choosing a new ref.")
        value = state
    elif kind == "event":
        value = event_by_id(ledger, key)
    elif kind == "archive":
        path = next((p for name, p in archived(root, ledger, state) if name == key), None)
        if path is None:
            raise LedgerError("Archive not found in this project's registered snapshots.")
        value = read_archive(root, path)
    else:
        raise LedgerError("Reference kind must be state, event or archive.")
    return at_pointer(value, pointer)


def show_page(value, ref, budget, offset=0):
    """Page one exact JSON serialization; Unicode offsets refer to content only."""
    text = json.dumps(value, ensure_ascii=False, indent=2)
    if offset < 0 or offset >= len(text):
        raise LedgerError("--offset is outside this value; start with 0.")
    header = f"Ref: {ref}\nJSON content (Unicode character offsets):\n"
    room = budget - len(header) - 160
    if room < 1:
        raise LedgerError("Reference is too long for this budget; increase --max-chars.")
    end = min(len(text), offset + room)
    footer = f"\nRange: {offset}:{end}/{len(text)}. "
    footer += f"Continue same ref with --offset {end}.\n" if end < len(text) else "Complete.\n"
    return header + text[offset:end] + footer


def archive_hits(root, ledger, state, query, limit, since=None):
    if not query:
        raise LedgerError("Archive search needs --topic; use resume for current context.")
    # Import only for an explicitly requested archive search.
    from datetime import datetime
    count = 0
    for name, path in archived(root, ledger, state):
        snapshot = read_archive(root, path)
        stamp = snapshot.get("project", {}).get("updated_at", "unknown")
        if since:
            try:
                observed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except ValueError as exc:
                raise LedgerError("Archive snapshot has an invalid timestamp.") from exc
            if observed.tzinfo is None:
                raise LedgerError("Archive snapshot timestamp needs a timezone.")
            if observed < since:
                continue
        for pointer, value in entries(snapshot):
            if pointer.split("/")[1] in {"project", "ledger_policy", "history_archives"}:
                continue
            if query.casefold() in (pointer + " " + json.dumps(value, ensure_ascii=False)).casefold():
                yield f"archive:{name}#{pointer}", {"snapshot_at": stamp, "historical_value": value}
                count += 1
                if count >= limit:
                    return


def history_view(hits, budget):
    lines = []
    footer = "\nNewest matches up to --limit/budget; not an exhaustive search report. Use show --ref for exact JSON.\n"
    size = len(footer)
    for ref, value in hits:
        content = json.dumps(value, ensure_ascii=False)
        prefix = f"Ref: {ref}\n"
        room = budget - size - len(prefix) - 2
        if room < 180:
            break
        text = content if len(content) <= room else content[:room - 30] + "… [excerpt; use show --ref]"
        lines.append(prefix + text)
        size += len(prefix) + len(text) + 2
        if len(text) < len(content):
            break
    return "\n\n".join(lines) + footer if lines else "No matching records."
