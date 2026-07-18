# my-harness

`my-harness` is a lightweight control layer for AI coding agents.

It helps agents classify work, select the right context, choose an appropriate
workflow, verify changes, and leave durable handoff state for the next session.

The core principle:

```text
Use the smallest process that safely proves the work.
```

The early versions kept the process deliberately small, then added state,
routing, adapters, gates, and contract tests only after the continuity loop was
proven.

## What v0.1 Includes

- Short `AGENTS.md` entrypoint.
- Manual request classification.
- Tiny, normal, high-risk, and approval-required lanes.
- Feature continuity state in `harness/features.json`.
- Verified session memory in `harness/progress.md`.
- Repeatable startup checks in `harness/init.ps1` and `harness/init.sh`.
- Documentation for context, workflows, verification, human gates, and quality.
- Templates for mini-specs, stories, decisions, validation reports, and
  high-risk story packets.

## What v0.2 Adds

- A small Python stdlib CLI.
- SQLite local state at `harness/harness.db`.
- Commands for intake, story, evidence, trace, and active-work queries.
- Optimistic story updates through expected revisions.

## What v0.3 Adds

- A `run once` orchestration command for one local task.
- Automatic lane classification from risk, scope, uncertainty, and reversibility.
- Guarded execution for `high_risk` and `approval_required` lanes.
- Runtime logs under ignored local state at `harness/runs/`.

## What v0.4 Adds

- Versioned schema migration loading from `state/schema/*.sql`.
- Agent adapter registration and execution through `adapter run`.
- A standard `harness check` command for startup, JSON, compile, whitespace, and active-queue gates.
- Adapter/tool registry state for future Claude and Codex integrations.

## What v0.5 Adds

- Provider adapter presets for `mock-python`, `codex-local`, and `claude-local`.
- Adapter executable discovery through `adapter discover`.
- Prompt-file rendering and `adapter run --prompt-file`.
- Safer template placeholders such as `{prompt_shell}` and `{prompt_file_shell}`.

## What v0.6 Adds

- Adapter `argv` command mode for shell-free execution where possible.
- Prompt template files with `adapter run --prompt-template` and `--var key=value`.
- Runtime recording of command mode and rendered argv.
- A reusable adapter smoke prompt template.

## What v0.7 Adds

- Adapter capability taxonomy.
- Capability queries through `adapter capability`.
- Verification metadata for adapter limits and modes.

## What v0.8 Adds

- Deterministic `route` command for workflow, skill, capability, and proof
  decisions.
- Tool capability registry and `tool seed`.
- Human approval request/resolve records.
- Route benchmark fixtures and `bench run`.

## What v0.9 Adds

- `report final` and `complete` completion gates.
- Evidence freshness checks tied to git head and dirty state.
- Required vs optional proof gaps.
- Scoped approval expiry and approval validation.
- Benchmark scores for quality, cost, adaptiveness, and durability.

## What v0.10 Adds

- JSON schema contracts for skills, benchmarks, route decisions, and final
  reports.
- `unittest` CLI contract tests that run against a temporary database.
- `harness check` now runs contract tests as part of the baseline.
- README/manifest alignment with the verified capability surface.

## Still Deferred

- No multi-agent orchestration.
- No real Codex/Claude provider conformance suite yet.
- No live UI variant mode.
- No installer/project-pack adoption command yet.
- No real agent-output benchmark scoring yet.

The CLI and SQLite state spine are in place. Provider adapters, multi-agent
orchestration, and live UI iteration come after the single-agent controller
contracts are stable.

## Start

On Windows:

```powershell
.\harness\init.ps1
.\harness\harness.ps1 query active
.\harness\harness.ps1 run once --help
.\harness\harness.ps1 check --include-active --strict-active
.\harness\harness.ps1 adapter preset list
python -m unittest discover -s tests -p "test_*.py"
```

On macOS/Linux:

```bash
bash harness/init.sh
bash harness/harness.sh query active
bash harness/harness.sh run once --help
bash harness/harness.sh check --include-active --strict-active
bash harness/harness.sh adapter preset list
python -m unittest discover -s tests -p "test_*.py"
```

Then read:

1. `AGENTS.md`
2. `harness/progress.md`
3. `harness/features.json`
4. `docs/INTAKE.md`
5. `docs/RUNNER.md` when executing orchestrated local tasks
6. `docs/ADAPTERS.md` when registering Claude, Codex, or local adapters
7. `docs/CHECKS.md` before closing a version
8. `docs/CONTRACTS.md` before changing public command output shapes
9. The workflow doc that matches the request

## Completion Rule

A task is not complete just because files changed. Completion requires evidence
appropriate to the change surface and an updated handoff state.
