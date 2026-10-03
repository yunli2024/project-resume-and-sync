# Keep the present small and the past reachable

The original Skill was built for a long research project with many sessions,
machines, artifacts and changing decisions. Repeated handoff files helped at
first, but eventually the current snapshot accumulated hundreds of completed
items. A manual compaction helped once; the same growth returned later.

The general lesson is to bound the default view and make history retrieval
explicit. Asking an agent to "keep it compact" alone is insufficient.

## Core responsibilities

1. Resume the current objective, constraints and next action cheaply.
2. Record material changes, reasons, attribution and evidence pointers.
3. Retrieve enough history for a handoff, retrospective or reproduction.

The public positioning is **small context, retrievable reasons**. See
[related work](RELATED_WORK.md) for inspected sources and the design choices
they informed, and [evaluation](EVALUATION.md) for how to challenge this claim.

The helper does not implement project execution, scientific gates, full chat
capture, remote synchronization or a new task-management service. Projects can
link those systems without copying their rules into every session.

## Changes informed by usage

| Observed failure | Design response |
| --- | --- |
| Manual compaction was followed by more state growth | Bounded default view; archived reviewed compaction; soft size advice |
| Both state and its generated handoff were loaded | One `resume` entrypoint; task-specific sources only |
| Every resume validated all history and inspected Git repeatedly | No Git/history audit on the daily path; explicit `doctor` and `--git` |
| Regenerating a view made old state look freshly observed | Separate snapshot time from event time; render changes neither |
| Records landed under a neighboring project | Recorded-root match and parent-ledger detection |
| Old warnings looked current beside later owner decisions | Keep history reachable; require semantic reconciliation, never infer completion by truncation |
| Independent sessions can edit the same snapshot | Short OS write lock plus expected revision |
| Multi-file updates can stop halfway | Local transaction journal and idempotent recovery |
| Strict checks against mutable state quickly invalidated external snapshots | A ledger is an observed record; immutable deliverables belong in their own source system |
| A preserved archive was still hard to use | On-demand archive search and exact JSON Pointer references |
| A clipped event could return no useful history detail | Keep its reference and provide bounded content pages |
| A summary hid whether a teammate's report was verified | Retain source kind and certainty in recent-event rows |

## Cost and integrity

The runtime entrypoint stays small. Optional guides are not loaded by default.
Resume parses one current JSON file and seeks backward for the newest three
events. Its output is bounded in **characters**, not model-dependent tokens.
The implementation never calls a model or computes a token count. A topical
history query may scan more data because the user explicitly requested it.

Snapshots may still be large for backward compatibility. A view labels excerpts
and warns that it omits information. It cannot choose the most relevant facts
perfectly; a maintained small current snapshot gives better results. Compaction
requires a reviewed replacement and preserves the exact old bytes. It must not
erase unresolved risks or silently turn proposals into verified work.

Writes retain cheap checks for project identity, JSON shape, revisions and
recoverability. These checks protect the record. Optional Git/history checks,
hashing external assets and research-specific acceptance are outside the daily
path. The credential pattern check catches common mistakes, not all secrets.

OS locks coordinate cooperative writers on one local filesystem. Revision
checks reject stale updates. An intent journal makes an interrupted event/state/
handoff update recoverable. This is not a distributed database or a guarantee
against disk loss, manual file corruption or non-cooperating older writers.

## Release scope and evidence

The first public release is version 0.3.1, following the original local-only
prototype and the 0.2/0.3 candidates. Tests cover bounded reads, old schema compatibility, preserving
unknown fields/history, concurrent writers, interruption recovery, local path
boundaries, Unicode, Git/worktree exclusions and installation/packaging.

One-time `enable` adds project routing for ongoing use, preserving existing rules
and records. It makes the intended invocation moments explicit. The host and
Agent still implement that behavior; activation is not a background service or
a guarantee that every model run will follow the instructions.

CI uses the official [checkout](https://github.com/actions/checkout) and
[setup-python](https://github.com/actions/setup-python) actions. The local release
report should state which platforms actually ran; a configured CI matrix does
not establish cross-platform success.

Future changes should be driven by external users' concrete failures. Candidate
work includes an explicit relocation tool and broader agent behavior evaluation.
Automatic semantic merging, remote replication, integrations, and dashboards
are deferred until a repeated use case justifies their ongoing complexity.
