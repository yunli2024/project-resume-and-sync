# Evaluate continuity, not just file validity

## Reproduce the deterministic checks

```sh
python examples/demo.py
python -m unittest discover -s tests -v
python scripts/benchmark.py --runs 5
```

The demo creates a synthetic project in a new local temporary directory and
prints its location. It preserves all artifacts for inspection. It exercises a
proposal, an owner reversal, an attributed teammate report, a stale writer, an
archive-only detail and a local handoff. It makes no network or model calls.

The benchmark creates small/current and legacy-sized snapshots with 100 or
20,000 events. It measures fresh Python process duration and output characters/
bytes, and checks that input hashes are unchanged. These hashes belong to an
optional developer measurement; daily resume does not calculate them. The
benchmark does not measure tokens, model reasoning time, or answer quality.

## Agent behavior scenarios

Storage tests cannot prove that an agent records the right meaning or follows
the Skill. Use the demo's printed project with the following prompts in a fresh
agent session. Invoke this Skill and keep a sanitized transcript when comparing
versions. Use an independent fresh fixture per write scenario.

| Prompt | Expected behavior | Failure to look for |
| --- | --- | --- |
| "Continue the importer project. What should we do next?" | One bounded resume; continue CSV import and cite the current source. | Reopens streaming or loads every historical file. |
| "Why did we drop streaming?" | Finds the recorded offline-use reason and earlier proposal; explains chronology. | Treats a rejected proposal as the current plan. |
| "What did we say about account IDs before compacting?" | Searches archived snapshots and retrieves the leading-zero note with its historical label. | Says the detail is lost or promotes every archive fact into current state. |
| "The teammate says tests pass. Is this ready to release?" | Keeps the report attributed; inspects relevant evidence or states what is missing. | Treats the report or a valid ledger as verified release readiness. |
| "We now support both CSV and TSV. Record that decision." | Records reason/source if available and changes only affected fields. | Deletes unrelated uncertainty or silently overwrites a newer revision. |
| "Remind me of the current next action." | Answers from available current context; no new event for a repeated question. | Repeats full resume/doctor or records the same status again. |
| "Sync the project folder to a server." | Recognizes that filesystem transfer is outside this Skill's meaning of sync. | Uploads the private ledger or invokes continuity tooling as file transfer. |

For each comparison, record the Skill version, model/host, prompt, files read,
helper invocations, semantic outcome, output tokens if the host exposes them,
and wall time. Report repeated-run variation and failures. A one-agent manual
walkthrough is useful feedback, but is not a blinded or independent evaluation.

The release includes these scenarios as an evaluation protocol. No model-based
success rate or cross-agent compatibility score has been established yet.

For project activation, run `enable` in a separate synthetic project, start a
fresh host session there, and ask "Continue the project" without naming the
Skill. Check whether the host loads the new instruction block and the Agent
resumes. Then give it a real decision and check for a material sync. Keep a
read-only follow-up as a negative control: it should not append another event.
This behavioral trial is distinct from the deterministic setup tests.

## Contribution standard

Start with a concrete continuity failure and a small sanitized reproduction.
Prefer removing a repeated read or improving a source pointer over adding a
mandatory step. A storage change should preserve old records and pass the
existing tests. A prompt change should be tried on the affected scenario.
Keep model-based evaluations optional; ordinary use needs no evaluation service.
