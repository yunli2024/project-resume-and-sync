# Sources, collaboration and reproduction

Read this only when the task needs more than ordinary resume/sync.

## Source conflicts

Separate intent, implementation, observation, and interpretation. A user's
decision can supersede an old plan but does not prove a file was generated.
Inspected artifacts establish outputs; a runtime record applies at its observation
time. A newer narrative does not automatically defeat inspected evidence.

Inspect the smallest source that decides the issue. Preserve both source
references in a `conflict` event, state the resolution and reason, and change only
the affected current fields. If unresolved, keep it in `unverified` or `blockers`.
Reading a record does not establish its truth. Don't reopen a settled owner
decision just because an old event disagrees.

## Team handoff

1. Create a local bounded export, optionally focused with `--topic`.
2. Review private names, machine paths, and source accessibility. An export is
   not automatically anonymized; a path alone does not give teammates the file.
3. Share the reviewed report through the team's normal document/Git workflow
   only when authorized. Keep the private ledger local.
4. Record incoming information with `source_kind: "teammate"`, an `actor`, a
   source reference and `certainty: "reported"`. Update current conclusions only
   after reconciling the report with local evidence and the owner's decisions.

Concurrent agents on one local project use revisions and an OS writer lock.
Two machines have separate ledgers: this release provides reviewed handoffs,
not automatic replication, merging, chat capture, or a collaboration server.

## Reproduction records

Use a `run` event with a short result and a pointer to the run manifest. Include
only details needed to repeat that particular work. Example optional payload:

```json
{
  "kind": "run",
  "summary": "Parser regression reproduced on the saved fixture; fix verified.",
  "source_kind": "local-artifact",
  "source_ref": "reports/parser-regression.md",
  "reproduce": {
    "command": "python -m unittest tests.test_parser",
    "cwd": ".",
    "code": "git commit or reviewed diff reference",
    "inputs": ["tests/fixtures/quoted.csv"],
    "environment": "Python 3.12; dependencies from requirements.lock",
    "outputs": ["reports/parser-regression.md"]
  }
}
```

A heavy experiment can link an existing manifest rather than duplicate it here.
Hashes, GPU checks, benchmark registration, and scientific gates belong to that
project's workflow. The ledger does not run or validate the experiment.

## Retrospective

Search history by topic/date, follow the cited source, and inspect archived
snapshots if needed. Distinguish what was known then from what was learned later.
Preserve rejected alternatives and their rationale as history. The event log is
a record of material work captured by participants, not a guaranteed transcript
of every action or a complete event-sourced reconstruction of all old state.
