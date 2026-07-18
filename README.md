# my-harness

`my-harness` is a lightweight control layer for AI coding agents.

It helps agents classify work, select the right context, choose an appropriate
workflow, verify changes, and leave durable handoff state for the next session.

The v0.1 principle:

```text
Use the smallest process that safely proves the work.
```

v0.1 is intentionally manual: it proves the operating loop before adding CLI,
SQLite, or multi-agent automation.

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

## What v0.1 Deferred

- No multi-agent orchestration.
- No provider-specific build system.
- No live UI variant mode.

The CLI and SQLite state spine arrived in v0.2. Orchestration and provider
adapters come after the state spine proves useful on real work.

## Start

On Windows:

```powershell
.\harness\init.ps1
.\harness\harness.ps1 query active
.\harness\harness.ps1 run once --help
.\harness\harness.ps1 check --include-active --strict-active
```

On macOS/Linux:

```bash
bash harness/init.sh
bash harness/harness.sh query active
bash harness/harness.sh run once --help
bash harness/harness.sh check --include-active --strict-active
```

Then read:

1. `AGENTS.md`
2. `harness/progress.md`
3. `harness/features.json`
4. `docs/INTAKE.md`
5. `docs/RUNNER.md` when executing orchestrated local tasks
6. `docs/ADAPTERS.md` when registering Claude, Codex, or local adapters
7. `docs/CHECKS.md` before closing a version
8. The workflow doc that matches the request

## Completion Rule

A task is not complete just because files changed. Completion requires evidence
appropriate to the change surface and an updated handoff state.
