# CLI

`my-harness` provides a small SQLite-backed CLI.

The CLI is intentionally narrow. It records intake, stories, evidence, traces,
active work, and single-task runner attempts. Guarded high-risk runs are
recorded but not executed without explicit approval.

v0.8 also adds the planned controller surface: route decisions, skill/capability
resolution, human approval records, and deterministic route benchmarks.

v0.9 adds final reports, completion gates, scoped approval expiry, and benchmark
scores.

## Start

Windows:

```powershell
.\scripts\harness.ps1 init
```

macOS/Linux:

```bash
bash scripts/harness.sh init
```

The default database is:

```text
harness/harness.db
```

This file is local runtime state and is ignored by git.

## Commands

```bash
harness init
harness check
harness intake add
harness story add
harness story update
harness evidence add
harness route
harness tool register
harness tool seed
harness approval request
harness approval resolve
harness approval check
harness bench run
harness report final
harness complete
harness adapter register
harness adapter list
harness adapter preset
harness adapter discover
harness adapter run
harness trace add
harness run once
harness query active
harness query intakes
harness query stories
harness query evidence
harness query traces
harness query runs
harness query adapters
harness query routes
harness query approvals
harness query benchmarks
harness query reports
```

Every command accepts `--json` at the top level:

```powershell
.\scripts\harness.ps1 --json query active
```

Run the standard checks:

```powershell
.\scripts\harness.ps1 check --include-active --strict-active
```

## Example

```powershell
.\scripts\harness.ps1 init

.\scripts\harness.ps1 intake add `
  --intent modify `
  --work-type feature `
  --scope module `
  --risk medium `
  --lane normal `
  --summary "Add CLI MVP"

.\scripts\harness.ps1 story add `
  --id MH-005 `
  --title "Implement CLI SQLite MVP" `
  --lane normal `
  --status in_progress

.\scripts\harness.ps1 evidence add `
  --kind smoke `
  --target cli `
  --result pass `
  --command ".\scripts\harness.ps1 query active" `
  --story MH-005
```

Runner example:

```powershell
.\scripts\harness.ps1 run once `
  --id MH-006 `
  --summary "Implement runner MVP" `
  --agent-command "python --version" `
  --verify-command "python -m py_compile cli\harness.py" `
  --work-type harness_improvement `
  --scope module `
  --risk low `
  --uncertainty low `
  --reversibility easy
```

Adapter example:

```powershell
.\scripts\harness.ps1 adapter register `
  --id mock-python `
  --provider mock `
  --command-template "python --version" `
  --availability present `
  --trust verified_local

.\scripts\harness.ps1 adapter run `
  --adapter mock-python `
  --id MH-007 `
  --summary "Validate adapter contract" `
  --prompt "Implement the requested task" `
  --verify-command "python -m py_compile cli/harness.py"
```

Prompt template example:

```powershell
.\scripts\harness.ps1 adapter run `
  --adapter mock-python `
  --id MH-009-TEMPLATE `
  --summary "Validate prompt template rendering" `
  --prompt-template templates\prompts\adapter-smoke.md `
  --var "task=Validate prompt template" `
  --var "context=v0.6 smoke" `
  --var "outcome=runner completes" `
  --verify-command "python -m py_compile cli/harness.py"
```

Preset and discovery example:

```powershell
.\scripts\harness.ps1 adapter preset all
.\scripts\harness.ps1 adapter discover --adapter mock-python
```

Route and capability example:

```powershell
.\scripts\harness.ps1 tool seed

.\scripts\harness.ps1 route --json `
  --summary "Fix parser bug" `
  --work-type bugfix `
  --scope module `
  --risk medium `
  --persist
```

Human gate example:

```powershell
.\scripts\harness.ps1 route --json `
  --summary "Irreversible external migration" `
  --intent execute `
  --work-type migration `
  --scope external_system `
  --reversibility irreversible `
  --risk critical

.\scripts\harness.ps1 approval request `
  --summary "Approve irreversible external migration" `
  --risk critical
```

Benchmark example:

```powershell
.\scripts\harness.ps1 bench run --json --fail-on-regression
```

Completion gate example:

```powershell
.\scripts\harness.ps1 report final --json `
  --story MH-011 `
  --route-id 5 `
  --persist

.\scripts\harness.ps1 complete --json `
  --story MH-011 `
  --route-id 5 `
  --residual-risk "none beyond local smoke" `
  --rollback "revert the change if checks regress"
```

## State Transition Safety

`story update` supports optimistic concurrency:

```powershell
.\scripts\harness.ps1 story update --id MH-005 --status verifying --expected-revision 1
```

If another process has already updated the story, the command fails instead of
silently overwriting newer state.
