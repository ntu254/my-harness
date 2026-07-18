# Agent Instructions

This repository uses `my-harness` through v0.9. The harness is the control
layer agents touch; the app or target repository is what users touch.

Use the smallest process that safely proves the work. Tiny work must stay
lightweight. High-risk or external work must stop at the human gate unless a
valid scoped approval exists.

## Current Capability Surface

- v0.1: continuity package, manual lanes, progress/features state.
- v0.2: SQLite CLI for intake, story, evidence, trace, and query.
- v0.3: `run once` local orchestration with high-risk blocking.
- v0.4: schema migrations, adapter registry/run, and `check`.
- v0.5: adapter presets, prompt files, and executable discovery.
- v0.6: argv adapter execution and prompt templates.
- v0.7: adapter capability taxonomy and verification metadata.
- v0.8: `route`, skill/tool/capability resolver, human gate records, benchmarks.
- v0.9: `report final`, `complete`, evidence freshness, scoped approvals, and benchmark scores.

## Request Classes

- Read-only: answer, explain, review, diagnose, plan, or status. Inspect only
  the needed files. Do not modify repository files.
- Change: build, fix, edit, refactor, write artifacts, or update harness state.
  Read continuity state, route the work, make a scoped change, verify it, and
  update progress/features when significant.
- Approval-required: deploy, release, publish, delete, force push, production
  migration, secret operation, external side effect, irreversible action, or
  critical risk. Stop for explicit human approval before execution unless a
  valid scoped approval is recorded and the command is bounded to that scope.

## Startup For Change Work

1. Confirm the repository root.
2. Read `harness/progress.md`.
3. Read `harness/features.json`.
4. Initialize local state:

   ```powershell
   .\harness\harness.ps1 init
   ```

5. Seed/check tools when routing or proof policy matters:

   ```powershell
   .\harness\harness.ps1 tool seed
   ```

6. Route non-trivial work before implementing:

   ```powershell
   .\harness\harness.ps1 route --json --summary "<task>" --work-type <type> --scope <scope> --risk <risk> --persist
   ```

7. Work on one active feature at a time unless the user explicitly asks for
   planning only.

## Standard Commands

Use top-level `--json` for machine-readable output when a command group does
not define its own subcommand-level `--json`.

```powershell
.\harness\harness.ps1 check --include-active --strict-active
.\harness\harness.ps1 --json query active
.\harness\harness.ps1 bench run --json --fail-on-regression
```

Runner and adapter work:

```powershell
.\harness\harness.ps1 run once --help
.\harness\harness.ps1 adapter preset list
.\harness\harness.ps1 adapter capability
```

Completion gates:

```powershell
.\harness\harness.ps1 report final --json --story <story-id> --route-id <route-id> --persist
.\harness\harness.ps1 complete --json --story <story-id> --route-id <route-id>
```

Human gates:

```powershell
.\harness\harness.ps1 approval request --summary "<bounded action>" --risk critical --scope <scope> --ttl-minutes 60
.\harness\harness.ps1 approval check --id <approval-id> --scope <scope> --fail-on-invalid
```

## Routing And Proof Policy

Routing produces the lane, workflow, skills, required capabilities, optional
capabilities, available tools, missing proof gaps, proof policy, and whether a
human gate is required.

- `proof_policy=pass`: required proof is available.
- `proof_policy=warn`: only optional proof is missing or skipped.
- `proof_policy=block`: required capability, approval, or proof is missing.

Missing required capability blocks completion. Missing optional capability can
produce weak proof, but high-risk work must not be completed with weak proof.

## Completion Rules

- Do not claim completion without verification evidence.
- Do not weaken tests to make work appear complete.
- Keep changes inside the selected request scope.
- Record blockers instead of hiding unfinished work.
- Use `report final` or `complete` for significant work once a route/story
  exists.
- Evidence is stale when git head or dirty state changes after evidence is
  recorded; stale evidence blocks completion unless explicitly allowed and
  explained as residual risk.
- Update `harness/progress.md` before ending significant change work.
- Keep `harness/features.json` truthful.

## Design And Craft Guidance

The development plan now includes Open Design inspired lessons, but do not copy
Open Design wholesale. For v1.0, use craft/rubric thinking lightly:

- Backend/tiny tasks should not load UI craft rules.
- UI/design tasks should consider state coverage, accessibility baseline,
  anti-AI-slop, typography, and form validation.
- Design taste is not proof unless tied to a rubric, screenshot/browser check,
  accessibility check, or human approval.

## Do Not

- Do not run deploy/release/delete/force-push/secret/external actions without a
  valid human gate.
- Do not introduce multi-agent orchestration before the single-agent core is
  stable.
- Do not copy full Open Design daemon/UI/plugin architecture into this repo.
- Do not commit runtime state such as `harness/harness.db`, `harness/runs/`, or
  generated prompts.
