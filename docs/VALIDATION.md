# Validation and measurement

## 0.3.1 final local review

The final review on 2026-10-03 reran all 52 tests on Windows with Python 3.12.4:
51 passed and one real-symlink test was skipped due to local privileges. This
includes the CLI demo, install/upgrade/setup, concurrency/recovery, exact retrieval,
and release allowlist/manifest checks. Skill format validation also passed.

The Chinese-default README and English counterpart have working local links and
language switches. Release packaging uses an explicit file list and LF text
line endings; private project records and temporary test output stay outside it.

For Linux, macOS and other Python versions, use the actual
[CI runs](https://github.com/yunli2024/project-resume-and-sync/actions/workflows/tests.yml).
The release notes report the workflow run used for publication. Helper tests and
the scripted demo do not establish an agent's automatic invocation rate.

## 0.3.1 project activation

Observed on 2026-10-03, Windows with Python 3.12.4: 52 tests executed, 51 passed
and 1 skipped for the same real-symlink privilege limitation described below.
Nine setup tests cover fresh enable, repeat enable, exact instruction backups,
UTF-8 BOM/CRLF preservation, existing ledger preservation, effective override
selection, custom-policy/marker conflicts, path and encoding errors, an explicit
CLAUDE.md adapter, parent project boundaries, combined installation/activation,
and new/legacy installation destinations.

These tests establish helper behavior and generated project routing. They do
not measure automatic model invocation rates. No host hook or background service
is installed. The earlier 0.3.0 timing measurements remain labeled by version.

## 0.3.0 release candidate

Observed on 2026-10-03, Windows with Python 3.12.4:

- 43 tests executed: 42 passed, 1 skipped because real symlink creation requires
  privileges unavailable on this host. A mock redirect check also passes, but
  does not replace that filesystem test.
- The included demo runs seven continuity checks through the CLI, including
  decision reversal, attribution, a stale writer, and archive-only retrieval.
- New retrieval tests cover exact Unicode page reconstruction, escaped JSON
  pointers, stale state references, reference retention when content is clipped,
  archive identity/path boundaries, and exact event lookup past 1,000 decoys.
- Skill format validation passed. The runtime entrypoint is 3,655 bytes versus
  4,621 bytes in 0.2.0, about 21% smaller despite added retrieval guidance.

Reproduce these checks with the commands in [EVALUATION.md](EVALUATION.md).
The table below comes from `python scripts/benchmark.py --runs 5`. Each row uses
five new Python processes. Duration includes startup, local IO and formatting.
All input file hashes stayed unchanged.

| Synthetic case | State bytes | Event count | Resume characters | Median process seconds |
| --- | ---: | ---: | ---: | ---: |
| Small current state | 1,852 | 100 | 1,234 | 0.0952 |
| Same current state, longer history | 1,852 | 20,000 | 1,252 | 0.0889 |
| Legacy snapshot with 1,000 completed items | 310,818 | 20,000 | 1,255 | 0.0902 |

Small timing differences are measurement noise, not proof that more history is
faster. The important contracts are bounded output and tail-only default event
reading. Resume still parses the entire current snapshot; maintaining a small
snapshot matters. These are character/byte and process-time measurements, not
token measurements or end-to-end model speedups.

Linux/macOS and other Python versions await actual CI execution. The agent
behavior scenarios are provided as a protocol; no blinded evaluation, model
success-rate claim, or external user study has been performed.

## Prior 0.2.0 candidate

Observed on 2026-10-03, Windows with Python 3.12.4:

- 35 tests executed: 34 passed, 1 skipped because creating real symlinks required
  privileges unavailable on that host. The rejection branch also has a mock-based
  test; this does not replace the skipped filesystem test.
- Skill frontmatter/format validation passed.
- Concurrent processes: exactly one writer succeeds from the same revision;
  the other receives a lock/revision conflict without losing the accepted update.
- Injected interruptions before/after the event append recover to one event and
  the intended state. Unexpected history changes are refused.
- Compaction preserves exact prior state/handoff bytes and the original event
  prefix. Unicode, Git repositories, linked worktrees, installation backups and
  release allowlist/manifest behavior are covered.

The configured Linux/macOS and other Python versions have not been executed in
this local run. Use actual CI results once the repository is published. This is
not independent agent behavioral evaluation or a multi-user field study.

## One real legacy-ledger measurement

A read-only check used an existing 360,633-byte state, a 289,225-byte generated
handoff and a 756,117-byte event log. Five fresh local Python processes produced
a bounded resume of 5,958 characters / 6,208 UTF-8 bytes, with a median process
duration of 0.110 seconds. Input file hashes were unchanged.

The old startup guidance requested both state and handoff (649,858 bytes). The
new view returned 6,208 bytes, about 99% less output for that case. This is a
byte-volume comparison, not a token measurement or a claim of 99% faster AI
turns. The view omits and labels excerpts; full facts remain in the ledger.

After a reviewed compaction, the real project's current snapshot was reduced
while the original snapshot and all existing history remained locally available.
Private project records and original conversation excerpts are not release inputs.
