# Related work and design choices

We reviewed these popular repositories on 2026-10-03. Stars are a discovery
signal, not evidence of correctness or the cause of a project's popularity.
Counts below are point-in-time GitHub API observations, rounded to thousands.
Links pin the actual files inspected; comparisons concern those workflows,
not every feature a repository might offer.

| Source | Stars observed | What we learned | Application here |
| --- | ---: | --- | --- |
| [Anthropic: skill-creator](https://github.com/anthropics/skills/blob/8a1541c4a3ffa5a20a5a91de0dcf3f0bab1d1ef4/skills/skill-creator/SKILL.md) | ~179k | Progressive disclosure and scenario-based iteration make a skill easier to evaluate. | Short runtime entrypoint; optional storage guide; runnable demo and explicit behavioral evaluation cases. |
| [Superpowers: using-superpowers](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/using-superpowers/SKILL.md) | ~295k | Precise activation and workflow ordering make expectations explicit. | Clear continuation/recording triggers. Its broad mandatory invocation policy is outside our narrower continuity scope. |
| [Planning with Files](https://github.com/OthmanAdi/planning-with-files/blob/dab9d16fbd9314448b319d112e99f497d7638d89/skills/planning-with-files/SKILL.md) | ~27k | Persistent files, explicit plan ownership and recovery address lost context. | Keep one project identity and durable reasons. Our daily path stays two explicit operations; no lifecycle hooks or repeated plan reinjection. |
| [Vercel: React Best Practices](https://github.com/vercel-labs/agent-skills/blob/063bee94c3f4df8453406c830b0a7df0f2860278/skills/react-best-practices/SKILL.md) | ~32k | A quick index leads to specific explanations and examples. | A short command path leads to an exact record, then its project source. |
| [Matt Pocock: handoff](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/productivity/handoff/SKILL.md) and [writing-for-agents](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/productivity/writing-for-agents/SKILL.md) | ~275k | Focused instructions, conditional references and source links reduce duplicated context. | Keep artifact contents in their owning files; load guides only when a branch needs them. |

## Our focus

Project Resume and Sync combines a bounded current view, exact on-demand
retrieval, and recoverable local writes around **project continuity**. Its useful
distinction is the combination and its implementation contract:

- A growing event log does not become mandatory startup context.
- Summary rows lead to exact records, including old snapshots after compaction.
- A changed decision keeps its recorded reason and source in history.
- Concurrent cooperative writers detect stale revisions; interrupted writes can
  finish without appending the intended event twice.
- The record stays local; an export is a deliberate review draft.

This is a product focus, not a claim that these ideas are unprecedented. A plan,
issue tracker, AGENTS.md and source control still have their own roles. Link to
them. Avoid a second copy of their contents or a competing execution workflow.

## Changes made after this review

The 0.2.0 candidate bounded output and preserved archives, but a missing detail
could still force a large manual read. The 0.3.0 candidate adds coverage counts,
exact paged retrieval, searchable archived snapshots and stale-reference checks.
It also includes a runnable continuity story and reproducible synthetic cost
measurements. Daily operations remain `resume` and `sync`.

These sources informed design review. Their implementations and prompts were
not copied into this project's runtime; this repository's code and documentation
are distributed under its own MIT license.
