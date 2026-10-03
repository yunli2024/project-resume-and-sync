# Changelog

## 0.3.1 — First public release (2026-10-03)

- Add one-time `enable` to install a short project routing block and initialize
  a missing ledger. Preserve existing instructions, facts and local backups;
  repeated enable does not duplicate the block or overwrite its customization.
- Support installation plus project activation with `install.py --project-root`.
- Explicitly allow implicit invocation; explain discovery versus ongoing routing.
- New default installations use `~/.agents/skills`; reuse existing `.codex`
  installations and explicit `CODEX_HOME`/`--dest` selections.
- Make Chinese the default README with an English version and language switches.
- Publish the standalone Skill, installer, demo, tests and MIT license together;
  use consistent text line endings for reproducible release packaging.

## 0.3.0 — Release candidate

- Add coverage counts and exact references to bounded resume views.
- Add `show --ref` with Unicode pagination and stale-state reference detection.
- Make preserved snapshots searchable through `history --source archives`.
- Fix exact event lookup being limited by unrelated keyword matches.
- Keep source attribution and certainty visible in recent-event summaries.
- Shorten runtime instructions; add a runnable demo, synthetic benchmark,
  agent evaluation scenarios, and a source-linked design comparison.

Compatibility: stored schema remains 1. `history` now includes reference headers
and excerpt labels; it is a text view rather than JSONL. Daily commands remain
`resume` and `sync`. Existing private ledgers and archives are not migrated.

## 0.2.0 — Release candidate

- One bounded `resume` view and one transactional `sync` operation for daily use.
- On-demand topic/date history, reviewed compaction, local handoff exports and diagnosis.
- Preserve schema-1 history and unknown fields; archive old snapshot bytes before compaction.
- Revision checks, process-safe writer locks and idempotent interruption recovery.
- Separate snapshot/event timestamps; rendering no longer makes old facts look fresh.
- Remove mandatory repository scans, repeated Git inspection, full-history validation,
  and fixed ten-section reports from ordinary usage.
- Add standard-library tests, install/upgrade backups, public release allowlist,
  English/Chinese documentation and MIT license.

Compatibility: legacy commands remain, but `inspect` returns bounded text rather
than its old JSON object. Remote observations now require an explicit observation
time; it is no longer inferred from the time they are recorded.

## Original local prototype

Local-only state/events/handoff, material event recording, remote observations,
source reconciliation, Git exclusion and a full validation command.
