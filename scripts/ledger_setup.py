"""One-time project opt-in. Keep existing project instructions byte-for-byte."""
import uuid

from ledger_store import LedgerError, atomic_bytes, inside, load_state, lock

START = "<!-- project-resume-and-sync:start -->"
END = "<!-- project-resume-and-sync:end -->"
BLOCK = """<!-- project-resume-and-sync:start -->
## Project continuity

Use the installed project-resume-and-sync skill for this project without waiting
for a separate reminder. Use the project root containing this instruction file.
- At the start of a new session doing substantive project work, run its bounded
  resume and read only task-relevant sources. Reuse that context during the session.
- After material decisions, progress, results, blockers or changed conclusions,
  sync one concise event with reasons/sources and update the affected current
  fields before handing work back. Skip unchanged status and routine narration.
- Keep .project-ledger local, untracked and free of secrets. If the skill is
  unavailable, say so and continue using the project's current source documents.
<!-- project-resume-and-sync:end -->
"""


def instruction_plan(root, filename="auto"):
    if filename == "auto":
        override = root / "AGENTS.override.md"
        filename = "AGENTS.override.md" if override.is_file() and override.stat().st_size else "AGENTS.md"
    if filename not in {"AGENTS.md", "AGENTS.override.md", "CLAUDE.md"}:
        raise LedgerError("Choose AGENTS.md, AGENTS.override.md or CLAUDE.md in the project root.")
    path = root / filename
    if path.is_symlink() or not inside(path, root):
        raise LedgerError("Project instruction file must not redirect outside the project.")
    before = path.read_bytes() if path.exists() else b""
    try:
        text = before.decode("utf-8-sig")
    except UnicodeError as exc:
        raise LedgerError("Instruction file must be UTF-8; convert it explicitly before enable.") from exc
    if START in text or END in text:
        if text.count(START) != 1 or text.count(END) != 1 or text.index(END) < text.index(START):
            raise LedgerError("Incomplete or repeated continuity markers; review the existing block before enable.")
        return path, before, before
    if "project-resume-and-sync" in text:
        raise LedgerError("This file already mentions project-resume-and-sync. Review/reuse that guidance instead of adding a second policy.")
    newline = b"\r\n" if b"\r\n" in before else b"\n"
    separator = (newline if before.endswith(b"\n") else newline * 2) if before else b""
    return path, before, before + separator + BLOCK.replace("\n", newline.decode()).encode("utf-8")


def enable(root, ledger, initialize, objective="", allow_nested=False, instructions="auto"):
    if ledger != root / ".project-ledger":
        raise LedgerError("enable configures .project-ledger; use init and custom project routing for another ledger directory.")
    # Check the instruction target before initializing an otherwise untouched project.
    instruction_plan(root, instructions)
    created = False
    if not ledger.exists():
        initialize(root, ledger, objective, allow_nested)
        created = True
    load_state(root, ledger)
    if (ledger / ".pending.json").exists():
        raise LedgerError("Interrupted sync pending; run recover before project setup.")
    with lock(ledger):
        if (ledger / ".pending.json").exists():
            raise LedgerError("Interrupted sync pending; run recover before project setup.")
        path, before, after = instruction_plan(root, instructions)
        backup = None
        if before != after:
            if before:
                backup_dir = ledger / "instruction-backups"
                if backup_dir.is_symlink() or not inside(backup_dir, ledger):
                    raise LedgerError("Instruction backup directory must stay inside the local ledger.")
                backup_dir.mkdir(exist_ok=True)
                backup = backup_dir / (uuid.uuid4().hex + "-" + path.name)
                atomic_bytes(backup, before)
            atomic_bytes(path, after)
    return {"routing_present": True, "instructions": str(path), "instructions_changed": before != after,
            "ledger_created": created, "previous_instructions": str(backup) if backup else None,
            "next": "Read the project instruction file in this session; start a new session to check host loading. Resume and capture current facts with sync.",
            "activation": "Agent follows project instructions; no background task or hook was installed."}
