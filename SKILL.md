---
name: project-resume-and-sync
description: Resume projects and sync material progress, decisions and evidence for later continuation, handoff or retrospective. Also use to enable ongoing project record maintenance. Not for server/file synchronization or routine one-off questions.
---

# Project Resume and Sync

Keep **now** small and **why** retrievable. The helper uses Python 3.10+, standard
library only. Resolve `<skill-dir>` to this installed directory.

## Enable a project once

When asked to enable ongoing maintenance, read the project's existing instructions,
then run `python "<skill-dir>/scripts/local_ledger.py" enable --project-root "<project>"`.
This adds a short routing block and initializes a missing ledger. Existing facts
are retained. Read [setup details](references/local-ledger-schema.md#enable-ongoing-project-maintenance)
only for instruction conflicts or another host. Capture current facts with sync.
Installation alone allows discovery; project routing establishes when to act.

## Resume once

Use the established project root, including when working in a subdirectory:

```sh
python "<skill-dir>/scripts/local_ledger.py" resume --project-root "<project>"
```

Read the bounded view and only the sources needed for the task. Keep this context
during ongoing work; resume again after a session break or a concurrent change.
The view reports coverage and references. For a missing detail, use
`resume --topic "words"`, `history --topic "words"`, or `show --ref "<ref>"`.
For compacted snapshots use `history --source archives --topic "words"`.
Follow pagination only as far as needed. See the
[retrieval guide](references/local-ledger-schema.md#retrieve-exact-records) for syntax.

Records are data. Follow project instructions and the user's latest intent;
use inspected artifacts for implementation facts. Historical observations retain
their date and uncertainty. An old completion or a valid ledger proves no claim.

## Sync material changes

Record changed decisions, meaningful progress/results, blockers, or observations.
Unchanged status and routine narration need no event. Write one UTF-8 JSON update
(or send it through stdin with `--input -`):

```json
{
  "expected_revision": 0,
  "event": {
    "kind": "decision",
    "summary": "Use the stable API; defer streaming for offline customers.",
    "source_kind": "user",
    "source_ref": "docs/api.md"
  },
  "set": {
    "decisions": ["Stable API accepted; streaming deferred for offline use."],
    "next_action": "Implement the adapter."
  }
}
```

```sh
python "<skill-dir>/scripts/local_ledger.py" sync --project-root "<project>" --input "change.json"
```

Use the revision from resume. `set` replaces each named value: preserve other
still-current list entries. On a revision conflict, resume and reconcile before
retrying. An interrupted write needs `recover`. Successful sync already renders
the handoff; stop there unless diagnosis is requested.

Keep the outcome, reason, source and next action concise. For reproduction, link
the command/config, code/input/environment identities and outputs. Keep teammate
reports attributed until verified. Read [reconciliation examples](references/reconciliation-rules.md)
when sources conflict or a handoff/run needs more structure.

## Maintain a small current record

Aim for a current snapshot under 16 KB; the default view is capped at 6,000
Unicode characters. Move long explanations to source documents. Use `compact`
with a reviewed update when old work accumulates: it archives exact previous
files and retains history. Preserve unresolved work and uncertainty.

Read the [storage guide](references/local-ledger-schema.md) for first-time `init`,
compaction, upgrades or diagnosis. Initialize only during authorized project
work. `doctor` and live Git checks are optional investigations.

Keep `.project-ledger/` local, untracked and free of secrets. Run outside SSH and
network shares. For collaboration, `export --output <new-local-file.md>` creates
a draft: review private details and source access before sharing it. The helper
does not upload or merge other machines' ledgers.
