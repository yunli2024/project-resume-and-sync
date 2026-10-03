[简体中文](README.md) | English

# 📝 Project Resume and Sync

**Keep track of progress and decisions, so your agent can pick up where you left off.**

You're halfway through a project, open a new chat, and have to explain it all again: what's done, why you chose this approach, and what comes next.
Come back a few weeks later, and you have to dig through the notes yourself.

This Skill keeps those notes in your project. The next session starts with a short summary. When you need the story behind a decision, follow its reference to the recorded details and source files.

**Python 3.10+ · Standard library only · Local storage · [MIT](LICENSE)**

[Get started](#get-started) · [Everyday use](#everyday-use) · [Behind the summary](#behind-the-summary) · [FAQ](#faq)

## When it comes in handy

| You want to… | The Skill helps you… |
| --- | --- |
| Continue in a new chat | Read the current goal, progress, blockers, and next step |
| Understand an earlier choice | Find the decision, its reason, and its source |
| Revisit work from weeks ago | Search by topic or date, including archived records |
| Hand the project to a teammate | Export a handoff draft with pointers to relevant files |
| Review or repeat a run | Find the commands, configs, inputs, and outputs you recorded |

There are two everyday actions:

- **`resume`: catch up.** Read the current state and next step before starting work.
- **`sync`: write down what changed.** Save meaningful progress or decisions, along with the reasons and sources.

Here, sync means updating the project record. Records stay on your machine; file transfers and cloud sync belong to your existing tools.

## Get started

The steps below use **Codex**. You'll need Python 3.10 or newer.

### 1. Install the Skill

```sh
git clone https://github.com/yunli2024/project-resume-and-sync.git
cd project-resume-and-sync
python scripts/install.py
```

You can also download a [release package](https://github.com/yunli2024/project-resume-and-sync/releases/latest) or get the source via **Code → Download ZIP**, extract it, and run the last command from that folder.
If your system uses `python3`, substitute it for `python` in these commands.

After installation, open a new Codex chat. To update an existing installation, use `python scripts/install.py --upgrade`.

### 2. Enable it once for your project

Open **the project you want to keep track of**, then send this to your agent:

```text
Use $project-resume-and-sync to enable ongoing records for this project.
Resume before starting work and sync meaningful progress or decisions without waiting for a reminder.
Start by recording the current goal, progress, and next step.
```

The agent adds a short agreement to the project's instruction file (usually `AGENTS.md`) and creates the local records. Existing content is preserved, and running setup again won't add a duplicate block.

**Install the Skill once; enable it once per project.** For another project, just repeat this step.

### 3. Keep working as usual

Next time you open a chat in that project, say “Continue this project.” The agent should follow the project instructions, read the record first, and update it after meaningful work.

Proactive use depends on the client loading project instructions and the agent following them. If it misses a step, say “Use project-resume-and-sync to catch up” or “Sync the project record.”

<details>
<summary>Install locations, custom paths, and command-line setup</summary>

New installations default to `~/.agents/skills/project-resume-and-sync`. An existing `~/.codex/skills/project-resume-and-sync` installation is reused; an explicit `CODEX_HOME` selects its `skills` directory. The installer prints the actual path.

Choose a custom install location:

```sh
python scripts/install.py --dest "/path/to/skills/project-resume-and-sync"
```

On a first install, you can also enable a project in the same command:

```sh
python scripts/install.py --project-root "/path/to/your-project"
```

Once installed, enable another project with:

```sh
python "<skill-dir>/scripts/local_ledger.py" enable --project-root "/path/to/your-project"
```

Replace `<skill-dir>` with the path printed by the installer. `enable` uses `AGENTS.md` by default, or a nonempty `AGENTS.override.md` when present. Existing custom routing rules are flagged for the agent to reconcile.

Upgrades back up replaced runtime files and keep other files in the installation directory. See the [setup guide](references/local-ledger-schema.md#enable-ongoing-project-maintenance) for details.

</details>

## Everyday use

Once enabled, you can keep talking to your agent as usual. To ask for a specific action, try:

| You say | What the agent uses |
| --- | --- |
| “Pick up yesterday's work. Tell me where we left off.” | `resume`: read the current state and next step |
| “Let's go with this approach. Save the reason, too.” | `sync`: update the state and record the decision |
| “Why did we decide against streaming?” | `history` / `show`: find the history and read the details |
| “Help me hand this project to a teammate.” | `export`: create a local handoff draft |
| “These notes are getting long. Tidy them up and keep the old details.” | `compact`: archive the old snapshot and trim the current state |

Routine questions and unchanged status don't need another entry. Keep what matters: **what got done, what changed, why it changed, what's blocked, and what's next.**

## Behind the summary

Suppose you're building a CSV importer. In a new session, the agent first sees something like this (simplified):

```text
Goal: Finish offline CSV import.
Decision: Use local files; defer streaming. [decision reference]
Next: Implement the import interface from docs/api.md.
Unverified: A teammate reported passing adapter tests; results still need checking.
```

When you ask “Why did we defer streaming?”, the agent can follow the reference to the full record, read the reason, and locate sources such as `docs/api.md`.
An actual reference looks like `state:4#/decisions/0`: one specific item in one version of the record.

That's the core idea: **read a short summary for everyday work, and look up the details when you need them.**

- **Limit what each session reads.** The default view is capped at 6,000 characters (not tokens). It draws from the current state and the three newest events, and reports how many items aren't shown. Older history is retrieved on demand.
- **Keep the story when plans change.** The current state holds the latest decision; history preserves earlier proposals, changes, and reasons.
- **Find old details after tidying up.** `compact` preserves the original snapshot, which remains searchable and readable.
- **Keep uncertainty visible.** “A teammate says the tests passed” can be recorded with its source, then updated once checked.
- **Catch conflicting updates.** For agents working on the same machine, stale writes are rejected so they can reread and reconcile. Interrupted updates have a recovery command, too.

The record helps you find what you need to reproduce work. Rerunning it still requires access to the relevant code, data, and environment.

## Want to try it first?

From the downloaded repository, run:

```sh
python examples/demo.py
```

The demo creates a temporary project and walks through recording progress, changing a decision, resuming in a fresh context, and finding an old reason after compaction. It needs no agent connection or API setup and prints the file location so you can look around.

## FAQ

<details>
<summary>Does it save the whole conversation?</summary>

It saves the progress, decisions, and sources that the agent writes through `sync`. There is no background chat capture. Anything not yet recorded needs to be recovered from a conversation or file you can still access.

</details>

<details>
<summary>Where do the records live? What about another computer or a teammate?</summary>

In the project's `.project-ledger/` directory: current state, event history, and a readable `HANDOFF.md`. Initialization adds a local Git exclusion when the project is a Git repository.

Everyday records stay on your machine. For a handoff, ask the agent to export a Markdown draft, review it for private information, and share it through your usual channel. The recipient also needs access to the referenced files. Merging records across machines currently needs manual coordination.

</details>

<details>
<summary>Can I use it with another coding agent?</summary>

The Skill consists of `SKILL.md` and standard-library Python scripts. Clients that support this kind of Skill can use `--dest` to select their install location. Project instructions can also be added to another file with `enable --instructions CLAUDE.md`.

The current getting-started guide focuses on Codex. Discovery and proactive invocation haven't been verified for every other client; setup needs to follow that client's instruction-loading mechanism.

</details>

<details>
<summary>I'd rather use the command line</summary>

From the downloaded repository, replace the path with the project you want to record:

```sh
python scripts/local_ledger.py resume --project-root "/path/to/your-project"
python scripts/local_ledger.py sync --project-root "/path/to/your-project" --input change.json
python scripts/local_ledger.py history --project-root "/path/to/your-project" --topic "CSV"
```

See [SKILL.md](SKILL.md) for a minimal `change.json`. A normal `sync` updates the state, event history, and handoff summary in one operation.
For exact retrieval, exports, compaction, or interrupted updates, see the [command and storage guide](references/local-ledger-schema.md).

</details>

## Why I built this

It started in a research project that ran for several months. As experiments, discussions, and handoffs piled up, the notes got longer and catching up got harder. Old decisions blended into new progress, and every fresh chat needed a growing pile of background reading.

Over time, it settled into this approach: keep the current state short, leave the reasons in the history, and look them up when needed. I hope it helps you spend less time explaining the project again and more time working on it.

If you've run into “we wrote this down, but still couldn't pick up the work,” [open an issue](https://github.com/yunli2024/project-resume-and-sync/issues). The situation, what you expected, and what actually happened are a useful start. Please remove private details from examples.

[Design choices](docs/DESIGN.md) · [Validation](docs/VALIDATION.md) · [Evaluation scenarios](docs/EVALUATION.md) · [Related projects](docs/RELATED_WORK.md) · [Changelog](CHANGELOG.md)

[MIT License](LICENSE) — use it, adapt it, and share it.
