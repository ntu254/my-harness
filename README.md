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

## What v0.1 Does Not Include

- No CLI.
- No SQLite.
- No multi-agent orchestration.
- No provider-specific build system.
- No live UI variant mode.

Those come after the manual loop proves useful on real work.

## Start

On Windows:

```powershell
.\harness\init.ps1
```

On macOS/Linux:

```bash
bash harness/init.sh
```

Then read:

1. `AGENTS.md`
2. `harness/progress.md`
3. `harness/features.json`
4. `docs/INTAKE.md`
5. The workflow doc that matches the request

## Completion Rule

A task is not complete just because files changed. Completion requires evidence
appropriate to the change surface and an updated handoff state.
