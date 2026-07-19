# Agent Instructions

This repository is designed for long-running coding-agent work. The goal is not
to maximize raw code output. The goal is to leave the repository in a state
where the next session can continue without guessing.

This repository uses `my-harness` through v0.10.4. The harness is the control layer
agents touch; the app or target repository is what users touch.

Use the smallest process that safely proves the work. Tiny work must stay
lightweight. High-risk or external work must stop at the human gate unless a
valid scoped approval exists.

## Durable Artifacts

Older continuity templates may call these `feature_list.json`,
`claude-progress.md`, and `init.sh`. In this repository, the canonical files
are:

- `harness/features.json`: source of truth for feature status and evidence.
- `harness/progress.md`: session log, verified state, blockers, and next step.
- `scripts/init.sh` and `scripts/init.ps1`: startup/bootstrap paths.
- `scripts/harness.sh` and `scripts/harness.ps1`: CLI entrypoints.
- `session-handoff.md`: optional short handoff for unusually large sessions.
- `docs/INDEX.md`: map of durable docs and decision records.

Prefer durable repository artifacts over chat-only summaries.

## Current Verified Capability Surface

- v0.1: continuity package, manual lanes, progress/features state.
- v0.2: SQLite CLI for intake, story, evidence, trace, and query.
- v0.3: `run once` local orchestration with high-risk blocking.
- v0.4: schema migrations, adapter registry/run, and `check`.
- v0.5: adapter presets, prompt files, and executable discovery.
- v0.6: argv adapter execution and prompt templates.
- v0.7: adapter capability taxonomy and verification metadata.
- v0.8: `route`, skill/tool/capability resolver, human gate records, benchmarks.
- v0.9: `report final`, `complete`, evidence freshness, scoped approvals, and benchmark scores.
- v0.10: schema contracts, CLI contract tests, and `check`-level regression coverage.
- v0.10.1: npm launcher metadata, workspace-safe packaged execution, and
  historical tag install testing.
- v0.10.2: quieter launcher install checkout for annotated Git tags.
- v0.10.3: professional-review contract tests for adapter and route behavior.
- v0.10.4: harness-engineering adoption guidance, artifact-lifecycle routing,
  and release-readiness routing.

Update this section only after the capability exists in the repository and the
required verification has passed. Planned or aspirational work belongs in the
development plan, not here.

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

Before writing code:

1. Confirm the working directory:

   ```powershell
   pwd
   ```

2. Read `harness/progress.md` for the latest verified state and best next step.
3. Read `harness/features.json` and select the highest-priority unfinished
   feature, unless the user explicitly asks for a different task.
4. Review recent history:

   ```powershell
   git log --oneline -5
   ```

5. Initialize local state:

   ```powershell
   .\scripts\harness.ps1 init
   ```

   On POSIX:

   ```bash
   bash scripts/harness.sh init
   ```

6. Run the necessary smoke or end-to-end verification before starting new work:

   ```powershell
   .\scripts\harness.ps1 check --include-active --strict-active
   ```

   If the baseline verification fails, fix that first. Do not stack new feature
   work on top of a broken starting state.

7. Seed/check tools when routing or proof policy matters:

   ```powershell
   .\scripts\harness.ps1 tool seed
   ```

8. Route non-trivial work before implementing:

   ```powershell
   .\scripts\harness.ps1 route --json --summary "<task>" --work-type <type> --scope <scope> --risk <risk> --persist
   ```

9. Work on one active feature at a time unless the user explicitly asks for
   planning only.

## Standard Commands

Use top-level `--json` for machine-readable output when a command group does
not define its own subcommand-level `--json`.

```powershell
.\scripts\harness.ps1 check --include-active --strict-active
.\scripts\harness.ps1 --json query active
.\scripts\harness.ps1 bench run --json --fail-on-regression
```

Runner and adapter work:

```powershell
.\scripts\harness.ps1 run once --help
.\scripts\harness.ps1 adapter preset list
.\scripts\harness.ps1 adapter capability
```

Completion gates:

```powershell
.\scripts\harness.ps1 report final --json --story <story-id> --route-id <route-id> --persist
.\scripts\harness.ps1 complete --json --story <story-id> --route-id <route-id>
```

Human gates:

```powershell
.\scripts\harness.ps1 approval request --summary "<bounded action>" --risk critical --scope <scope> --ttl-minutes 60
.\scripts\harness.ps1 approval check --id <approval-id> --scope <scope> --fail-on-invalid
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

- A feature is not complete just because code was added.
- Target behavior must be implemented.
- Required verification must actually run.
- Evidence must be recorded in `harness/features.json`, `harness/progress.md`,
  or SQLite evidence state.
- The repository must still restart from the standard startup path.
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

## End Of Session

Before ending a significant session:

1. Update `harness/progress.md`.
2. Update `harness/features.json` when feature status or evidence changed.
3. Record unresolved risks or blockers.
4. Run the appropriate verification path, usually:

   ```powershell
   .\scripts\harness.ps1 check --include-active --strict-active
   ```

5. Commit with a descriptive message when the work is in a safe state.
6. Leave the repo clean enough that the next session can run the startup path
   immediately.

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
- Do not copy full Harness Engineering skill-tree ceremony into this repo.
- Do not commit runtime state such as `harness/harness.db`, `harness/runs/`, or
  generated prompts.
