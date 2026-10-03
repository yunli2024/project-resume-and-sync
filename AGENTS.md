# Development boundary

This directory is the standalone distributable project-resume-and-sync Skill.
The surrounding research workspace, if any, is private and never release input.

- Keep everyday resume/sync cheap; optional history/diagnosis may do more work.
- Preserve schema-1 records, unknown fields and old snapshots. Never replace
  missing evidence with an inferred completion or timestamp.
- Run `python -m unittest discover -s tests -v` for storage/CLI changes.
- Use synthetic fixtures. Never include real project ledgers, transcripts,
  credentials, private hostnames or machine paths in commits or releases.
- Build packages through `python scripts/build_release.py --output <new.zip>`.
  The allowlist defines the release boundary. Do not recursively zip a workspace.
- Keep contributor detail in README/docs; SKILL.md is the agent's small runtime
  entrypoint. No model API, background service, or new dependency is needed.
