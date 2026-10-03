# Storage and occasional maintenance

Python 3.10+; standard library only. Commands accept `--project-root` and optional
`--ledger-dir` (inside that project). No daemon, account, API key, or network call.

## Files

| File | Purpose |
| --- | --- |
| `state.json` | Small current snapshot; source of the generated view |
| `events.jsonl` | Append-only material events, including changed snapshot fields |
| `HANDOFF.md` | Generated bounded view; never hand-edit it |
| `archive/snapshot-*/` | Exact previous state/handoff saved during compaction |
| `.lock`, `.pending.json` | Writer coordination and interrupted-transaction recovery |

Schema version 1 remains supported. Unknown top-level fields survive ordinary
syncs. An old ledger without `revision` starts at revision 0. Core fields:

```json
{
  "schema_version": 1,
  "revision": 0,
  "ledger_policy": {
    "storage": "local-only",
    "remote_writes_allowed": false,
    "git_tracking_allowed": false
  },
  "project": {
    "name": "example",
    "root": "/absolute/local/project",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  },
  "objective": "Ship a small offline report tool.",
  "next_action": "Implement CSV import.",
  "status": {"completed": [], "in_progress": [], "pending": []},
  "decisions": [], "constraints": [], "risks": [], "blockers": [],
  "unverified": [],
  "sources": {"canonical_local": ["README.md"], "remote_observations": []},
  "git": {}
}
```

`project.updated_at` changes when current snapshot fields change. `last_event_at`
records the newest event time. Rendering, inspection, and event-only updates do
not make old facts look newly verified. `revision` increments on every sync.

## Update format

Use the `sync` example in SKILL.md. `set` contains dotted paths; each value is a
replacement, not an append or a recursive merge. An empty `set` records history
without changing current conclusions. Identity, revision, policy, and archive
pointers are helper-managed. Unknown domain fields are allowed but should stay
small and point to project-owned source files.

An event needs `kind`, `summary` (up to 1,200 characters), and `source_kind`.
Kinds: `decision`, `progress`, `risk`, `blocker`, `conflict`, `pivot`, `run`,
`remote-observation`, `note`. Source kinds are descriptive strings, such as
`user`, `local-code`, `local-artifact`, `local-document`, `git`, or `teammate`.
Optional `details`, `source_ref`, `actor`, `topic`, `certainty`, and `reproduce`
are retained. The helper supplies `event_id`, `recorded_at`, and revision.

A remote observation additionally needs `observed_at` with timezone and a source
reference. Neither a remote connection nor a fresh observation is performed by
the helper. Basic credential detection is not a complete secret scanner.

## First use

For ongoing Agent maintenance, use `enable` below. To create only a local record
without changing project instructions, use `init`:

```sh
python scripts/local_ledger.py init --project-root /path/to/project --objective "Ship the report tool"
```

An existing ledger is never reinitialized. If a parent directory already owns a
ledger, use that project root. For a deliberately independent nested project,
pass `init --allow-nested`. The helper refuses mismatched roots to avoid
putting one project's records in another project. Work without Git is supported.

## Enable ongoing project maintenance

Ask the installed Skill: "Enable ongoing project continuity here; resume at the
start of substantive sessions and sync material changes without reminders."
The Agent reads the existing project rules and runs:

```sh
python "<skill-dir>/scripts/local_ledger.py" enable --project-root /path/to/project
```

`enable` adds one marked continuity block to the root instruction file, initializes
a missing ledger, and retains existing state. Repeating it preserves an existing
marked block, including user edits. Original instruction bytes and line endings
are preserved; a prior file is backed up under the local ledger's
`instruction-backups/`. Removing just the marked block stops this routing policy
without removing any records; explicit invocation remains available.

The default targets `AGENTS.override.md` when it exists and is nonempty; otherwise
it targets `AGENTS.md`. Use `--instructions CLAUDE.md` when that is the instruction
file your host loads. `enable` uses `.project-ledger`; custom ledger directories
or instruction names need `init` and manual routing. This is a file
adapter; automatic host behavior beyond Codex has not been evaluated. Review
existing/nested rules before enabling; the helper does not interpret semantic
conflicts. If an unmarked existing policy already mentions the Skill, reconcile
that policy instead of appending another. An incomplete marked block is reported.

From the downloaded repository, installation and setup can be combined:

```sh
python scripts/install.py --project-root /path/to/project
```

Installation without this flag changes only the Skill installation. For an
existing installation add `--upgrade`, or just invoke its `enable` command for
the new project. If project setup fails, the installer reports that separately
from the successful Skill installation.

After enabling, the current Agent can read the updated instructions; start a new
session to check that the host loads them automatically. Ask it to identify the
project root, show the next action, and later record a real decision without
reminding it to sync. Ordinary repeated status questions need no event. Setup
tests verify files, not a guaranteed model invocation rate. No hooks or background
service are installed.

Codex supports [implicit Skill selection](https://learn.chatgpt.com/docs/build-skills)
and [project/global instruction loading](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
Users who want the policy across their projects can put a short equivalent rule
in their own global instructions. The installer enables only the explicitly
selected project; it does not change global behavioral settings.

## Compact an old or oversized snapshot

Read only the current fields you need and the evidence that decides what remains
active. Prepare a normal sync input with shortened, reviewed `set` values. Add
`archive_fields: ["old_domain_snapshot"]` only for obsolete non-core top-level
fields that should leave current state. Then run:

```sh
python scripts/local_ledger.py compact --project-root /path/to/project --input compact.json
```

The command first preserves exact old state/handoff bytes in a new archive,
records its path in `history_archives` and the event, and applies your replacements.
It does not automatically decide which claims are obsolete. The entire event
log and other ledger subdirectories are untouched. A failed pre-commit operation
may leave an extra safe archive; there is no automatic archive deletion.

## History, handoff and diagnosis

```sh
python scripts/local_ledger.py history --project-root /path/to/project --topic "API" --limit 5
python scripts/local_ledger.py history --project-root /path/to/project --since 2026-01-01T00:00:00Z
python scripts/local_ledger.py export --project-root /path/to/project --output /local/review/handoff.md
python scripts/local_ledger.py doctor --project-root /path/to/project
python scripts/local_ledger.py doctor --project-root /path/to/project --git
python scripts/local_ledger.py recover --project-root /path/to/project
```

History is newest-first. Text search is literal and case-insensitive. Topic
searches can scan older events; default resume reads only the newest three.
Output is bounded; use `--max-chars` to deliberately expand it. Full records stay
in their source files. Missing historical information is not fabricated.

## Retrieve exact records

Every displayed fact has a reference. Quote it when passing it to the shell:

```sh
python scripts/local_ledger.py show --project-root /path/to/project --ref "state:3#/decisions/0"
python scripts/local_ledger.py history --project-root /path/to/project --source archives --topic "offline"
```

Copy actual refs from your output. `state:<revision>#/path` addresses current
state and refuses a stale revision; `event:<id>#/path` addresses an event;
`archive:snapshot-<id>#/path` addresses a registered historical snapshot. Paths
use JSON Pointer (`~1` for `/`, `~0` for `~`). A bare `#` selects the whole record.

`show` returns exact JSON content, in pages bounded by `--max-chars`. If it reports
a next offset, repeat the same ref with `--offset N`. Offsets count Unicode
characters of the JSON content, excluding headers/footers. Concatenating content
pages reconstructs the JSON value; a page alone can be incomplete JSON. Use a
more specific pointer whenever it answers the question with less reading.

`history --source archives` explicitly scans old snapshot files and requires
`--topic`. Results retain their historical label and snapshot timestamp; they
do not override current decisions. `--since` filters snapshot update time in
this mode and event record time in the default event mode. Each mode lists up
to `--limit` matches (10 by default), subject to the output budget. Exact event
lookup uses `history --event-id <id>` without other filters.

Resume's coverage counts nonempty current facts (each list item is one fact),
excluding helper metadata and Git observations. A topic view counts matching
facts plus the objective/next action. Recent events are separate. Dictionary
summaries and clipped rows count as excerpts; use their refs for full contents.
Neither archives nor the whole event log are scanned by default resume.

## Diagnose and recover

`doctor` scans the full history only when requested. It checks structure,
duplicates, incomplete writes, and size, not factual truth or scientific validity.
Malformed data is reported; no history is silently repaired or discarded.

An interrupted transaction leaves `.pending.json`. `recover` completes the
stored event/state/handoff once, including a partial append, then removes that
one journal file. It refuses an unexpectedly changed event tail. Don't manually
edit the journal or run the old helper while a transaction is pending.

Legacy `inspect`, `record`, `render`, and `validate` commands remain. `inspect`
now returns the compact view; `record` also regenerates the handoff; `validate`
is the explicit `doctor` alias. Existing external JSON parsers of old `inspect`
output must be updated. Use one helper version per ledger during rollout.

In 0.3.0, `history` adds reference headers and labels excerpts; it is a human/agent
view, not JSONL output. Tools needing raw JSONL can read the local events file
explicitly. `show` pages similarly include text headers and continuation metadata.
